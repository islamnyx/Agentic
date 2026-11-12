"""Microsoft Agent Governance Toolkit (AGT) reference policy engine.

Reference implementation of an alternative policy decision point to the OPA
sidecar (gateway/core/opa.py). Implements the same
``evaluate_policy(input_doc) -> PolicyDecision`` interface so the invoke layer
can swap the decision engine by config without changes.

Backed by AGT's Agent Control Specification (ACS) host API
(``agent_control_specification.AgentControl``), documented in the AGT README:

    from agent_control_specification import AgentControl
    runtime = AgentControl.from_path("manifest.yaml")
    result = runtime.evaluate("input", {...})
    print(result.verdict)
    runtime.close()

AGT is intentionally **not** a hard dependency of the gateway: the package was
not resolvable in this sandbox, so AGT imports are lazy and degrade gracefully.
When AGT is unavailable, evaluation fails closed (deny) unless dry-run is on.

See adr/0002-agent-governance-toolkit-review.md for the full review.
"""

from typing import Any

from gateway.core.config import settings
from gateway.core.opa import PolicyDecision


class _AgtUnavailable:
    """Sentinel raised when the AGT package cannot be imported."""

    def __init__(self, reason: str):
        self.reason = reason

    def __bool__(self) -> bool:
        return False


def _load_agent_control() -> Any:
    """Lazily import AGT's ACS host API.

    Returns the ``AgentControl`` class, or an ``_AgtUnavailable`` sentinel
    when the package is not installed. Never raises at import time so the
    gateway can boot without AGT.
    """
    try:
        from agent_control_specification import AgentControl  # type: ignore
    except Exception as exc:  # pragma: no cover - AGT not installed in sandbox
        return _AgtUnavailable(reason=f"agent_control_specification not importable: {exc}")
    return AgentControl


def _build_agt_input(input_doc: dict[str, Any]) -> dict[str, Any]:
    """Map the normalized who/what/on_what/context input to AGT's ACS envelope.

    ACS ``runtime.evaluate("input", {...})`` expects:
      {
        "envelope": {"agent_id": "<id>"},
        "input": {"body": {"action": "...", "params": {...}}}
      }
    """
    who = input_doc.get("who", {}) or {}
    what = input_doc.get("what", {}) or {}
    agent = who.get("agent", {}) or {}

    return {
        "envelope": {
            "agent_id": agent.get("id", ""),
            "agent_name": agent.get("name", ""),
            "scopes": agent.get("scopes", []),
            "org": who.get("org", {}).get("id", ""),
            "owner_role": (who.get("owner") or {}).get("role"),
        },
        "input": {
            "body": {
                "tool": what.get("tool", ""),
                "action": what.get("action", ""),
                "parameters": what.get("parameters", {}),
            },
            "on_what": input_doc.get("on_what", {}) or {},
            "context": input_doc.get("context", {}) or {},
        },
    }


def _verdict_to_decision(verdict: Any, reasons: list[str] | None = None) -> PolicyDecision:
    """Convert an AGT verdict into a :class:`PolicyDecision`."""
    reasons = list(reasons or [])

    verdict_str = str(getattr(verdict, "verdict", verdict) or "").lower()
    if "deny" in verdict_str:
        decision = "denied"
        deny, allow, require_approval = True, False, False
    elif "approv" in verdict_str:
        decision = "require_approval"
        deny, allow, require_approval = False, False, True
    else:
        decision = "allowed"
        deny, allow, require_approval = False, True, False

    if not reasons:
        reasons = [f"agt policy verdict: {verdict_str or 'allowed'}"]

    return PolicyDecision(
        decision=decision,
        reasons=reasons,
        allow=allow,
        deny=deny,
        require_approval=require_approval,
        raw={"verdict": verdict_str},
    )


async def evaluate_policy(input_doc: dict[str, Any]) -> PolicyDecision:
    """Evaluate ``input_doc`` with AGT's ACS policy engine.

    Mirrors :func:`gateway.core.opa.evaluate_policy` so both engines share the
    ``PolicyDecision`` contract. Falls back to fail-closed deny when AGT is
    unreachable or not installed (unless :data:`settings.POLICY_DRY_RUN`).
    """
    AgentControl = _load_agent_control()
    if isinstance(AgentControl, _AgtUnavailable):
        if settings.POLICY_DRY_RUN:
            return PolicyDecision(
                decision="allowed",
                reasons=[f"dry-run: AGT unavailable ({AgentControl.reason}), call permitted"],
                allow=True,
                deny=False,
                require_approval=False,
            )
        return PolicyDecision(
            decision="denied",
            reasons=[f"AGT policy engine unavailable: {AgentControl.reason}"],
            allow=False,
            deny=True,
            require_approval=False,
        )

    agt_input = _build_agt_input(input_doc)
    runtime: Any = None
    try:
        # AGT SDK is sync; run the blocking evaluate in the default executor
        # so the async FastAPI route is not blocked.
        import asyncio

        def _eval() -> Any:
            nonlocal runtime
            runtime = AgentControl.from_path(settings.AGT_POLICY_MANIFEST)
            result = runtime.evaluate("input", agt_input)
            return result

        result = await asyncio.get_event_loop().run_in_executor(None, _eval)
        verdict = getattr(result, "verdict", None)
        reasons = getattr(result, "reasons", None) or []
        return _verdict_to_decision(verdict, reasons)
    except Exception as exc:  # pragma: no cover - AGT runtime failure
        if settings.POLICY_DRY_RUN:
            return PolicyDecision(
                decision="allowed",
                reasons=[f"dry-run: AGT evaluation error ({exc}), call permitted"],
                allow=True,
                deny=False,
                require_approval=False,
            )
        return PolicyDecision(
            decision="denied",
            reasons=[f"AGT policy evaluation error: {exc}"],
            allow=False,
            deny=True,
            require_approval=False,
        )
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except Exception:  # pragma: no cover - best effort cleanup
                pass
