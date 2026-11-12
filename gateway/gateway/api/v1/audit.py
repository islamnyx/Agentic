"""Audit log routes (Phase 5).

Hash-chained, tamper-evident audit log with verification and JSON export.
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.api.deps import get_current_agent, get_db
from gateway.core.audit import AnchorService, AuditService
from gateway.models.audit_entry import AuditEntry
from gateway.schemas.approval import ApprovalList  # noqa: F401  (kept for consistency)

router = APIRouter()

_audit_service = AuditService()


@router.post("/audit/append", status_code=status.HTTP_201_CREATED)
async def append_audit_entry(
    body: dict[str, Any],
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Append a new hash-chained audit entry."""
    entry = await _audit_service.append(
        db=db,
        action=body.get("action", "unknown"),
        actor_id=current_agent.id,
        actor_type="agent",
        resource_type=body.get("resource_type"),
        resource_id=body.get("resource_id"),
        details=body.get("details"),
    )
    return {
        "id": entry.id,
        "sequence": entry.sequence,
        "entry_hash": entry.entry_hash,
        "prev_hash": entry.prev_hash,
    }


@router.get("/audit/verify")
async def verify_audit_chain(
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Verify the hash chain integrity. Returns (ok, first_bad_sequence)."""
    ok, first_bad = await _audit_service.verify(db)
    return {"ok": ok, "first_bad_sequence": first_bad}


@router.get("/audit/export")
async def export_audit_log(
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Export the full audit log as JSON."""
    entries = await _audit_service.export_json(db)
    return {"entries": entries, "count": len(entries)}


@router.post("/audit/sign-root")
async def sign_audit_root(
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Sign the latest audit root hash with Ed25519."""
    return await _audit_service.sign_root(db)


@router.get("/audit/public-key")
async def get_audit_public_key(
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Return the Ed25519 public key (hex) for external verification."""
    return {"public_key": _audit_service.public_key_hex()}


@router.post("/audit/anchor-root")
async def anchor_audit_root(
    current_agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Sign the latest audit root and externally anchor it to the append-only
    anchor log (``AUDIT_ANCHOR_PATH``). Returns the signed root, signature,
    and anchor record."""
    return await _audit_service.anchor_root(db, AnchorService())
