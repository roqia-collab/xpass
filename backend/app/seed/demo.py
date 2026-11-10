"""Données de DÉMONSTRATION synthétiques (is_demo = true).

Tous les établissements, personnes et prix sont fictifs. Les noms de marques
réelles visibles sur les maquettes ont été remplacés.

Usage :
    docker compose exec api python -m app.seed.demo           # crée si absent
    docker compose exec api python -m app.seed.demo --reset   # efface les données de démo puis recrée
"""
import sys
from datetime import time

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.catalog.models import (
    Category,
    City,
    Location,
    Market,
    Merchant,
    Offer,
    OfferVersion,
    OpeningHours,
    Resource,
    Subcategory,
)
from app.modules.identity.models import Membership, Organization, User

M = "demo/"  # préfixe des médias placeholder dans le bucket public


def point(lat: float, lng: float) -> str:
    return f"SRID=4326;POINT({lng} {lat})"


CATEGORIES = [
    dict(
        slug="divertissement",
        name="Divertissement",
        eyebrow="DIVERTISSEMENT",
        headline="Divertissement",
        tagline="Sorties, spectacles et grands moments à partager.",
        cta_label="Afficher sur la carte",
        subs=[("parcs", "Parcs", "attractions"), ("cinema", "Cinéma", "movie"), ("theatre", "Théâtre", "theater")],
    ),
    dict(
        slug="sport",
        name="Activité sportive",
        eyebrow="ACTIVITÉ SPORTIVE",
        headline="Bouger fait du bien",
        tagline="Des séances pour vous, près de chez vous.",
        cta_label="Voir les séances disponibles",
        subs=[
            ("fitness", "Fitness", "fitness"),
            ("danse", "Danse", "dance"),
            ("yoga", "Yoga", "yoga"),
            ("escalade", "Escalade", "climbing"),
        ],
    ),
    dict(
        slug="culture",
        name="Activité culturelle",
        eyebrow="CULTURE · RENCONTRES · DÉCOUVERTES",
        headline="Activité culturelle",
        tagline="Explorez des lieux uniques et des ateliers inspirants avec des passionnés.",
        cta_label="Découvrir les expériences",
        subs=[("visites", "Visites", "museum"), ("musees", "Musées", "palette"), ("ateliers", "Ateliers", "pottery")],
    ),
    dict(
        slug="beaute",
        name="Beauté",
        eyebrow="BEAUTÉ",
        headline="Beauté",
        tagline="Du temps pour vous",
        cta_label="Trouver un rendez-vous",
        subs=[("coiffure", "Coiffure", "scissors"), ("ongles", "Ongles", "nails"), ("soins", "Soins", "spa")],
    ),
]

WEEK = range(0, 7)


def hours(days, start: str, end: str) -> list[tuple[int, time, time]]:
    h1, m1 = map(int, start.split(":"))
    h2, m2 = map(int, end.split(":"))
    return [(d, time(h1, m1), time(h2, m2)) for d in days]


