"""Prix d'un créneau en crédits : prix de base de l'offre, ajusté selon l'heure et le remplissage.

Règles (entiers uniquement, arrondi au crédit le plus proche, jamais moins d'un crédit) :
- heure de pointe : +20 % du lundi au vendredi de 18 h à 21 h (heure locale du marché), et le samedi et le dimanche ;
- forte demande : +20 % quand le créneau est occupé à 70 % ou plus ;
- dernière minute : −20 % quand le créneau commence dans moins de 6 h et qu'il est occupé à moins de 30 %.
Les pourcentages s'additionnent. Le prix est figé sur la réservation au moment de la réserve ; le commerçant est payé
sur les crédits réellement consommés.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PEAK_PCT = 20
DEMAND_PCT = 20
LAST_MINUTE_PCT = -20
PEAK_WEEKDAY_HOURS = (18, 21)  # [18 h, 21 h)
DEMAND_MIN_FILL = 0.70
LAST_MINUTE_WINDOW = timedelta(hours=6)
LAST_MINUTE_MAX_FILL = 0.30

ADJUSTMENTS = ("peak", "demand", "last_minute")


@dataclass(frozen=True)
class SlotPrice:
    credits: int
    base_credits: int
    adjustments: tuple[str, ...]


def is_peak(starts_at: datetime, tz: ZoneInfo) -> bool:
    local = starts_at.astimezone(tz)
    if local.weekday() >= 5:
        return True
    return PEAK_WEEKDAY_HOURS[0] <= local.hour < PEAK_WEEKDAY_HOURS[1]


def slot_price(base: int, *, starts_at: datetime, tz: ZoneInfo, now: datetime, fill: float) -> SlotPrice:
    """`fill` : part occupée du créneau, de 0 à 1 (places réservées ou professionnels occupés)."""
    adjustments: list[str] = []
    pct = 0
    if is_peak(starts_at, tz):
        adjustments.append("peak")
        pct += PEAK_PCT
    if fill >= DEMAND_MIN_FILL:
        adjustments.append("demand")
        pct += DEMAND_PCT
    elif starts_at - now < LAST_MINUTE_WINDOW and fill < LAST_MINUTE_MAX_FILL:
        adjustments.append("last_minute")
        pct += LAST_MINUTE_PCT
    credits = max(1, (base * (100 + pct) + 50) // 100)
    return SlotPrice(credits=credits, base_credits=base, adjustments=tuple(adjustments))


def late_cancellation_refund(total_credits: int) -> int:
    """Annulation après le délai gratuit : la moitié des crédits est rendue (arrondi inférieur)."""
    return total_credits // 2
