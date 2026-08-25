from __future__ import annotations

from collections.abc import Callable, Iterable
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from shared_core.config import get_settings
from shared_core.models.identity import User
from .jwt import get_current_user

internal_api_key_header = APIKeyHeader(
    name="X-Internal-Key",
    auto_error=False,
    scheme_name="InternalApiKey",
    description="Internal service credential; never expose it to clients.",
)


def require_role(*allowed_roles: str | Iterable[str]) -> Callable:
    flattened: list[str] = []
    for role in allowed_roles:
        flattened.extend([role] if isinstance(role, str) else [str(x) for x in role])
    allowed = {x.lower() for x in flattened}

    def checker(user: User = Depends(get_current_user)) -> User:
        role = str(getattr(user.role, "value", user.role)).lower()
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return checker


def verify_internal_key(x_internal_key: str | None = Depends(internal_api_key_header)) -> None:
    expected = get_settings().internal_api_key
    if not expected or x_internal_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing internal API key")