# Chaque établissement : (marchand, lieu, offres, équipe, horaires)
LOCATIONS = [
    dict(
        merchant="Atelier Belle venue SAS",
        name="Atelier Belle venue",
        slug="atelier-belle-venue",
        sub="coiffure",
        kind="Salon de coiffure",
        address="12 rue Oberkampf",
        postal="75011",
        district="Paris 11e",
        geo=(48.8649, 2.3726),
        access="Métro Parmentier (ligne 3) · Entrée accessible aux personnes à mobilité réduite",
        wheelchair=True,
        cover="locations/atelier-belle-venue.jpg",
        description="Salon lumineux au cœur du 11e : coupes, couleurs et soins sur rendez-vous.",
        hours=hours(range(0, 6), "09:00", "19:00"),
        team=[("staff", "Sarah", "Coiffeuse"), ("staff", "Lina", "Coloriste"), ("equipment", "Fauteuil 1", "Ressource")],
        offers=[
            dict(title="Coupe et coiffage", summary="Diagnostic, coupe et coiffage.", includes="coupe et coiffage",
                 duration=30, credits=18, mode="resource_slot", image="offers/coupe-coiffage.jpg", staff=["Sarah"]),
            dict(title="Brushing", summary="Shampoing et brushing.", includes="shampoing, brushing",
                 duration=30, credits=15, mode="resource_slot", image="offers/brushing.jpg", staff=["Sarah", "Lina"]),
            dict(title="Coloration complète", summary="Couleur racines et longueurs.", includes="couleur, soin, coiffage",
                 duration=90, credits=40, mode="resource_slot", image="offers/coloration.jpg", staff=["Lina"]),
        ],
    ),
    dict(
        merchant="L'Atelier des Mains SARL",
        name="L'Atelier des Mains",
        slug="atelier-des-mains",
        sub="ongles",
        kind="Bar à ongles",
        address="8 rue de Bretagne",
        postal="75003",
        district="Paris 3e",
        geo=(48.8630, 2.3613),
        access="Métro Filles du Calvaire (ligne 8)",
        wheelchair=False,
        cover="locations/atelier-des-mains.jpg",
        description="Manucure, pose de vernis et soins des mains dans un cadre doux.",
        hours=hours(range(1, 6), "10:00", "19:30"),
        team=[("staff", "Inès", "Prothésiste ongulaire"), ("staff", "Maya", "Esthéticienne")],
        offers=[
            dict(title="Manucure complète", summary="Soin des cuticules, limage et vernis.", includes="vernis classique",
                 duration=45, credits=22, mode="resource_slot", staff=["Inès", "Maya"]),
        ],
    ),
    dict(
        merchant="Maison Lumière Soins",
        name="Maison Lumière",
        slug="maison-lumiere",
        sub="soins",
        kind="Institut de soins",
        address="27 rue Saint-Sabin",
        postal="75011",
        district="Paris 11e",
        geo=(48.8569, 2.3714),
        access="Métro Bréguet-Sabin (ligne 5)",
        wheelchair=True,
        cover="locations/atelier-belle-salon.jpg",
        description="Soins du visage et rituels détente.",
        hours=hours(range(0, 6), "10:00", "20:00"),
        team=[("staff", "Claire", "Esthéticienne")],
        offers=[
            dict(title="Soin visage éclat", summary="Nettoyage, gommage et masque.", includes="diagnostic de peau",
                 duration=60, credits=30, mode="resource_slot", staff=["Claire"]),
        ],
    ),
    dict(
        merchant="Studio Élan Danse",
        name="Studio Élan",
        slug="studio-elan",
        sub="danse",
        kind="Studio de danse",
        address="41 rue du Faubourg-Saint-Denis",
        postal="75010",
        district="Paris 10e",
        geo=(48.8716, 2.3540),
        access="Métro Château d'Eau (ligne 4)",
        wheelchair=False,
        cover="locations/studio-elan.jpg",
        description="Cours collectifs de danse pour tous les niveaux.",
        hours=hours(range(0, 5), "18:00", "21:00") + hours([5], "10:00", "13:00"),
        team=[("room", "Grande salle", "Salle"), ("staff", "Nora", "Professeure de danse")],
        offers=[
            dict(title="Danse débutant", summary="Bases, rythme et chorégraphie simple.", duration=60, credits=14,
                 mode="capacity_session", capacity=12, staff=["Nora"]),
        ],
    ),
    dict(
        merchant="Club Horizon Fitness",
        name="Club Horizon",
        slug="club-horizon",
        sub="fitness",
        kind="Salle de sport",
        address="5 rue Linois",
        postal="75015",
        district="Paris 15e",
        geo=(48.8469, 2.2848),
        access="Métro Charles Michels (ligne 10)",
        wheelchair=True,
        cover="locations/club-horizon.jpg",
        description="Plateau cardio et musculation avec vue panoramique.",
        hours=hours(WEEK, "07:00", "22:00"),
        team=[],
        offers=[
            dict(title="Accès plateau", summary="Accès immédiat · selon capacité", duration=120, credits=12,
                 mode="open_access", capacity=80),
        ],
    ),
    dict(
        merchant="Le Cercle Yoga",
        name="Le Cercle",
        slug="le-cercle",
        sub="yoga",
        kind="Studio de yoga",
        address="18 rue de Navarin",
        postal="75009",
        district="Paris 9e",
        geo=(48.8806, 2.3393),
        access="Métro Saint-Georges (ligne 12)",
        wheelchair=False,
        cover="locations/le-cercle.jpg",
        description="Yoga vinyasa et hatha dans un espace calme.",
        hours=hours(range(0, 6), "19:00", "20:00"),
        team=[("room", "Salle principale", "Salle"), ("staff", "Camille", "Professeure de yoga")],
        offers=[
            dict(title="Yoga tous niveaux", summary="Vinyasa doux, tapis fournis.", duration=60, credits=14,
                 mode="capacity_session", capacity=14, staff=["Camille"]),
        ],
    ),
    dict(
        merchant="Bloc Nation Escalade",
        name="Bloc Nation",
        slug="bloc-nation",
        sub="escalade",
        kind="Salle d'escalade indoor",
        address="64 boulevard de Charonne",
        postal="75011",
        district="Paris 11e",
        geo=(48.8517, 2.3934),
        access="Métro Nation (lignes 1, 2, 6, 9)",
        wheelchair=False,
        cover="locations/bloc-nation.jpg",
        description="Blocs et voies pour débutants et confirmés, chaussons inclus.",
        hours=hours(WEEK, "10:00", "22:30"),
        team=[("staff", "Hugo", "Moniteur")],
        offers=[
            dict(title="Séance découverte escalade", summary="Initiation encadrée de 90 minutes.",
                 includes="chaussons et magnésie", duration=90, credits=35, mode="capacity_session", capacity=8,
                 staff=["Hugo"]),
        ],
    ),
    dict(
        merchant="Parc Aventure Ouest",
        name="Parc Aventure Bois de Boulogne",
        slug="parc-aventure-bois-de-boulogne",
        sub="parcs",
        kind="Parc aventure",
        address="Route de la Muette",
        postal="75016",
        district="Paris 16e",
        geo=(48.8620, 2.2508),
        access="RER C Avenue Henri Martin",
        wheelchair=False,
        cover="locations/parc-aventure.jpg",
        description="Parcours dans les arbres pour petits et grands.",
        hours=hours([2, 5, 6], "10:00", "18:00"),
        team=[],
        offers=[
            dict(title="Entrée datée", summary="Accès aux parcours pour la journée choisie.", duration=180, credits=35,
                 mode="capacity_session", capacity=60, participants_max=6),
        ],
    ),
    dict(
        merchant="Théâtre Central Productions",
        name="Théâtre Central",
        slug="theatre-central",
        sub="theatre",
        kind="Théâtre",
        address="10 boulevard Poissonnière",
        postal="75002",
        district="Paris 2e",
        geo=(48.8712, 2.3462),
        access="Métro Bonne Nouvelle (lignes 8, 9)",
        wheelchair=True,
        cover="locations/theatre-central.jpg",
        description="Comédies et créations contemporaines.",
        hours=hours([3, 4, 5], "20:30", "22:30"),
        team=[("room", "Grande salle", "Salle")],
        offers=[
            dict(title="Comédie du vendredi", summary="Placement libre en orchestre.", duration=120, credits=28,
                 mode="capacity_session", capacity=200, participants_max=4),
        ],
    ),
    dict(
        merchant="Ciné Villette Exploitation",
        name="Ciné Villette",
        slug="cine-villette",
        sub="cinema",
        kind="Cinéma",
        address="30 quai de la Loire",
        postal="75019",
        district="Paris 19e",
        geo=(48.8879, 2.3747),
        access="Métro Jaurès (lignes 2, 5, 7 bis)",
        wheelchair=True,
        cover="locations/cine-villette.jpg",
        description="Cinéma de quartier, films récents en VF et VOST.",
        hours=hours(WEEK, "10:00", "23:30"),
        team=[],
        offers=[
            dict(title="Place de cinéma", summary="Séance au choix.", duration=120, credits=12, mode="external_ticket",
                 external_note="Billet externe · Fourni par le distributeur"),
        ],
    ),
    dict(
        merchant="Paris Insolite Visites",
        name="Les secrets du Paris méconnu",
        slug="paris-meconnu",
        sub="visites",
        kind="Visite guidée",
        address="Place Saint-Michel",
        postal="75005",
        district="Paris 5e",
        geo=(48.8535, 2.3440),
        access="Métro Saint-Michel (ligne 4)",
        meeting_point="Métro Saint-Michel (sortie 3)",
        wheelchair=True,
        cover="locations/paris-insolite.jpg",
        description="Passages cachés et histoires du Quartier latin avec un guide passionné.",
        hours=hours([5], "10:00", "12:00"),
        team=[("staff", "Antoine", "Guide conférencier")],
        offers=[
            dict(title="Visite guidée en français", summary="Parcours de 2 h dans le Quartier latin.", language="Français",
                 duration=120, credits=24, mode="capacity_session", capacity=15, participants_max=4, staff=["Antoine"]),
        ],
    ),
    dict(
        merchant="Terre & Tour Atelier",
        name="Atelier céramique du 11e",
        slug="atelier-ceramique",
        sub="ateliers",
        kind="Atelier créatif",
        address="22 rue Popincourt",
        postal="75011",
        district="Paris 11e",
        geo=(48.8578, 2.3779),
        access="Métro Voltaire (ligne 9)",
        meeting_point="Atelier du 11e arrondissement",
        wheelchair=True,
        cover="locations/atelier-ceramique.jpg",
        description="Initiez-vous aux techniques de modelage avec une artisane céramiste.",
        hours=hours([6], "14:00", "16:30"),
        team=[("staff", "Lucie", "Céramiste")],
        offers=[
            dict(title="Atelier céramique", summary="Modelage et tournage, 2 h.", includes="Matériel inclus",
                 duration=120, credits=32, mode="capacity_session", capacity=8, participants_max=2, staff=["Lucie"]),
        ],
    ),
    dict(
        merchant="Galerie des Lumières",
        name="Galerie des Lumières",
        slug="galerie-des-lumieres",
        sub="musees",
        kind="Musée",
        address="3 rue des Archives",
        postal="75004",
        district="Paris 4e",
        geo=(48.8573, 2.3549),
        access="Métro Hôtel de Ville (lignes 1, 11)",
        wheelchair=True,
        cover="locations/galerie-des-lumieres.jpg",
        description="Peintures européennes du XVIIIe siècle.",
        hours=hours(range(1, 7), "10:00", "18:00"),
        team=[],
        offers=[
            dict(title="Entrée collections permanentes", summary="Billet daté, audioguide inclus.", duration=90,
                 credits=16, mode="capacity_session", capacity=120, participants_max=4),
        ],
    ),
]

