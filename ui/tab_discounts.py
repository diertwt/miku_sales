# "Скидки"


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QLineEdit,
)

from core import repository as repo
from ui.dialog_discount import DiscountDialog
from ui.helpers import fmt_date


class DiscountsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        top = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить скидку")
        btn_add.clicked.connect(self.on_add)
        top.addWidget(btn_add)

        btn_edit = QPushButton("✎ Редактировать")
        btn_edit.clicked.connect(self.on_edit)
        top.addWidget(btn_edit)

        btn_del = QPushButton("🗑 Удалить")
        btn_del.clicked.connect(self.on_delete)
        top.addWidget(btn_del)

        top.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("поиск по названию…")
        self.search_edit.textChanged.connect(self.refresh)
        top.addWidget(self.search_edit)

        root.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Размер", "Начало", "Конец", "Примечание"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self.on_edit)
        root.addWidget(self.table, 1)

        self.refresh()

    def refresh(self):
        search = self.search_edit.text().strip().lower()
        items = repo.list_discounts()
        if search:
            items = [d for d in items if search in d.name.lower()]

        self._cache = items
        self.table.setRowCount(len(items))
        for row, d in enumerate(items):
            self._set(row, 0, d.name)
            self._set(row, 1, f"{d.percent:g}%")
            self._set(row, 2, fmt_date(d.start_date) if d.start_date else "—")
            self._set(row, 3, fmt_date(d.end_date) if d.end_date else "—")
            self._set(row, 4, d.note or "")

    def _set(self, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, col, item)

    def _selected(self):
        row = self.table.currentRow()
        return self._cache[row] if 0 <= row < len(self._cache) else None

    def on_add(self):
        if DiscountDialog(self).exec():
            self.refresh()

    def on_edit(self, *args):
        d = self._selected()
        if not d:
            return
        if DiscountDialog(self, discount=d).exec():
            self.refresh()

    def on_delete(self):
        d = self._selected()
        if not d:
            return
        if QMessageBox.question(self, "Удалить?",
                                f"Удалить скидку «{d.name}»?") == QMessageBox.Yes:
            repo.delete_discount(d.id)
            self.refresh()