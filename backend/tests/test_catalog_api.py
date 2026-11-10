from app.seed.demo import LOCATIONS


def test_health_ready_checks_postgis_and_redis(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["checks"]["redis"] == "ok"


def test_four_categories_with_subcategories(client):
    r = client.get("/api/v1/catalog/categories")
    assert r.status_code == 200
    slugs = [c["slug"] for c in r.json()]
    assert slugs == ["divertissement", "sport", "culture", "beaute"]
    sport = r.json()[1]
    assert [s["slug"] for s in sport["subcategories"]][:3] == ["fitness", "danse", "yoga"]


def test_unknown_category_is_404(client):
    assert client.get("/api/v1/catalog/categories/inconnu").status_code == 404


def test_search_returns_only_published_and_approved(client):
    r = client.get("/api/v1/catalog/locations", params={"limit": 50})
    body = r.json()
    assert body["total"] == len(LOCATIONS)
    names = {i["name"] for i in body["items"]}
    assert "Théâtre de la Rive" not in names  # marchand en attente de validation


def test_filter_by_category_and_subcategory(client):
    r = client.get("/api/v1/catalog/locations", params={"category": "sport"})
    assert {i["category_slug"] for i in r.json()["items"]} == {"sport"}
    r = client.get("/api/v1/catalog/locations", params={"category": "sport", "subcategory": "yoga"})
    assert [i["slug"] for i in r.json()["items"]] == ["le-cercle"]


def test_text_search_ignores_accents_and_case(client):
    r = client.get("/api/v1/catalog/locations", params={"q": "CERAMIQUE"})
    assert [i["slug"] for i in r.json()["items"]] == ["atelier-ceramique"]
    # Correspondance sur le titre d'une offre
    r = client.get("/api/v1/catalog/locations", params={"q": "brushing"})
    assert [i["slug"] for i in r.json()["items"]] == ["atelier-belle-venue"]


def test_like_wildcards_are_escaped(client):
    r = client.get("/api/v1/catalog/locations", params={"q": "%"})
    assert r.json()["total"] == 0


def test_max_credits_filter(client):
    r = client.get("/api/v1/catalog/locations", params={"max_credits": 14, "limit": 50})
    slugs = {i["slug"] for i in r.json()["items"]}
    assert slugs == {"club-horizon", "studio-elan", "le-cercle", "cine-villette"}


def test_distance_sort_from_position(client):
    # Position place Saint-Michel : la visite guidée doit être la plus proche.
    r = client.get("/api/v1/catalog/locations", params={"lat": 48.8535, "lng": 2.3440, "limit": 50})
    items = r.json()["items"]
    assert items[0]["slug"] == "paris-meconnu"
    distances = [i["distance_m"] for i in items]
    assert distances == sorted(distances)


def test_lat_without_lng_is_rejected(client):
    assert client.get("/api/v1/catalog/locations", params={"lat": 48.8}).status_code == 422


def test_location_detail(client):
    r = client.get("/api/v1/catalog/locations/atelier-belle-venue")
    assert r.status_code == 200
    d = r.json()
    assert d["address_line"] == "12 rue Oberkampf"
    assert d["hours_summary"] == "Lundi – Samedi : 9h00 – 19h00"
    assert [o["title"] for o in d["offers"]][0] == "Coupe et coiffage"
    assert d["offers"][0]["price_credits"] == 18
    assert {t["name"] for t in d["team"]} >= {"Sarah", "Lina"}
    slot = d["offers"][0]["next_slot"]
    assert slot is None or slot["indicative"] is True
    if slot:
        # Heure murale Europe/Paris, cohérente avec l'instant absolu.
        assert slot["starts_at"].startswith(slot["local_start"])


def test_external_ticket_has_no_slot(client):
    d = client.get("/api/v1/catalog/locations/cine-villette").json()
    assert d["offers"][0]["booking_mode"] == "external_ticket"
    assert d["offers"][0]["next_slot"] is None


def test_unknown_location_is_404(client):
    assert client.get("/api/v1/catalog/locations/nexiste-pas").status_code == 404
    assert client.get("/api/v1/catalog/locations/00000000-0000-0000-0000-000000000000").status_code == 404


def test_map_search_by_radius_returns_coordinates(client):
    loc = client.get("/api/v1/catalog/locations/atelier-belle-venue").json()
    lat, lng = loc["latitude"], loc["longitude"]
    near = client.get("/api/v1/catalog/locations", params={"lat": lat, "lng": lng, "radius_m": 1000, "limit": 50}).json()
    assert "atelier-belle-venue" in [i["slug"] for i in near["items"]]
    assert all(i["distance_m"] <= 1000 for i in near["items"])
    assert all(i["latitude"] is not None and i["longitude"] is not None for i in near["items"])
    wide = client.get("/api/v1/catalog/locations", params={"lat": lat, "lng": lng, "radius_m": 25000, "limit": 50}).json()
    assert wide["total"] >= near["total"]
    # Budget et catégorie combinés au rayon.
    cheap = client.get("/api/v1/catalog/locations",
                       params={"lat": lat, "lng": lng, "radius_m": 25000, "max_credits": 15, "category": "beaute"}).json()
    assert all(i["category_slug"] == "beaute" for i in cheap["items"])
    assert client.get("/api/v1/catalog/locations", params={"radius_m": 1000}).status_code == 422
