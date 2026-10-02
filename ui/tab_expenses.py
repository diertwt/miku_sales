from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QLineEdit,
)

from core import repository as repo
from core.config import EXPENSE_PERCENT
from ui.dialog_expense import ExpenseDialog


class ExpensesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        top = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить расход")
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
            ["Название", "Тип", "Значение", "По умолчанию", "Примечание"]
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
        items = repo.list_expenses()
        if search:
            items = [e for e in items if search in e.name.lower()]

        self._cache = items
        self.table.setRowCount(len(items))
        for row, e in enumerate(items):
            self._set(row, 0, e.name)
            self._set(row, 1, "Процент" if e.kind == EXPENSE_PERCENT else "Фикс")
            val = f"{e.value:g}%" if e.kind == EXPENSE_PERCENT else f"{e.value:g} ₽"
            self._set(row, 2, val)
            self._set(row, 3, "✓" if e.is_default else "")
            self._set(row, 4, e.note or "")

    def _set(self, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, col, item)

    def _selected(self):
        row = self.table.currentRow()
        return self._cache[row] if 0 <= row < len(self._cache) else None

    def on_add(self):
        if ExpenseDialog(self).exec():
            self.refresh()

    def on_edit(self, *args):
        e = self._selected()
        if not e:
            return
        if ExpenseDialog(self, expense=e).exec():
            self.refresh()

    def on_delete(self):
        e = self._selected()
        if not e:
            return
        if QMessageBox.question(self, "Удалить?",
                                f"Удалить расход «{e.name}»?") == QMessageBox.Yes:
            repo.delete_expense(e.id)
            self.refresh()