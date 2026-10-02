# виджет графика


from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QDateEdit, QSizePolicy,
)

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core import repository as repo


class SalesChart(QWidget):
    """Контейнер с тремя графиками на вкладках."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- График 1: продажи и прибыль по дням ---
        self.tab_daily = _MplCanvas()
        self.tabs.addTab(self.tab_daily, "Продажи и прибыль")

        # --- График 2: топ постеров за месяц ---
        self.tab_top = _MonthChart(
            title="Какие постеры больше брали",
            loader=self._load_top_products,
            empty_text="Нет продаж за этот месяц",
        )
        self.tabs.addTab(self.tab_top, "Топ постеров за месяц")

        # --- График 3: рамки за месяц ---
        self.tab_frames = _MonthChart(
            title="Какие рамки брали (доп. продажи)",
            loader=self._load_frames,
            empty_text="Нет доп. продаж за этот месяц",
        )
        self.tabs.addTab(self.tab_frames, "Рамки за месяц")

        self.refresh()

    # ---------- Загрузчики данных ----------

    @staticmethod
    def _load_top_products(year: int, month: int):
        # считаем продажи основного товара
        rows = repo.top_products_by_month(year, month, product_type=None)
        return [(name, cnt) for name, cnt in rows]

    @staticmethod
    def _load_frames(year: int, month: int):
        return repo.frames_by_month(year, month)

    # ---------- Обновление ----------

    def refresh(self, from_date: date | None = None, to_date: date | None = None):
        # 1) Продажи и прибыль
        self._draw_daily(self.tab_daily, from_date, to_date)

        # 2) Топ постеров и 3) Рамки — по выбранному месяцу
        self.tab_top.reload()
        self.tab_frames.reload()

    def _draw_daily(self, canvas: "_MplCanvas",
                    from_date: date | None, to_date: date | None):
        data = repo.sales_by_day(from_date, to_date)

        canvas.figure.clear()
        ax = canvas.figure.add_subplot(111)

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

        canvas.figure.tight_layout()
        canvas.draw_idle()


class _MplCanvas(FigureCanvasQTAgg):
    """Обёртка над FigureCanvas для удобства."""

    def __init__(self):
        self.figure = Figure(figsize=(6, 3))
        super().__init__(self.figure)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


class _MonthChart(QWidget):
    """Круговая диаграмма за выбранный месяц."""

    def __init__(self, title: str, loader, empty_text: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._loader = loader
        self._empty_text = empty_text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # строка выбора месяца
        top = QHBoxLayout()
        top.addWidget(QLabel("Месяц:"))

        self.month_edit = QDateEdit()
        self.month_edit.setDisplayFormat("MM.yyyy")
        self.month_edit.setCalendarPopup(True)
        self.month_edit.setDate(QDate.currentDate())
        self.month_edit.dateChanged.connect(self.reload)
        top.addWidget(self.month_edit)

        top.addWidget(QLabel(f"  ·  {title}"))
        top.addStretch()
        layout.addLayout(top)

        self.canvas = _MplCanvas()
        layout.addWidget(self.canvas, 1)

        self.reload()

    def reload(self):
        qd = self.month_edit.date()
        year, month = qd.year(), qd.month()

        rows = self._loader(year, month)

        self.canvas.figure.clear()
        ax = self.canvas.figure.add_subplot(111)

        if not rows:
            ax.text(0.5, 0.5, self._empty_text, ha="center", va="center",
                    transform=ax.transAxes, fontsize=12, color="#888")
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            names = [r[0] for r in rows]
            counts = [r[1] for r in rows]

            # обрезаем слишком длинные названия для легенды
            def short(s: str, n: int = 22) -> str:
                return s if len(s) <= n else s[: n - 1] + "…"

            labels = [short(n) for n in names]

            # цвета — берём из палитры matplotlib
            import matplotlib.cm as cm
            import numpy as np
            colors = cm.tab20(np.linspace(0, 1, len(names)))

            wedges, texts, autotexts = ax.pie(
                counts,
                labels=None,                 # подписи вынесем в легенду
                autopct=lambda p: f"{p:.0f}%" if p >= 3 else "",
                startangle=90,
                counterclock=False,
                colors=colors,
                wedgeprops={"edgecolor": "white", "linewidth": 1},
                textprops={"fontsize": 9, "color": "white", "weight": "bold"},
            )

            ax.axis("equal")                 # чтобы круг был ровным
            ax.legend(
                wedges,
                [f"{lbl}  ({cnt})" for lbl, cnt in zip(labels, counts)],
                loc="center left",
                bbox_to_anchor=(1.0, 0.5),
                fontsize=9,
                frameon=False,
            )

        self.canvas.figure.tight_layout()
        self.canvas.draw_idle()