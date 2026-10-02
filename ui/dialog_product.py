# анкета товара


from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDoubleSpinBox, QDateEdit, QPlainTextEdit, QCheckBox,
    QDialogButtonBox, QMessageBox, QLabel,
)
from PySide6.QtCore import QDate

from core import repository as repo
from core.models import Product, PRODUCT_TYPE, FRAME_TYPE
from ui.helpers import qdate_to_date, date_to_qdate


class ProductDialog(QDialog):
    def __init__(self, parent=None, product: Product | None = None,
                 default_type: str = PRODUCT_TYPE):
        super().__init__(parent)
        self.product = product

        self.setWindowTitle(
            "Редактирование" if product else "Новый товар / рамка"
        )
        self.resize(460, 460)

        root = QVBoxLayout(self)
        form = QFormLayout()

        # Тип
        self.type_combo = QComboBox()
        self.type_combo.addItem("Товар", PRODUCT_TYPE)
        self.type_combo.addItem("Рамка", FRAME_TYPE)
        i = self.type_combo.findData(default_type)
        if i >= 0:
            self.type_combo.setCurrentIndex(i)
        form.addRow("Тип:", self.type_combo)

        # Название
        self.name_edit = QLineEdit()
        form.addRow("Название:", self.name_edit)

        # Цена без скидки
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 10_000_000)
        self.price_spin.setDecimals(2)
        self.price_spin.setSuffix(" ₽")
        form.addRow("Цена без скидки:", self.price_spin)

        # Себестоимость
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 10_000_000)
        self.cost_spin.setDecimals(2)
        self.cost_spin.setSuffix(" ₽")
        form.addRow("Себестоимость:", self.cost_spin)

        # Дата поступления (опционально)
        date_row = QVBoxLayout()
        self.has_start = QCheckBox("Указать дату поступления")
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd.MM.yyyy")
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setEnabled(False)
        self.has_start.toggled.connect(self.start_date.setEnabled)
        date_row.addWidget(self.has_start)
        date_row.addWidget(self.start_date)
        form.addRow("Поступит в продажу:", date_row)

        # Примечание
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(90)
        form.addRow("Примечание:", self.note_edit)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        if product:
            self._fill(product)

    def _fill(self, p: Product):
        i = self.type_combo.findData(p.type)
        if i >= 0:
            self.type_combo.setCurrentIndex(i)
        self.name_edit.setText(p.name)
        self.price_spin.setValue(p.price or 0)
        self.cost_spin.setValue(p.cost or 0)
        if p.start_date:
            self.has_start.setChecked(True)
            self.start_date.setDate(date_to_qdate(p.start_date))
        self.note_edit.setPlainText(p.note or "")

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введи название.")
            return

        start = (
            qdate_to_date(self.start_date.date())
            if self.has_start.isChecked() else None
        )

        data = dict(
            name=name,
            type_=self.type_combo.currentData(),
            price=self.price_spin.value(),
            cost=self.cost_spin.value(),
            start_date=start,
            note=self.note_edit.toPlainText().strip(),
        )

        try:
            if self.product:
                repo.update_product(self.product.id, **data)
            else:
                repo.add_product(**data)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")
            return
        self.accept()