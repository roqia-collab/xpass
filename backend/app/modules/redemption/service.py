"""QR éphémère, aperçu au scan et consommation atomique.

- Le client obtient un jeton opaque (QR) et un code court (saisie manuelle), valables 60 s,
  liés à une réservation CONFIRMÉE et à son site. Seules leurs empreintes sont stockées.
- Le scan n'a AUCUN effet financier : il renvoie un aperçu et réserve le jeton à l'opérateur
  pendant 5 minutes pour lui laisser le temps de confirmer.
- La confirmation écrit, dans une seule transaction : capture des crédits (réservé -> consommé),
  statut REDEEMED, consommation (unique par réservation), reçu, dette partenaire, outbox.
- Aucune validation hors ligne : chaque étape interroge PostgreSQL.
"""
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import redis
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.booking.models import Booking
from app.modules.booking.service import BookingError, _lock_wallet_then_booking, funding_by_source
from app.modules.catalog.models import Location
from app.modules.platform.service import emit
from app.modules.redemption.models import PartnerPayable, QrToken, Receipt, Redemption
from app.modules.settlement.service import value_payable
from app.modules.wallet import service as wallet_service

TOKEN_TTL = timedelta(seconds=60)
SCAN_HOLD = timedelta(minutes=5)
# Fenêtre de consommation autour de la prestation.
REDEEM_EARLY = timedelta(minutes=60)
REDEEM_LATE = timedelta(minutes=120)
QR_PREFIX = "XPASS1:"
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sans 0/O, 1/I/L
MAX_FAILED_SCANS = 20
FAILED_SCAN_WINDOW_S = 600


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_code(code: str) -> str:
    return "".join(c for c in code.upper() if c.isalnum())


# ---------------------------------------------------------------- émission (client)


@dataclass
class IssuedPass:
    qr_payload: str
    manual_code: str
    expires_at: datetime


