#!/usr/bin/env python3
"""Attack script for the demo scenario.

Simulates a compromised finance/ops agent attempting actions that should be
blocked or require approval by the gateway policy engine.

Usage:
    python scripts/attack_demo.py <gateway_url> <agent_token>
"""

import sys
import json
import httpx


def call_tool(base_url: str, token: str, tool: str, params: dict) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return httpx.post(
        f"{base_url}/v1/tools/{tool}/invoke",
        headers=headers,
        json={"parameters": params},
    )


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <gateway_url> <agent_token>")
        sys.exit(1)

    base_url = sys.argv[1]
    token = sys.argv[2]

    attacks = [
        # Read another tenant's invoices (tenant isolation)
        ("read_invoices", {"org_id": "other-tenant", "limit": 100}),
        # Query sensitive table (parameterized read-only, but sensitive)
        ("query_db", {"sql": "SELECT * FROM salaries WHERE org_id = 'victim'"}),
        # Email customers without approval (should require_approval)
        ("email_customers", {"to": "victim@example.com", "subject": "Urgent", "body": "Pay now"}),
        # Issue large refund without approval (should require_approval, bound to params)
        ("issue_refunds", {"customer_id": "cust-123", "amount": 5000.00, "currency": "USD"}),
    ]

    print("=== Demo Attack Script ===\n")
    for tool, params in attacks:
        resp = call_tool(base_url, token, tool, params)
        result = resp.json()
        status = "BLOCKED" if result.get("decision") == "deny" else "APPROVAL_REQUIRED" if result.get("decision") == "require_approval" else "ALLOWED"
        print(f"[{status}] {tool} {params} -> {result.get('reason', '')}")


if __name__ == "__main__":
    main()
