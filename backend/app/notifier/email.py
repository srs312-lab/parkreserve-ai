import smtplib
from email.message import EmailMessage
from typing import Optional

from app.config.settings import settings
from app.schemas.reservations import Alert


class EmailNotifier:
    async def send(self, alert: Alert, to_email: Optional[str]) -> tuple[str, str]:
        if not to_email:
            return "not_configured", "No recipient email was provided."

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
        message.set_content(
            "\n".join(
                [
                    alert.message,
                    "",
                    f"Reserve here: {alert.reservation_url}",
                ]
            )
        )

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except Exception as exc:
            return "failed", str(exc)

        return "sent", "Email sent."
