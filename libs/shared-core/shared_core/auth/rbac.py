from __future__ import annotations

import os
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status

from shared_core.models.identity import User

from .jwt import get_current_user


def require_role(*allowed_roles: str) -> Callable:
    """Create a FastAPI dependency that allows only the listed roles."""

    normalized_roles = {role.lower() for role in allowed_roles}

    def role_checker(current_user: dict | User = Depends(get_current_user)) -> dict | User:
        user_role = current_user.get("role") if isinstance(current_user, dict) else current_user.role
        normalized_user_role = getattr(user_role, "value", user_role)

        if str(normalized_user_role).lower() not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(sorted(normalized_roles))}",
            )

        return current_user

    return role_checker


def verify_internal_key(
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
) -> None:
    """Require a valid shared internal API key for service-to-service calls."""

    expected = os.getenv("INTERNAL_API_KEY", "")
    if not expected or x_internal_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )
