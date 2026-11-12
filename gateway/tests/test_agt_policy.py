"""Tests for the Microsoft Agent Governance Toolkit reference policy engine.

AGT (`agent-governance-toolkit`) is not installed in this sandbox, so these
tests exercise the wrapper's fail-closed behavior and verdict mapping using a
mocked ACS ``AgentControl`` host API. They mirror the OPA policy tests in
``tests/test_phase2.py``.
"""

from unittest.mock import MagicMock, patch

import pytest

from gateway.core.agt_policy import (
    _AgtUnavailable,
    _build_agt_input,
    _load_agent_control,
    _verdict_to_decision,
    evaluate_policy,
)
from gateway.core.config import settings

# ---------------------------------------------------------------------------
# Import / availability
# ---------------------------------------------------------------------------


def test_load_agent_control_returns_unavailable_sentinel_when_agt_missing():
    """AGT is not installed; the loader returns a falsy sentinel, not a crash."""
    with patch(
        "gateway.core.agt_policy._load_agent_control",
        return_value=_AgtUnavailable(reason="no module named agent_control_specification"),
    ):
        result = _load_agent_control()
    assert isinstance(result, _AgtUnavailable)
    assert bool(result) is False


# ---------------------------------------------------------------------------
# Verdict mapping
# ---------------------------------------------------------------------------


def test_verdict_to_decision_allowed():
    verdict = MagicMock()
    verdict.verdict = "allow"
    decision = _verdict_to_decision(verdict, reasons=["agt policy verdict: allow"])
    assert decision.decision == "allowed"
    assert decision.allow is True
    assert decision.deny is False


def test_verdict_to_decision_denied():
    verdict = MagicMock()
    verdict.verdict = "deny"
    decision = _verdict_to_decision(verdict, reasons=["agt policy verdict: deny"])
    assert decision.decision == "denied"
    assert decision.deny is True
    assert decision.allow is False


def test_verdict_to_decision_require_approval():
    verdict = MagicMock()
    verdict.verdict = "require_approval"
    decision = _verdict_to_decision(verdict, reasons=["agt policy verdict: require_approval"])
    assert decision.decision == "require_approval"
    assert decision.require_approval is True


def test_verdict_to_decision_plain_string_verdict():
    """Verdict may arrive as a plain string rather than an object."""
    decision = _verdict_to_decision("DENY")
    assert decision.decision == "denied"


# ---------------------------------------------------------------------------
# AGT input mapping
# ---------------------------------------------------------------------------


def test_build_agt_input_maps_envelope_and_body():
    input_doc = {
        "who": {
            "agent": {"id": "a-1", "name": "finance-agent", "scopes": ["read_invoices"]},
            "owner": {"id": "u-1", "role": "user"},
            "org": {"id": "org-1"},
        },
        "what": {"tool": "read_invoices", "action": "read", "parameters": {"limit": 10}},
        "on_what": {"resource_type": None, "resource_id": None, "tenant_id": None},
        "context": {"session_id": "s-1", "risk_level": "low", "data_labels": ["internal"]},
    }
    mapped = _build_agt_input(input_doc)
    assert mapped["envelope"]["agent_id"] == "a-1"
    assert mapped["envelope"]["agent_name"] == "finance-agent"
    assert mapped["envelope"]["scopes"] == ["read_invoices"]
    assert mapped["envelope"]["org"] == "org-1"
    assert mapped["input"]["body"]["tool"] == "read_invoices"
    assert mapped["input"]["body"]["action"] == "read"
    assert mapped["input"]["body"]["parameters"] == {"limit": 10}
    assert mapped["input"]["context"]["risk_level"] == "low"


# ---------------------------------------------------------------------------
# evaluate_policy: AGT unavailable -> fail-closed deny
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_policy_agt_unavailable_deny():
    settings.POLICY_DRY_RUN = False
    try:
        with patch(
            "gateway.core.agt_policy._load_agent_control",
            return_value=_AgtUnavailable(reason="no module named agent_control_specification"),
        ):
            decision = await evaluate_policy(
                {
                    "who": {"agent": {"id": "a-1", "scopes": ["read_invoices"]}},
                    "what": {"tool": "read_invoices", "action": "read", "parameters": {}},
                    "on_what": {},
                    "context": {"risk_level": "low", "data_labels": ["internal"]},
                }
            )
        assert decision.decision == "denied"
        assert decision.deny is True
    finally:
        settings.POLICY_DRY_RUN = False


