"""Tests for holiday detection logic."""

import pytest
from datetime import date

from holidays import get_holiday, Holiday


# ── Fixed-date holidays ──────────────────────────────────────────────────────

@pytest.mark.parametrize("month,day,expected_name,expected_featured", [
    (1,  1,  "New Year's Day",                False),
    (1,  2,  "Science Fiction Day",           True),
    (2,  2,  "Groundhog Day",                 True),
    (2,  14, "Valentine's Day",               False),
    (3,  14, "Pi Day",                        True),
    (3,  17, "St. Patrick's Day",             False),
    (4,  1,  "April Fools' Day",              False),
    (4,  22, "Earth Day",                     False),
    (4,  23, "World Book Day",                True),
    (5,  4,  "Star Wars Day",                 True),
    (5,  25, "Towel Day",                     True),
    (6,  17, "Eat Your Vegetables Day",       True),
    (7,  4,  "Independence Day",              False),
    (7,  14, "Bastille Day",                  True),
    (7,  17, "World Emoji Day",               True),
    (7,  22, "Pi Approximation Day",          True),
    (8,  13, "International Left-Handers Day", True),
    (8,  26, "National Dog Day",              True),
    (9,  19, "Talk Like a Pirate Day",        True),
    (10, 31, "Halloween",                     False),
    (11, 11, "Veterans Day",                  False),
    (11, 30, "Computer Security Day",         True),
    (12, 9,  "Pretend to Be a Time Traveler Day", True),
    (12, 21, "Winter Solstice",               True),
    (12, 25, "Christmas",                     False),
    (12, 26, "Boxing Day",                    True),
    (12, 31, "New Year's Eve",                False),
])
def test_fixed_holidays(month, day, expected_name, expected_featured):
    h = get_holiday(date(2026, month, day))
    assert h is not None, f"Expected holiday on {month}/{day}"
    assert h.name == expected_name
    assert h.featured == expected_featured


def test_fixed_holiday_has_nonempty_theme():
    """Every fixed holiday must have non-empty theming guidance."""
    for (month, day), holiday in [
        ((3, 14), get_holiday(date(2026, 3, 14))),  # Pi Day
        ((10, 31), get_holiday(date(2026, 10, 31))),  # Halloween
        ((5, 4), get_holiday(date(2026, 5, 4))),  # Star Wars Day
    ]:
        assert holiday is not None
        assert len(holiday.theme) > 50, f"Theme for {holiday.name} is too short"


# ── Non-holiday dates return None ────────────────────────────────────────────

@pytest.mark.parametrize("month,day", [
    (1, 15),
    (3, 10),
    (6, 1),
    (8, 1),
    (10, 15),
    (11, 5),
    (12, 15),
])
def test_non_holidays_return_none(month, day):
    assert get_holiday(date(2026, month, day)) is None


# ── Computed holidays ────────────────────────────────────────────────────────

@pytest.mark.parametrize("year,expected_date", [
    (2024, date(2024, 11, 28)),  # 4th Thursday of November 2024
    (2025, date(2025, 11, 27)),
    (2026, date(2026, 11, 26)),
])
def test_thanksgiving(year, expected_date):
    h = get_holiday(expected_date)
    assert h is not None
    assert h.name == "Thanksgiving"
    assert h.featured is False
    # Adjacent dates are not Thanksgiving
    assert get_holiday(expected_date.replace(day=expected_date.day - 1)) != h


@pytest.mark.parametrize("year,expected_date", [
    (2024, date(2024, 9, 12)),  # leap year: 256th day = Sep 12
    (2025, date(2025, 9, 13)),
    (2026, date(2026, 9, 13)),
])
def test_programmers_day(year, expected_date):
    h = get_holiday(expected_date)
    assert h is not None
    assert h.name == "International Programmers' Day"
    assert h.featured is True


@pytest.mark.parametrize("year,expected_date", [
    (2024, date(2024, 7, 26)),  # last Friday of July 2024
    (2025, date(2025, 7, 25)),
    (2026, date(2026, 7, 31)),
])
def test_sysadmin_day(year, expected_date):
    h = get_holiday(expected_date)
    assert h is not None
    assert h.name == "System Administrator Appreciation Day"
    assert h.featured is True


@pytest.mark.parametrize("year,expected_date", [
    (2024, date(2024, 10, 8)),   # 2nd Tuesday of October 2024
    (2025, date(2025, 10, 14)),
    (2026, date(2026, 10, 13)),
])
def test_ada_lovelace_day(year, expected_date):
    h = get_holiday(expected_date)
    assert h is not None
    assert h.name == "Ada Lovelace Day"
    assert h.featured is True


def test_programmers_day_is_256th_day():
    """The 256th day of the year should always be Programmers' Day."""
    for year in [2024, 2025, 2026, 2027]:
        d = date(year, 1, 1).replace(month=1, day=1)
        # Calculate 256th day
        from datetime import timedelta
        day_256 = date(year, 1, 1) + timedelta(days=255)
        h = get_holiday(day_256)
        assert h is not None and h.name == "International Programmers' Day", \
            f"Expected Programmers' Day on {day_256} (year {year})"


# ── Holiday return type ──────────────────────────────────────────────────────

def test_holiday_is_named_tuple():
    h = get_holiday(date(2026, 12, 25))
    assert isinstance(h, Holiday)
    assert isinstance(h.name, str)
    assert isinstance(h.emoji, str)
    assert isinstance(h.featured, bool)
    assert isinstance(h.theme, str)


def test_no_holiday_on_day_before_and_after_thanksgiving():
    """Days adjacent to computed holidays should not themselves be holidays."""
    thanksgiving_2026 = date(2026, 11, 26)
    assert get_holiday(date(2026, 11, 25)) is None
    assert get_holiday(date(2026, 11, 27)) is None
    assert get_holiday(thanksgiving_2026) is not None
