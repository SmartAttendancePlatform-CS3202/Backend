from typing import Any, Dict


def get_current_user() -> Dict[str, Any]:
    return {"sub": "local-user", "role": "student"}
