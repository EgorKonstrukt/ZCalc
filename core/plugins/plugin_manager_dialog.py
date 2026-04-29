from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

if TYPE_CHECKING:
    from core.plugins.plugin_manager import PluginManager

_HEADER_STYLE = (
    "QLabel{font-size:14px;font-weight:bold;color:#1a1a2e;}"
)

_META_STYLE = "QLabel{font-size:11px;color:#555;}"
_NAME_STYLE = "QLabel{font-size:13px;font-weight:bold;color:#222;}"
_BTN_ENABLE = (
    "QPushButton{background:#27ae60;color:white;border:none;border-radius:4px;"
    "font-size:11px;padding:4px 12px;}"
    "QPushButton:hover{background:#219150;}"
)
_BTN_DISABLE = (
    "QPushButton{background:#e74c3c;color:white;border:none;border-radius:4px;"
    "font-size:11px;padding:4px 12px;}"
    "QPushButton:hover{background:#c0392b;}"
)
_TAG_STYLE = (
    "QLabel{background:#eaf4fb;color:#2980b9;border-radius:3px;"
    "font-size:10px;padding:2px 6px;}"
)
_ERR_STYLE = "QLabel{color:#e74c3c;font-size:10px;}"


def _kind_tag(plugin) -> str:
    from core.plugins.plugin_base import PanelPlugin, SidebarPlugin, MenuPlugin
    if isinstance(plugin, PanelPlugin):
        return "Panel item"
    if isinstance(plugin, SidebarPlugin):
        return "Sidebar panel"
    if isinstance(plugin, MenuPlugin):
        return "Menu actions"
    return "Plugin"


class PluginManagerDialog(QDialog):
    """
    Modal dialog showing all discovered plugins with enable/disable controls.
    """

    def __init__(self, manager: "PluginManager", parent: QWidget = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self.setWindowTitle("Plugin Manager")
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        header = QLabel("Plugin Manager")
        root.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#ddd;")
        root.addWidget(sep)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)
        root.addWidget(self._scroll, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._refresh_list()

    def _refresh_list(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        records = self._manager.records()
        if not records:
            empty = QLabel("No plugins found in the plugins/ directory.")
            empty.setStyleSheet(_META_STYLE)
            empty.setAlignment(Qt.AlignCenter)
            self._list_layout.insertWidget(0, empty)
            return

        for i, rec in enumerate(records):
            card = self._make_card(rec)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, rec) -> QFrame:
        card = QFrame()
        card.setObjectName("plugin_card")

        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        info = QVBoxLayout()
        info.setSpacing(3)

        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_lbl = QLabel(rec.meta.name)
        name_lbl.setStyleSheet(_NAME_STYLE)
        tag = QLabel(_kind_tag(rec.plugin))
        tag.setStyleSheet(_TAG_STYLE)
        name_row.addWidget(name_lbl)
        name_row.addWidget(tag)
        name_row.addStretch()
        info.addLayout(name_row)

        desc = QLabel(rec.meta.description)
        desc.setStyleSheet(_META_STYLE)
        desc.setWordWrap(True)
        info.addWidget(desc)

        meta_line = QLabel(
            f"v{rec.meta.version}  |  {rec.meta.author}  |  id: {rec.meta.id}"
        )
        meta_line.setStyleSheet("QLabel{font-size:9px;color:#aaa;}")
        info.addWidget(meta_line)

        if rec.error:
            err = QLabel(f"Error: {rec.error}")
            err.setStyleSheet(_ERR_STYLE)
            info.addWidget(err)

        lay.addLayout(info, 1)

        toggle = QPushButton("Disable" if rec.enabled else "Enable")
        toggle.setStyleSheet(_BTN_DISABLE if rec.enabled else _BTN_ENABLE)
        toggle.setFixedWidth(72)
        toggle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        pid = rec.meta.id

        def on_toggle(checked=False, _pid=pid, _btn=toggle, _rec=rec):
            if _rec.enabled:
                self._manager.disable_plugin(_pid)
                _btn.setText("Enable")
                _btn.setStyleSheet(_BTN_ENABLE)
                _rec.enabled = False
            else:
                self._manager.enable_plugin(_pid)
                _btn.setText("Disable")
                _btn.setStyleSheet(_BTN_DISABLE)
                _rec.enabled = True

        toggle.clicked.connect(on_toggle)
        lay.addWidget(toggle, 0, Qt.AlignVCenter)

        return card
