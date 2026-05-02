from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING
from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QTabBar,
    QTabWidget, QLabel, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from .console_api import ConsoleAPI
from .repl_tab import ReplTabWidget
from .script_tab import ScriptTabWidget
from .console_model import ConsoleLine
from .console_theme import DEFAULT_COLORS

_DOCK_STYLE = f"QDockWidget{{background:{DEFAULT_COLORS.bg};}}"
_TAB_STYLE = (
    f"QTabWidget::pane{{background:{DEFAULT_COLORS.bg};border:none;}}"
    f"QTabBar::tab{{background:{DEFAULT_COLORS.tab_inactive};color:{DEFAULT_COLORS.tab_text};"
    f"padding:4px 12px;border:none;border-right:1px solid {DEFAULT_COLORS.border};"
    f"font-size:10px;}}"
    f"QTabBar::tab:selected{{background:{DEFAULT_COLORS.tab_active};color:#ffffff;"
    f"border-bottom:2px solid #89b4fa;}}"
    f"QTabBar::tab:hover{{background:{DEFAULT_COLORS.selection_bg};}}"
    f"QTabWidget{{background:{DEFAULT_COLORS.bg};}}"
)

class ConsoleDock(QDockWidget):
    """
    Main console dock widget.
    Hosts a REPL tab plus per-script output tabs, all driven by ConsoleAPI.
    """
    def __init__(self, api: ConsoleAPI, parent=None) -> None:
        super().__init__("Console", parent)
        self._api = api
        self._script_tabs: Dict[str, ScriptTabWidget] = {}
        self._repl_tab: Optional[ReplTabWidget] = None
        self.setObjectName("ZarCalcConsoleDock")
        self.setStyleSheet(_DOCK_STYLE)
        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable,
        )
        self._build_ui()
        self._connect_api()

    def _build_ui(self) -> None:
        container = QWidget()
        container.setStyleSheet(f"QWidget{{background:{DEFAULT_COLORS.bg};}}")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(_TAB_STYLE)
        self._tabs.setTabPosition(QTabWidget.North)
        self._tabs.setDocumentMode(True)
        self._tabs.setMovable(True)
        lay.addWidget(self._tabs)
        self._repl_tab = ReplTabWidget(self._api)
        self._tabs.addTab(self._repl_tab, "REPL")
        self.setWidget(container)

    def _connect_api(self) -> None:
        self._api.line_appended.connect(self._on_line)
        self._api.tab_added.connect(self._on_tab_added)
        self._api.tab_removed.connect(self._on_tab_removed)
        self._api.tab_focused.connect(self._focus_tab)
        self._api.cleared.connect(self._on_cleared)

    def _on_line(self, payload) -> None:
        tab_id, line = payload
        if tab_id == "__repl__":
            return
        tab = self._script_tabs.get(tab_id)
        if tab is not None:
            tab.append_line(line)

    def _on_tab_added(self, tab_id: str, label: str) -> None:
        if tab_id in self._script_tabs:
            return
        tab = ScriptTabWidget(tab_id, label)
        tab.save_requested.connect(lambda path, tid=tab_id: self._api.save_to_file(path, tid))
        self._script_tabs[tab_id] = tab
        self._tabs.addTab(tab, label)
        self._tabs.setCurrentWidget(tab)

    def _on_tab_removed(self, tab_id: str) -> None:
        tab = self._script_tabs.pop(tab_id, None)
        if tab is None:
            return
        idx = self._tabs.indexOf(tab)
        if idx >= 0:
            self._tabs.removeTab(idx)
        tab.deleteLater()

    def _focus_tab(self, tab_id: str) -> None:
        if tab_id == "__repl__" and self._repl_tab:
            self._tabs.setCurrentWidget(self._repl_tab)
            return
        tab = self._script_tabs.get(tab_id)
        if tab:
            self._tabs.setCurrentWidget(tab)

    def _on_cleared(self) -> None:
        cur = self._tabs.currentWidget()
        if isinstance(cur, ScriptTabWidget):
            cur.clear_output()

    def show_and_focus(self) -> None:
        self.setVisible(True)
        self.raise_()
        if self._repl_tab:
            self._repl_tab.focus_input()