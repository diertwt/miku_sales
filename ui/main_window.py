# главное окно с вкладками

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QMainWindow, QTabWidget

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

    def _on_tab_changed(self, index: int):
        w = self.tabs.widget(index)
        if hasattr(w, "refresh"):
            w.refresh()