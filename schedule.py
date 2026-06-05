"""Расписание отложенных постов VK (МСК)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")
WEEKDAYS_RU = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")

# weekday(): 0=пн … 1=вт … 5=сб
SCHEDULE_DAYS = {
    1: ("среда", 1),       # вторник → +1 день, 12:00
    5: ("воскресенье", 1),  # суббота → +1 день, 12:00
}


class WrongWeekdayError(Exception):
    """Запуск не во вторник и не в субботу."""


def scheduled_publish_time(now: datetime | None = None) -> datetime:
    now = (now or datetime.now(MSK)).astimezone(MSK)
    rule = SCHEDULE_DAYS.get(now.weekday())
    if not rule:
        today = WEEKDAYS_RU[now.weekday()]
        raise WrongWeekdayError(
            "Отложенный пост ставится только во вторник (→ среда 12:00 МСК) "
            "или в субботу (→ воскресенье 12:00 МСК). "
            f"Сегодня: {today}."
        )

    _label, days_ahead = rule
    target_date = now.date() + timedelta(days=days_ahead)
    return datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        12,
        0,
        0,
        tzinfo=MSK,
    )


def schedule_label(when: datetime) -> str:
    when = when.astimezone(MSK)
    day = WEEKDAYS_RU[when.weekday()]
    return f"{day} {when.strftime('%d.%m.%Y %H:%M')} МСК"
