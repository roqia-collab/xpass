import uuid
from dataclasses import dataclass
from datetime import date

from geoalchemy2 import Geography
from geoalchemy2 import Geometry
from sqlalchemy import Select, and_, exists, func, null, or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.modules.catalog.models import (
    OpeningHours,
    ScheduleException,
    Category,
    City,
    Location,
    Merchant,
    Offer,
    OfferVersion,
    Subcategory,
)

PUBLIC_MERCHANT_STATUS = "approved"
PUBLIC_LOCATION_STATUS = "published"


@dataclass
class LocationSearch:
    category: str | None = None
    subcategory: str | None = None
    city: str | None = None
    q: str | None = None
    max_credits: int | None = None
    lat: float | None = None
    lng: float | None = None
    # Rayon en mètres autour de (lat, lng) : carte « Autour de moi ».
    radius_m: int | None = None
    # Jour souhaité : établissement ouvert ce jour-là (horaires et fermetures exceptionnelles).
    day: date | None = None
    # Nombre de participants accepté par au moins une prestation active.
    participants: int | None = None
    sort: str = "distance"
    limit: int = 20
    offset: int = 0


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _location_loader() -> list:
    return [
        selectinload(Location.merchant).selectinload(Merchant.market),
        selectinload(Location.city),
        selectinload(Location.subcategory).selectinload(Subcategory.category),
        selectinload(Location.offers).selectinload(Offer.current_version),
        selectinload(Location.offers).selectinload(Offer.resources),
        selectinload(Location.opening_hours),
        selectinload(Location.exceptions),
        selectinload(Location.resources),
    ]


def list_categories(db: Session) -> list[Category]:
    stmt = select(Category).options(selectinload(Category.subcategories)).order_by(Category.sort_order)
    return list(db.scalars(stmt))


def get_category(db: Session, slug: str) -> Category | None:
    stmt = select(Category).options(selectinload(Category.subcategories)).where(Category.slug == slug)
    return db.scalar(stmt)


def list_cities(db: Session) -> list[tuple[City, float, float]]:
    stmt = (
        select(
            City,
            func.ST_Y(City.center.cast(_geometry())),
            func.ST_X(City.center.cast(_geometry())),
        )
        .where(City.opened.is_(True))
        .options(selectinload(City.market))
        .order_by(City.name)
    )
    return [(c, lat, lng) for c, lat, lng in db.execute(stmt)]


def _geometry() -> Geometry:
    return Geometry("POINT", srid=4326)


def _active_offer():
    return exists().where(
        Offer.location_id == Location.id,
        Offer.is_active.is_(True),
        Offer.current_version_id.is_not(None),
    )


def _public_filter(stmt: Select, *, real: bool) -> Select:
    """Catalogue client.

    Tant que Paris n'a pas 15 vrais établissements avec une prestation active, la démo reste visible.
    Dès ce seuil, l'application ne montre que des lieux validés, ouverts, avec une prestation active.
    """
    opened_city = aliased(City)
    stmt = stmt.where(
        Location.status == PUBLIC_LOCATION_STATUS,
        Merchant.commercial_status == PUBLIC_MERCHANT_STATUS,
        exists().where(opened_city.id == Location.city_id, opened_city.opened.is_(True)),
    )
    if real:
        stmt = stmt.where(Location.is_demo.is_(False), Merchant.is_demo.is_(False), _active_offer())
    return stmt


