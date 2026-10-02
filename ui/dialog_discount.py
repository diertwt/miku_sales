# анкета скидки


from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDoubleSpinBox,
    QDateEdit, QPlainTextEdit, QDialogButtonBox, QMessageBox, QCheckBox,
)

from core import repository as repo
from core.models import Discount
from ui.helpers import qdate_to_date, date_to_qdate


class DiscountDialog(QDialog):
    def __init__(self, parent=None, discount: Discount | None = None):
        super().__init__(parent)
        self.discount = discount
        self.setWindowTitle("Редактирование скидки" if discount else "Новая скидка")
        self.resize(440, 420)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Название:", self.name_edit)

        self.percent_spin = QDoubleSpinBox()
        self.percent_spin.setRange(0, 100)
        self.percent_spin.setDecimals(2)
        self.percent_spin.setSuffix(" %")
        form.addRow("Размер:", self.percent_spin)

        self.has_dates = QCheckBox("Указать период действия")
        form.addRow("", self.has_dates)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd.MM.yyyy")
        self.start_date.setDate(QDate.currentDate())

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd.MM.yyyy")
        self.end_date.setDate(QDate.currentDate())

        form.addRow("Дата начала:", self.start_date)
        form.addRow("Дата конца:", self.end_date)

        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(90)
        form.addRow("Примечание:", self.note_edit)

        root.addLayout(form)

        self.has_dates.toggled.connect(self._toggle_dates)
        self._toggle_dates(False)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        if discount:
            self._fill(discount)

    def _toggle_dates(self, enabled: bool):
        self.start_date.setEnabled(enabled)
        self.end_date.setEnabled(enabled)

    def _fill(self, d: Discount):
        self.name_edit.setText(d.name)
        self.percent_spin.setValue(d.percent or 0)
        if d.start_date or d.end_date:
            self.has_dates.setChecked(True)
            self._toggle_dates(True)
            if d.start_date:
                self.start_date.setDate(date_to_qdate(d.start_date))
            if d.end_date:
                self.end_date.setDate(date_to_qdate(d.end_date))
        self.note_edit.setPlainText(d.note or "")

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введи название.")
            return

        if self.has_dates.isChecked():
            start = qdate_to_date(self.start_date.date())
            end = qdate_to_date(self.end_date.date())
            if end < start:
                QMessageBox.warning(self, "Ошибка",
                                    "Дата конца раньше даты начала.")
                return
        else:
            start, end = None, None

        data = dict(
            name=name,
            percent=self.percent_spin.value(),
            start_date=start,
            end_date=end,
            note=self.note_edit.toPlainText().strip(),
        )

        try:
            if self.discount:
                repo.update_discount(self.discount.id, **data)
            else:
                repo.add_discount(**data)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")
            return
        self.accept()