from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import Depends, Header, HTTPException, status

from shared_core.config import get_settings
from shared_core.models.identity import User

from .jwt import get_current_user


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

def verify_internal_key(x_internal_key: str = Header(...)):
    settings = get_settings()
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )
