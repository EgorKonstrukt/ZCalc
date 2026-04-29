from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class ThemeDef:
    name: str
    stylesheet: str
    palette_fn: str

_LIGHT_SS = ""

_DARK_SS = """
QMainWindow, QDialog, QWidget {
    background-color: #2b2b2b;
    color: #bbbbbb;
}
QMenuBar {
    background-color: #3c3f41;
    color: #bbbbbb;
}
QMenuBar::item:selected {
    background-color: #4c5052;
}
QMenu {
    background-color: #3c3f41;
    color: #bbbbbb;
    border: 1px solid #555555;
}
QMenu::item:selected {
    background-color: #4b6eaf;
}
QToolBar {
    background-color: #3c3f41;
    border: none;
}
QPushButton {
    background-color: #4c5052;
    color: #bbbbbb;
    border: 1px solid #5e6060;
    border-radius: 4px;
    padding: 4px 10px;
}
QPushButton:hover {
    background-color: #5c6164;
}
QPushButton:pressed {
    background-color: #3a3d3f;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #45494a;
    color: #bbbbbb;
    border: 1px solid #5e6060;
    border-radius: 3px;
    padding: 2px 4px;
    selection-background-color: #4b6eaf;
}
QComboBox QAbstractItemView {
    background-color: #3c3f41;
    color: #bbbbbb;
    selection-background-color: #4b6eaf;
}
QScrollBar:vertical {
    background: #3c3f41;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #5e6060;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #3c3f41;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #5e6060;
    border-radius: 4px;
    min-width: 20px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QSplitter::handle {
    background-color: #555555;
}
QStatusBar {
    background-color: #3c3f41;
    color: #bbbbbb;
}
QGroupBox {
    color: #bbbbbb;
    border: 1px solid #555555;
    border-radius: 6px;
    margin-top: 8px;
    padding: 8px 6px 6px 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
QLabel {
    color: #bbbbbb;
}
QCheckBox {
    color: #bbbbbb;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #777777;
    border-radius: 3px;
    background: #45494a;
}
QCheckBox::indicator:checked {
    background: #4b6eaf;
    border-color: #4b6eaf;
}
QSlider::groove:horizontal {
    background: #555555;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #4b6eaf;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QTabWidget::pane {
    border: 1px solid #555555;
    background: #2b2b2b;
}
QTabBar::tab {
    background: #3c3f41;
    color: #bbbbbb;
    padding: 4px 10px;
    border: 1px solid #555555;
    border-bottom: none;
}
QTabBar::tab:selected {
    background: #4b6eaf;
    color: white;
}
QHeaderView::section {
    background-color: #3c3f41;
    color: #bbbbbb;
    border: 1px solid #555555;
    padding: 4px;
}
QTableView, QListView, QTreeView {
    background-color: #2b2b2b;
    color: #bbbbbb;
    gridline-color: #555555;
    selection-background-color: #4b6eaf;
}
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #555555;
}
"""

_HC_SS = """
QMainWindow, QDialog, QWidget {
    background-color: #000000;
    color: #ffffff;
    font-family: "JetBrains Mono", "Consolas", monospace;
}
QMenuBar {
    background-color: #1a1a1a;
    color: #ffffff;
    border-bottom: 2px solid #ff8c00;
}
QMenuBar::item:selected {
    background-color: #ff8c00;
    color: #000000;
}
QMenu {
    background-color: #1a1a1a;
    color: #ffffff;
    border: 2px solid #ff8c00;
}
QMenu::item:selected {
    background-color: #ff8c00;
    color: #000000;
}
QToolBar {
    background-color: #1a1a1a;
    border: none;
    border-bottom: 1px solid #ff8c00;
}
QPushButton {
    background-color: #1a1a1a;
    color: #ffffff;
    border: 2px solid #ff8c00;
    border-radius: 2px;
    padding: 4px 10px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #ff8c00;
    color: #000000;
}
QPushButton:pressed {
    background-color: #cc7000;
    color: #000000;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0d0d0d;
    color: #ffffff;
    border: 2px solid #ff8c00;
    border-radius: 2px;
    padding: 2px 4px;
    selection-background-color: #ff8c00;
    selection-color: #000000;
}
QComboBox QAbstractItemView {
    background-color: #1a1a1a;
    color: #ffffff;
    border: 2px solid #ff8c00;
    selection-background-color: #ff8c00;
    selection-color: #000000;
}
QScrollBar:vertical {
    background: #0d0d0d;
    width: 12px;
    border-left: 1px solid #ff8c00;
}
QScrollBar::handle:vertical {
    background: #ff8c00;
    border-radius: 2px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #0d0d0d;
    height: 12px;
    border-top: 1px solid #ff8c00;
}
QScrollBar::handle:horizontal {
    background: #ff8c00;
    border-radius: 2px;
    min-width: 20px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QSplitter::handle {
    background-color: #ff8c00;
    width: 2px;
    height: 2px;
}
QStatusBar {
    background-color: #1a1a1a;
    color: #ff8c00;
    border-top: 2px solid #ff8c00;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 11px;
}
QGroupBox {
    color: #ff8c00;
    border: 2px solid #ff8c00;
    border-radius: 2px;
    margin-top: 8px;
    padding: 8px 6px 6px 6px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
QLabel {
    color: #ffffff;
}
QCheckBox {
    color: #ffffff;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 2px solid #ff8c00;
    border-radius: 0px;
    background: #000000;
}
QCheckBox::indicator:checked {
    background: #ff8c00;
    border-color: #ff8c00;
}
QSlider::groove:horizontal {
    background: #333333;
    height: 4px;
    border: 1px solid #ff8c00;
}
QSlider::handle:horizontal {
    background: #ff8c00;
    width: 14px;
    height: 14px;
    border-radius: 0px;
    margin: -5px 0;
}
QTabWidget::pane {
    border: 2px solid #ff8c00;
    background: #000000;
}
QTabBar::tab {
    background: #1a1a1a;
    color: #ffffff;
    padding: 4px 10px;
    border: 1px solid #ff8c00;
    border-bottom: none;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: #ff8c00;
    color: #000000;
}
QHeaderView::section {
    background-color: #1a1a1a;
    color: #ff8c00;
    border: 1px solid #ff8c00;
    padding: 4px;
    font-weight: bold;
}
QTableView, QListView, QTreeView {
    background-color: #000000;
    color: #ffffff;
    gridline-color: #ff8c00;
    selection-background-color: #ff8c00;
    selection-color: #000000;
}
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #ff8c00;
}
"""

THEMES: Dict[str, ThemeDef] = {
    "light": ThemeDef(name="Light", stylesheet=_LIGHT_SS, palette_fn="light"),
    "dark": ThemeDef(name="Dark (Fusion)", stylesheet=_DARK_SS, palette_fn="dark"),
    "high_contrast": ThemeDef(name="High Contrast (JetBrains)", stylesheet=_HC_SS, palette_fn="high_contrast"),
}