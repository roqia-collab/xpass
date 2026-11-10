import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentPrincipal, DbSession
from app.modules.booking.models import Booking
from app.modules.catalog.models import Market
from app.modules.wallet.models import CreditJournal, CreditJournalLine, CreditLot, CreditLotBalance, Wallet

router = APIRouter(tags=["crédits"])


class LotOut(BaseModel):
    id: uuid.UUID
    source: str
    label: str
    origin_type: str
    granted_credits: int
    available: int
    reserved: int
    expires_at: datetime | None
    is_demo: bool


class SourceOut(BaseModel):
    available: int
    reserved: int


class WalletOut(BaseModel):
    market_code: str
    available: int
    reserved: int
    consumed: int
    by_source: dict[str, SourceOut]
    lots: list[LotOut]


class HistoryItem(BaseModel):
    id: uuid.UUID
    kind: str
    memo: str
    created_at: datetime
    # Variation des crédits disponibles et réservés provoquée par l'écriture.
    available_delta: int
    reserved_delta: int
    booking_id: uuid.UUID | None
    offer_title: str | None


@router.get("/wallet", response_model=WalletOut)
def wallet(principal: CurrentPrincipal, db: DbSession, market: str = "FR") -> WalletOut:
    """Soldes calculés à partir des projections transactionnelles des lots (aucune valeur stockée côté client)."""
    now = datetime.now(UTC)
    rows = db.execute(
        select(CreditLot, CreditLotBalance)
        .join(CreditLotBalance, CreditLotBalance.lot_id == CreditLot.id)
        .join(Wallet, Wallet.id == CreditLot.wallet_id)
        .join(Market, Market.id == Wallet.market_id)
        .where(Wallet.user_id == principal.user.id, Market.code == market)
        .order_by(CreditLot.expires_at.asc().nulls_last(), CreditLot.created_at)
    ).all()
    by_source = {s: SourceOut(available=0, reserved=0) for s in ("personal", "employer", "promotional")}
    lots, consumed = [], 0
    for lot, bal in rows:
        # Un lot échu n'est plus disponible même si l'expiration n'est pas encore écrite au journal.
        usable = bal.available if lot.expires_at is None or lot.expires_at > now else 0
        by_source[lot.source].available += usable
        by_source[lot.source].reserved += bal.reserved
        consumed += bal.consumed
        lots.append(
            LotOut(
                id=lot.id, source=lot.source, label=lot.label, origin_type=lot.origin_type,
                granted_credits=lot.granted_credits, available=usable, reserved=bal.reserved,
                expires_at=lot.expires_at,
                # Démonstration : crédits offerts pour tester, ou payés dans le bac à sable (aucun argent).
                is_demo=lot.origin_type == "demo_grant" or (lot.origin_ref or "").startswith("sandbox:"),
            )
        )
    return WalletOut(
        market_code=market,
        available=sum(s.available for s in by_source.values()),
        reserved=sum(s.reserved for s in by_source.values()),
        consumed=consumed,
        by_source=by_source,
        lots=lots,
    )


@router.get("/wallet/history", response_model=list[HistoryItem])
def history(principal: CurrentPrincipal, db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    from app.modules.catalog.models import OfferVersion

    journals = db.execute(
        select(CreditJournal, OfferVersion.title)
        .join(Wallet, Wallet.id == CreditJournal.wallet_id)
        .outerjoin(Booking, Booking.id == CreditJournal.booking_id)
        .outerjoin(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .where(Wallet.user_id == principal.user.id)
        .order_by(CreditJournal.created_at.desc())
        .limit(limit)
    ).all()
    ids = [j.id for j, _ in journals]
    deltas: dict[tuple[uuid.UUID, str], int] = {
        (jid, acc): int(total)
        for jid, acc, total in db.execute(
            select(CreditJournalLine.journal_id, CreditJournalLine.account, func.sum(CreditJournalLine.amount))
            .where(CreditJournalLine.journal_id.in_(ids))
            .group_by(CreditJournalLine.journal_id, CreditJournalLine.account)
        )
    }
    return [
        HistoryItem(
            id=j.id, kind=j.kind, memo=j.memo, created_at=j.created_at,
            available_delta=deltas.get((j.id, "available"), 0), reserved_delta=deltas.get((j.id, "reserved"), 0),
            booking_id=j.booking_id, offer_title=title,
        )
        for j, title in journals
    ]
