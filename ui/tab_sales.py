# "Учёт продаж" + главная


from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QStackedWidget, QAbstractItemView,
)

from core import repository as repo
from core.models import Sale
from ui.helpers import fmt_date, fmt_money
from ui.widgets.chart import SalesChart


class SalesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.stack = QStackedWidget(self)
        self.home_page = self._build_home_page()
        self.table_page = self._build_table_page()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.table_page)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack)

        self.refresh()

    # ---------------- Главная ----------------

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Учёт продаж")
        title.setFont(QFont("", 18, QFont.Bold))
        layout.addWidget(title)

        btn_new = QPushButton("➕  Новая продажа")
        btn_new.setMinimumHeight(64)
        btn_new.setFont(QFont("", 14, QFont.Bold))
        btn_new.clicked.connect(self.on_new_sale)
        layout.addWidget(btn_new)

        btn_check = QPushButton("🔎  Проверка пользователя")
        btn_check.setMinimumHeight(36)
        btn_check.clicked.connect(self.on_user_check)
        layout.addWidget(btn_check)

        btn_all = QPushButton("Показать всю таблицу продаж")
        btn_all.clicked.connect(lambda: self.stack.setCurrentWidget(self.table_page))
        layout.addWidget(btn_all)

        layout.addWidget(QLabel("Последние продажи:"))
        self.recent_table = QTableWidget(0, 3)
        self.recent_table.setHorizontalHeaderLabels(
            ["Дата", "Кому", "Заработал (чистыми)"]
        )
        self.recent_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recent_table.setMaximumHeight(200)
        layout.addWidget(self.recent_table)

        layout.addWidget(QLabel("График продаж и прибыли:"))
        self.chart = SalesChart()
        layout.addWidget(self.chart, 1)

        return page

    # ---------------- Таблица ----------------

    def _build_table_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        top = QHBoxLayout()
        btn_back = QPushButton("← На главную")
        btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(self.home_page))
        top.addWidget(btn_back)

        btn_new = QPushButton("➕ Новая продажа")
        btn_new.clicked.connect(self.on_new_sale)

        btn_check = QPushButton("🔎 Проверка пользователя")
        btn_check.clicked.connect(self.on_user_check)
        top.addWidget(btn_check)

        top.addWidget(btn_new)

        top.addStretch()
        layout.addLayout(top)

        self.full_table = QTableWidget(0, 10)
        self.full_table.setHorizontalHeaderLabels([
            "Дата", "Кому", "Имя", "Скидка", "Товар",
            "Чистая прибыль", "Диалог", "Чек", "Рамка", "Отзыв",
        ])
        self.full_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.full_table.horizontalHeader().setStretchLastSection(True)
        self.full_table.verticalHeader().setVisible(False)
        self.full_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.full_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.full_table.doubleClicked.connect(self.on_row_double_clicked)
        layout.addWidget(self.full_table)

        hint = QLabel("Двойной клик по строке — редактировать продажу.")
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        return page

    # ---------------- Действия ----------------

       # ---------------- Действия ----------------

    def on_new_sale(self):
        from ui.dialog_sale import SaleDialog
        dlg = SaleDialog(self)
        if dlg.exec():
            self.refresh()

    def on_user_check(self):
        from ui.dialog_user_check import UserCheckDialog
        UserCheckDialog(self).exec()

    def on_row_double_clicked(self, index):
        row = index.row()
        if not (0 <= row < len(self._sales_cache)):
            return
        from ui.dialog_sale import SaleDialog
        dlg = SaleDialog(self, sale=self._sales_cache[row])
        if dlg.exec():
            self.refresh()

    # ---------------- Обновление ----------------

    def refresh(self):
        # Последние продажи
        recent = repo.last_sales(limit=5)
        self.recent_table.setRowCount(len(recent))
        for row, sale in enumerate(recent):
            self._set(self.recent_table, row, 0, fmt_date(sale.sale_date))
            self._set(self.recent_table, row, 1, sale.buyer_name or "—")
            self._set(self.recent_table, row, 2, fmt_money(sale.profit))

        # Полная таблица + кеш
        self._sales_cache = repo.list_sales()
        self.full_table.setRowCount(len(self._sales_cache))
        for row, s in enumerate(self._sales_cache):
            self._set(self.full_table, row, 0, fmt_date(s.sale_date))
            self._set(self.full_table, row, 1, s.buyer_link or "—")
            self._set(self.full_table, row, 2, s.buyer_name or "—")
            self._set(self.full_table, row, 3, s.discount.name if s.discount else "—")
            self._set(self.full_table, row, 4, s.product.name if s.product else "—")
            self._set(self.full_table, row, 5, fmt_money(s.profit))
            self._set(self.full_table, row, 6, "открыть" if s.dialog_link else "—")
            self._set(self.full_table, row, 7, "есть" if s.receipt_path else "—")
            self._set(self.full_table, row, 8, s.frame.name if s.frame else "—")
            self._set(self.full_table, row, 9, "✓" if s.has_review else "")

        # График
        self.chart.refresh()
        
    @staticmethod
    def _set(table: QTableWidget, row: int, col: int, text: str):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        table.setItem(row, col, item)