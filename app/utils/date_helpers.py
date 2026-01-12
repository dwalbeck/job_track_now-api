from datetime import datetime, date
import calendar


def get_month_date_range(year_month: str) -> tuple[date, date]:
    """
    Get the first and last day of a month from YYYY-MM format.

    Args:
        year_month: Date string in YYYY-MM format

    Returns:
        tuple: (start_date, end_date) for the month
    """
    year, month = map(int, year_month.split('-'))

    # First day of the month
    start_date = date(year, month, 1)

    # Last day of the month
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    return start_date, end_date


def get_week_date_range(start_date_str: str) -> tuple[date, date]:
    """
    Get the date range for a week starting from the given date.

    Args:
        start_date_str: Date string in YYYY-MM-DD format

    Returns:
        tuple: (start_date, end_date) for the week
    """
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

    # Check if it's Monday (weekday 0)
    if start_date.weekday() != 0:
        raise ValueError("Start date must be a Monday (first day of the week)")

    # Calculate end date (6 days later)
    from datetime import timedelta
    end_date = start_date + timedelta(days=6)

    return start_date, end_date


def validate_week_start(date_str: str) -> bool:
    """
    Validate that the given date is a Monday.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        bool: True if the date is a Monday, False otherwise
    """
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        return check_date.weekday() == 0  # Monday is 0
    except ValueError:
        return False