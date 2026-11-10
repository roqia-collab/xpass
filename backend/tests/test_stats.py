"""Statistiques commerçant : visites, clients, crédits, montants, tendance, prestations les plus utilisées."""
from tests.conftest import login
from tests.test_admin import redeemed_booking
from tests.test_redemption import new_operator


def _venue(client, h) -> str:
    return next(x["id"] for x in client.get("/api/v1/partner/locations", headers=h).json() if x["slug"] == "atelier-belle-venue")


def test_stats_follow_redemptions(client):
    owner = login(client, "partenaire@xpass.demo")
    loc = _venue(client, owner)
    before = client.get(f"/api/v1/partner/locations/{loc}/stats?days=30", headers=owner)
    assert before.status_code == 200, before.text
    redeemed_booking(client)
    after = client.get(f"/api/v1/partner/locations/{loc}/stats?days=30", headers=owner).json()
    b = before.json()
    assert after["visits"] == b["visits"] + 1 and after["unique_customers"] >= 1
    assert after["credits_used"] > b["credits_used"]
    assert after["net_minor"] == after["gross_minor"] - after["commission_minor"]
    assert sum(w["visits"] for w in after["weeks"]) == after["visits"]
    assert sum(after["weekdays"]) == after["visits"] and len(after["weekdays"]) == 7
    assert any(o["title"] == "Coupe et coiffage" for o in after["top_offers"])
    assert after["currency"] == "EUR"


def test_stats_rules(client):
    owner = login(client, "partenaire@xpass.demo")
    loc = _venue(client, owner)
    assert client.get(f"/api/v1/partner/locations/{loc}/stats?days=12", headers=owner).status_code == 422
    # Montants financiers : réservés au responsable.
    assert client.get(f"/api/v1/partner/locations/{loc}/stats", headers=login(client, new_operator())).status_code == 403
    assert client.get(f"/api/v1/partner/locations/{loc}/stats", headers=login(client, "client@xpass.demo")).status_code == 403
