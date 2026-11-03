"""The last line of defence for errors nobody anticipated.

An unexpected exception becomes a plain 500 response with a request id and nothing
else: no stack trace, SQL, file paths or library versions reach the client. The full
details are logged on the server under the same request id.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.http_hardening import REQUEST_ID_HEADER, request_id_var

logger = logging.getLogger("app.errors")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_var.get()
    logger.exception(
        "Unhandled error (request_id=%s, method=%s, path=%s)",
        request_id,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Something went wrong on our side. Please try again.",
            "request_id": request_id,
        },
        headers={
            REQUEST_ID_HEADER: request_id,
            "cache-control": "no-store",
            "x-content-type-options": "nosniff",
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, unhandled_exception_handler)
