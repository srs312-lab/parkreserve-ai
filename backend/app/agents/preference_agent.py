from app.config.settings import settings
from app.schemas.reservations import UserPreferences, WatchReservationRequest


class PreferenceAgent:
    def normalize(self, request: WatchReservationRequest) -> UserPreferences:
        return UserPreferences(
            park_name=request.park_name.strip(),
            facility_id=request.facility_id,
            campground_name=request.campground_name,
            date_start=request.date_start,
            date_end=request.date_end,
            camp_type=request.camp_type.strip().lower(),
            min_nights=request.min_nights,
            flexibility_days=request.flexibility_days,
            notification_type=request.notification_type,
            email_address=request.email_address or settings.default_alert_email,
            phone_number=request.phone_number or settings.default_alert_phone,
            max_price=request.max_price,
            weekend_preferred=request.weekend_preferred,
        )
