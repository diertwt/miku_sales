# главное окно с вкладками

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QFileDialog, QMessageBox,
)
from core.excel_export import (
    get_excel_path, set_excel_path, export_sales,
)

from ui.tab_sales import SalesTab
from ui.tab_products import ProductsTab
from ui.tab_discounts import DiscountsTab
from ui.tab_expenses import ExpensesTab
from ui.tab_ideas import IdeasTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Учёт продаж")
        self.resize(1200, 800)

        tabs = QTabWidget()
        tabs.setFont(QFont("", 11))

        self.sales_tab = SalesTab()
        self.products_tab = ProductsTab()
        self.discounts_tab = DiscountsTab()
        self.expenses_tab = ExpensesTab()
        self.ideas_tab = IdeasTab()

        tabs.addTab(self.sales_tab, "Учёт продаж")
        tabs.addTab(self.products_tab, "Цены")
        tabs.addTab(self.discounts_tab, "Скидки")
        tabs.addTab(self.expenses_tab, "Расходы")
        tabs.addTab(self.ideas_tab, "Идеи")

        tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs = tabs
        self.setCentralWidget(tabs)

        # Настройка и ручной запуск синхронизации Excel.
        export_menu = self.menuBar().addMenu("Excel")
        choose_action = export_menu.addAction("Выбрать файл Excel…")
        choose_action.triggered.connect(self.choose_excel_file)
        sync_action = export_menu.addAction("Синхронизировать сейчас")
        sync_action.triggered.connect(self.sync_excel_now)

    def choose_excel_file(self):
        current = get_excel_path()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Выбрать книгу Excel для синхронизации",
            current or "Продажи.xlsx",
            "Книга Excel (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            count = export_sales(path)
            set_excel_path(path)
        except Exception as exc:
            QMessageBox.critical(
                self, "Не удалось экспортировать продажи",
                f"Excel-файл не обновлён.\n\n{exc}",
            )
            return

        QMessageBox.information(
            self, "Синхронизация настроена",
            f"Экспортировано продаж: {count}\n\n"
            f"Файл:\n{path}\n\n"
            "Теперь лист «Продажи» будет обновляться автоматически "
            "при обновлении списка продаж.",
        )

    def sync_excel_now(self):
        path = get_excel_path()
        if not path:
            self.choose_excel_file()
            return
        try:
            count = export_sales(path)
        except Exception as exc:
            QMessageBox.warning(
                self, "Ошибка синхронизации",
                f"Не удалось обновить Excel.\n\n{exc}\n\n"
                "Закрой файл Excel, если он открыт, и повтори попытку.",
            )
            return
        QMessageBox.information(
            self, "Excel обновлён",
            f"Экспортировано продаж: {count}\nФайл: {path}",
        )

    def _on_tab_changed(self, index: int):
        w = self.tabs.widget(index)
        if hasattr(w, "refresh"):
            w.refresh()