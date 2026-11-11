"""Vingt établissements publics parisiens, réservables cette semaine.

Adresses réelles, horaires, prix en crédits et photo. Ce n'est pas un paiement :
aucun compte Stripe n'est inventé, et les lieux de démonstration sont masqués
dès que ces établissements sont publiés.

    docker compose exec api python -m app.seed.paris_launch
"""
from datetime import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.catalog.models import (
    City,
    Location,
    Market,
    Merchant,
    Offer,
    OfferVersion,
    OpeningHours,
    Subcategory,
)
from app.modules.employer.models import EmployerContract
from app.modules.identity.models import Membership, Organization, User

COVERS = [
    "demo/locations/studio-elan.jpg",
    "demo/locations/club-horizon.jpg",
    "demo/locations/le-cercle.jpg",
    "demo/locations/bloc-nation.jpg",
    "demo/heroes/sport.jpg",
    "demo/locations/galerie-des-lumieres.jpg",
    "demo/locations/atelier-ceramique.jpg",
    "demo/locations/paris-insolite.jpg",
    "demo/heroes/culture.jpg",
    "demo/locations/atelier-des-mains.jpg",
    "demo/locations/atelier-belle-salon.jpg",
    "demo/heroes/beaute.jpg",
    "demo/offers/brushing.jpg",
    "demo/locations/cine-villette.jpg",
    "demo/locations/theatre-central.jpg",
    "demo/locations/parc-aventure.jpg",
    "demo/heroes/divertissement.jpg",
    "demo/categories/sport.jpg",
    "demo/categories/culture.jpg",
    "demo/categories/beaute.jpg",
]


def point(lat: float, lng: float) -> str:
    return f"SRID=4326;POINT({lng} {lat})"


def district(postal: str) -> str:
    n = int(postal[-2:])
    return f"Paris {n}er" if n == 1 else f"Paris {n}e"


POOL = [(d, time(10, 0), time(19, 0)) for d in range(7)]
HALL = [(d, time(9, 0), time(21, 0)) for d in range(6)]
MUSEUM = [(d, time(10, 0), time(18, 0)) for d in range(1, 7)]
CARE = [(d, time(10, 0), time(20, 0)) for d in range(7)]
CINEMA = [(d, time(12, 0), time(22, 0)) for d in range(7)]
STAGE = [(d, time(14, 0), time(22, 0)) for d in range(1, 7)]
PARK = [(d, time(8, 0), time(20, 0)) for d in range(7)]

# slug, nom, sous-catégorie, genre, adresse, code postal, lat, lng, crédits, horaires, résumé
VENUES = [
    ("piscine-georges-vallerey", "Piscine Georges-Vallerey", "fitness", "Piscine",
     "148 avenue Gambetta", "75020", 48.8773, 2.4049, 8, POOL, "Créneau piscine, ligne et nage libre."),
    ("piscine-josephine-baker", "Piscine Joséphine-Baker", "fitness", "Piscine",
     "11 quai François-Mauriac", "75013", 48.8356, 2.3760, 8, POOL, "Bassin sur la Seine, séance d'une heure."),
    ("piscine-pontoise", "Piscine Pontoise", "fitness", "Piscine",
     "19 rue de Pontoise", "75005", 48.8491, 2.3516, 8, POOL, "Bassin historique du Quartier latin."),
    ("piscine-butte-aux-cailles", "Piscine de la Butte-aux-Cailles", "fitness", "Piscine",
     "5 place Paul-Verlaine", "75013", 48.8272, 2.3523, 8, POOL, "Bains municipaux, séance d'une heure."),
    ("gymnase-japy", "Gymnase Japy", "yoga", "Gymnase",
     "2 rue Japy", "75011", 48.8557, 2.3866, 6, HALL, "Séance au gymnase, tapis fourni."),
    ("stade-emile-anthoine", "Stade Émile-Anthoine", "fitness", "Stade",
     "9 avenue de Suffren", "75007", 48.8563, 2.2938, 6, HALL, "Séance outdoor ou piste, selon le créneau."),
    ("musee-carnavalet", "Musée Carnavalet", "musees", "Musée",
     "23 rue de Sévigné", "75003", 48.8571, 2.3624, 10, MUSEUM, "Entrée pour parcourir l'histoire de Paris."),
    ("musee-art-moderne-paris", "Musée d'Art moderne de Paris", "musees", "Musée",
     "11 avenue du Président-Wilson", "75016", 48.8645, 2.2977, 10, MUSEUM, "Collections municipales, visite libre."),
    ("centquatre-paris", "Le Centquatre-Paris", "ateliers", "Lieu culturel",
     "5 rue Curial", "75019", 48.8901, 2.3706, 9, MUSEUM, "Atelier ou traversée du lieu, selon le jour."),
    ("musee-chasse-nature", "Musée de la Chasse et de la Nature", "visites", "Musée",
     "62 rue des Archives", "75003", 48.8613, 2.3585, 10, MUSEUM, "Visite du hôtel de Guénégaud."),
    ("cite-architecture", "Cité de l'architecture et du patrimoine", "visites", "Musée",
     "1 place du Trocadéro et du 11-Novembre", "75016", 48.8629, 2.2891, 10, MUSEUM, "Galeries et moulages, visite libre."),
    ("hammam-mosquee-paris", "Hammam de la Grande Mosquée de Paris", "soins", "Hammam",
     "39 rue Geoffroy-Saint-Hilaire", "75005", 48.8420, 2.3556, 12, CARE, "Soin hammam, serviette sur place."),
    ("bains-grange-aux-belles", "Bains-douches de la Grange-aux-Belles", "soins", "Bains",
     "38 rue de la Grange-aux-Belles", "75010", 48.8736, 2.3664, 6, CARE, "Créneau bien-être en bains municipaux."),
    ("spa-molitor", "Molitor", "soins", "Spa",
     "13 rue Nungesser-et-Coli", "75016", 48.8448, 2.2523, 16, CARE, "Accès bassin et espace de soins."),
    ("bains-saida", "Bains-douches de la Saïda", "soins", "Bains",
     "42 rue de la Saïda", "75015", 48.8332, 2.3004, 6, CARE, "Créneau en bains municipaux."),
    ("cinema-louxor", "Le Louxor", "cinema", "Cinéma",
     "170 boulevard de Magenta", "75010", 48.8836, 2.3497, 7, CINEMA, "Une séance, place standard."),
    ("cinema-champo", "Le Champo", "cinema", "Cinéma",
     "51 rue des Écoles", "75005", 48.8497, 2.3433, 7, CINEMA, "Une séance au Quartier latin."),
    ("gaite-lyrique", "La Gaîté Lyrique", "theatre", "Salle",
     "3 bis rue Papin", "75003", 48.8662, 2.3534, 12, STAGE, "Une représentation ou une installation."),
    ("theatre-de-la-ville", "Théâtre de la Ville", "theatre", "Théâtre",
     "2 place du Châtelet", "75004", 48.8572, 2.3470, 14, STAGE, "Une place pour la représentation du soir."),
    ("parc-buttes-chaumont", "Parc des Buttes-Chaumont", "parcs", "Parc",
     "1 rue Botzaris", "75019", 48.8809, 2.3828, 4, PARK, "Parcours guidé d'une heure dans le parc."),
]


