"""Opérations du portefeuille. Toutes s'exécutent dans la transaction de l'appelant.

Règles :
- les crédits sont des entiers ; aucun montant monétaire ici ;
- chaque mouvement écrit un journal équilibré + met à jour les projections des lots ;
- le portefeuille est verrouillé (SELECT ... FOR UPDATE) avant toute allocation :
  deux réservations simultanées d'un même client ne peuvent pas dépasser son solde.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.wallet.models import (
    SOURCE_PRIORITY,
    CreditJournal,
    CreditJournalLine,
    CreditLot,
    CreditLotBalance,
    Wallet,
)


class InsufficientCredits(Exception):
    def __init__(self, needed: int, available: int):
        super().__init__(f"Crédits insuffisants : {available} disponibles, {needed} nécessaires.")
        self.needed = needed
        self.available = available


@dataclass(frozen=True)
class Allocation:
    lot_id: uuid.UUID
    source: str
    amount: int


# Effet de chaque type d'écriture sur les comptes (débit, crédit).
_MOVES = {
    "grant": ("issuance", "available"),
    "reserve": ("available", "reserved"),
    "release": ("reserved", "available"),
    "capture": ("reserved", "consumed"),
    "expire": ("available", "expired"),
}


def get_or_create_wallet(db: Session, user_id: uuid.UUID, market_id: uuid.UUID, *, lock: bool = False) -> Wallet:
    stmt = select(Wallet).where(Wallet.user_id == user_id, Wallet.market_id == market_id)
    if lock:
        stmt = stmt.with_for_update()
    wallet = db.scalar(stmt)
    if wallet is None:
        # INSERT ... ON CONFLICT pour rester sûr en concurrence.
        from sqlalchemy.dialects.postgresql import insert

        db.execute(
            insert(Wallet)
            .values(id=uuid.uuid4(), user_id=user_id, market_id=market_id)
            .on_conflict_do_nothing(index_elements=["user_id", "market_id"])
        )
        wallet = db.scalar(stmt)
    assert wallet is not None
    return wallet


def _post(db: Session, wallet_id: uuid.UUID, kind: str, moves: list[tuple[uuid.UUID, int]], memo: str,
          booking_id: uuid.UUID | None = None) -> CreditJournal:
    """Écrit une écriture équilibrée et met à jour les projections (verrouillées) des lots concernés."""
    debit, credit = _MOVES[kind]
    journal = CreditJournal(id=uuid.uuid4(), wallet_id=wallet_id, kind=kind, memo=memo, booking_id=booking_id)
    db.add(journal)
    db.flush()
    for lot_id, amount in moves:
        if amount <= 0:
            continue
        db.add_all([
            CreditJournalLine(journal_id=journal.id, lot_id=lot_id, account=debit, amount=-amount),
            CreditJournalLine(journal_id=journal.id, lot_id=lot_id, account=credit, amount=amount),
        ])
        balance = db.scalar(select(CreditLotBalance).where(CreditLotBalance.lot_id == lot_id).with_for_update())
        assert balance is not None
        if debit != "issuance":
            setattr(balance, debit, getattr(balance, debit) - amount)
        setattr(balance, credit, getattr(balance, credit) + amount)
    db.flush()  # les CHECK (>= 0) des projections s'appliquent ici
    return journal


def grant(db: Session, wallet: Wallet, *, source: str, amount: int, label: str, origin_type: str,
          origin_ref: str | None = None, expires_at: datetime | None = None,
          eligible_categories: list[str] | None = None) -> CreditLot:
    lot = CreditLot(
        id=uuid.uuid4(),
        wallet_id=wallet.id,
        source=source,
        origin_type=origin_type,
        origin_ref=origin_ref,
        label=label,
        granted_credits=amount,
        expires_at=expires_at,
        eligible_categories=eligible_categories,
    )
    db.add(lot)
    db.flush()
    db.add(CreditLotBalance(lot_id=lot.id, available=0, reserved=0, consumed=0, expired=0))
    db.flush()
    _post(db, wallet.id, "grant", [(lot.id, amount)], memo=label)
    return lot


def usable_lots(db: Session, wallet: Wallet, *, category_slug: str, at: datetime) -> list[tuple[CreditLot, int]]:
    """Lots éligibles, non expirés à la date de la prestation, triés par priorité de consommation."""
    rows = db.execute(
        select(CreditLot, CreditLotBalance.available)
        .join(CreditLotBalance, CreditLotBalance.lot_id == CreditLot.id)
        .where(CreditLot.wallet_id == wallet.id, CreditLotBalance.available > 0)
    ).all()
    eligible = [
        (lot, available)
        for lot, available in rows
        if (lot.expires_at is None or lot.expires_at > at)
        and (lot.eligible_categories is None or category_slug in lot.eligible_categories)
    ]
    far_future = datetime.max.replace(tzinfo=at.tzinfo)
    return sorted(eligible, key=lambda r: (SOURCE_PRIORITY[r[0].source], r[0].expires_at or far_future, r[0].created_at))


def reserve(db: Session, wallet: Wallet, *, amount: int, category_slug: str, at: datetime,
            booking_id: uuid.UUID, memo: str) -> list[Allocation]:
    """Bloque `amount` crédits. Le portefeuille DOIT être verrouillé par l'appelant."""
    lots = usable_lots(db, wallet, category_slug=category_slug, at=at)
    total = sum(a for _, a in lots)
    if total < amount:
        raise InsufficientCredits(amount, total)
    remaining, allocations = amount, []
    for lot, available in lots:
        take = min(available, remaining)
        allocations.append(Allocation(lot.id, lot.source, take))
        remaining -= take
        if remaining == 0:
            break
    _post(db, wallet.id, "reserve", [(a.lot_id, a.amount) for a in allocations], memo, booking_id)
    return allocations


