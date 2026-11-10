"""Valorisation des dettes partenaires, versements hebdomadaires et rapprochement.

- Valorisation : crédits × valeur du barème en vigueur à la date de la prestation ; commission
  arrondie au centime le plus proche (demi vers le haut). Écriture monétaire équilibrée.
- Versement : une ligne par établissement marchand et par semaine fermée (lundi -> dimanche, fuseau
  du marché). Il reprend toutes les dettes valorisées et tous les ajustements non encore versés.
- Le transfert est demandé au prestataire après commit ; seul le webhook signé du prestataire
  marque le versement « confirmé ». Un montant différent du net attendu passe « à rapprocher ».
"""
import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalog.models import Market, Merchant
from app.modules.payments.service import PaymentAnomaly, RetryLater, post_money
from app.modules.platform.service import emit
from app.modules.redemption.models import PartnerPayable
from app.modules.settlement.models import PartnerAdjustment, PartnerPayout, SettlementTerms


def commission_of(gross_minor: int, bps: int) -> int:
    return (gross_minor * bps + 5000) // 10000


def terms_at(db: Session, market_id: uuid.UUID, at: datetime) -> SettlementTerms | None:
    return db.scalar(
        select(SettlementTerms)
        .where(SettlementTerms.market_id == market_id, SettlementTerms.effective_from <= at)
        .order_by(SettlementTerms.effective_from.desc())
        .limit(1)
    )


def value_payable(db: Session, payable: PartnerPayable, now: datetime | None = None) -> bool:
    """Valorise une dette ; sans barème applicable, elle reste « à valoriser »."""
    if payable.status != "pending_valuation":
        return False
    merchant = db.get(Merchant, payable.merchant_id)
    terms = terms_at(db, merchant.market_id, payable.occurred_at)
    if terms is None:
        return False
    gross = payable.credits * terms.gross_minor_per_credit
    commission = commission_of(gross, terms.commission_bps)
    payable.amount_minor, payable.commission_minor, payable.currency = gross, commission, terms.currency
    payable.status, payable.valued_at = "valued", now or datetime.now(UTC)
    post_money(
        db, kind="payable_valued", memo=f"Prestation ({payable.kind})", ref_type="partner_payable", ref_id=payable.id,
        lines=[
            ("partner_expense", gross, terms.currency, None),
            ("partner_payable", -(gross - commission), terms.currency, merchant.id),
            ("commission_revenue", -commission, terms.currency, None),
        ],
    )
    return True


def value_pending(db: Session, limit: int = 500) -> int:
    rows = db.scalars(
        select(PartnerPayable).where(PartnerPayable.status == "pending_valuation").limit(limit).with_for_update(skip_locked=True)
    ).all()
    return sum(1 for p in rows if value_payable(db, p))


def create_adjustment(db: Session, *, merchant_id: uuid.UUID, amount_minor: int, label: str,
                      created_by: uuid.UUID | None) -> PartnerAdjustment:
    """Avoir (négatif) ou complément (positif). Interface d'administration : lot 7."""
    merchant = db.get(Merchant, merchant_id)
    currency = db.scalar(select(Market.currency).where(Market.id == merchant.market_id))
    n = db.scalar(text("SELECT nextval('adjustment_reference_seq')"))
    adj = PartnerAdjustment(merchant_id=merchant_id, reference=f"AV-{n}", label=label, amount_minor=amount_minor,
                            currency=currency, created_by=created_by)
    db.add(adj)
    db.flush()
    post_money(db, kind="partner_adjustment", memo=label, ref_type="partner_adjustment", ref_id=adj.id, lines=[
        ("partner_expense", amount_minor, currency, None),
        ("partner_payable", -amount_minor, currency, merchant_id),
    ])
    return adj


# ---------------------------------------------------------------- périodes


