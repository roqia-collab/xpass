"""Avantage salarié (lot 6) : invitations, CSV, financement, allocations uniques, rapports agrégés."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.modules.catalog.models import Market
from app.modules.employer import service as employer
from app.modules.employer.models import EmployerContract
from app.modules.identity.models import Membership, Organization, User
from tests.conftest import login
from tests.test_bookings import COUPE, free_slot, hold, post, wallet
from tests.test_redemption import new_operator, redeem


def _user(prefix: str = "u") -> str:
    email = f"{prefix}-{uuid.uuid4().hex[:10]}@xpass.demo"
    with SessionLocal() as db, db.begin():
        db.add(User(email=email, display_name=prefix.title(), is_demo=True))
    return email


def make_org(*, funding_minor: int = 100_000, credits: int = 100, status: str = "active") -> tuple[str, str]:
    """Organisation isolée : (identifiant, e-mail de son administrateur RH)."""
    hr = _user("rh")
    with SessionLocal() as db, db.begin():
        market = db.scalar(select(Market).where(Market.code == "FR"))
        org = Organization(market_id=market.id, name=f"Org {uuid.uuid4().hex[:6]}", is_demo=True)
        db.add(org)
        db.flush()
        user_id = db.scalar(select(User.id).where(User.email == hr))
        db.add(Membership(user_id=user_id, scope_type="organization", scope_id=org.id, role="hr_admin"))
        today = datetime.now(UTC).date()
        db.add(EmployerContract(organization_id=org.id, status=status, credit_price_minor=100, currency="EUR",
                                starts_on=today.replace(day=1), is_demo=True))
        db.flush()
        employer.set_policy(db, org, credits_per_month=credits, eligible_categories=None, credit_validity_days=60,
                            effective_from=employer.current_period(db, org), by=None)
        if funding_minor:
            inv = employer.request_funding(db, org, amount_minor=funding_minor, by=None)
            employer.confirm_payment(db, inv.id, by=None)
        return str(org.id), hr


def invite(client, hr_headers, email: str) -> dict:
    r = client.post("/api/v1/company/employees", json={"email": email, "first_name": "Prénom", "last_name": "Nom"},
                    headers=hr_headers)
    assert r.status_code == 201, r.text
    return r.json()


def accept(client, email: str) -> dict:
    h = login(client, email)
    inv = client.get("/api/v1/me/employer-invitations", headers=h).json()
    assert len(inv) == 1, inv
    r = client.post(f"/api/v1/me/employer-invitations/{inv[0]['id']}/accept", headers=h)
    assert r.status_code == 200, r.text
    return h


# ---------------------------------------------------------------- droits


def test_rights(client):
    _, hr = make_org()
    hr_h = login(client, hr)
    assert client.get("/api/v1/company/overview", headers=hr_h).json()["can_edit"] is True
    for other in ("partenaire@xpass.demo", _user("client")):
        h = login(client, other)
        assert client.get("/api/v1/company/overview", headers=h).status_code == 403
        assert client.post("/api/v1/company/employees", json={"email": "x@y.fr"}, headers=h).status_code == 403
    # RH en lecture seule.
    viewer = _user("viewer")
    org_id = client.get("/api/v1/company/organization", headers=hr_h).json()["id"]
    with SessionLocal() as db, db.begin():
        uid = db.scalar(select(User.id).where(User.email == viewer))
        db.add(Membership(user_id=uid, scope_type="organization", scope_id=org_id, role="hr_viewer"))
    vh = login(client, viewer)
    assert client.get("/api/v1/company/employees", headers=vh).status_code == 200
    r = client.post("/api/v1/company/employees", json={"email": "a@b.fr"}, headers=vh)
    assert r.status_code == 403 and "administrateurs RH" in r.json()["detail"]["message"]
    # Confirmation d'un paiement : administration XPASS uniquement.
    inv = client.post("/api/v1/company/invoices", json={"amount_minor": 10000}, headers=hr_h).json()
    assert client.post(f"/api/v1/admin/employer-invoices/{inv['id']}/confirm-payment", headers=hr_h).status_code == 403


# ---------------------------------------------------------------- invitations


def test_invite_and_csv_import(client):
    _, hr = make_org()
    h = login(client, hr)
    invite(client, h, "Sophie.Dupont@Exemple.fr")
    dup = client.post("/api/v1/company/employees", json={"email": "sophie.dupont@exemple.fr"}, headers=h)
    assert dup.status_code == 409
    bad = client.post("/api/v1/company/employees", json={"email": "aline.martin@"}, headers=h)
    assert bad.json()["detail"]["code"] == "invalid_email"

    content = ("Prénom;Nom;Email\n"
               "Camille;Laurent;camille.laurent@exemple.fr\n"
               "Sophie;Dupont;sophie.dupont@exemple.fr\n"
               "Aline;Martin;aline.martin@\n"
               "Tom;Bernard;tom.bernard@exemple.fr\n"
               "Tom;Bernard;TOM.BERNARD@exemple.fr\n"
               "\n")
    pv = client.post("/api/v1/company/employees/import/preview", json={"content": content}, headers=h).json()
    assert pv["mapping"] == {"email": "Email", "last_name": "Nom", "first_name": "Prénom"}
    assert (pv["valid_count"], pv["duplicate_count"], pv["invalid_count"]) == (2, 2, 1)
    assert {(e["line"], e["problem"]) for e in pv["errors"]} == {(3, "duplicate"), (4, "invalid_email"), (6, "duplicate")}
    # Rien n'est créé par l'aperçu.
    assert len(client.get("/api/v1/company/employees", headers=h).json()) == 1
    assert client.post("/api/v1/company/employees/import", json={"content": content}, headers=h).json() == {"created": 2}
    assert client.post("/api/v1/company/employees/import", json={"content": content}, headers=h).json() == {"created": 0}
    emails = {e["email"] for e in client.get("/api/v1/company/employees", headers=h).json()}
    assert emails == {"sophie.dupont@exemple.fr", "camille.laurent@exemple.fr", "tom.bernard@exemple.fr"}
    # Colonnes non reconnues : correspondance explicite.
    custom = "Mail pro,Nom de famille\nzoe@exemple.fr,Durand\n"
    err = client.post("/api/v1/company/employees/import/preview", json={"content": "A,B\nx,y\n"}, headers=h)
    assert err.json()["detail"]["code"] == "missing_email_column" and err.json()["detail"]["headers"] == ["A", "B"]
    pv = client.post("/api/v1/company/employees/import/preview",
                     json={"content": custom, "mapping": {"email": "Mail pro", "last_name": "Nom de famille"}}, headers=h)
    assert pv.json()["valid_count"] == 1


def test_only_the_invited_email_can_accept(client):
    _, hr = make_org()
    email = _user("salarie")
    invite(client, login(client, hr), email)
    intruder = login(client, _user("intrus"))
    assert client.get("/api/v1/me/employer-invitations", headers=intruder).json() == []
    emp_id = client.get("/api/v1/company/employees", headers=login(client, hr)).json()[0]["id"]
    assert client.post(f"/api/v1/me/employer-invitations/{emp_id}/accept", headers=intruder).status_code == 404
    h = accept(client, email)
    assert client.post(f"/api/v1/me/employer-invitations/{emp_id}/accept", headers=h).status_code == 409


# ---------------------------------------------------------------- allocations


def test_acceptance_allocates_monthly_credits_once(client):
    org_id, hr = make_org(credits=80)
    email = _user("salarie")
    invite(client, login(client, hr), email)
    h = accept(client, email)
    w = wallet(client, h)
    assert w["by_source"]["employer"]["available"] == 80
    lot = next(l for l in w["lots"] if l["source"] == "employer")
    assert lot["origin_type"] == "employer_allocation" and lot["expires_at"] is not None
    with SessionLocal() as db, db.begin():
        org = db.get(Organization, uuid.UUID(org_id))
        period = employer.current_period(db, org)
        assert employer.allocate_period(db, org, period).allocated == 0  # déjà attribué ce mois-ci
    assert wallet(client, h)["by_source"]["employer"]["available"] == 80
    report = client.get("/api/v1/company/report", headers=login(client, hr)).json()
    assert (report["active"], report["allocated_credits"], report["allocated_cost_minor"]) == (1, 80, 8000)
    assert report["balance_minor"] == 100_000 - 8000


def test_insufficient_funding_blocks_then_payment_unblocks(client):
    _, hr = make_org(funding_minor=15_000, credits=100)  # 150 € : un seul salarié couvert (100 €)
    hr_h = login(client, hr)
    a, b = _user("a"), _user("b")
    invite(client, hr_h, a)
    invite(client, hr_h, b)
    ha, hb = accept(client, a), accept(client, b)
    assert wallet(client, ha)["by_source"]["employer"]["available"] == 100
    assert wallet(client, hb)["by_source"]["employer"]["available"] == 0
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM outbox_events WHERE event_type = 'employer.funding_insufficient' "
                              "AND payload->>'employees' = '1'")) >= 1
    # Demande de financement : facture en attente, rien ne bouge tant que le virement n'est pas confirmé.
    inv = client.post("/api/v1/company/invoices", json={"amount_minor": 10_000}, headers=hr_h).json()
    assert inv["status"] == "pending" and inv["reference"].startswith("FAC-")
    assert client.post("/api/v1/company/invoices", json={"amount_minor": 10_050}, headers=hr_h).status_code == 422
    assert wallet(client, hb)["by_source"]["employer"]["available"] == 0
    admin = login(client, "admin@xpass.demo")
    assert client.post(f"/api/v1/admin/employer-invoices/{inv['id']}/confirm-payment", headers=admin).status_code == 200
    assert client.post(f"/api/v1/admin/employer-invoices/{inv['id']}/confirm-payment", headers=admin).status_code == 409
    assert wallet(client, hb)["by_source"]["employer"]["available"] == 100
    assert client.get("/api/v1/company/report", headers=hr_h).json()["balance_minor"] == 5_000


def test_contract_not_active_allocates_nothing(client):
    _, hr = make_org(status="suspended", funding_minor=0)
    email = _user("salarie")
    invite(client, login(client, hr), email)
    assert wallet(client, accept(client, email))["by_source"]["employer"]["available"] == 0


def test_concurrent_allocation_runs_never_double_allocate(client):
    org_id, hr = make_org(funding_minor=50_000)
    emails = [_user("c") for _ in range(3)]
    hr_h = login(client, hr)
    for e in emails:
        invite(client, hr_h, e)
    # Liaison directe sans allocation (contrat suspendu le temps de l'acceptation).
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE employer_contracts SET status = 'suspended' WHERE organization_id = :o"), {"o": org_id})
    headers = [accept(client, e) for e in emails]
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE employer_contracts SET status = 'active' WHERE organization_id = :o"), {"o": org_id})
    barrier = Barrier(4)

    def run(_):
        barrier.wait()
        with SessionLocal() as db, db.begin():
            org = db.get(Organization, uuid.UUID(org_id))
            return employer.allocate_period(db, org, employer.current_period(db, org)).allocated

    with ThreadPoolExecutor(4) as pool:
        assert sum(pool.map(run, range(4))) == 3
    assert [wallet(client, h)["by_source"]["employer"]["available"] for h in headers] == [100, 100, 100]


def test_suspension_stops_future_allocations_but_keeps_credits(client):
    org_id, hr = make_org()
    email = _user("salarie")
    hr_h = login(client, hr)
    invite(client, hr_h, email)
    h = accept(client, email)
    emp_id = client.get("/api/v1/company/employees", headers=hr_h).json()[0]["id"]
    assert client.post(f"/api/v1/company/employees/{emp_id}/suspend", headers=hr_h).json() == {"status": "suspended"}
    with SessionLocal() as db, db.begin():
        org = db.get(Organization, uuid.UUID(org_id))
        next_month = (employer.current_period(db, org) + timedelta(days=32)).replace(day=1)
        assert employer.allocate_period(db, org, next_month).allocated == 0
    assert wallet(client, h)["by_source"]["employer"]["available"] == 100
    assert client.post(f"/api/v1/company/employees/{emp_id}/reactivate", headers=hr_h).json() == {"status": "active"}


# ---------------------------------------------------------------- politique


def test_policy_changes_apply_to_future_months(client):
    org_id, hr = make_org()
    hr_h = login(client, hr)
    email = _user("salarie")
    invite(client, hr_h, email)
    accept(client, email)
    ov = client.get("/api/v1/company/overview", headers=hr_h).json()
    period = ov["report"]["period"]
    r = client.put("/api/v1/company/policy", json={"credits_per_month": 150, "effective_from": period}, headers=hr_h)
    assert r.json()["detail"]["code"] == "period_started"
    nxt = (datetime.fromisoformat(period) + timedelta(days=32)).date().replace(day=1).isoformat()
    body = {"credits_per_month": 150, "eligible_categories": ["sport", "culture"], "effective_from": nxt}
    assert client.put("/api/v1/company/policy", json=body, headers=hr_h).status_code == 200
    ov = client.get("/api/v1/company/overview", headers=hr_h).json()
    assert ov["policy"]["credits_per_month"] == 100 and ov["next_policy"]["credits_per_month"] == 150
    bad = client.put("/api/v1/company/policy", json={**body, "eligible_categories": ["inconnue"]}, headers=hr_h)
    assert bad.json()["detail"]["code"] == "invalid_categories"


# ---------------------------------------------------------------- rapports


def test_reports_are_aggregated_with_privacy_threshold(client):
    _, hr = make_org()
    hr_h = login(client, hr)
    email = _user("salarie")
    invite(client, hr_h, email)
    h = accept(client, email)
    # Le salarié réserve et consomme avec ses crédits employeur.
    oid = COUPE()
    b = hold(client, h, oid, free_slot(client, oid)).json()
    assert b["funding"] == [{"source": "employer", "credits": 18}]
    post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE bookings SET starts_at = now() + interval '10 minutes', "
                        "ends_at = now() + interval '40 minutes' WHERE id = :id"), {"id": b["id"]})
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    assert redeem(client, login(client, new_operator()), {"qr": p["qr_payload"]}).status_code == 201

    r = client.get("/api/v1/company/report", headers=hr_h).json()
    assert r["consumed_credits"] == 18 and r["consumed_cost_minor"] == 1800
    beaute = next(c for c in r["categories"] if c["slug"] == "beaute")
    assert beaute == {"slug": "beaute", "name": beaute["name"], "masked": True, "share": None, "employees": None}
    csv = client.get("/api/v1/company/report.csv", headers=hr_h)
    assert csv.status_code == 200 and "masqué" in csv.text and "Crédits utilisés;18" in csv.text
    cal = client.get("/api/v1/company/allocations", headers=hr_h).json()
    assert cal and cal[0]["employees"] == 1 and cal[0]["credits"] == 100
