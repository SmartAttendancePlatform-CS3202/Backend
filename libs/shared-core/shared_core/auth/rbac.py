from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

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
