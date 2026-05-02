import httpx
from typing import Optional

from app.config.settings import settings
from app.schemas.reservations import Alert


class SmsNotifier:
    async def send(self, alert: Alert, to_phone: Optional[str]) -> tuple[str, str]:
        if not to_phone:
            return "not_configured", "No recipient phone number was provided."

        required_settings = [
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_from_phone,
        ]
        if not all(required_settings):
            print(f"SMS alert preview for {to_phone}: {alert.message}")
            return "not_configured", "Twilio settings are missing; printed preview."

        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.twilio_account_sid}/Messages.json"
        )
        data = {
            "From": settings.twilio_from_phone,
            "To": to_phone,
            "Body": f"{alert.message} {alert.reservation_url}",
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                )
                response.raise_for_status()
        except Exception as exc:
            return "failed", str(exc)

        return "sent", f"SMS sent to {to_phone}."
