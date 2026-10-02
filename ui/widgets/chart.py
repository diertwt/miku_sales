# виджет графика


from datetime import date

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core import repository as repo


class SalesChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(6, 3), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.refresh()

    def refresh(self, from_date: date | None = None, to_date: date | None = None):
        data = repo.sales_by_day(from_date, to_date)
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not data:
            ax.text(0.5, 0.5, "Нет данных", ha="center", va="center",
                    transform=ax.transAxes, fontsize=12, color="#888")
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            days = [d.strftime("%d.%m") for d, _, _ in data]
            amounts = [a for _, a, _ in data]
            profits = [p for _, _, p in data]
            x = range(len(days))
            width = 0.4
            ax.bar([i - width / 2 for i in x], amounts, width,
                   label="Получено", color="#4a90e2")
            ax.bar([i + width / 2 for i in x], profits, width,
                   label="Чистая прибыль", color="#27ae60")
            ax.set_xticks(list(x))
            ax.set_xticklabels(days, rotation=45, ha="right")
            ax.legend(loc="upper left", fontsize=9)
            ax.grid(axis="y", alpha=0.3)

        self.canvas.draw_idle()