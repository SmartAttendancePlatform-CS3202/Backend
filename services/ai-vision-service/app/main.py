from fastapi import Depends, FastAPI

from shared_core.auth.rbac import verify_internal_key

from app.routers import verify

app = FastAPI(title="AI Vision Service")

app.include_router(verify.router, dependencies=[Depends(verify_internal_key)])


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-vision-service"}
