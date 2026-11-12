package gateway

# ---------------------------------------------------------------------------
# Knowledge ACL policies (Company Brain per-item read/write enforcement)
# ---------------------------------------------------------------------------

# A sales agent (or any agent) cannot read HR/finance knowledge items unless
# an explicit ACL grant exists for the item. Enforced via data_labels and
# resource_type/tenant in the policy input.
#
# input.on_what.resource_type = "knowledge_item"
# input.on_what.resource_id   = <knowledge item id>
# input.context.data_labels   = ["internal", "customer-supplied", "web"]

# Reading a confidential knowledge item without an ACL grant is denied.
deny {
    input.on_what.resource_type = "knowledge_item"
    input.context.data_labels[_] = "internal"
    not knowledge_access_granted("read")
}

# Writing to a knowledge item requires an ACL grant.
deny {
    input.on_what.resource_type = "knowledge_item"
    input.what.action = "write"
    not knowledge_access_granted("write")
}

# Reading HR/finance category items is denied unless explicitly granted.
deny {
    input.on_what.resource_type = "knowledge_item"
    input.context.data_labels[_] = "internal"
    input.what.parameters.category = "hr"
    not knowledge_access_granted("read")
}

deny {
    input.on_what.resource_type = "knowledge_item"
    input.context.data_labels[_] = "internal"
    input.what.parameters.category = "finance"
    not knowledge_access_granted("read")
}

# ---------------------------------------------------------------------------
# Knowledge ACL helpers
# ---------------------------------------------------------------------------

# knowledge_access_granted(permission) is true when the agent/org has an ACL
# grant for the target knowledge item. The grant information is expected to be
# present in the policy input context via on_what.resource_id; the gateway
# resolves the actual ACL from Postgres before calling OPA so this helper reads
# the resolved grant from input context when available.
knowledge_access_granted(permission) {
    input.context.data_labels[_] = "internal"
    input._grants[_] = permission
}

knowledge_access_granted(permission) {
    not input.context.data_labels[_] = "internal"
    input._grants[_] = permission
}

# ---------------------------------------------------------------------------
# Knowledge ACL reasons
# ---------------------------------------------------------------------------

deny_reasons[_] := "knowledge item read not permitted by ACL" {
    input.on_what.resource_type = "knowledge_item"
    input.context.data_labels[_] = "internal"
    not knowledge_access_granted("read")
}

deny_reasons[_] := "knowledge item write not permitted by ACL" {
    input.on_what.resource_type = "knowledge_item"
    input.what.action = "write"
    not knowledge_access_granted("write")
}

approval_reasons[_] := "confidential knowledge access requires approval" {
    input.on_what.resource_type = "knowledge_item"
    input.context.data_labels[_] = "internal"
    knowledge_access_granted("read")
    input.context.risk_level = "high"
}
