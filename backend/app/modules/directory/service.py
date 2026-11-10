"""Services publics français, gratuits et sans clé : annuaire des entreprises (SIRET) et Base Adresse Nationale.

- Annuaire : https://recherche-entreprises.api.gouv.fr (données SIRENE de l'INSEE).
- Adresses : Géoplateforme de l'IGN (Base Adresse Nationale), https://data.geopf.fr/geocodage.

Une indisponibilité n'est jamais présentée comme une vérification réussie : `ServiceUnavailable` est levée et
l'appelant enregistre l'état « non vérifié » pour l'équipe XPASS.
"""
import re
from dataclasses import asdict, dataclass

import httpx

from app.core.config import get_settings

TIMEOUT = httpx.Timeout(8.0, connect=4.0)
HEADERS = {"User-Agent": "XPASS (inscription des partenaires)"}


class ServiceUnavailable(Exception):
    """Le service public n'a pas répondu ou a répondu en erreur."""


# ---------------------------------------------------------------- SIRET


def normalize_siret(raw: str) -> str:
    return re.sub(r"\s+", "", raw or "")


def siret_is_valid(siret: str) -> bool:
    """14 chiffres et clé de Luhn (règle particulière de La Poste : somme des chiffres multiple de 5)."""
    if not re.fullmatch(r"\d{14}", siret):
        return False
    total = 0
    for i, c in enumerate(reversed(siret)):
        d = int(c) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    if total % 10 == 0:
        return True
    return siret.startswith("356000000") and sum(int(c) for c in siret) % 5 == 0


@dataclass
class Company:
    siret: str
    siren: str
    legal_name: str
    trade_name: str | None
    active: bool
    address: str
    postal_code: str
    city: str
    naf_code: str | None
    head_office: bool

    def as_dict(self) -> dict:
        return asdict(self)


def lookup_siret(siret: str) -> Company | None:
    """Établissement correspondant au SIRET, ou None s'il n'existe pas dans l'annuaire."""
    url = f"{get_settings().sirene_api_url.rstrip('/')}/search"
    try:
        r = httpx.get(url, params={"q": siret, "per_page": 1}, timeout=TIMEOUT, headers=HEADERS)
    except httpx.HTTPError as exc:
        raise ServiceUnavailable(str(exc)) from exc
    if r.status_code != 200:
        raise ServiceUnavailable(f"annuaire HTTP {r.status_code}")
    for result in r.json().get("results") or []:
        for etab in result.get("matching_etablissements") or []:
            if etab.get("siret") != siret:
                continue
            signs = etab.get("liste_enseignes") or []
            return Company(
                siret=siret,
                siren=result.get("siren") or siret[:9],
                legal_name=result.get("nom_raison_sociale") or result.get("nom_complet") or "",
                trade_name=etab.get("nom_commercial") or (signs[0] if signs else None),
                active=etab.get("etat_administratif") == "A" and result.get("etat_administratif") == "A",
                address=etab.get("adresse") or "",
                postal_code=etab.get("code_postal") or "",
                city=etab.get("libelle_commune") or "",
                naf_code=etab.get("activite_principale"),
                head_office=bool(etab.get("est_siege")),
            )
    return None


# ---------------------------------------------------------------- adresses


@dataclass
class Place:
    label: str
    latitude: float
    longitude: float
    score: float
    housenumber: str | None
    street: str | None
    postal_code: str
    city: str
    district: str | None


MIN_SCORE = 0.5


def street_from_label(address: str, postal_code: str = "", city: str = "") -> str:
    """Rue exploitable : enlève le complément SIRENE (bâtiment, CEDEX) et part du numéro."""
    line = address or ""
    if postal_code:
        line = re.sub(re.escape(postal_code), " ", line, flags=re.I)
    if city:
        line = re.sub(re.escape(city), " ", line, flags=re.I)
    numbered = re.search(r"\d+\s+\S.*", line)
    return re.sub(r"\s+", " ", (numbered.group(0) if numbered else line)).strip(" ,")


def _place_from_feature(f: dict, postal_code: str, city: str) -> Place | None:
    p = f.get("properties") or {}
    if float(p.get("score") or 0) < MIN_SCORE or p.get("type") not in ("housenumber", "street", "locality"):
        return None
    lng, lat = f["geometry"]["coordinates"]
    return Place(
        label=p.get("label") or "",
        latitude=float(lat),
        longitude=float(lng),
        score=float(p.get("score") or 0),
        housenumber=p.get("housenumber"),
        street=p.get("street") or p.get("name"),
        postal_code=p.get("postcode") or postal_code,
        city=p.get("city") or city,
        district=p.get("district"),
    )


def geocode(address_line: str, postal_code: str, city: str) -> Place | None:
    """Position d'une adresse française, ou None si elle n'est pas trouvée avec une confiance suffisante."""
    url = f"{get_settings().geocoder_url.rstrip('/')}/search"
    street = street_from_label(address_line, postal_code, city) or address_line
    queries: list[dict[str, str]] = [{"q": f"{street} {postal_code} {city}".strip(), "limit": "1"}]
    if re.fullmatch(r"\d{5}", postal_code or ""):
        queries.insert(0, {**queries[0], "postcode": postal_code})
    seen: set[tuple[str, str]] = set()
    for params in queries:
        key = (params["q"], params.get("postcode", ""))
        if key in seen:
            continue
        seen.add(key)
        try:
            r = httpx.get(url, params=params, timeout=TIMEOUT, headers=HEADERS)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if r.status_code != 200:
            raise ServiceUnavailable(f"géocodage HTTP {r.status_code}")
        features = r.json().get("features") or []
        if not features:
            continue
        place = _place_from_feature(features[0], postal_code, city)
        if place is not None:
            return place
    return None


def district_label(postal_code: str, city: str) -> str:
    """« Paris 11e », « Lyon 3e », sinon le nom de la commune."""
    arrondissements = {"75": "Paris", "69": "Lyon", "13": "Marseille"}
    prefix = arrondissements.get(postal_code[:2])
    if prefix and city.lower().startswith(prefix.lower()):
        n = int(postal_code[-2:]) if postal_code[-2:].isdigit() else 0
        if prefix == "Paris" and 1 <= n <= 20:
            return f"Paris {n}{'er' if n == 1 else 'e'}"
        if prefix == "Lyon" and postal_code.startswith("6900") and 1 <= n <= 9:
            return f"Lyon {n}{'er' if n == 1 else 'e'}"
        if prefix == "Marseille" and postal_code.startswith("130") and 1 <= n <= 16:
            return f"Marseille {n}{'er' if n == 1 else 'e'}"
    return city[:40]