# Marchands en attente : visibles uniquement dans le portail admin.
PENDING_MERCHANTS = [
    ("Musée des Beaux-Arts de la Presqu'île", "Lyon", "pending_review", "pending"),
    ("Le Polaris Scène", "Reims", "documents_missing", "not_started"),
    ("Théâtre de la Rive", "Bordeaux", "pending_review", "not_started"),
]

# Clients de démonstration (aucun rattachement : app mobile). Crédits attribués par une écriture
# « grant » d'origine demo_grant : ce ne sont NI des paiements NI de vraies allocations employeur.
DEMO_CUSTOMERS = [("client@xpass.demo", "Camille Démo")]

DEMO_USERS = [
    ("admin@xpass.demo", "Admin Démo", "platform", None, "platform_admin"),
    ("partenaire@xpass.demo", "Partenaire Démo", "merchant", "Atelier Belle venue SAS", "merchant_owner"),
    ("rh@xpass.demo", "RH Démo", "organization", "Entreprise Démo Horizon", "hr_admin"),
]


def reset(db: Session) -> None:
    """Supprime les données de démo. Le journal étant en ajout seul, les tables transactionnelles
    sont vidées par TRUNCATE (développement uniquement, refusé en production)."""
    from app.core.config import get_settings

    if get_settings().app_env == "production":
        raise SystemExit("--reset est interdit en production.")
    db.execute(text(
        "TRUNCATE credit_journal_lines, credit_journals, credit_lot_balances, credit_lots, wallets, "
        "idempotency_keys, outbox_events, resource_occupancies, external_blocks, bookings, session_inventories, "
        "qr_tokens, redemptions, receipts, partner_payables, partner_adjustments, partner_payouts, "
        "money_journal_lines, money_journals, invoices, subscriptions, payment_webhook_events, "
        "subscription_plans, settlement_terms, employer_allocations, employer_invoices, budget_policies, "
        "employees, employer_contracts, disputes, audit_events, support_requests"
    ))
    db.execute(delete(Membership).where(Membership.user_id.in_(select(User.id).where(User.is_demo.is_(True)))))
    db.execute(delete(User).where(User.is_demo.is_(True)))
    db.execute(delete(Organization).where(Organization.is_demo.is_(True)))
    db.execute(text("UPDATE offers SET current_version_id = NULL WHERE location_id IN "
                    "(SELECT id FROM locations WHERE is_demo)"))
    db.execute(delete(Location).where(Location.is_demo.is_(True)))
    db.execute(delete(Merchant).where(Merchant.is_demo.is_(True)))
    db.execute(delete(Subcategory))
    db.execute(delete(Category))
    db.execute(delete(City))
    db.execute(delete(Market).where(Market.code == "FR"))
    db.flush()