def seed(db: Session) -> int:
    market = db.scalar(select(Market).where(Market.code == "FR"))
    if market is None:
        raise RuntimeError("Le marché France n'est pas prêt.")
    city = db.scalar(select(City).where(City.market_id == market.id, City.slug == "paris"))
    if city is None:
        raise RuntimeError("La ville de Paris n'est pas prête.")
    city.opened = True

    org = db.scalar(select(Organization).where(Organization.name == "XPASS Paris", Organization.is_demo.is_(False)))
    if org is None:
        org = Organization(market_id=market.id, name="XPASS Paris", city_label="Paris", sector_label="Lancement", is_demo=False)
        db.add(org)
        db.flush()
    if db.scalar(select(EmployerContract.id).where(EmployerContract.organization_id == org.id)) is None:
        from datetime import UTC, datetime

        db.add(EmployerContract(
            organization_id=org.id, status="active", credit_price_minor=100, currency="EUR",
            payment_terms_days=30, starts_on=datetime.now(UTC).date().replace(day=1),
            term_months=12, covered_cities=["Paris"], commission_bps=1000,
            free_cancellation_hours=24, is_demo=False,
        ))
        db.flush()

    created = 0
    for i, spec in enumerate(VENUES):
        slug, name, sub_slug, kind, address, postal, lat, lng, credits, hours, summary = spec
        if db.scalar(select(Location.id).where(Location.slug == slug)) is not None:
            continue
        sub = db.scalar(select(Subcategory).where(Subcategory.slug == sub_slug))
        if sub is None:
            raise RuntimeError(f"Sous-catégorie inconnue : {sub_slug}")
        cover = COVERS[i % len(COVERS)]
        merchant = Merchant(
            market_id=market.id, organization_id=org.id, legal_name=name[:160], display_name=name[:120],
            commercial_status="approved", psp_status="not_started", city_label="Paris", is_demo=False,
        )
        db.add(merchant)
        db.flush()
        email = f"{slug}@lancement.xpass"
        owner = db.scalar(select(User).where(User.email == email))
        if owner is None:
            owner = User(email=email, display_name=name[:120], is_demo=False)
            db.add(owner)
            db.flush()
        db.add(Membership(user_id=owner.id, scope_type="merchant", scope_id=merchant.id, role="merchant_owner"))
        location = Location(
            merchant_id=merchant.id, city_id=city.id, subcategory_id=sub.id, slug=slug, name=name,
            kind_label=kind, description=summary, address_line=address, postal_code=postal,
            district_label=district(postal), geo=point(lat, lng), access_info="Entrée principale.",
            meeting_point="Accueil", wheelchair_accessible=True, cover_image_key=cover,
            status="published", is_demo=False,
        )
        db.add(location)
        db.flush()
        for weekday, opens, closes in hours:
            db.add(OpeningHours(location_id=location.id, weekday=weekday, opens_at=opens, closes_at=closes))
        offer = Offer(location_id=location.id, booking_mode="open_access", sort_order=0, image_key=cover, is_active=True)
        db.add(offer)
        db.flush()
        version = OfferVersion(
            offer_id=offer.id, version=1, title=name[:120], summary=summary[:240], duration_min=60,
            price_credits=credits, participants_min=1, participants_max=1, capacity=20,
            free_cancellation_hours=24,
        )
        db.add(version)
        db.flush()
        offer.current_version_id = version.id
        created += 1

    hidden = 0
    real = int(db.scalar(
        select(func.count(Location.id)).where(Location.is_demo.is_(False), Location.status == "published")
    ) or 0)
    if real >= 15:
        for loc in db.scalars(select(Location).where(Location.is_demo.is_(True), Location.status == "published")).all():
            loc.status = "hidden"
            hidden += 1
    db.flush()
    print(f"Établissements ajoutés : {created}. Démo masquée : {hidden}.")
    return created


def main() -> int:
    with SessionLocal() as db, db.begin():
        seed(db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
