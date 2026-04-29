from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox, QGroupBox,
)
from core.plugins.settings_page import SettingsPage
from .locale_registry import LocaleRegistry
from .builtin_strings import LOCALE_DISPLAY_NAMES
if TYPE_CHECKING:
    from core import AppContext

_GROUP_STYLE = (
    "QGroupBox{font-size:11px;font-weight:bold;color:#555;"
    "border:1px solid #ddd;border-radius:6px;margin-top:8px;"
    "padding:8px 6px 6px 6px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;}"
)

class LocaleSettingsPage(SettingsPage):
    """Settings tab for locale selection."""
    tab_label = "Language"
    def __init__(self, registry: LocaleRegistry) -> None:
        self._registry = registry
        self._ctx: "AppContext" = None
        self._combo: QComboBox = None
    def create_widget(self, context: "AppContext") -> QWidget:
        self._ctx = context
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(10)
        grp = QGroupBox("Application Language")
        grp.setStyleSheet(_GROUP_STYLE)
        gl = QGridLayout(grp)
        gl.setSpacing(8)
        gl.setColumnMinimumWidth(0, 160)
        hint = QLabel(
            "Select the UI language. Plugins that support localization will "
            "update their labels automatically."
        )
        hint.setStyleSheet("QLabel{font-size:11px;color:#888;}")
        hint.setWordWrap(True)
        gl.addWidget(hint, 0, 0, 1, 2)
        gl.addWidget(QLabel("Active locale:"), 1, 0)
        self._combo = QComboBox()
        gl.addWidget(self._combo, 1, 1)
        info_lbl = QLabel(
            "Changes take effect on Apply. Some widgets may require a restart."
        )
        info_lbl.setStyleSheet("QLabel{font-size:10px;color:#aaa;}")
        info_lbl.setWordWrap(True)
        gl.addWidget(info_lbl, 2, 0, 1, 2)
        root.addWidget(grp)
        root.addStretch()
        return w
    def load(self) -> None:
        self._combo.clear()
        for code in self._registry.available_locales:
            label = LOCALE_DISPLAY_NAMES.get(code, code)
            self._combo.addItem(label, userData=code)
        cur = self._registry.locale
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == cur:
                self._combo.setCurrentIndex(i)
                break
    def apply(self) -> None:
        code = self._combo.currentData()
        if code:
            self._registry.set_locale(code)
            if self._ctx:
                self._ctx.config.set("locale_id", code)
                self._ctx.config.save()
    def reset(self) -> None:
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == "en":
                self._combo.setCurrentIndex(i)
                break