def seed(db: Session, with_accounts: bool = True) -> bool:
    """Catalogue de démonstration ; les comptes de démo (client, commerçant, RH, admin) seulement si demandé."""
    existing = db.scalar(select(Market).where(Market.code == "FR"))
    if existing is not None:
        upgrade_existing(db, existing)
        return False

    fr = Market(code="FR", name="France", country_code="FR", currency="EUR", timezone="Europe/Paris")
    db.add(fr)
    db.flush()

    cities = {}
    for slug, name, lat, lng in [
        ("paris", "Paris", 48.8566, 2.3522),
        ("lyon", "Lyon", 45.7640, 4.8357),
        ("bordeaux", "Bordeaux", 44.8378, -0.5792),
        ("reims", "Reims", 49.2583, 4.0317),
    ]:
        cities[slug] = City(market_id=fr.id, slug=slug, name=name, center=point(lat, lng))
        db.add(cities[slug])

    subs: dict[str, Subcategory] = {}
    for i, c in enumerate(CATEGORIES):
        cat = Category(
            slug=c["slug"],
            name=c["name"],
            eyebrow=c["eyebrow"],
            headline=c["headline"],
            tagline=c["tagline"],
            cta_label=c["cta_label"],
            tile_image_key=f"{M}categories/{c['slug']}.jpg",
            hero_image_key=f"{M}heroes/{c['slug']}.jpg",
            sort_order=i,
        )
        db.add(cat)
        db.flush()
        for j, (slug, name, icon) in enumerate(c["subs"]):
            subs[slug] = Subcategory(category_id=cat.id, slug=slug, name=name, icon=icon, sort_order=j)
            db.add(subs[slug])
    db.flush()

    merchants: dict[str, Merchant] = {}
    for spec in LOCATIONS:
        merchant = Merchant(
            market_id=fr.id,
            legal_name=spec["merchant"],
            display_name=spec["name"],
            commercial_status="approved",
            psp_status="verified",
            # Compte de démonstration : ne fonctionne qu'avec le bac à sable (refusé par un vrai PSP).
            psp_account_id=f"acct_demo_{spec['slug'][:20]}",
            city_label="Paris",
            is_demo=True,
        )
        db.add(merchant)
        db.flush()
        merchants[spec["merchant"]] = merchant

        loc = Location(
            merchant_id=merchant.id,
            city_id=cities["paris"].id,
            subcategory_id=subs[spec["sub"]].id,
            slug=spec["slug"],
            name=spec["name"],
            kind_label=spec["kind"],
            description=spec["description"],
            address_line=spec["address"],
            postal_code=spec["postal"],
            district_label=spec["district"],
            geo=point(*spec["geo"]),
            access_info=spec["access"],
            meeting_point=spec.get("meeting_point"),
            wheelchair_accessible=spec["wheelchair"],
            cover_image_key=f"{M}{spec['cover']}" if spec["cover"] else None,
            status="published",
            is_demo=True,
        )
        db.add(loc)
        db.flush()

        for weekday, opens, closes in spec["hours"]:
            db.add(OpeningHours(location_id=loc.id, weekday=weekday, opens_at=opens, closes_at=closes))

        resources: dict[str, Resource] = {}
        for k, (kind, name, role) in enumerate(spec["team"]):
            resources[name] = Resource(location_id=loc.id, kind=kind, name=name, role_label=role, sort_order=k)
            db.add(resources[name])
        db.flush()

        for k, o in enumerate(spec["offers"]):
            offer = Offer(
                location_id=loc.id,
                booking_mode=o["mode"],
                sort_order=k,
                image_key=f"{M}{o['image']}" if o.get("image") else None,
            )
            offer.resources = [resources[n] for n in o.get("staff", [])]
            db.add(offer)
            db.flush()
            version = OfferVersion(
                offer_id=offer.id,
                version=1,
                title=o["title"],
                summary=o["summary"],
                includes=o.get("includes"),
                language=o.get("language"),
                duration_min=o["duration"],
                price_credits=o["credits"],
                participants_min=1,
                participants_max=o.get("participants_max", 1),
                capacity=o.get("capacity"),
                free_cancellation_hours=24,
                external_ticket_note=o.get("external_note"),
            )
            db.add(version)
            db.flush()
            offer.current_version_id = version.id

    for name, city, commercial, psp in PENDING_MERCHANTS:
        m = Merchant(
            market_id=fr.id,
            legal_name=name,
            display_name=name,
            commercial_status=commercial,
            psp_status=psp,
            city_label=city,
            is_demo=True,
        )
        db.add(m)
        merchants[name] = m

    org = Organization(
        market_id=fr.id, name="Entreprise Démo Horizon", sector_label="Services", city_label="Paris", is_demo=True
    )
    db.add(org)
    db.flush()

    for email, display, scope_type, scope_name, role in (DEMO_USERS if with_accounts else []):
        user = User(email=email, display_name=display, is_demo=True)
        db.add(user)
        db.flush()
        scope_id = None
        if scope_type == "merchant":
            scope_id = merchants[scope_name].id
        elif scope_type == "organization":
            scope_id = org.id
        db.add(Membership(user_id=user.id, scope_type=scope_type, scope_id=scope_id, role=role))

    seed_billing(db, fr)
    seed_employer(db, org)

    for email, display in (DEMO_CUSTOMERS if with_accounts else []):
        customer = User(email=email, display_name=display, is_demo=True)
        db.add(customer)
        db.flush()
        seed_demo_credits(db, customer.id, fr.id)

    db.flush()
    return True


