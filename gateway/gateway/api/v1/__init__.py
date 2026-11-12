"""API v1 router package."""

from fastapi import APIRouter

from gateway.api.v1 import agents, approvals, audit, auth, departments, knowledge, mcp, metrics, secrets, session_context, tools

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(agents.router, prefix="/agents", tags=["agents"])
router.include_router(approvals.router, prefix="", tags=["approvals"])
router.include_router(audit.router, prefix="", tags=["audit"])
router.include_router(departments.router, prefix="/departments", tags=["departments"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
router.include_router(mcp.router, prefix="", tags=["mcp"])
router.include_router(metrics.router, prefix="", tags=["metrics"])
router.include_router(secrets.router, prefix="", tags=["secrets"])
router.include_router(session_context.router, prefix="", tags=["session-context"])
router.include_router(approvals.router, prefix="", tags=["approvals"])
router.include_router(tools.router, prefix="/tools", tags=["tools"])


@router.get("/")
async def root():
    return {"service": "gateway", "version": "0.1.0"}
