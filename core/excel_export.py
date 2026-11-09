"""Экспорт всех продаж в отдельный лист Excel.

Путь к книге хранится в настройках приложения (QSettings), а не рядом с EXE.
Другие листы книги не изменяются.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

from core import repository as repo
from PySide6.QtCore import QSettings

ORG_NAME = "MikuSales"
APP_NAME = "Учёт продаж"
SETTINGS_KEY = "excel/sales_workbook"
SHEET_NAME = "Продажи"


def get_excel_path() -> str:
    settings = QSettings(ORG_NAME, APP_NAME)
    return settings.value(SETTINGS_KEY, "", type=str)


def set_excel_path(path: str) -> None:
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(SETTINGS_KEY, str(Path(path)))
    settings.sync()


def _date_value(value):
    return value if value else None


def export_sales(path: str | Path) -> int:
    """Полностью обновляет лист «Продажи», сохраняя остальные листы книги."""
    target = Path(path).expanduser()
    if target.suffix.lower() != ".xlsx":
        raise ValueError("Для экспорта выбери файл с расширением .xlsx")

    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        wb = load_workbook(target)
        if SHEET_NAME in wb.sheetnames:
            ws = wb[SHEET_NAME]
            # Удаляем только содержимое и таблицы зарезервированного листа.
            for table_name in list(ws.tables.keys()):
                del ws.tables[table_name]
            if ws.max_row:
                ws.delete_rows(1, ws.max_row)
        else:
            ws = wb.create_sheet(SHEET_NAME)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = SHEET_NAME

    headers = [
        "ID продажи", "Дата продажи", "Дата создания",
        "Покупатель", "Ссылка на профиль",
        "Товар", "Размер товара", "Рамка", "Размер рамки",
        "Получено, ₽", "Скидка", "Чистая прибыль, ₽",
        "Расходы по заказу, ₽", "Состав расходов",
        "Ссылка на диалог", "Чек", "Отзыв", "Примечание",
    ]
    ws.append(headers)

    sales = repo.list_sales()
    for sale in sales:
        expense_total = sum(float(item.amount or 0) for item in sale.expense_links)
        expense_names = "; ".join(
            f"{item.name}: {float(item.amount or 0):.2f} ₽"
            for item in sale.expense_links
        )
        ws.append([
            sale.id,
            _date_value(sale.sale_date),
            _date_value(sale.created_at),
            sale.buyer_name or "",
            sale.buyer_link or "",
            sale.product.name if sale.product else "",
            sale.size or "",
            sale.frame.name if sale.frame else "",
            sale.frame_size or "",
            float(sale.amount_received or 0),
            sale.discount.name if sale.discount else "",
            float(sale.profit or 0),
            expense_total,
            expense_names,
            sale.dialog_link or "",
            sale.receipt_path or "",
            "Да" if sale.has_review else "Нет",
            sale.note or "",
        ])

    # Оформление заголовка и таблицы.
    header_fill = PatternFill("solid", fgColor="28302E")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 32

    if sales:
        table_ref = f"A1:{get_column_letter(len(headers))}{len(sales) + 1}"
        table = Table(displayName="SalesData", ref=table_ref)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws.add_table(table)

    widths = {
        1: 12, 2: 15, 3: 20, 4: 22, 5: 32, 6: 24, 7: 16, 8: 22,
        9: 16, 10: 16, 11: 20, 12: 20, 13: 20, 14: 42, 15: 35,
        16: 38, 17: 12, 18: 42,
    }
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    for row in ws.iter_rows(min_row=2):
        for idx in (2, 3):
            row[idx - 1].number_format = "dd.mm.yyyy" if idx == 2 else "dd.mm.yyyy hh:mm"
        for idx in (10, 12, 13):
            row[idx - 1].number_format = '#,##0.00 "₽"'
        for cell in row:
            cell.alignment = Alignment(vertical="top")

    wb.save(target)
    wb.close()
    return len(sales)


def sync_if_configured() -> int | None:
    path = get_excel_path()
    if not path:
        return None
    return export_sales(path)
