from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from app.modules.catalog.availability import hours_summary, next_indicative_slot


@dataclass
class H:
    weekday: int
    opens_at: time
    closes_at: time


@dataclass
class E:
    day: date
    is_closed: bool
    opens_at: time | None = None
    closes_at: time | None = None


WEEKDAYS_9_19 = [H(d, time(9), time(19)) for d in range(0, 6)]
TZ = "Europe/Paris"


def slot(now, weekly=WEEKDAYS_9_19, exceptions=(), duration=30):
    return next_indicative_slot(weekly=weekly, exceptions=exceptions, duration_min=duration, timezone=TZ, now=now)


def test_slot_respects_lead_time_and_grid():
    # Jeudi 12 novembre 2026, 15h50 à Paris (14h50 UTC) -> 16h30 (délai 15 min, grille 30 min)
    s = slot(datetime(2026, 11, 12, 14, 50, tzinfo=UTC))
    assert s.isoformat() == "2026-11-12T16:30:00+01:00"


def test_slot_moves_to_next_open_day_after_closing():
    # Samedi 14 novembre 18h45 -> lundi 16 novembre 9h00 (dimanche fermé)
    s = slot(datetime(2026, 11, 14, 17, 45, tzinfo=UTC))
    assert s.isoformat() == "2026-11-16T09:00:00+01:00"


def test_duration_must_fit_before_closing():
    s = slot(datetime(2026, 11, 12, 16, 0, tzinfo=UTC), duration=120)  # 17h00 Paris
    assert s.isoformat() == "2026-11-13T09:00:00+01:00"  # 17h30 + 120 min > 19h00


def test_closed_exception_skips_day():
    s = slot(datetime(2026, 11, 12, 6, 0, tzinfo=UTC), exceptions=[E(date(2026, 11, 12), True)])
    assert s.date() == date(2026, 11, 13)


def test_special_hours_exception_replaces_weekly_hours():
    exc = [E(date(2026, 11, 12), False, time(14), time(15))]
    s = slot(datetime(2026, 11, 12, 6, 0, tzinfo=UTC), exceptions=exc)
    assert s.isoformat() == "2026-11-12T14:00:00+01:00"


def test_no_hours_means_no_slot():
    assert slot(datetime(2026, 11, 12, tzinfo=UTC), weekly=[]) is None


def test_hours_summary():
    assert hours_summary(WEEKDAYS_9_19) == "Lundi – Samedi : 9h00 – 19h00"
    assert hours_summary([H(5, time(10), time(12))]) == "Samedi : 10h00 – 12h00"
    assert hours_summary([]) == "Horaires non communiqués"
