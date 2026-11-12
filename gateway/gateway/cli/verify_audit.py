"""Verify CLI for the hash-chained audit log.

Usage:
    python -m gateway.cli.verify_audit [--db-url URL] [--export PATH]
                                       [--anchor] [--verify-anchors]

Detects tampering in the audit log by recomputing and comparing hashes.
Optionally anchors the latest signed root to the external append-only anchor
log and/or verifies the anchor log chain.
"""

import argparse
import asyncio
import json
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from gateway.db.session import Base
from gateway.models.audit_entry import AuditEntry  # noqa: F401  (register model)
from gateway.core.audit import AnchorService, AuditService


async def _run(
    db_url: str,
    export_path: str | None,
    anchor: bool,
    verify_anchors: bool,
) -> int:
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        service = AuditService()
        ok, first_bad = await service.verify(session)
        print(f"audit chain: {'OK' if ok else 'BROKEN'}")
        if not ok:
            print(f"first bad sequence: {first_bad}")

        if anchor:
            result = await service.anchor_root(session, AnchorService())
            print(
                f"anchor: signed_root={result.get('signed_root','')[:16]}... "
                f"anchor_written={bool(result.get('anchor'))}"
            )

        if verify_anchors:
            a_ok, a_bad = AnchorService().verify_anchors()
            print(f"anchor chain: {'OK' if a_ok else 'BROKEN'}")
            if not a_ok:
                print(f"first bad anchor line: {a_bad}")
                ok = False

        if export_path:
            entries = await service.export_json(session)
            with open(export_path, "w") as f:
                json.dump(entries, f, indent=2)
            print(f"exported {len(entries)} entries to {export_path}")

    await engine.dispose()
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify hash-chained audit log")
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./audit.db"),
    )
    parser.add_argument("--export", default=None, help="Export audit log to JSON file")
    parser.add_argument(
        "--anchor",
        action="store_true",
        help="Sign and externally anchor the latest audit root",
    )
    parser.add_argument(
        "--verify-anchors",
        action="store_true",
        help="Verify the external anchor log chain",
    )
    args = parser.parse_args()
    return asyncio.run(
        _run(args.db_url, args.export, args.anchor, args.verify_anchors)
    )


if __name__ == "__main__":
    sys.exit(main())
