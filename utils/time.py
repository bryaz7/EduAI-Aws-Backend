from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta


def get_current_hour():
    current_time = datetime.utcnow()
    current_hour = current_time.replace(minute=0, second=0, microsecond=0)
    return current_hour


def get_current_month():
    current_time = datetime.utcnow()
    current_month = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return current_month


def get_month_dates(current_date_start):
    current_time = datetime.utcnow()
    current_month_start = current_time.replace(day=current_date_start.day, hour=0, minute=0, second=0, microsecond=0)

    if current_time.day < current_date_start.day:
        # If the current day is less than the day of the current_date_start,
        # set the month to the previous month
        current_month_start = current_month_start - relativedelta(months=1)

    return current_month_start


def get_age(date_of_birth):
    if not date_of_birth:
        return 100
    current_time = datetime.utcnow()
    age = relativedelta(current_time, date_of_birth).years
    return age


def calculate_age(date_of_birth):
    if not date_of_birth:
        return 13
    current_date = datetime.now()
    age = current_date.year - date_of_birth.year

    # Check if the birthday has already occurred this year
    if current_date.month < date_of_birth.month:
        age -= 1
    elif current_date.month == date_of_birth.month and current_date.day < date_of_birth.day:
        age -= 1

    return age
