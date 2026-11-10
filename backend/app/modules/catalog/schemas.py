import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SubcategoryOut(Schema):
    slug: str
    name: str
    icon: str


class CategoryOut(Schema):
    slug: str
    name: str
    eyebrow: str
    headline: str
    tagline: str
    cta_label: str
    tile_image_key: str | None
    hero_image_key: str | None
    subcategories: list[SubcategoryOut]


class CityOut(Schema):
    slug: str
    name: str
    market_code: str
    currency: str
    latitude: float
    longitude: float


class NextSlotOut(Schema):
    starts_at: datetime
    # Heure murale dans le fuseau du marché (« 2026-11-12T16:00:00 »), à afficher sans conversion.
    local_start: str
    resource_name: str | None = None
    # Toujours vrai au lot 1 : calcul fondé uniquement sur les horaires.
    indicative: bool = True


class OfferOut(Schema):
    id: uuid.UUID
    version_id: uuid.UUID
    title: str
    summary: str
    includes: str | None
    language: str | None
    duration_min: int
    price_credits: int
    booking_mode: str
    participants_min: int
    participants_max: int
    capacity: int | None
    free_cancellation_hours: int
    external_ticket_note: str | None
    image_key: str | None
    next_slot: NextSlotOut | None = None


class LocationCardOut(Schema):
    id: uuid.UUID
    slug: str
    name: str
    kind_label: str
    category_slug: str
    category_name: str
    subcategory_slug: str
    subcategory_name: str
    city_slug: str
    district_label: str
    cover_image_key: str | None
    distance_m: int | None
    wheelchair_accessible: bool
    meeting_point: str | None
    featured_offer: OfferOut | None
    is_demo: bool
    # Position (carte) : présente dans les résultats de recherche.
    latitude: float | None = None
    longitude: float | None = None


class LocationPage(Schema):
    items: list[LocationCardOut]
    total: int
    limit: int
    offset: int


class OpeningHoursOut(Schema):
    weekday: int
    opens_at: time
    closes_at: time


class TeamMemberOut(Schema):
    name: str
    role_label: str
    kind: str


class LocationDetailOut(LocationCardOut):
    merchant_name: str
    description: str
    address_line: str
    postal_code: str
    city_name: str
    latitude: float
    longitude: float
    access_info: str | None
    review_url: str | None
    hours_summary: str
    opening_hours: list[OpeningHoursOut]
    offers: list[OfferOut]
    team: list[TeamMemberOut]
    status: str
    merchant_status: str | None = None  # validation XPASS du partenaire (portail commerçant)
    # Avis notés publiés (note moyenne sur 5) : renseignés sur la fiche publique.
    rating_average: float | None = None
    rating_count: int = 0
