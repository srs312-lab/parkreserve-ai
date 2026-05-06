from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

NotificationType = Literal["email", "sms", "both", "push"]
WatchStatus = Literal["active", "paused"]
NotificationStatus = Literal["sent", "not_configured", "failed"]
WatchPriority = Literal["high", "normal", "low"]


class WatchReservationRequest(BaseModel):
    park_name: str = Field(..., examples=["Yosemite National Park"])
    facility_id: Optional[str] = Field(
        None,
        examples=["232447"],
        description="Optional Recreation.gov campground/facility ID.",
    )
    campground_name: Optional[str] = Field(None, examples=["Fallen Leaf Campground"])
    date_start: date
    date_end: date
    camp_type: str = Field("tent", examples=["tent", "rv", "cabin"])
    min_nights: int = Field(
        1,
        ge=1,
        le=30,
        description="Minimum consecutive available nights required for an alert.",
    )
    flexibility_days: int = Field(0, ge=0, le=30)
    notification_type: NotificationType = "email"
    priority: WatchPriority = Field(
        "normal",
        description=(
            "Controls background availability check frequency. "
            "High checks faster, low checks slower."
        ),
    )
    email_address: Optional[str] = Field(None, examples=["you@example.com"])
    phone_number: Optional[str] = Field(None, examples=["+15551234567"])
    max_price: Optional[float] = Field(None, ge=0)
    weekend_preferred: bool = False


class AvailabilityQuery(BaseModel):
    park_name: str
    facility_id: Optional[str] = None
    campground_name: Optional[str] = None
    date_start: date
    date_end: date
    camp_type: Optional[str] = None
    min_nights: int = Field(1, ge=1, le=30)


class UserPreferences(BaseModel):
    park_name: str
    facility_id: Optional[str] = None
    campground_name: Optional[str] = None
    date_start: date
    date_end: date
    camp_type: str
    min_nights: int = 1
    flexibility_days: int
    notification_type: NotificationType
    priority: WatchPriority = "normal"
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    max_price: Optional[float] = None
    weekend_preferred: bool = False

    def to_availability_query(self) -> AvailabilityQuery:
        return AvailabilityQuery(
            park_name=self.park_name,
            facility_id=self.facility_id,
            campground_name=self.campground_name,
            date_start=self.date_start,
            date_end=self.date_end,
            camp_type=self.camp_type,
            min_nights=self.min_nights,
        )


class AvailabilityResult(BaseModel):
    park_name: str
    campground_name: str
    facility_id: str
    campsite_id: str
    site: str
    status: str
    available: bool
    available_date: date
    available_end_date: date
    nights: int = Field(1, ge=1)
    site_type: str
    price: Optional[float] = None
    is_weekend: bool = False
    source: str
    reservation_url: str


class CampgroundSearchResult(BaseModel):
    facility_id: str
    name: str
    park_name: str
    city: Optional[str] = None
    state_code: Optional[str] = None
    reservation_url: str


class ParkSearchResult(BaseModel):
    recarea_id: str
    name: str
    state_code: Optional[str] = None
    campgrounds_count: int = 0


class NextAvailabilityResult(BaseModel):
    park_name: str
    campground_name: str
    facility_id: str
    available_date: date
    available_end_date: date
    nights: int
    site_count: int
    site_types: list[str]
    reservation_url: str


class Watch(BaseModel):
    watch_id: str
    status: WatchStatus
    preferences: UserPreferences
    last_checked_at: Optional[datetime] = None


class WatchReservationResponse(BaseModel):
    watch_id: str
    status: WatchStatus
    message: str


class DuplicateWatchResponse(BaseModel):
    existing_watch_id: str
    park_name: str
    facility_id: Optional[str] = None
    campground_name: Optional[str] = None
    date_start: date
    date_end: date
    camp_type: str
    min_nights: int
    notification_type: NotificationType
    priority: WatchPriority
    message: str


class BatchWatchReservationRequest(BaseModel):
    watches: list[WatchReservationRequest] = Field(..., min_length=1, max_length=25)


class BatchWatchReservationResponse(BaseModel):
    created: list[WatchReservationResponse] = Field(default_factory=list)
    skipped_duplicates: list[DuplicateWatchResponse] = Field(default_factory=list)


class IntegrationStatus(BaseModel):
    configured: bool
    recipient: Optional[str] = None
    provider: Optional[str] = None
    detail: str


class SettingsStatus(BaseModel):
    environment: str
    store: str
    poll_interval_seconds: int
    api_auth_configured: bool
    recreation_gov_base_url: str
    ridb_api_configured: bool
    email: IntegrationStatus
    sms: IntegrationStatus


class TestAlertRequest(BaseModel):
    notification_type: Literal["email", "sms", "both"] = "both"


class WatchUpdateRequest(BaseModel):
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    camp_type: Optional[str] = Field(None, examples=["any", "tent", "rv"])
    min_nights: Optional[int] = Field(None, ge=1, le=30)
    notification_type: Optional[NotificationType] = None
    priority: Optional[WatchPriority] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None


class WatchSummary(BaseModel):
    watch_id: str
    status: WatchStatus
    park_name: str
    facility_id: Optional[str] = None
    campground_name: Optional[str] = None
    date_start: date
    date_end: date
    camp_type: str
    min_nights: int = 1
    notification_type: NotificationType
    priority: WatchPriority = "normal"
    email_address: Optional[str] = None
    phone_number_masked: Optional[str] = None
    check_interval_seconds: int
    last_checked_at: Optional[datetime] = None


class NotificationDelivery(BaseModel):
    channel: Literal["email", "sms"]
    status: NotificationStatus
    detail: str


class TestAlertResponse(BaseModel):
    message: str
    deliveries: list[NotificationDelivery]
    cooldown_seconds: int


class Alert(BaseModel):
    alert_id: str
    watch_id: str
    park_name: str
    message: str
    reservation_url: str
    created_at: datetime
    campground_name: Optional[str] = None
    facility_id: Optional[str] = None
    campsite_id: Optional[str] = None
    site: Optional[str] = None
    available_date: Optional[date] = None
    available_end_date: Optional[date] = None
    nights: Optional[int] = None
    site_type: Optional[str] = None
    deliveries: list[NotificationDelivery] = Field(default_factory=list)


class PauseAgentRequest(BaseModel):
    watch_id: str
