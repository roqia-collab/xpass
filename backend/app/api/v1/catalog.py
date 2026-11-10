from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.modules.catalog import repository, service
from app.modules.catalog.schemas import CategoryOut, CityOut, LocationDetailOut, LocationPage

router = APIRouter(tags=["catalogue"])


@router.get("/geo/cities", response_model=list[CityOut])
def list_cities(db: DbSession) -> list[CityOut]:
    return [
        CityOut(
            slug=c.slug,
            name=c.name,
            market_code=c.market.code,
            currency=c.market.currency,
            latitude=lat,
            longitude=lng,
        )
        for c, lat, lng in repository.list_cities(db)
    ]


@router.get("/catalog/categories", response_model=list[CategoryOut])
def list_categories(db: DbSession) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in repository.list_categories(db)]


@router.get("/catalog/categories/{slug}", response_model=CategoryOut)
def get_category(slug: str, db: DbSession) -> CategoryOut:
    category = repository.get_category(db, slug)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "category_not_found", "message": "Univers inconnu."})
    return CategoryOut.model_validate(category)


@router.get("/catalog/locations", response_model=LocationPage)
def search_locations(
    db: DbSession,
    category: str | None = None,
    subcategory: str | None = None,
    city: str | None = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    max_credits: Annotated[int | None, Query(ge=1, le=10_000)] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_m: Annotated[int | None, Query(ge=100, le=50_000)] = None,
    day: date | None = None,
    participants: Annotated[int | None, Query(ge=1, le=50)] = None,
    sort: Literal["distance", "price"] = "distance",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LocationPage:
    if (lat is None) != (lng is None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"code": "invalid_position", "message": "lat et lng doivent être fournis ensemble."},
        )
    if radius_m is not None and lat is None and city is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"code": "invalid_radius", "message": "Un rayon exige une position ou une ville."},
        )
    params = repository.LocationSearch(
        category=category,
        subcategory=subcategory,
        city=city,
        q=q or None,
        max_credits=max_credits,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        day=day,
        participants=participants,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    rows, total = repository.search_locations(db, params)
    return LocationPage(
        items=[service.location_card(loc, dist, lat=la, lng=lo) for loc, dist, la, lo in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/catalog/locations/{slug_or_id}", response_model=LocationDetailOut)
def get_location(slug_or_id: str, db: DbSession) -> LocationDetailOut:
    found = repository.get_public_location(db, slug_or_id)
    if found is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, {"code": "location_not_found", "message": "Établissement introuvable."}
        )
    location, lat, lng = found
    from app.modules.engagement.service import rating_summary

    out = service.location_detail(location, lat, lng)
    out.rating_average, out.rating_count = rating_summary(db, location.id)
    return out
