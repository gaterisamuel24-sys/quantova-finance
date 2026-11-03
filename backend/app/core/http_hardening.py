"""HTTP hardening applied to every request: security headers, request ids, size limits.

These are plain ASGI middlewares (not BaseHTTPMiddleware) so they never buffer or
slow down responses, and they apply to every route, including ones added later.
"""

import logging
import re
import uuid
from contextvars import ContextVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "x-request-id"
# Incoming request ids (from a proxy or the frontend) are kept only if they look safe,
# so a client cannot inject newlines or huge values into our logs.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Interactive docs (development only) load Swagger UI from a CDN, so they are left out of
# the strict API Content-Security-Policy.
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

_BASE_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"cross-origin-resource-policy", b"same-site"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
]
# The API only ever returns data (JSON, CSV, PDF): nothing in a response may run or be framed.
_API_CSP = (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")
_HSTS = (b"strict-transport-security", b"max-age=31536000; includeSubDomains")


class SecurityHeadersMiddleware:
    """Security headers for every response.

    API paths get a policy that allows nothing to run. Other paths (the built frontend,
    served in production) get the frontend's own policy plus frame-ancestors 'none'.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        hsts: bool,
        api_prefix: str = "/api",
        frontend_csp: str | None = None,
    ) -> None:
        self.app = app
        self.hsts = hsts
        self.api_prefix = api_prefix.rstrip("/")
        self.frontend_csp = (
            (b"content-security-policy", f"{frontend_csp}; frame-ancestors 'none'".encode())
            if frontend_csp
            else None
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope.get("path", "")
        is_docs = path.startswith(_DOCS_PATHS)
        is_frontend = self.frontend_csp is not None and not (
            path == self.api_prefix or path.startswith(self.api_prefix + "/") or is_docs
        )

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                names = {name.lower() for name, _ in headers}
                extra = list(_BASE_HEADERS)
                if is_frontend and self.frontend_csp is not None:
                    # Caching for app files is set by the route (app/web.py).
                    extra.append(self.frontend_csp)
                elif not is_docs:
                    extra.append(_API_CSP)
                    # Financial data must never sit in a shared or browser cache.
                    if b"cache-control" not in names:
                        extra.append((b"cache-control", b"no-store"))
                if self.hsts:
                    extra.append(_HSTS)
                headers += [(name, value) for name, value in extra if name not in names]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestIdMiddleware:
    """Give every request an id, returned in X-Request-ID and included in error responses.

    When a user reports a problem, the id finds the matching server log lines.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = (
            dict(scope.get("headers", [])).get(REQUEST_ID_HEADER.encode(), b"").decode("latin-1")
        )
        request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        # Each request runs in its own task, with its own copy of this context variable, so it
        # is not reset afterwards: the error handler (outside this middleware) still reads it.
        request_id_var.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    *message.get("headers", []),
                    (REQUEST_ID_HEADER.encode(), request_id.encode()),
                ]
            await send(message)

        await self.app(scope, receive, send_with_id)


class BodySizeLimitMiddleware:
    """Refuse requests that declare a body larger than `max_bytes` (413), before reading it.

    CSV imports are the largest legitimate uploads (5 MB). The reverse proxy in production
    enforces the same limit for bodies sent without a Content-Length.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            declared = dict(scope.get("headers", [])).get(b"content-length")
            if declared is not None:
                try:
                    too_large = int(declared) > self.max_bytes
                except ValueError:
                    too_large = True  # a malformed length is refused too
                if too_large:
                    await _send_json(send, 413, b'{"detail":"The request is too large."}')
                    return
        await self.app(scope, receive, send)


async def _send_json(send: Send, status_code: int, body: bytes) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
