"""Serve the built frontend from the API in production, so both share one origin.

One origin means the refresh cookie (SameSite=Strict) works, production needs no CORS,
and the frontend's security headers are sent by this server rather than a meta tag.

- /assets/* are content-hashed by Vite, so they are cached for a year.
- Every other path that is not a real file gets index.html (the app's own router
  handles it). Unknown /api/... paths still get the API's JSON 404.
- Paths are resolved and checked, so ../ tricks can never read files outside the folder.
- When the public website lives on another address (Vercel, which forwards /api here),
  people who open this server's own address are redirected there, so the app has one
  public home and search engines don't index two copies.
"""

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse, Response

CSP_FILE = "content-security-policy.txt"
IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"  # always check for a new version (index.html changes every deploy)
# Build outputs that exist for the server's use, not for browsers.
NOT_SERVED = frozenset({CSP_FILE})


def read_frontend_csp(dist: Path) -> str | None:
    """The Content Security Policy the frontend build wrote, if there is one."""
    policy_file = dist / CSP_FILE
    if not policy_file.is_file():
        return None
    return policy_file.read_text(encoding="utf-8").strip()


def mount_frontend(
    app: FastAPI, dist: Path, *, api_prefix: str, public_base_url: str | None = None
) -> None:
    """Add the catch-all route that serves the app. Call after the API routes are added.

    `public_base_url` is the website's public address (APP_BASE_URL in production). App
    pages requested on any other host are redirected there; API routes never are.
    """
    root = dist.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"FRONTEND_DIST_DIR has no index.html: {root}")
    api_path = api_prefix.strip("/") + "/"
    public = urlsplit(public_base_url) if public_base_url else None

    @app.get("/{path:path}", include_in_schema=False)
    # Annotated as Response so FastAPI doesn't try to build a JSON schema from it.
    async def frontend(path: str, request: Request) -> Response:
        if path.startswith(api_path) or path == api_path.rstrip("/"):
            # An API address that matched no route: JSON 404, never the app's HTML.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
        if public is not None and request.url.netloc != public.netloc:
            # Only the path and query are kept; the host always comes from settings, so a
            # crafted Host header can never redirect someone to another site.
            target = f"{public.scheme}://{public.netloc}/{path}"
            if request.url.query:
                target += f"?{request.url.query}"
            return RedirectResponse(target, status_code=status.HTTP_308_PERMANENT_REDIRECT)

        candidate = (root / path).resolve()
        is_inside = candidate.is_relative_to(root)
        if path and is_inside and candidate.is_file() and candidate.name not in NOT_SERVED:
            cache = IMMUTABLE if candidate.parent.name == "assets" else REVALIDATE
            return FileResponse(candidate, headers={"cache-control": cache})
        return FileResponse(index, headers={"cache-control": REVALIDATE})