def week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _period_utc(start: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    return (datetime.combine(start, time.min, tz).astimezone(UTC),
            datetime.combine(start + timedelta(days=7), time.min, tz).astimezone(UTC))


def build_payouts(db: Session, now: datetime | None = None) -> list[PartnerPayout]:
    """Crée les versements de la dernière semaine fermée (idempotent)."""
    now = now or datetime.now(UTC)
    created: list[PartnerPayout] = []
    for market in db.scalars(select(Market)):
        tz = ZoneInfo(market.timezone)
        current_start, _ = week_bounds(now.astimezone(tz).date())
        period_start = current_start - timedelta(days=7)
        _, cutoff = _period_utc(period_start, tz)
        merchant_ids = db.scalars(select(Merchant.id).where(Merchant.market_id == market.id)).all()
        for merchant_id in merchant_ids:
            payout = _build_one(db, merchant_id, market.currency, period_start, cutoff)
            if payout:
                created.append(payout)
    return created


def _build_one(db: Session, merchant_id: uuid.UUID, currency: str, period_start: date, cutoff: datetime):
    payables = db.scalars(
        select(PartnerPayable)
        .where(PartnerPayable.merchant_id == merchant_id, PartnerPayable.status == "valued",
               PartnerPayable.payout_id.is_(None), PartnerPayable.currency == currency,
               PartnerPayable.occurred_at < cutoff)
        .with_for_update()
    ).all()
    adjustments = db.scalars(
        select(PartnerAdjustment)
        .where(PartnerAdjustment.merchant_id == merchant_id, PartnerAdjustment.payout_id.is_(None),
               PartnerAdjustment.currency == currency, PartnerAdjustment.created_at < cutoff)
        .with_for_update()
    ).all()
    if not payables and not adjustments:
        return None
    gross = sum(p.amount_minor for p in payables)
    commission = sum(p.commission_minor for p in payables)
    adj = sum(a.amount_minor for a in adjustments)
    net = gross - commission + adj
    payout = PartnerPayout(
        id=uuid.uuid4(), merchant_id=merchant_id, period_start=period_start, period_end=period_start + timedelta(days=6),
        currency=currency, gross_minor=gross, commission_minor=commission, adjustments_minor=adj, net_minor=net,
        visits=sum(1 for p in payables if p.kind == "redemption"),
        # Un net négatif (avoirs supérieurs aux prestations) n'est jamais prélevé automatiquement.
        status="pending" if net > 0 else "to_reconcile",
    )
    try:
        with db.begin_nested():
            db.add(payout)
            db.flush()
    except IntegrityError:
        return None  # période déjà constituée : ces lignes iront dans le versement suivant
    for p in payables:
        p.payout_id, p.status = payout.id, "in_payout"
    for a in adjustments:
        a.payout_id = payout.id
    db.flush()
    emit(db, "partner_payout", payout.id, "payout.created", {"net_minor": net, "currency": currency})
    return payout


# ---------------------------------------------------------------- transferts


def execute_pending(db: Session, provider) -> int:
    """Demande au prestataire les transferts des versements en attente (marchand vérifié uniquement)."""
    count = 0
    rows = db.execute(
        select(PartnerPayout, Merchant)
        .join(Merchant, Merchant.id == PartnerPayout.merchant_id)
        .where(PartnerPayout.status == "pending", PartnerPayout.psp_transfer_id.is_(None))
        .with_for_update(of=PartnerPayout, skip_locked=True)
    ).all()
    for payout, merchant in rows:
        if merchant.psp_status != "verified" or not merchant.psp_account_id:
            continue  # reste en attente jusqu'à la vérification PSP du partenaire
        payout.provider = provider.name
        payout.psp_transfer_id = provider.create_transfer(
            payout_id=payout.id, amount_minor=payout.net_minor, currency=payout.currency,
            destination=merchant.psp_account_id,
        )
        payout.status = "in_transit"
        db.commit()  # la clé d'idempotence (identifiant du versement) protège un éventuel réessai
        count += 1
    return count


def _payout_for(db: Session, provider: str, obj: dict) -> PartnerPayout:
    ref = (obj.get("metadata") or {}).get("xpass_payout_id")
    payout = db.scalar(select(PartnerPayout).where(PartnerPayout.psp_transfer_id == obj.get("id")).with_for_update())
    if payout is None and ref:
        try:
            payout = db.scalar(select(PartnerPayout).where(PartnerPayout.id == uuid.UUID(ref)).with_for_update())
        except ValueError:
            payout = None
    if payout is None:
        raise RetryLater("Versement inconnu pour ce transfert.")
    if payout.provider and payout.provider != provider:
        raise PaymentAnomaly("Prestataire différent de celui du versement.")
    return payout


def confirm_transfer(db: Session, *, provider: str, obj: dict, now: datetime) -> str:
    payout = _payout_for(db, provider, obj)
    if payout.status == "paid":
        return "ignored"
    amount = int(obj.get("amount", -1))
    currency = str(obj.get("currency", "")).upper()
    payout.confirmed_minor = amount
    payout.psp_transfer_id = payout.psp_transfer_id or obj.get("id")
    if amount != payout.net_minor or currency != payout.currency:
        payout.status = "to_reconcile"
        from app.modules.ops.service import audit

        audit(db, actor_kind="system", actor_user_id=None, action="payout.mismatch", object_type="partner_payout",
              object_id=payout.id, object_label=f"Versement {payout.period_start}", reason="Montant différent",
              details={"expected": payout.net_minor, "confirmed": amount, "currency": currency})
        emit(db, "partner_payout", payout.id, "payout.mismatch", {"expected": payout.net_minor, "confirmed": amount})
        return "applied"
    payout.status, payout.paid_at = "paid", now
    db.execute(update(PartnerPayable).where(PartnerPayable.payout_id == payout.id).values(status="paid"))
    post_money(db, kind="payout_paid", memo=f"Versement {payout.period_start}", ref_type="partner_payout",
               ref_id=payout.id, lines=[("partner_payable", amount, currency, payout.merchant_id),
                                        ("psp_cash", -amount, currency, None)])
    emit(db, "partner_payout", payout.id, "payout.paid", {"net_minor": amount, "currency": currency})
    return "applied"


def reverse_transfer(db: Session, *, provider: str, obj: dict) -> str:
    payout = _payout_for(db, provider, obj)
    if payout.status == "paid":
        # L'argent était sorti : on ne défait pas l'écriture, l'écart est à traiter par l'administration.
        payout.status = "to_reconcile"
    else:
        payout.status = "failed"
    return "applied"


# ---------------------------------------------------------------- lecture


def open_period_summary(db: Session, merchant_id: uuid.UUID) -> dict:
    """Montants non encore rattachés à un versement (période en cours et retards)."""
    row = db.execute(
        select(func.coalesce(func.sum(PartnerPayable.amount_minor), 0),
               func.coalesce(func.sum(PartnerPayable.commission_minor), 0),
               func.count().filter(PartnerPayable.kind == "redemption"))
        .where(PartnerPayable.merchant_id == merchant_id, PartnerPayable.payout_id.is_(None),
               PartnerPayable.status == "valued")
    ).one()
    adj = db.scalar(select(func.coalesce(func.sum(PartnerAdjustment.amount_minor), 0)).where(
        PartnerAdjustment.merchant_id == merchant_id, PartnerAdjustment.payout_id.is_(None)))
    pending_valuation = db.scalar(select(func.count()).where(
        PartnerPayable.merchant_id == merchant_id, PartnerPayable.status == "pending_valuation"))
    gross, commission, visits = int(row[0]), int(row[1]), int(row[2])
    return {"gross_minor": gross, "commission_minor": commission, "adjustments_minor": int(adj),
            "net_minor": gross - commission + int(adj), "visits": visits, "pending_valuation": int(pending_valuation)}
