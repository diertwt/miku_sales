# анкета продажи


import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QPlainTextEdit,
    QCheckBox, QPushButton, QLabel, QFileDialog, QDialogButtonBox,
    QMessageBox, QGroupBox,
)

from core import repository as repo
from core.config import (
    STANDARD_SIZES, CUSTOM_SIZE_LABEL, EXPENSE_PERCENT,
)
from core.models import Sale, PRODUCT_TYPE, FRAME_TYPE
from ui.helpers import qdate_to_date, date_to_qdate, fmt_money
from utils.paths import RECEIPTS_DIR


class SaleDialog(QDialog):
    def __init__(self, parent=None, sale: Sale | None = None):
        super().__init__(parent)
        self.sale = sale
        self._receipt_path = ""

        self._products = {p.id: p for p in repo.list_products(PRODUCT_TYPE)}
        self._frames = {f.id: f for f in repo.list_products(FRAME_TYPE)}
        self._expenses = repo.list_expenses()
        self._expense_checks: dict[int, QCheckBox] = {}
        self._user_touched_profit = False

        self.setWindowTitle("Редактирование продажи" if sale else "Новая продажа")
        self.resize(620, 900)

        self._build_ui()

        if sale:
            self._fill_from_sale(sale)
        else:
            self._apply_default_expenses()
            self._recalc_profit()

    # ---------- UI ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        form = QFormLayout()

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
            self.product_combo.addItem(f"{p.name}  (себест. {p.cost:.0f} ₽)", p.id)
        self.product_combo.currentIndexChanged.connect(self._recalc_profit)
        form.addRow("Товар:", self.product_combo)

        # Размер товара
        size_row = QHBoxLayout()
        self.size_combo = QComboBox()
        for s in STANDARD_SIZES:
            self.size_combo.addItem(s, s)
        self.size_combo.addItem(CUSTOM_SIZE_LABEL, None)
        self.size_combo.currentIndexChanged.connect(self._on_size_changed)
        self.size_custom = QLineEdit()
        self.size_custom.setPlaceholderText("своё значение…")
        self.size_custom.setVisible(False)
        size_row.addWidget(self.size_combo, 1)
        size_row.addWidget(self.size_custom, 1)
        form.addRow("Размер:", size_row)

        # Рамка
        self.frame_combo = QComboBox()
        self.frame_combo.addItem("— без рамки —", None)
        for f in self._frames.values():
            self.frame_combo.addItem(f"{f.name}  (себест. {f.cost:.0f} ₽)", f.id)
        self.frame_combo.currentIndexChanged.connect(self._recalc_profit)
        form.addRow("Рамка:", self.frame_combo)

        # Размер рамки
        frame_size_row = QHBoxLayout()
        self.frame_size_combo = QComboBox()
        for s in STANDARD_SIZES:
            self.frame_size_combo.addItem(s, s)
        self.frame_size_combo.addItem(CUSTOM_SIZE_LABEL, None)
        self.frame_size_combo.currentIndexChanged.connect(self._on_frame_size_changed)
        self.frame_size_custom = QLineEdit()
        self.frame_size_custom.setPlaceholderText("своё значение…")
        self.frame_size_custom.setVisible(False)
        frame_size_row.addWidget(self.frame_size_combo, 1)
        frame_size_row.addWidget(self.frame_size_custom, 1)
        form.addRow("Размер рамки:", frame_size_row)

        # Сумма
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10_000_000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix(" ₽")
        self.amount_spin.valueChanged.connect(self._recalc_profit)
        form.addRow("Сумма к получению:", self.amount_spin)

        root.addLayout(form)

        # ---- Блок расходов ----
        if self._expenses:
            expenses_box = QGroupBox("Расходы по заказу")
            exp_layout = QVBoxLayout(expenses_box)
            exp_layout.setContentsMargins(10, 10, 10, 10)

            grid = QGridLayout()
            for i, e in enumerate(self._expenses):
                if e.kind == EXPENSE_PERCENT:
                    text = f"{e.name}  ({e.value:g}%)"
                else:
                    text = f"{e.name}  ({e.value:g} ₽)"
                cb = QCheckBox(text)
                cb.toggled.connect(self._recalc_profit)
                self._expense_checks[e.id] = cb
                grid.addWidget(cb, i // 2, i % 2)
            exp_layout.addLayout(grid)
            root.addWidget(expenses_box)

        # ---- Прибыль ----
        profit_box = QGroupBox("Чистая прибыль")
        profit_layout = QGridLayout(profit_box)

        profit_layout.addWidget(QLabel("Авторасчёт:"), 0, 0)
        self.profit_auto_label = QLabel("0.00 ₽")
        self.profit_auto_label.setStyleSheet("color: #666; font-size: 13px;")
        profit_layout.addWidget(self.profit_auto_label, 0, 1)

        profit_layout.addWidget(QLabel("Итоговая:"), 1, 0)
        self.profit_spin = QDoubleSpinBox()
        self.profit_spin.setRange(-10_000_000, 10_000_000)
        self.profit_spin.setDecimals(2)
        self.profit_spin.setSuffix(" ₽")
        self.profit_spin.setStyleSheet(
            "font-weight: bold; color: #27ae60; font-size: 14px;"
        )
        self.profit_spin.valueChanged.connect(self._on_profit_manual_changed)
        profit_layout.addWidget(self.profit_spin, 1, 1)

        hint = QLabel("Не трогай — сохранится авторасчёт. "
                      "Изменишь — сохранится твоё число.")
        hint.setStyleSheet("color: #999; font-size: 11px;")
        profit_layout.addWidget(hint, 2, 0, 1, 2)

        root.addWidget(profit_box)

        # ---- Остальное ----
        form2 = QFormLayout()

        self.dialog_edit = QLineEdit()
        form2.addRow("Ссылка на диалог:", self.dialog_edit)

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
        form2.addRow("Чек:", receipt_row)

        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(70)
        form2.addRow("Примечание:", self.note_edit)

        self.review_check = QCheckBox("Покупатель оставил отзыв")
        form2.addRow("", self.review_check)

        root.addLayout(form2)

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

    def _on_size_changed(self):
        self.size_custom.setVisible(self.size_combo.currentData() is None)

    def _on_frame_size_changed(self):
        self.frame_size_custom.setVisible(
            self.frame_size_combo.currentData() is None
        )

    def _selected_expenses(self) -> list[dict]:
        """Собирает данные отмеченных расходов."""
        result = []
        for e in self._expenses:
            cb = self._expense_checks.get(e.id)
            if cb and cb.isChecked():
                result.append({
                    "expense_id": e.id,
                    "name": e.name,
                    "kind": e.kind,
                    "value": e.value,
                })
        return result

    def _compute_auto_profit(self) -> float:
        pid = self.product_combo.currentData()
        fid = self.frame_combo.currentData()
        p = self._products.get(pid) if pid else None
        f = self._frames.get(fid) if fid else None

        total_exp = 0.0
        amount = self.amount_spin.value()
        for e in self._selected_expenses():
            total_exp += repo.expense_amount(e["kind"], e["value"], amount)

        return repo.calc_profit(
            amount,
            p.cost if p else 0.0,
            f.cost if f else 0.0,
            total_exp,
        )

    def _recalc_profit(self, *args):
        auto = self._compute_auto_profit()
        self.profit_auto_label.setText(fmt_money(auto))
        if not self._user_touched_profit:
            # обновляем спин, но не помечаем как «ручное»
            self.profit_spin.blockSignals(True)
            self.profit_spin.setValue(auto)
            self.profit_spin.blockSignals(False)

    def _on_profit_manual_changed(self, _value):
        auto = self._compute_auto_profit()
        # если пользователь вернул ровно авто — считаем, что «не трогал»
        if abs(_value - auto) < 0.005:
            self._user_touched_profit = False
        else:
            self._user_touched_profit = True

    def _apply_default_expenses(self):
        for e in self._expenses:
            cb = self._expense_checks.get(e.id)
            if cb and e.is_default:
                cb.setChecked(True)

    def _autofill_review(self):
        if self.sale:
            return
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
        if not src:
            return ""
        src_path = Path(src)
        try:
            if src_path.parent.resolve() == RECEIPTS_DIR.resolve():
                return str(src_path)
        except OSError:
            pass
        ext = src_path.suffix
        dst = RECEIPTS_DIR / f"{uuid.uuid4().hex}{ext}"
        shutil.copy2(src_path, dst)
        return str(dst)

    def _restore_size(self, value: str, combo: QComboBox, custom_edit: QLineEdit):
        value = (value or "").strip()
        if not value:
            combo.setCurrentIndex(0)
            custom_edit.setText("")
            custom_edit.setVisible(False)
            return
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            custom_edit.setText("")
            custom_edit.setVisible(False)
        else:
            combo.setCurrentIndex(combo.findData(None))
            custom_edit.setText(value)
            custom_edit.setVisible(True)

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

        self._restore_size(sale.size, self.size_combo, self.size_custom)
        self._restore_size(sale.frame_size, self.frame_size_combo, self.frame_size_custom)

        self.amount_spin.setValue(sale.amount_received or 0.0)

        # Восстанавливаем отмеченные расходы
        for link in sale.expense_links:
            cb = self._expense_checks.get(link.expense_id) if link.expense_id else None
            if cb:
                cb.setChecked(True)

        self.dialog_edit.setText(sale.dialog_link or "")
        self._receipt_path = sale.receipt_path or ""
        self.receipt_label.setText(
            Path(self._receipt_path).name if self._receipt_path else "— не выбран —"
        )
        self.note_edit.setPlainText(sale.note or "")
        self.review_check.setChecked(bool(sale.has_review))

        # Прибыль: если сохраняли вручную — показываем сохранённое значение
        self._recalc_profit()   # сначала посчитает auto и поставит спин (пока user_touched=False)
        if sale.profit_manual:
            self.profit_spin.blockSignals(True)
            self.profit_spin.setValue(sale.profit)
            self.profit_spin.blockSignals(False)
            self._user_touched_profit = True

    def _on_ok(self):
        if not self.link_edit.text().strip() and not self.name_edit.text().strip():
            QMessageBox.warning(
                self, "Ошибка",
                "Заполни хотя бы имя или ссылку на профиль."
            )
            return

        new_receipt = self._save_receipt_copy(self._receipt_path)

        # размеры
        size_value = (self.size_custom.text().strip()
                      if self.size_combo.currentData() is None
                      else self.size_combo.currentData())
        frame_size_value = (self.frame_size_custom.text().strip()
                            if self.frame_size_combo.currentData() is None
                            else self.frame_size_combo.currentData())

        data = dict(
            sale_date=qdate_to_date(self.date_edit.date()),
            buyer_link=self.link_edit.text().strip(),
            buyer_name=self.name_edit.text().strip(),
            amount_received=self.amount_spin.value(),
            product_id=self.product_combo.currentData(),
            frame_id=self.frame_combo.currentData(),
            discount_id=self.discount_combo.currentData(),
            size=size_value or "",
            frame_size=frame_size_value or "",
            dialog_link=self.dialog_edit.text().strip(),
            receipt_path=new_receipt,
            note=self.note_edit.toPlainText().strip(),
            has_review=self.review_check.isChecked(),
        )

        expenses = self._selected_expenses()
        profit_override = (
            self.profit_spin.value() if self._user_touched_profit else None
        )

        if self.sale:
            repo.update_sale(
                self.sale.id,
                expenses=expenses,
                profit_override=profit_override,
                **data,
            )
        else:
            repo.add_sale(
                expenses=expenses,
                profit_override=profit_override,
                **data,
            )

        self.accept()