def seed_demo_credits(db: Session, user_id, market_id) -> None:
    from datetime import UTC, datetime, timedelta

    from app.modules.wallet import service as wallet_service

    now = datetime.now(UTC)
    wallet = wallet_service.get_or_create_wallet(db, user_id, market_id, lock=True)
    for source, amount, label, days in [
        ("personal", 50, "Crédits personnels de démonstration", None),
        ("employer", 70, "Lot employeur de démonstration", 60),
        ("promotional", 20, "Crédits promotionnels de démonstration", 30),
    ]:
        wallet_service.grant(
            db, wallet, source=source, amount=amount, label=label, origin_type="demo_grant",
            expires_at=now + timedelta(days=days) if days else None,
        )


def main(argv: list[str]) -> int:
    with SessionLocal() as db, db.begin():
        if "--reset" in argv:
            reset(db)
        # Comptes de démonstration désormais facultatifs : --with-demo-accounts pour les recréer.
        created = seed(db, with_accounts="--with-demo-accounts" in argv)
    print("Données de démonstration créées." if created else "Données de démonstration déjà présentes (--reset pour recréer).")
    return 0


def seed_billing(db: Session, market: Market) -> None:
    """Formule et barème ILLUSTRATIFS (valeurs des maquettes 15 et 22), marqués démonstration.

    À remplacer par les conditions commerciales réelles avant toute mise en production.
    """
    import os
    from datetime import UTC, datetime

    from app.modules.payments.models import SubscriptionPlan
    from app.modules.settlement.models import SettlementTerms

    db.add(SubscriptionPlan(
        market_id=market.id, code="essentiel", name="XPASS Essentiel", price_minor=10000, currency=market.currency,
        credits_per_period=100, credit_validity_days=None, psp_price_id=os.environ.get("PSP_PRICE_ESSENTIEL") or None,
        is_active=True, is_demo=True,
    ))
    db.add(SettlementTerms(
        market_id=market.id, currency=market.currency, gross_minor_per_credit=100, commission_bps=1000,
        effective_from=datetime(2026, 1, 1, tzinfo=UTC), is_demo=True,
    ))
    db.flush()


