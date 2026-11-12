"""Governance gateway for business AI agents."""

from fastapi import FastAPI, Request

from gateway.api.v1 import router as v1_router
from gateway.core.observability import record_request, setup_observability

app = FastAPI(title="Governance Gateway", version="0.1.0")

setup_observability(app)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    response = await call_next(request)
    record_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response


app.include_router(v1_router, prefix="/v1")
