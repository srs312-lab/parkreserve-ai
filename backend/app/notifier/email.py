import html
import smtplib
from email.message import EmailMessage
from typing import Optional

import httpx

from app.config.settings import settings
from app.schemas.reservations import Alert


class EmailNotifier:
    async def send(self, alert: Alert, to_email: Optional[str]) -> tuple[str, str]:
        if not to_email:
            return "not_configured", "No recipient email was provided."

        provider = settings.email_provider.lower()
        if provider == "auto":
            provider = "resend" if settings.resend_api_key else "smtp"

        if provider == "smtp":
            return self._send_smtp(alert, to_email)

        return await self._send_resend(alert, to_email)

    async def _send_resend(self, alert: Alert, to_email: str) -> tuple[str, str]:
        if not settings.resend_api_key or not settings.resend_from_email:
            print(f"Email alert preview for {to_email}: {alert.message}")
            return "not_configured", "Resend API key or from email is missing."

        payload = {
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": f"ParkReserve AI alert: {alert.park_name}",
            "text": self._text_body(alert),
            "html": self._html_body(alert),
        }
        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"parkreserve-alert-email-{alert.alert_id}",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{settings.resend_base_url.rstrip('/')}/emails",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._resend_error_detail(exc.response)
            return "failed", f"Resend API error ({exc.response.status_code}): {detail}"
        except httpx.RequestError as exc:
            return "failed", f"Resend request failed: {exc.__class__.__name__}"

        return "sent", "Email sent."

    def _send_smtp(self, alert: Alert, to_email: str) -> tuple[str, str]:
        required_settings = [
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from_email,
        ]
        if not all(required_settings):
            print(f"Email alert preview for {to_email}: {alert.message}")
            return "not_configured", "SMTP settings are missing; printed preview."

        message = EmailMessage()
        message["Subject"] = f"ParkReserve AI alert: {alert.park_name}"
        message["From"] = settings.smtp_from_email
        message["To"] = to_email
        message.set_content(self._text_body(alert))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except Exception as exc:
            return "failed", str(exc)

        return "sent", "Email sent."

    @staticmethod
    def _text_body(alert: Alert) -> str:
        lines = [
            alert.message,
            "",
            f"Reserve here: {alert.reservation_url}",
        ]
        if alert.campground_name:
            lines.extend(["", f"Campground: {alert.campground_name}"])
        if alert.available_date and alert.available_end_date:
            lines.append(f"Dates: {alert.available_date} to {alert.available_end_date}")
        if alert.site:
            lines.append(f"Site: {alert.site}")

        return "\n".join(lines)

    @staticmethod
    def _html_body(alert: Alert) -> str:
        details = []
        if alert.campground_name:
            campground_name = html.escape(alert.campground_name)
            details.append(
                f"<li><strong>Campground:</strong> {campground_name}</li>"
            )
        if alert.available_date and alert.available_end_date:
            details.append(
                "<li><strong>Dates:</strong> "
                f"{html.escape(str(alert.available_date))} to "
                f"{html.escape(str(alert.available_end_date))}</li>"
            )
        if alert.site:
            details.append(f"<li><strong>Site:</strong> {html.escape(alert.site)}</li>")

        detail_html = f"<ul>{''.join(details)}</ul>" if details else ""
        return "\n".join(
            [
                "<div>",
                f"<p>{html.escape(alert.message)}</p>",
                detail_html,
                (
                    f'<p><a href="{html.escape(alert.reservation_url, quote=True)}">'
                    "Open reservation"
                    "</a></p>"
                ),
                "</div>",
            ]
        )

    @staticmethod
    def _resend_error_detail(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text[:220] or response.reason_phrase

        if isinstance(data, dict):
            for key in ("message", "error", "detail"):
                value = data.get(key)
                if isinstance(value, str):
                    return value[:220]
            if isinstance(data.get("errors"), list):
                return "; ".join(str(error) for error in data["errors"])[:220]

        return response.reason_phrase
