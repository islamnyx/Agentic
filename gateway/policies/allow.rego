package gateway

# Default decisions: deny by default, no approval required unless a rule says so.
default allow = false
default deny = false
default require_approval = false

# The evaluated decision is exposed as data.gateway.decision
decision := "denied" {
    deny
}

decision := "require_approval" {
    require_approval
    not deny
}

decision := "allowed" {
    allow
    not deny
    not require_approval
}

# Reasons are exposed as data.gateway.reasons
reasons[reason] {
    deny
    reason := deny_reasons[_]
}

reasons[reason] {
    require_approval
    not deny
    reason := approval_reasons[_]
}

reasons[reason] {
    allow
    not deny
    not require_approval
    reason := "tool invocation permitted by policy"
}

# ---------------------------------------------------------------------------
# Allow rules
# ---------------------------------------------------------------------------

# Agent is allowed to invoke a tool when the tool name matches one of the
# agent's granted scopes and the invocation risk is not critical.
allow {
    input.who.agent.id != ""
    scope_allowed
    not critical_without_approval
}

scope_allowed {
    input.what.tool = input.who.agent.scopes[_]
}

# Explicit allow: low-risk reads are always permitted when scoped.
allow {
    input.who.agent.id != ""
    input.what.tool = input.who.agent.scopes[_]
    input.context.risk_level = "low"
}

# ---------------------------------------------------------------------------
# Deny rules
# ---------------------------------------------------------------------------

# Revoked or missing agent identity is denied.
deny {
    not input.who.agent.id
}

deny {
    input.who.agent.id == ""
}

# No matching scope for the requested tool.
deny {
    not scope_allowed
    not input.context.risk_level = "low"
}

# Critical risk invocations are always denied unless explicitly allowed above.
deny {
    input.context.risk_level = "critical"
}

# Web-sourced data labels on sensitive tool actions are denied.
deny {
    input.context.data_labels[_] = "web"
    input.what.action = "write"
}

# ---------------------------------------------------------------------------
# Require approval rules
# ---------------------------------------------------------------------------

# High-risk invocations require approval.
require_approval {
    input.context.risk_level = "high"
    not deny
}

# Customer-supplied data written to the system requires approval.
require_approval {
    input.context.data_labels[_] = "customer-supplied"
    input.what.action = "write"
    not deny
}

# Cross-organization resource access requires approval.
require_approval {
    input.on_what.tenant_id != ""
    input.on_what.tenant_id != input.who.org.id
    not deny
}

# ---------------------------------------------------------------------------
# Reason messages
# ---------------------------------------------------------------------------

deny_reasons[_] := "agent identity missing" {
    not input.who.agent.id
}

deny_reasons[_] := "no matching scope for tool " concat input.what.tool {
    not scope_allowed
    not input.context.risk_level = "low"
}

deny_reasons[_] := "critical risk invocations are denied" {
    input.context.risk_level = "critical"
}

deny_reasons[_] := "web-sourced data labels not permitted for write actions" {
    input.context.data_labels[_] = "web"
    input.what.action = "write"
}

approval_reasons[_] := "high risk invocation requires approval" {
    input.context.risk_level = "high"
}

approval_reasons[_] := "customer-supplied data write requires approval" {
    input.context.data_labels[_] = "customer-supplied"
    input.what.action = "write"
}

approval_reasons[_] := "cross-organization resource access requires approval" {
    input.on_what.tenant_id != ""
    input.on_what.tenant_id != input.who.org.id
}
