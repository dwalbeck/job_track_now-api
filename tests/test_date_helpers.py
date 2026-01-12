import pytest
from datetime import date, timedelta
from app.utils.date_helpers import (
    get_month_date_range,
    get_week_date_range,
    validate_week_start
)


class TestGetMonthDateRange:
    """Test suite for get_month_date_range function."""

    def test_january_2025(self):
        """Test getting date range for January 2025."""
        start_date, end_date = get_month_date_range("2025-01")

        assert start_date == date(2025, 1, 1)
        assert end_date == date(2025, 1, 31)

    def test_february_2024_leap_year(self):
        """Test getting date range for February in a leap year."""
        start_date, end_date = get_month_date_range("2024-02")

        assert start_date == date(2024, 2, 1)
        assert end_date == date(2024, 2, 29)  # 29 days in leap year

    def test_february_2025_non_leap_year(self):
        """Test getting date range for February in a non-leap year."""
        start_date, end_date = get_month_date_range("2025-02")

        assert start_date == date(2025, 2, 1)
        assert end_date == date(2025, 2, 28)  # 28 days in non-leap year

    def test_april_2025_30_days(self):
        """Test getting date range for April (30 days)."""
        start_date, end_date = get_month_date_range("2025-04")

        assert start_date == date(2025, 4, 1)
        assert end_date == date(2025, 4, 30)

    def test_december_2025(self):
        """Test getting date range for December."""
        start_date, end_date = get_month_date_range("2025-12")

        assert start_date == date(2025, 12, 1)
        assert end_date == date(2025, 12, 31)

    def test_invalid_format(self):
        """Test with invalid date format."""
        with pytest.raises(ValueError):
            get_month_date_range("2025/01")

    def test_invalid_month(self):
        """Test with invalid month number."""
        with pytest.raises(ValueError):
            get_month_date_range("2025-13")

    def test_single_digit_month(self):
        """Test with single digit month."""
        start_date, end_date = get_month_date_range("2025-3")

        assert start_date == date(2025, 3, 1)
        assert end_date == date(2025, 3, 31)


class TestGetWeekDateRange:
    """Test suite for get_week_date_range function."""

    def test_valid_monday(self):
        """Test getting week range starting from Monday (2025-01-13)."""
        # 2025-01-13 is a Monday
        start_date, end_date = get_week_date_range("2025-01-13")

        assert start_date == date(2025, 1, 13)
        assert end_date == date(2025, 1, 19)  # Sunday (6 days later)

    def test_week_spans_month_boundary(self):
        """Test week that spans across month boundary."""
        # 2025-01-27 is a Monday
        start_date, end_date = get_week_date_range("2025-01-27")

        assert start_date == date(2025, 1, 27)
        assert end_date == date(2025, 2, 2)  # Crosses into February

    def test_week_spans_year_boundary(self):
        """Test week that spans across year boundary."""
        # 2024-12-30 is a Monday
        start_date, end_date = get_week_date_range("2024-12-30")

        assert start_date == date(2024, 12, 30)
        assert end_date == date(2025, 1, 5)  # Crosses into 2025

    def test_not_monday_tuesday(self):
        """Test with Tuesday (should raise error)."""
        # 2025-01-14 is a Tuesday
        with pytest.raises(ValueError, match="Start date must be a Monday"):
            get_week_date_range("2025-01-14")

    def test_not_monday_wednesday(self):
        """Test with Wednesday (should raise error)."""
        # 2025-01-15 is a Wednesday
        with pytest.raises(ValueError, match="Start date must be a Monday"):
            get_week_date_range("2025-01-15")

    def test_not_monday_sunday(self):
        """Test with Sunday (should raise error)."""
        # 2025-01-12 is a Sunday
        with pytest.raises(ValueError, match="Start date must be a Monday"):
            get_week_date_range("2025-01-12")

    def test_invalid_date_format(self):
        """Test with invalid date format."""
        with pytest.raises(ValueError):
            get_week_date_range("2025/01/13")

    def test_invalid_date(self):
        """Test with invalid date."""
        with pytest.raises(ValueError):
            get_week_date_range("2025-02-30")  # February doesn't have 30 days


class TestValidateWeekStart:
    """Test suite for validate_week_start function."""

    def test_valid_monday(self):
        """Test validation with a Monday."""
        # 2025-01-13 is a Monday
        assert validate_week_start("2025-01-13") == True

    def test_another_valid_monday(self):
        """Test validation with another Monday."""
        # 2025-01-20 is a Monday
        assert validate_week_start("2025-01-20") == True

    def test_invalid_tuesday(self):
        """Test validation with Tuesday."""
        # 2025-01-14 is a Tuesday
        assert validate_week_start("2025-01-14") == False

    def test_invalid_wednesday(self):
        """Test validation with Wednesday."""
        # 2025-01-15 is a Wednesday
        assert validate_week_start("2025-01-15") == False

    def test_invalid_thursday(self):
        """Test validation with Thursday."""
        # 2025-01-16 is a Thursday
        assert validate_week_start("2025-01-16") == False

    def test_invalid_friday(self):
        """Test validation with Friday."""
        # 2025-01-17 is a Friday
        assert validate_week_start("2025-01-17") == False

    def test_invalid_saturday(self):
        """Test validation with Saturday."""
        # 2025-01-18 is a Saturday
        assert validate_week_start("2025-01-18") == False

    def test_invalid_sunday(self):
        """Test validation with Sunday."""
        # 2025-01-12 is a Sunday
        assert validate_week_start("2025-01-12") == False

    def test_invalid_date_format(self):
        """Test validation with invalid date format."""
        assert validate_week_start("2025/01/13") == False

    def test_invalid_date_string(self):
        """Test validation with invalid date string."""
        assert validate_week_start("invalid-date") == False

    def test_empty_string(self):
        """Test validation with empty string."""
        assert validate_week_start("") == False

    def test_invalid_date_value(self):
        """Test validation with invalid date value."""
        assert validate_week_start("2025-02-30") == False
