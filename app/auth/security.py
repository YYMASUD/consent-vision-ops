"""Authentication & RBAC primitives (spec §18: OIDC/OAuth2, JWT, RBAC)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.common.enums import ROLE_SYSTEM_ADMIN
from app.common.utils import AppError, ForbiddenError
from app.config.settings import get_settings


@dataclass
class Principal:
    """Authenticated caller: human user or integration service."""

    subject_id: str
    roles: tuple[str, ...] = ()
    kind: str = "user"  # user | service
    metadata: dict = field(default_factory=dict)

    def has_any_role(self, roles: tuple[str, ...] | list[str]) -> bool:
        return bool(set(self.roles) & set(roles))


DEV_PRINCIPAL = Principal(subject_id="dev-admin", roles=(ROLE_SYSTEM_ADMIN,), kind="user")


class AuthenticationError(AppError):
    """Missing or invalid credentials."""

    status_code = 401


def _parse_api_key_registry() -> dict[str, list[str]]:
    """Parse ``api_keys`` JSON mapping of key -> [roles]."""
    settings = get_settings()
    raw = settings.api_keys or ""
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - config error
        raise AuthenticationError("api_keys setting is not valid JSON") from exc
    if not isinstance(parsed, dict):
        return {}
    return {str(k): [str(r) for r in v] for k, v in parsed.items()}


def principal_from_api_key(api_key: str | None) -> Principal | None:
    """Resolve a Principal from an API key, or None when unknown."""
    if not api_key:
        return None
    settings = get_settings()
    if settings.static_api_key and api_key == settings.static_api_key:
        return Principal(subject_id="static-api-key", roles=(ROLE_SYSTEM_ADMIN,), kind="service")
    registry = _parse_api_key_registry()
    roles = registry.get(api_key)
    if roles is not None:
        return Principal(subject_id=f"key:{api_key[:6]}", roles=tuple(roles), kind="service")
    return None


def principal_from_jwt(token: str | None) -> Principal | None:
    """Resolve a Principal from a JWT bearer token, or None when invalid."""
    if not token:
        return None
    settings = get_settings()
    try:
        import jwt  # PyJWT

        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False},
        )
    except Exception:
        return None
    roles = claims.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    return Principal(
        subject_id=str(claims.get("sub") or claims.get("preferred_username") or "jwt-user"),
        roles=tuple(str(r) for r in roles),
        kind=str(claims.get("kind") or "user"),
        metadata={"email": claims.get("email")},
    )


def require_roles(principal: Principal, allowed: tuple[str, ...] | list[str], action: str) -> None:
    """Raise ForbiddenError when the principal lacks every allowed role."""
    if not principal.has_any_role(allowed):
        raise ForbiddenError(
            f"role not permitted for {action}",
            details={"required_any_of": list(allowed), "granted": list(principal.roles)},
        )