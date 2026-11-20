"""FastAPI auth dependencies."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request

from app.auth.security import (
    DEV_PRINCIPAL,
    AuthenticationError,
    Principal,
    principal_from_api_key,
    principal_from_jwt,
    require_roles,
)
from app.config.settings import get_settings


async def get_principal(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> Principal:
    """Resolve the caller from API key or bearer JWT (spec §18)."""
    settings = get_settings()

    principal = principal_from_api_key(x_api_key)
    if principal is None and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            principal = principal_from_jwt(token.strip())

    if principal is not None:
        request.state.principal = principal
        return principal

    if settings.auth_disabled:
        request.state.principal = DEV_PRINCIPAL
        return DEV_PRINCIPAL

    raise HTTPException(
        status_code=AuthenticationError.status_code,
        detail={"error": "authentication required", "hint": "supply X-API-Key or Bearer token"},
    )


def roles_required(*roles: str):
    """Dependency factory enforcing that the caller holds one of ``roles``."""

    async def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        try:
            require_roles(principal, roles, "this endpoint")
        except Exception as exc:  # ForbiddenError -> 403
            status = getattr(exc, "status_code", 403)
            raise HTTPException(
                status_code=status,
                detail={"error": str(exc), "required_any_of": list(roles)},
            ) from exc
        return principal

    return _dep