package gateway

# ---------------------------------------------------------------------------
# Department-scoped policies
# ---------------------------------------------------------------------------

# Cross-department agent calls require explicit approval.
# An agent invoking a tool against a resource owned by a different department
# (tenant) must be approved.
require_approval {
    input.on_what.tenant_id != ""
    input.on_what.tenant_id != input.who.org.id
    not deny
}

# An agent operating outside its own organization is denied unless scoped.
deny {
    input.on_what.tenant_id != ""
    input.on_what.tenant_id != input.who.org.id
    input.context.risk_level = "high"
}

# ---------------------------------------------------------------------------
# Department-scoped reasons
# ---------------------------------------------------------------------------

deny_reasons[_] := "cross-department high-risk call denied" {
    input.on_what.tenant_id != ""
    input.on_what.tenant_id != input.who.org.id
    input.context.risk_level = "high"
}

approval_reasons[_] := "cross-department call requires explicit approval" {
    input.on_what.tenant_id != ""
    input.on_what.tenant_id != input.who.org.id
    not deny
}
