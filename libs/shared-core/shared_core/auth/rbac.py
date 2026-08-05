from __future__ import annotations

import os
from collections.abc import Callable, Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from shared_core.models.identity import User

from .jwt import get_current_user

# Shown in Swagger "Authorize" for service-to-service routes (ai-vision).
internal_api_key_header = APIKeyHeader(
    name="X-Internal-Key",
    auto_error=False,
    scheme_name="InternalApiKey",
    description="Shared INTERNAL_API_KEY from service .env (service-to-service only).",
)


def require_role(*allowed_roles: str | Iterable[str]) -> Callable:
    """Create a FastAPI dependency that allows only the listed roles."""

    flattened_roles: list[str] = []
    for role in allowed_roles:
        if isinstance(role, str):
            flattened_roles.append(role)
        else:
            flattened_roles.extend(str(item) for item in role)

    normalized_roles = {role.lower() for role in flattened_roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = getattr(current_user.role, "value", current_user.role)

        if str(user_role).lower() not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(sorted(normalized_roles))}",
            )

        return current_user

    return role_checker


def verify_internal_key(
    x_internal_key: str | None = Depends(internal_api_key_header),
) -> None:
    """Require a valid shared internal API key for service-to-service calls."""

    expected = os.getenv("INTERNAL_API_KEY", "")
    if not expected or x_internal_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )
