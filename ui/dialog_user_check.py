# проверка пользователя


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QAbstractItemView,
)

from core import repository as repo
from ui.helpers import fmt_date, fmt_money


class UserCheckDialog(QDialog):
    def __init__(self, parent=None, initial_link: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Проверка пользователя")
        self.resize(820, 520)

        root = QVBoxLayout(self)

        top = QHBoxLayout()
        self.link_edit = QLineEdit()
        self.link_edit.setPlaceholderText("Вставь ссылку на профиль и нажми Enter")
        self.link_edit.setText(initial_link)
        self.link_edit.returnPressed.connect(self._search)
        btn = QPushButton("Найти")
        btn.clicked.connect(self._search)
        top.addWidget(self.link_edit, 1)
        top.addWidget(btn)
        root.addLayout(top)

        self.info = QLabel("Введи ссылку и нажми «Найти».")
        self.info.setStyleSheet("color: #333; font-size: 13px;")
        root.addWidget(self.info)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Дата", "Товар", "Рамка", "Получено", "Чистая прибыль"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.table, 1)

        if initial_link:
            self._search()

    def _search(self):
        link = self.link_edit.text().strip()
        if not link:
            return

        sales = repo.user_sales(link)
        self.table.setRowCount(len(sales))

        total_amount = 0.0
        total_profit = 0.0
        for row, s in enumerate(sales):
            self._set(row, 0, fmt_date(s.sale_date))
            self._set(row, 1, s.product.name if s.product else "—")
            self._set(row, 2, s.frame.name if s.frame else "—")
            self._set(row, 3, fmt_money(s.amount_received))
            self._set(row, 4, fmt_money(s.profit))
            total_amount += s.amount_received
            total_profit += s.profit

        if sales:
            name = sales[0].buyer_name or "—"
            has_review = "✓ да" if any(s.has_review for s in sales) else "нет"
            self.info.setText(
                f"<b>Имя:</b> {name} &nbsp;|&nbsp; "
                f"<b>Покупок:</b> {len(sales)} &nbsp;|&nbsp; "
                f"<b>Получено:</b> {fmt_money(total_amount)} &nbsp;|&nbsp; "
                f"<b>Чистая прибыль:</b> {fmt_money(total_profit)} &nbsp;|&nbsp; "
                f"<b>Отзыв:</b> {has_review}"
            )
        else:
            self.info.setText("Покупок по этой ссылке не найдено.")

    def _set(self, row: int, col: int, text: str):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, col, item)