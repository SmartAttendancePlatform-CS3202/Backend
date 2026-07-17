from typing import Any, Dict


def verify_internal_key() -> Dict[str, Any]:
    return {"ok": True}


def require_role(*roles: str):
    def dependency() -> Dict[str, Any]:
        return {"roles": list(roles)}

    return dependency