def search_locations(
    db: Session, params: LocationSearch
) -> tuple[list[tuple[Location, float | None, float, float]], int]:
    base = (
        select(Location.id)
        .join(Merchant, Merchant.id == Location.merchant_id)
        .join(Subcategory, Subcategory.id == Location.subcategory_id)
        .join(Category, Category.id == Subcategory.category_id)
        .join(City, City.id == Location.city_id)
    )
    from app.modules.catalog.launch import network_is_real

    base = _public_filter(base, real=network_is_real(db))

    if params.category:
        base = base.where(Category.slug == params.category)
    if params.subcategory:
        base = base.where(Subcategory.slug == params.subcategory)
    if params.city:
        base = base.where(City.slug == params.city)
    if params.q:
        pattern = func.unaccent(f"%{_escape_like(params.q.strip().lower())}%")

        def match(col):
            return func.unaccent(func.lower(col)).like(pattern, escape="\\")

        offer_match = exists().where(
            Offer.location_id == Location.id,
            Offer.is_active.is_(True),
            OfferVersion.id == Offer.current_version_id,
            match(OfferVersion.title),
        )
        base = base.where(
            or_(
                match(Location.name),
                match(Location.kind_label),
                match(Location.district_label),
                match(Subcategory.name),
                match(Category.name),
                offer_match,
            )
        )
    if params.max_credits is not None:
        base = base.where(
            exists().where(
                and_(
                    Offer.location_id == Location.id,
                    Offer.is_active.is_(True),
                    OfferVersion.id == Offer.current_version_id,
                    OfferVersion.price_credits <= params.max_credits,
                )
            )
        )

    if params.participants is not None:
        base = base.where(
            exists().where(
                and_(
                    Offer.location_id == Location.id,
                    Offer.is_active.is_(True),
                    OfferVersion.id == Offer.current_version_id,
                    OfferVersion.participants_min <= params.participants,
                    OfferVersion.participants_max >= params.participants,
                )
            )
        )
    if params.day is not None:
        closed = exists().where(and_(ScheduleException.location_id == Location.id, ScheduleException.day == params.day,
                                     ScheduleException.is_closed.is_(True)))
        special = exists().where(and_(ScheduleException.location_id == Location.id, ScheduleException.day == params.day,
                                      ScheduleException.is_closed.is_(False)))
        regular = exists().where(and_(OpeningHours.location_id == Location.id, OpeningHours.weekday == params.day.weekday()))
        base = base.where(~closed, or_(special, regular))

    # Point de référence : position fournie, sinon centre de la ville filtrée.
    if params.lat is not None and params.lng is not None:
        ref = func.ST_SetSRID(func.ST_MakePoint(params.lng, params.lat), 4326).cast(Geography)
    elif params.city:
        ref = select(City.center).where(City.slug == params.city).scalar_subquery()
    else:
        ref = None
    if params.radius_m is not None and ref is not None:
        # ST_DWithin sur geography : distance réelle en mètres, utilise l'index spatial.
        base = base.where(func.ST_DWithin(Location.geo, ref, params.radius_m))

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    distance = func.ST_Distance(Location.geo, ref) if ref is not None else None
    stmt = select(
        Location,
        distance if distance is not None else null(),
        func.ST_Y(Location.geo.cast(_geometry())),
        func.ST_X(Location.geo.cast(_geometry())),
    )
    stmt = stmt.where(Location.id.in_(base)).options(*_location_loader())

    if params.sort == "price":
        min_price = (
            select(func.min(OfferVersion.price_credits))
            .join(Offer, Offer.current_version_id == OfferVersion.id)
            .where(Offer.location_id == Location.id, Offer.is_active.is_(True))
            .scalar_subquery()
        )
        stmt = stmt.order_by(min_price.asc().nulls_last(), Location.name)
    elif distance is not None:
        stmt = stmt.order_by(distance.asc(), Location.name)
    else:
        stmt = stmt.order_by(Location.name)

    stmt = stmt.limit(params.limit).offset(params.offset)
    rows = db.execute(stmt).all()
    return [(loc, float(d) if isinstance(d, (int, float)) else None, lat, lng) for loc, d, lat, lng in rows], total


def get_public_location(db: Session, slug_or_id: str) -> tuple[Location, float, float] | None:
    stmt = (
        select(
            Location,
            func.ST_Y(Location.geo.cast(_geometry())),
            func.ST_X(Location.geo.cast(_geometry())),
        )
        .join(Merchant, Merchant.id == Location.merchant_id)
        .options(*_location_loader())
    )
    from app.modules.catalog.launch import network_is_real

    stmt = _public_filter(stmt, real=network_is_real(db))
    try:
        stmt = stmt.where(Location.id == uuid.UUID(slug_or_id))
    except ValueError:
        stmt = stmt.where(Location.slug == slug_or_id)
    row = db.execute(stmt).first()
    return (row[0], row[1], row[2]) if row else None


def list_merchant_locations(db: Session, merchant_ids: list[uuid.UUID]) -> list[tuple[Location, float, float]]:
    if not merchant_ids:
        return []
    stmt = (
        select(
            Location,
            func.ST_Y(Location.geo.cast(_geometry())),
            func.ST_X(Location.geo.cast(_geometry())),
        )
        .where(Location.merchant_id.in_(merchant_ids))
        .options(*_location_loader())
        .order_by(Location.name)
    )
    return [(loc, lat, lng) for loc, lat, lng in db.execute(stmt)]


def list_merchants(db: Session, status: str | None = None) -> list[tuple[Merchant, int]]:
    count = (
        select(func.count(Location.id)).where(Location.merchant_id == Merchant.id).correlate(Merchant).scalar_subquery()
    )
    stmt = select(Merchant, count).order_by(Merchant.created_at.desc(), Merchant.display_name)
    if status:
        stmt = stmt.where(Merchant.commercial_status == status)
    return [(m, n) for m, n in db.execute(stmt)]
