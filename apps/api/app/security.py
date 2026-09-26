from fastapi import Request
from fastapi.responses import JSONResponse

from app.settings import settings


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def enforce_request_origin(request: Request, call_next):
    """Reject cross-site state changes before cookie-authenticated handlers run."""
    origin = request.headers.get("origin")
    if request.method not in SAFE_METHODS and origin:
        normalized_origin = origin.rstrip("/")
        allowed_origins = {configured.rstrip("/") for configured in settings.cors_origins}
        if normalized_origin not in allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"detail": "Request origin is not allowed"},
            )
    return await call_next(request)
