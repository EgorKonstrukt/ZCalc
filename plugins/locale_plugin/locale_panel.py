from __future__ import annotations
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
)
from PyQt5.QtCore import Qt
from .locale_registry import LocaleRegistry
from .builtin_strings import LOCALE_DISPLAY_NAMES

_NS = "locale_plugin"

class LocalePanel(QWidget):
    """Sidebar panel for switching the active application locale."""
    def __init__(self, registry: LocaleRegistry, context, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._reg = registry
        self._ctx = context
        self._build_ui()
        self._reg.add_observer(self._on_locale_changed)
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)
        self._hdr = QLabel(self._t("panel_title"))
        self._hdr.setStyleSheet("font-weight:bold;font-size:12px;")
        root.addWidget(self._hdr)
        row = QHBoxLayout()
        row.setSpacing(6)
        self._lbl = QLabel(self._t("label_locale"))
        self._combo = QComboBox()
        self._populate_combo()
        self._apply_btn = QPushButton(self._t("btn_apply"))
        self._apply_btn.clicked.connect(self._on_apply)
        row.addWidget(self._lbl)
        row.addWidget(self._combo, 1)
        row.addWidget(self._apply_btn)
        root.addLayout(row)
        root.addStretch()
    def _populate_combo(self) -> None:
        self._combo.clear()
        for code in self._reg.available_locales:
            label = LOCALE_DISPLAY_NAMES.get(code, code)
            self._combo.addItem(label, userData=code)
        cur = self._reg.locale
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == cur:
                self._combo.setCurrentIndex(i)
                break
    def _on_apply(self) -> None:
        code = self._combo.currentData()
        if code:
            self._reg.set_locale(code)
            self._ctx.config.set("locale_id", code)
            self._ctx.config.save()
    def _on_locale_changed(self, locale: str) -> None:
        self._hdr.setText(self._t("panel_title"))
        self._lbl.setText(self._t("label_locale"))
        self._apply_btn.setText(self._t("btn_apply"))
        self._populate_combo()
    def _t(self, key: str) -> str:
        return self._reg.tr(_NS, key)
    def closeEvent(self, event) -> None:
        self._reg.remove_observer(self._on_locale_changed)
        super().closeEvent(event)