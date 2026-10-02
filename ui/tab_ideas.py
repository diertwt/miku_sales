# "Идеи"


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QLabel,
)

from core import repository as repo


class IdeasTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(QLabel("Новая идея:"))
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Напиши идею и нажми «Добавить» "
                                      "(Ctrl+Enter — быстрая отправка)")
        self.input.setMaximumHeight(110)

        # Ctrl+Enter — отправить
        self.input.installEventFilter(self)

        root.addWidget(self.input)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить идею")
        btn_add.clicked.connect(self.on_add)
        btn_row.addWidget(btn_add)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addWidget(QLabel("Список идей:"))
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.itemDoubleClicked.connect(self.on_copy)
        root.addWidget(self.list, 1)

        btn_del = QPushButton("🗑 Удалить выбранную")
        btn_del.clicked.connect(self.on_delete)
        root.addWidget(btn_del)

        self.refresh()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeySequence
        if obj is self.input and event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Return
                    and event.modifiers() & Qt.ControlModifier):
                self.on_add()
                return True
        return super().eventFilter(obj, event)

    def refresh(self):
        self._cache = repo.list_ideas()
        self.list.clear()
        for idea in self._cache:
            ts = idea.created_at.strftime("%d.%m.%Y %H:%M")
            text = idea.text.replace("\n", " ")
            item = QListWidgetItem(f"[{ts}]  {text}")
            item.setData(Qt.UserRole, idea.id)
            self.list.addItem(item)

    def on_add(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        repo.add_idea(text)
        self.input.clear()
        self.refresh()

    def on_delete(self):
        item = self.list.currentItem()
        if not item:
            return
        idea_id = item.data(Qt.UserRole)
        if QMessageBox.question(self, "Удалить?",
                                "Удалить выбранную идею?") == QMessageBox.Yes:
            repo.delete_idea(idea_id)
            self.refresh()

    def on_copy(self, item):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(item.text())