def booking_allocations(db: Session, booking_id: uuid.UUID) -> list[Allocation]:
    """Crédits encore réservés pour une réservation, par lot (somme des mouvements « reserved »)."""
    rows = db.execute(
        select(CreditJournalLine.lot_id, CreditLot.source, func.sum(CreditJournalLine.amount))
        .join(CreditJournal, CreditJournal.id == CreditJournalLine.journal_id)
        .join(CreditLot, CreditLot.id == CreditJournalLine.lot_id)
        .where(CreditJournal.booking_id == booking_id, CreditJournalLine.account == "reserved")
        .group_by(CreditJournalLine.lot_id, CreditLot.source)
    ).all()
    return [Allocation(lot_id, source, int(total)) for lot_id, source, total in rows if total]


def settle(db: Session, wallet_id: uuid.UUID, *, booking_id: uuid.UUID, kind: str, memo: str) -> list[Allocation]:
    """Libère (`release`) ou consomme (`capture`) tout ce qui reste réservé pour la réservation."""
    assert kind in ("release", "capture")
    allocations = booking_allocations(db, booking_id)
    if allocations:
        _post(db, wallet_id, kind, [(a.lot_id, a.amount) for a in allocations], memo, booking_id)
    return allocations


def settle_split(db: Session, wallet_id: uuid.UUID, *, booking_id: uuid.UUID, capture: int, capture_memo: str,
                 release_memo: str) -> None:
    """Consomme `capture` crédits de la réservation et libère le reste (lots pris dans l'ordre de réservation)."""
    allocations = booking_allocations(db, booking_id)
    to_capture, kept, freed = capture, [], []
    for a in allocations:
        take = min(a.amount, to_capture)
        to_capture -= take
        kept.append((a.lot_id, take))
        freed.append((a.lot_id, a.amount - take))
    if to_capture:
        raise ValueError("Plus de crédits à consommer que de crédits réservés.")
    if any(amount for _, amount in kept):
        _post(db, wallet_id, "capture", kept, capture_memo, booking_id)
    if any(amount for _, amount in freed):
        _post(db, wallet_id, "release", freed, release_memo, booking_id)


def expire_amounts(db: Session, wallet_id: uuid.UUID, moves: list[tuple[uuid.UUID, int]], *, memo: str) -> None:
    """Fait expirer des montants précis de crédits disponibles (report plafonné, fin d'abonnement)."""
    if any(amount > 0 for _, amount in moves):
        _post(db, wallet_id, "expire", moves, memo)


def rebuild_balances(db: Session, lot_ids: list[uuid.UUID] | None = None) -> dict[uuid.UUID, dict[str, int]]:
    """Recalcule les soldes depuis le journal (contrôle de cohérence des projections)."""
    stmt = select(CreditJournalLine.lot_id, CreditJournalLine.account, func.sum(CreditJournalLine.amount)).group_by(
        CreditJournalLine.lot_id, CreditJournalLine.account
    )
    if lot_ids is not None:
        stmt = stmt.where(CreditJournalLine.lot_id.in_(lot_ids))
    result: dict[uuid.UUID, dict[str, int]] = {}
    for lot_id, account, total in db.execute(stmt):
        if account != "issuance":
            result.setdefault(lot_id, {"available": 0, "reserved": 0, "consumed": 0, "expired": 0})[account] = int(total)
    return result


def expire_lots(db: Session, now: datetime, limit: int = 200) -> int:
    """Passe en « expired » le solde disponible des lots échus (les crédits réservés restent honorés)."""
    rows = db.execute(
        select(CreditLot.id, CreditLot.wallet_id)
        .join(CreditLotBalance, CreditLotBalance.lot_id == CreditLot.id)
        .where(CreditLot.expires_at <= now, CreditLotBalance.available > 0)
        .limit(limit)
    ).all()
    count = 0
    for lot_id, wallet_id in rows:
        if db.scalar(select(Wallet.id).where(Wallet.id == wallet_id).with_for_update(skip_locked=True)) is None:
            continue
        available = db.scalar(select(CreditLotBalance.available).where(CreditLotBalance.lot_id == lot_id))
        if available:
            _post(db, wallet_id, "expire", [(lot_id, available)], memo="Crédits expirés")
            count += 1
    return count