@pytest.mark.asyncio
async def test_evaluate_policy_agt_unavailable_dry_run_allows():
    previous = settings.POLICY_DRY_RUN
    settings.POLICY_DRY_RUN = True
    try:
        with patch(
            "gateway.core.agt_policy._load_agent_control",
            return_value=_AgtUnavailable(reason="no module named agent_control_specification"),
        ):
            decision = await evaluate_policy(
                {
                    "who": {"agent": {"id": "a-1", "scopes": ["read_invoices"]}},
                    "what": {"tool": "read_invoices", "action": "read", "parameters": {}},
                    "on_what": {},
                    "context": {"risk_level": "low", "data_labels": ["internal"]},
                }
            )
        assert decision.decision == "allowed"
        assert decision.allow is True
        assert "dry-run" in decision.reasons[0]
    finally:
        settings.POLICY_DRY_RUN = previous


# ---------------------------------------------------------------------------
# evaluate_policy: mocked AgentControl host API
# ---------------------------------------------------------------------------


class _FakeRuntime:
    """Stand-in for AGT's AgentControl runtime returned by from_path()."""

    def __init__(self, verdict, reasons=None):
        self.result = MagicMock()
        self.result.verdict = verdict
        self.result.reasons = reasons or []

    def evaluate(self, mode, payload):
        assert mode == "input"
        assert "envelope" in payload and "input" in payload
        return self.result

    def close(self):
        pass


def _make_agent_control(verdict, reasons=None):
    cls = MagicMock()
    instance = _FakeRuntime(verdict, reasons)
    cls.from_path.return_value = instance
    return cls


@pytest.mark.asyncio
async def test_evaluate_policy_agt_allow(monkeypatch):
    monkeypatch.setattr(
        "gateway.core.agt_policy._load_agent_control",
        lambda: _make_agent_control("allow"),
    )
    decision = await evaluate_policy(
        {
            "who": {
                "agent": {"id": "a-1", "name": "finance-agent", "scopes": ["read_invoices"]},
                "org": {"id": "org-1"},
            },
            "what": {"tool": "read_invoices", "action": "read", "parameters": {}},
            "on_what": {},
            "context": {"risk_level": "low", "data_labels": ["internal"]},
        }
    )
    assert decision.decision == "allowed"
    assert decision.allow is True


@pytest.mark.asyncio
async def test_evaluate_policy_agt_deny():
    with patch(
        "gateway.core.agt_policy._load_agent_control",
        return_value=_make_agent_control("deny", ["destructive op blocked"]),
    ):
        decision = await evaluate_policy(
            {
                "who": {"agent": {"id": "a-1", "scopes": ["drop_table"]}},
                "what": {"tool": "drop_table", "action": "write", "parameters": {}},
                "on_what": {},
                "context": {"risk_level": "critical", "data_labels": ["internal"]},
            }
        )
    assert decision.decision == "denied"
    assert decision.deny is True
    assert "destructive op blocked" in decision.reasons


@pytest.mark.asyncio
async def test_evaluate_policy_agt_require_approval():
    with patch(
        "gateway.core.agt_policy._load_agent_control",
        return_value=_make_agent_control("require_approval"),
    ):
        decision = await evaluate_policy(
            {
                "who": {"agent": {"id": "a-1", "scopes": ["issue_refunds"]}},
                "what": {"tool": "issue_refunds", "action": "write", "parameters": {"amount": 500}},
                "on_what": {},
                "context": {"risk_level": "high", "data_labels": ["internal"]},
            }
        )
    assert decision.decision == "require_approval"
    assert decision.require_approval is True


@pytest.mark.asyncio
async def test_evaluate_policy_agt_runtime_error_fail_closed():
    def _boom(from_path):
        raise RuntimeError("manifest not found")

    cls = MagicMock()
    cls.from_path.side_effect = _boom
    with patch(
        "gateway.core.agt_policy._load_agent_control",
        return_value=cls,
    ):
        settings.POLICY_DRY_RUN = False
        try:
            decision = await evaluate_policy(
                {
                    "who": {"agent": {"id": "a-1", "scopes": ["read_invoices"]}},
                    "what": {"tool": "read_invoices", "action": "read", "parameters": {}},
                    "on_what": {},
                    "context": {"risk_level": "low", "data_labels": ["internal"]},
                }
            )
        finally:
            settings.POLICY_DRY_RUN = False
    assert decision.decision == "denied"
    assert decision.deny is True
