"""Séances à venir sur les établissements parisiens déjà publiés.

Les lieux existent déjà. Ces séances leur donnent une date, pour que
l'application affiche un agenda réel. Relancer le script ne duplique pas
un titre déjà présent sur le même établissement.

    docker compose exec api python -m app.seed.paris_events
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.catalog.events import backfill_offers
from app.modules.catalog.models import Location, Merchant, VenueEvent

PARIS = ZoneInfo("Europe/Paris")

# slug, titre, résumé, jour (0 = lundi), début, fin, crédits
PROGRAM = [
    ("cinema-louxor", "Séance du soir au Louxor", "Une place pour la séance du soir, dans la salle historique.", 5, (19, 0), (21, 0), 7),
    ("gymnase-japy", "Cours collectif au gymnase Japy", "Séance en groupe, tapis fourni. Arrivez dix minutes avant.", 5, (10, 30), (12, 0), 6),
    ("musee-carnavalet", "Visite commentée de Carnavalet", "Parcours guidé dans les collections de l'histoire de Paris.", 6, (14, 0), (16, 0), 10),
    ("gaite-lyrique", "Soirée à la Gaîté Lyrique", "Une représentation ou une installation, selon la programmation du soir.", 4, (19, 0), (21, 0), 12),
    ("piscine-georges-vallerey", "Nage en ligne à Georges-Vallerey", "Créneau piscine, ligne et nage libre.", 5, (11, 0), (12, 30), 8),
    ("parc-buttes-chaumont", "Parcours guidé aux Buttes-Chaumont", "Une heure dans le parc, au départ de l'accueil.", 6, (15, 0), (16, 30), 4),
    ("hammam-mosquee-paris", "Rituel hammam", "Soin hammam, serviette sur place.", 2, (18, 0), (20, 0), 12),
    ("theatre-de-la-ville", "Représentation au Théâtre de la Ville", "Une place pour la représentation du soir.", 3, (19, 30), (21, 30), 14),
]


def upcoming(weekday: int, hour: int, minute: int) -> datetime:
    now = datetime.now(PARIS)
    days = (weekday - now.weekday()) % 7
    if days == 0 and (now.hour, now.minute) >= (hour, minute):
        days = 7
    return (now + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)


def seed() -> int:
    created = 0
    with SessionLocal() as db, db.begin():
        for slug, title, summary, weekday, start_hm, end_hm, credits in PROGRAM:
            location = db.scalar(select(Location).where(Location.slug == slug, Location.status == "published"))
            if location is None:
                print(f"Ignoré, établissement absent : {slug}")
                continue
            merchant = db.get(Merchant, location.merchant_id)
            if merchant is None or merchant.organization_id is None:
                print(f"Ignoré, sans service RH : {slug}")
                continue
            exists = db.scalar(select(VenueEvent.id).where(VenueEvent.location_id == location.id, VenueEvent.title == title))
            if exists is not None:
                continue
            start = upcoming(weekday, *start_hm)
            end = upcoming(weekday, *end_hm)
            if end <= start:
                end = start + timedelta(hours=2)
            db.add(VenueEvent(
                organization_id=merchant.organization_id,
                location_id=location.id,
                title=title,
                summary=summary,
                starts_at=start,
                ends_at=end,
                price_credits=credits,
                cover_image_key=location.cover_image_key,
                status="published",
            ))
            created += 1
        linked = backfill_offers(db)
    print(f"Événements ajoutés : {created}. Séances rattachées : {linked}.")
    return created


if __name__ == "__main__":
    raise SystemExit(0 if seed() >= 0 else 1)
