# "Цены"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox,
    QMessageBox, QLabel, QLineEdit,
)

from core import repository as repo
from core.models import PRODUCT_TYPE, FRAME_TYPE
from ui.dialog_product import ProductDialog
from ui.dialog_user_check import UserCheckDialog
from ui.helpers import fmt_date, fmt_money


class ProductsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        top = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить")
        btn_add.clicked.connect(self.on_add)
        top.addWidget(btn_add)

        btn_edit = QPushButton("✎ Редактировать")
        btn_edit.clicked.connect(self.on_edit)
        top.addWidget(btn_edit)

        btn_del = QPushButton("🗑 Удалить")
        btn_del.clicked.connect(self.on_delete)
        top.addWidget(btn_del)

        top.addStretch()

        # Быстрая проверка пользователя (по просьбе)
        btn_check = QPushButton("🔎 Проверка пользователя")
        btn_check.clicked.connect(lambda: UserCheckDialog(self).exec())
        top.addWidget(btn_check)

        root.addLayout(top)

        # Фильтр типа + поиск
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Показать:"))
        self.type_filter = QComboBox()
        self.type_filter.addItem("Все", None)
        self.type_filter.addItem("Только товары", PRODUCT_TYPE)
        self.type_filter.addItem("Только рамки", FRAME_TYPE)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.type_filter)

        filter_row.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("часть названия…")
        self.search_edit.textChanged.connect(self.refresh)
        filter_row.addWidget(self.search_edit, 1)
        root.addLayout(filter_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Тип", "Название", "Цена без скидки", "Себестоимость",
            "Поступит", "Примечание",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self.on_edit)
        root.addWidget(self.table, 1)

        self.refresh()

    def refresh(self):
        type_filter = self.type_filter.currentData()
        search = self.search_edit.text().strip().lower()

        all_items = repo.list_products(type_filter)
        if search:
            all_items = [p for p in all_items if search in p.name.lower()]

        self._cache = all_items
        self.table.setRowCount(len(all_items))
        for row, p in enumerate(all_items):
            self._set(row, 0, "Рамка" if p.type == FRAME_TYPE else "Товар")
            self._set(row, 1, p.name)
            self._set(row, 2, fmt_money(p.price))
            self._set(row, 3, fmt_money(p.cost))
            self._set(row, 4, fmt_date(p.start_date) if p.start_date else "—")
            self._set(row, 5, p.note or "")

    def _set(self, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, col, item)

    def _selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._cache):
            return self._cache[row]
        return None

    def on_add(self):
        # стартовый тип — тот, что выбран в фильтре (если не «Все»)
        default_type = self.type_filter.currentData() or PRODUCT_TYPE
        dlg = ProductDialog(self, default_type=default_type)
        if dlg.exec():
            self.refresh()

    def on_edit(self, *args):
        p = self._selected()
        if not p:
            return
        dlg = ProductDialog(self, product=p)
        if dlg.exec():
            self.refresh()

    def on_delete(self):
        p = self._selected()
        if not p:
            return
        ok = QMessageBox.question(
            self, "Удалить?",
            f"Удалить «{p.name}»? Записи о продажах с этим товаром/рамкой "
            f"останутся, но ссылка станет пустой."
        )
        if ok == QMessageBox.Yes:
            repo.delete_product(p.id)
            self.refresh()