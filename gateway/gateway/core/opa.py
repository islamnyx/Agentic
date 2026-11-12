"""Open Policy Agent client for the governance gateway (Phase 2+6).

Evaluates the normalized policy input (who/what/on_what/context) against the
Rego policies loaded in the OPA sidecar and returns a structured decision.

Phase 6 adds session-aware rule evaluation for trust label propagation.
"""

from typing import Any

import httpx

from gateway.core.config import settings
from gateway.core.session_context import get_session_context_service


class PolicyDecision:
    """Structured result of an OPA policy evaluation."""

    def __init__(
        self,
        decision: str,
        reasons: list[str],
        allow: bool,
        deny: bool,
        require_approval: bool,
        raw: dict[str, Any] | None = None,
    ):
        self.decision = decision  # "allowed" | "denied" | "require_approval"
        self.reasons = reasons
        self.allow = allow
        self.deny = deny
        self.require_approval = require_approval
        self.raw = raw or {}

    def __repr__(self) -> str:
        return f"PolicyDecision(decision={self.decision!r}, reasons={self.reasons})"


async def _evaluate_opa(input_doc: dict[str, Any]) -> PolicyDecision:
    """Send `input_doc` to OPA and return the evaluated decision.

    Falls back to a safe deny decision if OPA is unreachable.
    """
    url = f"{settings.OPA_URL}{settings.OPA_POLICY_PATH}"
    payload = {"input": input_doc}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json().get("result", {})
    except Exception:
        # OPA unreachable: fail closed (deny) unless dry-run is on.
        if settings.POLICY_DRY_RUN:
            return PolicyDecision(
                decision="allowed",
                reasons=["dry-run: OPA unreachable, call permitted"],
                allow=True,
                deny=False,
                require_approval=False,
            )
        return PolicyDecision(
            decision="denied",
            reasons=["OPA policy engine unreachable"],
            allow=False,
            deny=True,
            require_approval=False,
        )

    allow = bool(result.get("allow"))
    deny = bool(result.get("deny"))
    require_approval = bool(result.get("require_approval"))
    decision = result.get("decision")
    if not decision:
        if deny:
            decision = "denied"
        elif require_approval:
            decision = "require_approval"
        elif allow:
            decision = "allowed"
        else:
            decision = "denied"
    reasons = result.get("reasons", []) or []
    if isinstance(reasons, str):
        reasons = [reasons]

    return PolicyDecision(
        decision=decision,
        reasons=reasons,
        allow=allow,
        deny=deny,
        require_approval=require_approval,
        raw=result,
    )


async def evaluate_policy(input_doc: dict[str, Any]) -> PolicyDecision:
    """Evaluate policy with OPA + session-aware rules.

    If input contains session_id, also evaluates session-aware rules
    (trust label propagation, untrusted -> external send -> require_approval).
    """
    # First, evaluate base OPA policy
    opa_decision = await _evaluate_opa(input_doc)

    # If OPA already denies, return immediately (fail closed)
    if opa_decision.deny:
        return opa_decision

    # Check for session-aware rules
    session_id = input_doc.get("context", {}).get("session_id")
    if not session_id:
        return opa_decision

    # Import here to avoid circular import
    from gateway.db.session import AsyncSessionLocal
    from gateway.models.session_context import SessionAwareRule, SessionContext, TrustLabel
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        session_service = get_session_context_service()
        session_result = await session_service.evaluate_session_rules(
            db=db,
            session_id=session_id,
            tool=input_doc.get("what", {}).get("tool", ""),
            action=input_doc.get("what", {}).get("action", ""),
            resource_type=input_doc.get("on_what", {}).get("resource_type", ""),
        )

        if session_result:
            session_action, session_reasons = session_result
            # Session rules can escalate: require_approval overrides allow
            if session_action == "deny":
                return PolicyDecision(
                    decision="denied",
                    reasons=opa_decision.reasons + session_reasons,
                    allow=False,
                    deny=True,
                    require_approval=False,
                )
            elif session_action == "require_approval":
                if opa_decision.decision == "allowed":
                    return PolicyDecision(
                        decision="require_approval",
                        reasons=opa_decision.reasons + session_reasons,
                        allow=False,
                        deny=False,
                        require_approval=True,
                    )
            # "allow" from session rules is redundant since OPA already allowed

    return opa_decision