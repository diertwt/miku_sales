from datetime import date

from PySide6.QtCore import QDate

from core.config import DATE_DISPLAY_FORMAT


def qdate_to_date(qd: QDate) -> date:
    return date(qd.year(), qd.month(), qd.day())


def date_to_qdate(d: date | None) -> QDate:
    if d is None:
        return QDate.currentDate()
    return QDate(d.year, d.month, d.day)


def fmt_date(d: date | None) -> str:
    if d is None:
        return ""
    return d.strftime("%d.%m.%Y")


def fmt_money(v: float) -> str:
    return f"{v:,.2f} ₽".replace(",", " ")


def parse_date_str(s: str) -> date | None:
    """Парсит 'DD.MM.YYYY' (как в config.DATE_DISPLAY_FORMAT)."""
    s = s.strip()
    if not s:
        return None
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None