def issue_pass(db: Session, *, user_id: uuid.UUID, booking_id: uuid.UUID, now: datetime | None = None) -> IssuedPass:
    now = now or datetime.now(UTC)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None or booking.user_id != user_id:
        raise BookingError("booking_not_found", "Réservation introuvable.", 404)
    if booking.status != "confirmed":
        raise BookingError("not_confirmed", "Le QR est disponible pour une réservation confirmée.", 409)
    if now > booking.ends_at + REDEEM_LATE:
        raise BookingError("outside_window", "Cette réservation est terminée.", 409)

    # Un seul jeton actif par réservation : les précédents sont révoqués.
    db.execute(
        update(QrToken)
        .where(QrToken.booking_id == booking.id, QrToken.used_at.is_(None), QrToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    token = secrets.token_urlsafe(32)
    for _ in range(5):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
        try:
            with db.begin_nested():
                db.add(
                    QrToken(
                        booking_id=booking.id,
                        location_id=booking.location_id,
                        token_hash=_hash(token),
                        code_hash=_hash(code),
                        expires_at=now + TOKEN_TTL,
                    )
                )
                db.flush()
            break
        except IntegrityError:
            continue  # collision de code sur ce site : on en tire un autre
    else:
        raise BookingError("code_unavailable", "Réessayez dans un instant.", 503)
    return IssuedPass(qr_payload=QR_PREFIX + token, manual_code=f"{code[:4]}-{code[4:]}", expires_at=now + TOKEN_TTL)


# ---------------------------------------------------------------- scan (partenaire)


def _rate_limit(user_id: uuid.UUID, failed: bool) -> None:
    """Limite les essais de codes invalides par opérateur (anti force brute sur les codes courts)."""
    try:
        r = redis.Redis.from_url(get_settings().redis_url, socket_timeout=1)
        key = f"xpass:scan-fail:{user_id}"
        if failed:
            n = r.incr(key)
            if n == 1:
                r.expire(key, FAILED_SCAN_WINDOW_S)
        elif int(r.get(key) or 0) >= MAX_FAILED_SCANS:
            raise BookingError("too_many_attempts", "Trop de codes invalides. Réessayez dans quelques minutes.", 429)
    except redis.RedisError:
        # Redis indisponible : on refuse plutôt que de désactiver la protection.
        raise BookingError("service_unavailable", "Vérification momentanément indisponible.", 503) from None


def _find_token(db: Session, *, location_id: uuid.UUID, qr: str | None, code: str | None, lock: bool) -> QrToken | None:
    stmt = select(QrToken)
    if qr:
        raw = qr.strip()
        if not raw.startswith(QR_PREFIX):
            return None
        stmt = stmt.where(QrToken.token_hash == _hash(raw[len(QR_PREFIX):]))
    elif code:
        stmt = stmt.where(
            QrToken.code_hash == _hash(normalize_code(code)),
            QrToken.location_id == location_id,
            QrToken.used_at.is_(None),
            QrToken.revoked_at.is_(None),
        )
    else:
        return None
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def _validate(token: QrToken | None, booking: Booking | None, *, location_id: uuid.UUID, operator: uuid.UUID,
              now: datetime) -> Booking:
    if token is None or booking is None:
        raise BookingError("invalid_code", "Code inconnu ou invalide.", 404)
    if token.location_id != location_id:
        raise BookingError("wrong_location", "Cette réservation concerne un autre établissement.", 409)
    if booking.status == "redeemed" or token.used_at is not None:
        raise BookingError("already_redeemed", "Cette réservation a déjà été consommée.", 409)
    if token.revoked_at is not None:
        raise BookingError("expired_code", "Ce code a été renouvelé. Demandez au client d'actualiser son QR.", 409)
    held_for_operator = (
        token.scanned_by == operator and token.scanned_at is not None and now < token.scanned_at + SCAN_HOLD
    )
    if token.expires_at <= now and not held_for_operator:
        raise BookingError("expired_code", "Code expiré. Demandez au client d'actualiser son QR.", 409)
    if booking.status != "confirmed":
        raise BookingError("not_confirmed", "Cette réservation n'est pas confirmée.", 409)
    if not (booking.starts_at - REDEEM_EARLY <= now <= booking.ends_at + REDEEM_LATE):
        raise BookingError("outside_window", "Ce n'est pas l'heure de cette réservation.", 409)
    return booking


def preview(db: Session, *, operator_id: uuid.UUID, location_id: uuid.UUID, qr: str | None, code: str | None,
            now: datetime | None = None) -> tuple[Booking, QrToken]:
    """Aperçu SANS effet financier. Réserve le jeton à cet opérateur pour la confirmation."""
    now = now or datetime.now(UTC)
    _rate_limit(operator_id, failed=False)
    token = _find_token(db, location_id=location_id, qr=qr, code=code, lock=True)
    booking = db.get(Booking, token.booking_id) if token else None
    try:
        booking = _validate(token, booking, location_id=location_id, operator=operator_id, now=now)
    except BookingError as exc:
        if exc.code == "invalid_code":
            _rate_limit(operator_id, failed=True)
        raise
    token.scanned_at = now
    token.scanned_by = operator_id
    db.flush()
    return booking, token


@dataclass
class RedeemResult:
    booking: Booking
    receipt: Receipt
    redemption: Redemption


def redeem(db: Session, *, operator_id: uuid.UUID, location_id: uuid.UUID, qr: str | None, code: str | None,
           now: datetime | None = None) -> RedeemResult:
    """Consommation atomique. L'appelant valide la transaction (commit) ou l'annule en bloc."""
    now = now or datetime.now(UTC)
    token = _find_token(db, location_id=location_id, qr=qr, code=code, lock=False)
    if token is None:
        _rate_limit(operator_id, failed=True)
        raise BookingError("invalid_code", "Code inconnu ou invalide.", 404)
    # Verrous : portefeuille -> réservation -> jeton (même ordre que le lot 2).
    booking = _lock_wallet_then_booking(db, token.booking_id)
    token = db.scalar(select(QrToken).where(QrToken.id == token.id).with_for_update())
    booking = _validate(token, booking, location_id=location_id, operator=operator_id, now=now)

    captured = wallet_service.settle(
        db, booking.wallet_id, booking_id=booking.id, kind="capture", memo="Prestation effectuée"
    )
    credits = sum(a.amount for a in captured)
    if credits != booking.total_credits:
        raise BookingError("ledger_mismatch", "Incohérence des crédits réservés : consommation refusée.", 500)

    booking.status = "redeemed"
    booking.redeemed_at = now
    token.used_at = now
    redemption = Redemption(
        booking_id=booking.id,
        location_id=location_id,
        qr_token_id=token.id,
        method="qr" if qr else "code",
        validated_by=operator_id,
        credits=credits,
    )
    db.add(redemption)
    funding = funding_by_source(db, [booking.id]).get(booking.id, {})
    reference = f"XP-{db.scalar(text('SELECT nextval(\'receipt_reference_seq\')'))}"
    receipt = Receipt(booking_id=booking.id, reference=reference, credits_total=credits, funding=funding)
    db.add(receipt)
    location = db.get(Location, booking.location_id)
    payable = PartnerPayable(
        merchant_id=location.merchant_id,
        location_id=location.id,
        booking_id=booking.id,
        kind="redemption",
        credits=credits,
        status="pending_valuation",
        occurred_at=now,
    )
    db.add(payable)
    try:
        db.flush()  # unicités : une seule consommation, un seul reçu, une seule dette par réservation
    except IntegrityError as exc:
        raise BookingError("already_redeemed", "Cette réservation a déjà été consommée.", 409) from exc
    value_payable(db, payable, now)
    emit(db, "booking", booking.id, "booking.redeemed",
         {"booking_id": str(booking.id), "receipt": reference, "credits": credits})
    return RedeemResult(booking=booking, receipt=receipt, redemption=redemption)


def _record_payable(db: Session, booking: Booking, *, kind: str, credits: int, occurred_at: datetime) -> None:
    location = db.get(Location, booking.location_id)
    payable = PartnerPayable(
        merchant_id=location.merchant_id,
        location_id=location.id,
        booking_id=booking.id,
        kind=kind,
        credits=credits,
        status="pending_valuation",
        occurred_at=occurred_at,
    )
    db.add(payable)
    db.flush()
    value_payable(db, payable)


def record_late_cancellation_payable(db: Session, booking: Booking, *, credits: int) -> None:
    """Annulation tardive : la part conservée des crédits est versée au partenaire."""
    _record_payable(db, booking, kind="late_cancellation", credits=credits,
                    occurred_at=booking.cancelled_at or datetime.now(UTC))


def record_no_show_payable(db: Session, booking: Booking, now: datetime) -> None:
    """Absence : tous les crédits sont consommés et versés au partenaire."""
    _record_payable(db, booking, kind="no_show", credits=booking.total_credits, occurred_at=now)


# ---------------------------------------------------------------- agenda


def _ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_for(booking: Booking, *, title: str, address: str, now: datetime | None = None) -> str:
    """Événement iCalendar. Ne contient JAMAIS de jeton QR ni de code : seulement l'horaire et le lieu."""
    now = now or datetime.now(UTC)
    fmt = "%Y%m%dT%H%M%SZ"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//XPASS//Reservations//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:booking-{booking.id}@xpass",
        f"DTSTAMP:{now.astimezone(UTC).strftime(fmt)}",
        f"DTSTART:{booking.starts_at.astimezone(UTC).strftime(fmt)}",
        f"DTEND:{booking.ends_at.astimezone(UTC).strftime(fmt)}",
        f"SUMMARY:{_ics_escape(title)}",
        f"LOCATION:{_ics_escape(address)}",
        "DESCRIPTION:" + _ics_escape("Réservation XPASS. Présentez votre QR depuis l'application le jour J."),
        "BEGIN:VALARM",
        "TRIGGER:-PT1H",
        "ACTION:DISPLAY",
        "DESCRIPTION:" + _ics_escape(title),
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
