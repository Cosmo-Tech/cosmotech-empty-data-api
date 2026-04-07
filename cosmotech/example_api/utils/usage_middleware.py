import time
from typing import Callable

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from cosmotech.example_api.utils.logging import LOGGER


def _extract_user_from_token(authorization: str | None) -> tuple[str, str] | None:
    """
    Extract user_id (sub) and user_name (name) from a Bearer token header.
    Does NOT re-validate the token — the route handler already did that.
    Returns None if the header is missing or the token cannot be decoded.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    try:
        # Decode without verification — we only need the claims, not security checks
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub", "unknown")
        user_name = payload.get("name", "unknown")
        return user_id, user_name
    except Exception:
        return None


def _get_matched_route(request: Request) -> str:
    """Return the matched route pattern from the request scope, e.g. '/value_framework/{value_framework_id}'."""
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", request.url.path)
    return request.url.path


class UsageMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records API usage per authenticated user per endpoint.
    Only requests carrying a valid Bearer token (i.e. authenticated routes) are recorded.
    The record is written asynchronously after the response is sent.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        authorization = request.headers.get("Authorization")
        user_info = _extract_user_from_token(authorization)

        # Only record authenticated requests
        if user_info is None:
            return response

        user_id, user_name = user_info
        method = request.method
        endpoint = request.url.path
        route = _get_matched_route(request)
        status_code = response.status_code

        # Write the record in a background task to avoid blocking the response
        async def _record():
            try:
                from cosmotech.example_api.schema import get_session
                from cosmotech.example_api.schema.api_usage import ApiUsage

                for session in get_session():
                    record = ApiUsage(
                        user_id=user_id,
                        user_name=user_name,
                        method=method,
                        endpoint=endpoint,
                        route=route,
                        status_code=status_code,
                        response_time_ms=elapsed_ms,
                    )
                    session.add(record)
                    session.commit()
            except Exception as e:
                LOGGER.warning(f"Failed to record API usage: {e}")

        import asyncio

        asyncio.ensure_future(_record())

        return response