def upgrade_existing(db: Session, market: Market) -> None:
    """Complète une base de démo créée par un lot précédent (sans rien effacer)."""
    from app.modules.payments.models import SubscriptionPlan

    if db.scalar(select(SubscriptionPlan.id).where(SubscriptionPlan.market_id == market.id).limit(1)) is None:
        seed_billing(db, market)
    from app.modules.employer.models import EmployerContract

    org = db.scalar(select(Organization).where(Organization.is_demo.is_(True), Organization.market_id == market.id))
    if org and db.scalar(select(EmployerContract.id).where(EmployerContract.organization_id == org.id)) is None:
        seed_employer(db, org)
    for loc in db.scalars(select(Location).where(Location.is_demo.is_(True))):
        merchant = db.get(Merchant, loc.merchant_id)
        if merchant.psp_status == "verified" and not merchant.psp_account_id:
            merchant.psp_account_id = f"acct_demo_{loc.slug[:20]}"
    db.flush()



# Salariés fictifs de l'entreprise de démonstration (domaine réservé .demo : aucun e-mail réel).
DEMO_EMPLOYEES = [
    ("client@xpass.demo", "Camille", "Démo"),
    ("lea.martin@horizon.demo", "Léa", "Martin"),
    ("hugo.bernard@horizon.demo", "Hugo", "Bernard"),
    ("ines.petit@horizon.demo", "Inès", "Petit"),
    ("yanis.roux@horizon.demo", "Yanis", "Roux"),
    ("chloe.moreau@horizon.demo", "Chloé", "Moreau"),
]


def seed_employer(db: Session, org: Organization) -> None:
    """Contrat, politique et financement ILLUSTRATIFS (marqués démonstration, aucun virement réel).

    `client@xpass.demo` est invité : il peut accepter l'invitation depuis l'application.
    """
    from datetime import UTC, datetime

    from app.modules.employer import service as employer
    from app.modules.employer.models import Employee, EmployerContract

    today = datetime.now(UTC).date()
    db.add(EmployerContract(organization_id=org.id, status="active", credit_price_minor=100, currency="EUR",
                            payment_terms_days=7, starts_on=today.replace(day=1), is_demo=True))
    db.flush()
    employer.set_policy(db, org, credits_per_month=100, eligible_categories=None, credit_validity_days=60,
                        effective_from=today.replace(day=1), by=None)
    for email, first, last in DEMO_EMPLOYEES:
        db.add(Employee(organization_id=org.id, email=email, first_name=first, last_name=last, status="invited",
                        is_demo=True))
    db.flush()
    invoice = employer.request_funding(db, org, amount_minor=500_000, by=None)
    invoice.is_demo = True
    invoice.label = "Financement employeur (démonstration)"
    employer.confirm_payment(db, invoice.id, by=None)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
