"""Paris reste la seule ville ouverte tant que le réseau n'a pas vraiment démarré."""
from tests.conftest import login


def test_seule_paris_est_ouverte(client):
    cities = client.get("/api/v1/geo/cities").json()
    assert [c["slug"] for c in cities] == ["paris"]


def test_deuxieme_ville_refusee_tant_que_le_reseau_n_est_pas_reel(client):
    admin = login(client, "admin@xpass.demo")
    r = client.post(
        "/api/v1/admin/cities/open",
        headers=admin,
        json={"slug": "lyon", "reason": "Trop tôt pour ouvrir une deuxième ville"},
    )
    assert r.status_code == 409, r.text
    message = r.json()["detail"]["message"]
    assert "Stripe" in message or "facture" in message or "établissement" in message
