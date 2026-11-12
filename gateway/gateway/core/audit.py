"""Hash-chained audit service (Phase 5).

Writes audit entries chained via SHA-256 so that any tampering (editing,
deleting, reordering) breaks the chain and is detectable by the verify CLI.

Provides:
* append()  - append a new audit entry (auto-chains to previous)
* verify()  - verify the chain integrity, returns (ok, first_bad_sequence)
* export_json() - export all entries as JSON
* sign_root() - periodically sign the latest root hash with Ed25519
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.core.config import settings
from gateway.models.audit_entry import AuditEntry


class AuditChainError(Exception):
    """Raised when the audit chain is broken."""


class AuditService:
    """Hash-chained audit log service."""

    def __init__(self) -> None:
        self._signing_key: ed25519.Ed25519PrivateKey | None = None
        self._verify_key: ed25519.Ed25519PublicKey | None = None
        self._load_keys()

    def _load_keys(self) -> None:
        key_path = os.environ.get("AUDIT_SIGNING_KEY_PATH", "")
        if key_path and os.path.exists(key_path):
            with open(key_path, "rb") as f:
                self._signing_key = ed25519.Ed25519PrivateKey.from_private_bytes(
                    f.read()
                )
            self._verify_key = self._signing_key.public_key()
        else:
            # Dev/test fallback: ephemeral key (not persisted; verification
            # of signed roots only works within the same process).
            self._signing_key = ed25519.Ed25519PrivateKey.generate()
            self._verify_key = self._signing_key.public_key()

    async def _next_sequence(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(AuditEntry).order_by(AuditEntry.sequence.desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        return (last.sequence + 1) if last else 1

    async def _last_hash(self, db: AsyncSession) -> str:
        result = await db.execute(
            select(AuditEntry).order_by(AuditEntry.sequence.desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        return last.entry_hash if last else AuditEntry.genesis_hash()

    async def append(
        self,
        db: AsyncSession,
        action: str,
        actor_id: str | None = None,
        actor_type: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Append a new hash-chained audit entry."""
        sequence = await self._next_sequence(db)
        prev_hash = await self._last_hash(db)
        now = datetime.now(timezone.utc)
        timestamp_str = now.isoformat()
        details_str = json.dumps(details, sort_keys=True) if details else None

        entry_hash = AuditEntry.compute_hash(
            sequence=sequence,
            timestamp=timestamp_str,
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details_str,
            prev_hash=prev_hash,
        )

        entry = AuditEntry(
            sequence=sequence,
            timestamp=now,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details_str,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    async def verify(self, db: AsyncSession) -> tuple[bool, int | None]:
        """Verify the hash chain. Returns (ok, first_bad_sequence).

        ``first_bad_sequence`` is None when the chain is intact.
        """
        result = await db.execute(
            select(AuditEntry).order_by(AuditEntry.sequence.asc())
        )
        entries = list(result.scalars().all())

        expected_prev = AuditEntry.genesis_hash()
        for entry in entries:
            if entry.prev_hash != expected_prev:
                return False, entry.sequence
            timestamp_str = (
                entry.timestamp.isoformat()
                if hasattr(entry.timestamp, "isoformat")
                else str(entry.timestamp)
            )
            # SQLite strips tzinfo; treat naive timestamps as UTC.
            if entry.timestamp.tzinfo is None:
                timestamp_str = timestamp_str + "+00:00"
            recomputed = AuditEntry.compute_hash(
                sequence=entry.sequence,
                timestamp=timestamp_str,
                action=entry.action,
                actor_id=entry.actor_id,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                details=entry.details,
                prev_hash=entry.prev_hash,
            )
            if recomputed != entry.entry_hash:
                return False, entry.sequence
            expected_prev = entry.entry_hash
        return True, None

    async def export_json(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Export all audit entries as a list of dicts."""
        result = await db.execute(
            select(AuditEntry).order_by(AuditEntry.sequence.asc())
        )
        entries = list(result.scalars().all())
        out = []
        for e in entries:
            out.append(
                {
                    "id": e.id,
                    "sequence": e.sequence,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "action": e.action,
                    "actor_id": e.actor_id,
                    "actor_type": e.actor_type,
                    "resource_type": e.resource_type,
                    "resource_id": e.resource_id,
                    "details": json.loads(e.details) if e.details else None,
                    "prev_hash": e.prev_hash,
                    "entry_hash": e.entry_hash,
                    "signed_root": e.signed_root,
                    "signed_at": e.signed_at.isoformat() if e.signed_at else None,
                }
            )
        return out

    async def sign_root(self, db: AsyncSession) -> dict[str, str]:
        """Sign the latest audit root hash with Ed25519.

        Returns the signature (hex) and the signed root hash.
        """
        result = await db.execute(
            select(AuditEntry).order_by(AuditEntry.sequence.desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        if not last:
            return {"signed_root": "", "signature": "", "signed_at": ""}

        root_hash = last.entry_hash
        signature = self._signing_key.sign(root_hash.encode("utf-8"))
        sig_hex = signature.hex()
        now = datetime.now(timezone.utc)
        last.signed_root = root_hash
        last.signed_at = now
        await db.commit()
        await db.refresh(last)
        return {
            "signed_root": root_hash,
            "signature": sig_hex,
            "signed_at": now.isoformat(),
        }

    def verify_signature(self, root_hash: str, signature_hex: str) -> bool:
        """Verify an Ed25519 signature over a root hash."""
        try:
            self._verify_key.verify(
                bytes.fromhex(signature_hex), root_hash.encode("utf-8")
            )
            return True
        except Exception:
            return False

    def public_key_hex(self) -> str:
        """Return the Ed25519 public key as hex (for external verification)."""
        return self._verify_key.public_bytes_raw().hex()

    async def anchor_root(
        self,
        db: AsyncSession,
        anchor_service: AnchorService | None = None,
    ) -> dict[str, str]:
        """Sign the latest audit root and externally anchor it.

        Returns the signed root, signature, and anchor record (may be empty
        if anchoring is disabled or the anchor path is unwritable).
        """
        signed = await self.sign_root(db)
        if not signed["signed_root"]:
            return signed

        result = await db.execute(
            select(AuditEntry).order_by(AuditEntry.sequence.desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        audit_sequence = last.sequence if last else 0

        anchor_service = anchor_service or AnchorService()
        anchor = anchor_service.anchor_root(
            audit_sequence=audit_sequence,
            root_hash=signed["signed_root"],
            signature=signed["signature"],
        )
        return {
            "signed_root": signed["signed_root"],
            "signature": signed["signature"],
            "signed_at": signed["signed_at"],
            "anchor": anchor,
        }


class AnchorService:
    """Optional external hash anchoring.

    Writes each signed audit root to an append-only, hash-chained anchor log
    (one JSON object per line). Every anchor references the previous anchor's
    hash, so removing or reordering anchor lines is detectable. The anchor
    log lives outside the database, giving an external tamper-evident record.

    The anchor path is controlled by ``AUDIT_ANCHOR_PATH`` (defaults to
    ``./audit_anchors.log``). Anchoring is a no-op when the path is not
    configured, keeping this feature optional.
    """

    def __init__(self) -> None:
        self.path = Path(os.environ.get("AUDIT_ANCHOR_PATH", "audit_anchors.log"))

    def _load_last(self) -> tuple[int, str]:
        """Return (last_anchor_sequence, last_anchor_hash) from the log."""
        if not self.path.exists():
            return 0, hashlib.sha256(b"anchor-genesis").hexdigest()
        last_seq = 0
        last_hash = hashlib.sha256(b"anchor-genesis").hexdigest()
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                last_seq = int(obj.get("anchor_sequence", 0))
                last_hash = obj.get("anchor_hash", last_hash)
        return last_seq, last_hash

    def _compute_anchor_hash(
        self,
        anchor_sequence: int,
        timestamp: str,
        audit_sequence: int,
        root_hash: str,
        signature: str,
        prev_anchor_hash: str,
    ) -> str:
        canonical = json.dumps(
            {
                "anchor_sequence": anchor_sequence,
                "timestamp": timestamp,
                "audit_sequence": audit_sequence,
                "root_hash": root_hash,
                "signature": signature,
                "prev_anchor_hash": prev_anchor_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def anchor_root(
        self,
        audit_sequence: int,
        root_hash: str,
        signature: str,
    ) -> dict[str, Any]:
        """Append an anchor record for a signed audit root.

        Returns the anchor record dict. No-op (returns empty dict) when the
        anchor path cannot be written.
        """
        last_seq, prev_anchor_hash = self._load_last()
        anchor_sequence = last_seq + 1
        now = datetime.now(timezone.utc)
        timestamp_str = now.isoformat()
        anchor_hash = self._compute_anchor_hash(
            anchor_sequence=anchor_sequence,
            timestamp=timestamp_str,
            audit_sequence=audit_sequence,
            root_hash=root_hash,
            signature=signature,
            prev_anchor_hash=prev_anchor_hash,
        )
        record = {
            "anchor_sequence": anchor_sequence,
            "timestamp": timestamp_str,
            "audit_sequence": audit_sequence,
            "root_hash": root_hash,
            "signature": signature,
            "prev_anchor_hash": prev_anchor_hash,
            "anchor_hash": anchor_hash,
        }
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        except OSError:
            # Anchoring is optional; failure must not break the audit flow.
            return {}
        return record

    def verify_anchors(self) -> tuple[bool, int | None]:
        """Verify the anchor log chain. Returns (ok, first_bad_sequence)."""
        if not self.path.exists():
            return True, None
        expected_prev = hashlib.sha256(b"anchor-genesis").hexdigest()
        expected_seq = 1
        with self.path.open("r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    return False, lineno
                if int(obj.get("anchor_sequence", -1)) != expected_seq:
                    return False, lineno
                if obj.get("prev_anchor_hash") != expected_prev:
                    return False, lineno
                recomputed = self._compute_anchor_hash(
                    anchor_sequence=int(obj["anchor_sequence"]),
                    timestamp=obj["timestamp"],
                    audit_sequence=int(obj["audit_sequence"]),
                    root_hash=obj["root_hash"],
                    signature=obj["signature"],
                    prev_anchor_hash=obj["prev_anchor_hash"],
                )
                if recomputed != obj.get("anchor_hash"):
                    return False, lineno
                expected_prev = obj["anchor_hash"]
                expected_seq += 1
        return True, None
