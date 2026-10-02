from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDoubleSpinBox, QCheckBox, QPlainTextEdit, QDialogButtonBox,
    QMessageBox, QLabel,
)

from core import repository as repo
from core.config import EXPENSE_FIXED, EXPENSE_PERCENT
from core.models import Expense


class ExpenseDialog(QDialog):
    def __init__(self, parent=None, expense: Expense | None = None):
        super().__init__(parent)
        self.expense = expense

        self.setWindowTitle("Редактирование расхода" if expense else "Новый расход")
        self.resize(440, 380)

        root = QVBoxLayout(self)
        form = QFormLayout()

        # Название
        self.name_edit = QLineEdit()
        form.addRow("Название:", self.name_edit)

        # Тип расчёта
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Фиксированная сумма (₽)", EXPENSE_FIXED)
        self.kind_combo.addItem("Процент от суммы (%)", EXPENSE_PERCENT)
        self.kind_combo.currentIndexChanged.connect(self._update_suffix)
        form.addRow("Тип расчёта:", self.kind_combo)

        # Значение
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(0, 10_000_000)
        self.value_spin.setDecimals(2)
        form.addRow("Значение:", self.value_spin)

        # По умолчанию
        self.default_check = QCheckBox("Включать в новые продажи автоматически")
        form.addRow("", self.default_check)

        # Примечание
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(80)
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

        self._update_suffix()

        if expense:
            self._fill(expense)

    def _update_suffix(self):
        if self.kind_combo.currentData() == EXPENSE_PERCENT:
            self.value_spin.setSuffix(" %")
        else:
            self.value_spin.setSuffix(" ₽")

    def _fill(self, e: Expense):
        self.name_edit.setText(e.name)
        i = self.kind_combo.findData(e.kind)
        if i >= 0:
            self.kind_combo.setCurrentIndex(i)
        self.value_spin.setValue(e.value or 0)
        self.default_check.setChecked(bool(e.is_default))
        self.note_edit.setPlainText(e.note or "")
        self._update_suffix()

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введи название.")
            return

        data = dict(
            name=name,
            kind=self.kind_combo.currentData(),
            value=self.value_spin.value(),
            is_default=self.default_check.isChecked(),
            note=self.note_edit.toPlainText().strip(),
        )

        try:
            if self.expense:
                repo.update_expense(self.expense.id, **data)
            else:
                repo.add_expense(**data)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")
            return
        self.accept()