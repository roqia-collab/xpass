"""Calcul INDICATIF du prochain créneau à partir des horaires d'ouverture.

Lot 1 : aucune réservation, occupation ni blocage externe n'existe encore, donc le
résultat ne tient compte que des horaires et des exceptions. Il est exposé avec
`indicative = true` et ne garantit pas la disponibilité. Le moteur réel
(capacité, occupations exclusives, blocages) remplacera ce calcul au lot 2.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SLOT_STEP_MIN = 30
LEAD_TIME_MIN = 15
HORIZON_DAYS = 14


@dataclass(frozen=True)
class Window:
    opens_at: time
    closes_at: time


def day_windows(day: date, weekly: Iterable, exceptions: Iterable) -> list[Window]:
    """Plages d'ouverture d'un jour donné ; une exception remplace l'horaire hebdomadaire."""
    day_exceptions = [e for e in exceptions if e.day == day]
    if day_exceptions:
        return [Window(e.opens_at, e.closes_at) for e in day_exceptions if not e.is_closed]
    return [Window(h.opens_at, h.closes_at) for h in weekly if h.weekday == day.weekday()]


def day_slots(
    *,
    day: date,
    weekly: Iterable,
    exceptions: Iterable,
    duration_min: int,
    timezone: str,
    now: datetime,
) -> list[datetime]:
    """Débuts de créneaux d'un jour (grille de 30 min, durée tenant avant la fermeture, délai minimal)."""
    tz = ZoneInfo(timezone)
    earliest = now.astimezone(tz) + timedelta(minutes=LEAD_TIME_MIN)
    duration = timedelta(minutes=duration_min)
    slots: list[datetime] = []
    for window in sorted(day_windows(day, weekly, exceptions), key=lambda w: w.opens_at):
        start = datetime.combine(day, window.opens_at, tzinfo=tz)
        end = datetime.combine(day, window.closes_at, tzinfo=tz)
        while start + duration <= end:
            if start >= earliest:
                slots.append(start)
            start += timedelta(minutes=SLOT_STEP_MIN)
    return slots


def next_indicative_slot(
    *,
    weekly: Iterable,
    exceptions: Iterable,
    duration_min: int,
    timezone: str,
    now: datetime,
) -> datetime | None:
    weekly, exceptions = list(weekly), list(exceptions)
    today = now.astimezone(ZoneInfo(timezone)).date()
    for offset in range(HORIZON_DAYS):
        slots = day_slots(
            day=today + timedelta(days=offset),
            weekly=weekly,
            exceptions=exceptions,
            duration_min=duration_min,
            timezone=timezone,
            now=now,
        )
        if slots:
            return slots[0]
    return None


def hours_summary(weekly: Iterable) -> str:
    """Résumé lisible : « Lundi – Samedi : 9h00 – 19h00 »."""
    names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

    def fmt(t: time) -> str:
        return f"{t.hour}h{t.minute:02d}"

    by_hours: dict[str, list[int]] = {}
    for h in sorted(weekly, key=lambda h: (h.weekday, h.opens_at)):
        by_hours.setdefault(f"{fmt(h.opens_at)} – {fmt(h.closes_at)}", []).append(h.weekday)

    parts = []
    for label, days in by_hours.items():
        days = sorted(set(days))
        contiguous = days == list(range(days[0], days[-1] + 1))
        if len(days) > 2 and contiguous:
            span = f"{names[days[0]]} – {names[days[-1]]}"
        else:
            span = ", ".join(names[d] for d in days)
        parts.append(f"{span} : {label}")
    return " · ".join(parts) if parts else "Horaires non communiqués"
