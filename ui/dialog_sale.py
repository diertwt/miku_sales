# анкета продажи


import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDateEdit, QDoubleSpinBox, QPlainTextEdit, QCheckBox,
    QPushButton, QLabel, QFileDialog, QDialogButtonBox, QMessageBox,
)

from core import repository as repo
from core.models import Sale, PRODUCT_TYPE, FRAME_TYPE
from ui.helpers import qdate_to_date, date_to_qdate, fmt_money
from utils.paths import RECEIPTS_DIR


class SaleDialog(QDialog):
    def __init__(self, parent=None, sale: Sale | None = None):
        super().__init__(parent)
        self.sale = sale
        self._receipt_path = ""

        # кеш справочников, чтобы не дёргать БД в цикле
        self._products = {p.id: p for p in repo.list_products(PRODUCT_TYPE)}
        self._frames = {f.id: f for f in repo.list_products(FRAME_TYPE)}

        self.setWindowTitle("Редактирование продажи" if sale else "Новая продажа")
        self.resize(580, 720)

        self._build_ui()

        if sale:
            self._fill_from_sale(sale)
        else:
            self._recalc_profit()

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())

        # Дата
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Дата:", self.date_edit)

        # Ссылка на профиль
        self.link_edit = QLineEdit()
        self.link_edit.setPlaceholderText("https://avito.ru/user/...")
        self.link_edit.editingFinished.connect(self._autofill_review)
        form.addRow("Кому (ссылка):", self.link_edit)

        # Имя
        self.name_edit = QLineEdit()
        form.addRow("Имя:", self.name_edit)

        # Скидка
        self.discount_combo = QComboBox()
        self.discount_combo.addItem("— без скидки —", None)
        for d in repo.list_discounts():
            self.discount_combo.addItem(f"{d.name} ({d.percent:g}%)", d.id)
        form.addRow("Скидка:", self.discount_combo)

        # Товар
        self.product_combo = QComboBox()
        self.product_combo.addItem("— не выбрано —", None)
        for p in self._products.values():
            self.product_combo.addItem(
                f"{p.name}  (себест. {p.cost:.0f} ₽)", p.id
            )
        self.product_combo.currentIndexChanged.connect(self._recalc_profit)
        form.addRow("Товар:", self.product_combo)

        # Рамка
        self.frame_combo = QComboBox()
        self.frame_combo.addItem("— без рамки —", None)
        for f in self._frames.values():
            self.frame_combo.addItem(
                f"{f.name}  (себест. {f.cost:.0f} ₽)", f.id
            )
        self.frame_combo.currentIndexChanged.connect(self._recalc_profit)
        form.addRow("Рамка:", self.frame_combo)

        # Сумма к получению
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10_000_000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix(" ₽")
        self.amount_spin.valueChanged.connect(self._recalc_profit)
        form.addRow("Сумма к получению:", self.amount_spin)

        # Авторасчёт прибыли
        self.profit_label = QLabel("0.00 ₽")
        self.profit_label.setStyleSheet(
            "font-weight: bold; color: #27ae60; font-size: 14px;"
        )
        form.addRow("Чистая прибыль:", self.profit_label)

        # Ссылка на диалог
        self.dialog_edit = QLineEdit()
        form.addRow("Ссылка на диалог:", self.dialog_edit)

        # Чек
        receipt_row = QHBoxLayout()
        self.receipt_label = QLabel("— не выбран —")
        self.receipt_label.setStyleSheet("color: #666;")
        btn_receipt = QPushButton("Выбрать файл…")
        btn_receipt.clicked.connect(self._choose_receipt)
        btn_clear = QPushButton("×")
        btn_clear.setFixedWidth(32)
        btn_clear.setToolTip("Убрать чек")
        btn_clear.clicked.connect(self._clear_receipt)
        receipt_row.addWidget(self.receipt_label, 1)
        receipt_row.addWidget(btn_receipt)
        receipt_row.addWidget(btn_clear)
        form.addRow("Чек:", receipt_row)

        # Примечание
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(80)
        form.addRow("Примечание:", self.note_edit)

        # Отзыв
        self.review_check = QCheckBox("Покупатель оставил отзыв")
        form.addRow("", self.review_check)

        root.addLayout(form)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ---------- Логика ----------

    def _recalc_profit(self):
        pid = self.product_combo.currentData()
        fid = self.frame_combo.currentData()
        p = self._products.get(pid) if pid else None
        f = self._frames.get(fid) if fid else None
        profit = repo.calc_profit(
            self.amount_spin.value(),
            p.cost if p else 0.0,
            f.cost if f else 0.0,
        )
        self.profit_label.setText(fmt_money(profit))

    def _autofill_review(self):
        """Подтянуть статус отзыва по последней продаже этого покупателя."""
        if self.sale:
            return  # при редактировании не трогаем
        link = self.link_edit.text().strip()
        if not link:
            self.review_check.setChecked(False)
            return
        past = repo.user_sales(link)
        if past:
            self.review_check.setChecked(any(s.has_review for s in past))

    def _choose_receipt(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать чек", "",
            "Все файлы (*.*);;Изображения (*.png *.jpg *.jpeg);;PDF (*.pdf)"
        )
        if path:
            self._receipt_path = path
            self.receipt_label.setText(Path(path).name)

    def _clear_receipt(self):
        self._receipt_path = ""
        self.receipt_label.setText("— не выбран —")

    def _save_receipt_copy(self, src: str) -> str:
        """Копирует файл чека в data/receipts/ и возвращает новый путь."""
        if not src:
            return ""
        src_path = Path(src)
        # если файл уже там — не копируем
        try:
            if src_path.parent.resolve() == RECEIPTS_DIR.resolve():
                return str(src_path)
        except OSError:
            pass
        ext = src_path.suffix
        dst = RECEIPTS_DIR / f"{uuid.uuid4().hex}{ext}"
        shutil.copy2(src_path, dst)
        return str(dst)

    def _fill_from_sale(self, sale: Sale):
        self.date_edit.setDate(date_to_qdate(sale.sale_date))
        self.link_edit.setText(sale.buyer_link or "")
        self.name_edit.setText(sale.buyer_name or "")

        if sale.discount_id:
            i = self.discount_combo.findData(sale.discount_id)
            if i >= 0:
                self.discount_combo.setCurrentIndex(i)
        if sale.product_id:
            i = self.product_combo.findData(sale.product_id)
            if i >= 0:
                self.product_combo.setCurrentIndex(i)
        if sale.frame_id:
            i = self.frame_combo.findData(sale.frame_id)
            if i >= 0:
                self.frame_combo.setCurrentIndex(i)

        self.amount_spin.setValue(sale.amount_received or 0.0)
        self.dialog_edit.setText(sale.dialog_link or "")
        self._receipt_path = sale.receipt_path or ""
        self.receipt_label.setText(
            Path(self._receipt_path).name if self._receipt_path else "— не выбран —"
        )
        self.note_edit.setPlainText(sale.note or "")
        self.review_check.setChecked(bool(sale.has_review))
        self._recalc_profit()

    def _on_ok(self):
        if not self.link_edit.text().strip() and not self.name_edit.text().strip():
            QMessageBox.warning(
                self, "Ошибка",
                "Заполни хотя бы имя или ссылку на профиль."
            )
            return

        new_receipt = self._save_receipt_copy(self._receipt_path)

        data = dict(
            sale_date=qdate_to_date(self.date_edit.date()),
            buyer_link=self.link_edit.text().strip(),
            buyer_name=self.name_edit.text().strip(),
            amount_received=self.amount_spin.value(),
            product_id=self.product_combo.currentData(),
            frame_id=self.frame_combo.currentData(),
            discount_id=self.discount_combo.currentData(),
            dialog_link=self.dialog_edit.text().strip(),
            receipt_path=new_receipt,
            note=self.note_edit.toPlainText().strip(),
            has_review=self.review_check.isChecked(),
        )

        if self.sale:
            repo.update_sale(self.sale.id, **data)
        else:
            repo.add_sale(**data)

        self.accept()