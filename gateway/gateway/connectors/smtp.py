"""SMTP email connector (Phase 3)."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Any

from gateway.connectors.base import ConnectorBase, ConnectorError


class SmtpConnector(ConnectorBase):
    """SMTP email connector.

    Config keys:
      host, port: SMTP server (default port 587)
      from_email: default sender address
      use_tls: whether to use STARTTLS (default True)

    The ``secret`` injected by the broker is used as the SMTP password.
    """

    connector_type = "smtp"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = int(self.config.get("port", 587))
        self.from_email = self.config.get("from_email", "gateway@example.com")
        self.use_tls = bool(self.config.get("use_tls", True))

    def validate_params(self, params: dict[str, Any]) -> None:
        for field in ("to", "subject", "body"):
            if not params.get(field):
                raise ConnectorError(f"SMTP connector requires a '{field}' parameter")

    async def _run(
        self, params: dict[str, Any], secret: str | None = None
    ) -> dict[str, Any]:
        def _send() -> dict[str, Any]:
            msg = EmailMessage()
            msg["From"] = params.get("from_email", self.from_email)
            msg["To"] = params["to"]
            msg["Subject"] = params["subject"]
            msg.set_content(params["body"])
            if params.get("html"):
                msg.add_alternative(params["html"], subtype="html")

            with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
                if self.use_tls:
                    smtp.starttls()
                user = params.get("user")
                password = secret or params.get("password")
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
            return {"sent": True}

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _send)
        except Exception as exc:  # noqa: BLE001 - surface SMTP errors to caller
            raise ConnectorError(f"SMTP send failed: {exc}") from exc
