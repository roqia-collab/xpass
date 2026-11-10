"""Extrait des photos PLACEHOLDER depuis les maquettes PNG pour le développement local.

Ces images sont des recadrages des maquettes générées : elles ne sont pas des
photographies originales dont les droits sont acquis. Elles doivent être
remplacées avant toute mise en production.

Usage (depuis la racine du projet) :
    python infra/seed-media/extract_placeholders.py
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MOCKS = ROOT / "28_interfaces"
OUT = Path(__file__).resolve().parent / "placeholders"

# (fichier maquette, boîte (gauche, haut, droite, bas), clé de sortie)
CROPS = [
    ("01_Accueil_client.png", (36, 242, 431, 478), "categories/divertissement.jpg"),
    ("01_Accueil_client.png", (458, 242, 853, 478), "categories/sport.jpg"),
    ("01_Accueil_client.png", (36, 590, 431, 830), "categories/culture.jpg"),
    ("01_Accueil_client.png", (458, 590, 853, 830), "categories/beaute.jpg"),
    ("01_Accueil_client.png", (30, 1042, 443, 1300), "locations/bloc-nation.jpg"),
    ("08_Fiche_partenaire.png", (0, 70, 887, 482), "locations/atelier-belle-venue.jpg"),
    ("08_Fiche_partenaire.png", (47, 768, 270, 933), "offers/coupe-coiffage.jpg"),
    ("04_Activite_sportive.png", (32, 615, 821, 756), "locations/studio-elan.jpg"),
    ("04_Activite_sportive.png", (32, 990, 821, 1131), "locations/club-horizon.jpg"),
    ("04_Activite_sportive.png", (32, 1307, 615, 1470), "locations/le-cercle.jpg"),
    ("04_Activite_sportive.png", (480, 80, 853, 380), "heroes/sport.jpg"),
    ("03_Divertissement.png", (30, 530, 484, 842), "locations/parc-aventure.jpg"),
    ("03_Divertissement.png", (30, 862, 484, 1117), "locations/theatre-central.jpg"),
    ("03_Divertissement.png", (30, 1137, 484, 1384), "locations/cine-villette.jpg"),
    ("06_Beaute.png", (27, 562, 915, 800), "locations/atelier-belle-salon.jpg"),
    ("06_Beaute.png", (27, 1040, 915, 1276), "locations/atelier-des-mains.jpg"),
    ("06_Beaute.png", (500, 95, 941, 392), "heroes/beaute.jpg"),
    ("05_Activite_culturelle.png", (30, 640, 452, 965), "locations/paris-insolite.jpg"),
    ("05_Activite_culturelle.png", (30, 1080, 452, 1435), "locations/atelier-ceramique.jpg"),
    ("05_Activite_culturelle.png", (660, 110, 940, 400), "heroes/culture.jpg"),
    ("01_Accueil_client.png", (36, 242, 431, 478), "heroes/divertissement.jpg"),
    # Galerie des Lumières : la salle de tableaux de la tuile « Activité culturelle » (maquette 01).
    ("01_Accueil_client.png", (36, 590, 431, 830), "locations/galerie-des-lumieres.jpg"),
    # Photos d'écran (en-têtes) — boutons et textes des maquettes exclus du cadre.
    ("02_Connexion_et_inscription.png", (500, 90, 853, 600), "screens/login.jpg"),
    ("14_Mes_credits.png", (530, 80, 853, 330), "screens/credits.jpg"),
    ("16_Profil_et_assistance.png", (500, 80, 850, 270), "screens/profile.jpg"),
    ("15_Abonnement.png", (485, 318, 870, 610), "screens/subscription.jpg"),
    ("12_Reservation_et_QR.png", (450, 80, 941, 330), "screens/confirmed.jpg"),
    ("13_Recu_et_avis.png", (590, 120, 887, 480), "screens/receipt.jpg"),
    # Photos des prestations (maquettes 09 et 21).
    ("09_Calendrier.png", (24, 100, 828, 512), "offers/brushing.jpg"),
    ("21_Prestations_et_equipe.png", (277, 535, 416, 667), "offers/coloration.jpg"),
    ("21_Prestations_et_equipe.png", (277, 693, 416, 810), "offers/barbe.jpg"),
]

# Visuels des portails (servis par Next.js depuis apps/portals/public/visuels).
PORTAL_OUT = ROOT / "apps" / "portals" / "public" / "visuels"
PORTAL_CROPS = [
    ("21_Prestations_et_equipe.png", (16, 711, 210, 878), "promo-partenaires.jpg"),
    ("26_Administration_operations.png", (0, 460, 240, 750), "promo-administration.jpg"),
    ("22_Reglements_commercant.png", (960, 60, 1536, 283), "reglements.jpg"),
    ("23_Portail_RH_budgets.png", (941, 97, 1509, 299), "budgets.jpg"),
    ("24_RH_salaries_invitations.png", (808, 56, 1536, 285), "salaries.jpg"),
    ("25_RH_factures_rapports.png", (747, 60, 1536, 242), "factures.jpg"),
]


def main() -> None:
    for name, box, key in CROPS:
        dest = OUT / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        Image.open(MOCKS / name).convert("RGB").crop(box).save(dest, "JPEG", quality=85)
        print("ok", key)
    PORTAL_OUT.mkdir(parents=True, exist_ok=True)
    for name, box, key in PORTAL_CROPS:
        Image.open(MOCKS / name).convert("RGB").crop(box).save(PORTAL_OUT / key, "JPEG", quality=85)
        print("ok portail", key)

    logo = Image.open(ROOT / "logo" / "XPASS_logo_proposition.png").convert("RGBA")
    w, h = logo.size
    brand = OUT / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    # Logo complet sans marges blanches, et symbole carré seul.
    logo.crop((int(w * 0.08), int(h * 0.16), int(w * 0.92), int(h * 0.82))).save(brand / "logo.png")
    logo.crop((int(w * 0.085), int(h * 0.17), int(w * 0.305), int(h * 0.8))).save(brand / "mark.png")
    print("ok brand")


if __name__ == "__main__":
    main()
