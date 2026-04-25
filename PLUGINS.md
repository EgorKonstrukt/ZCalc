# ZCalc Plugin System

## Overview

ZCalc supports three plugin types:

| Type | Base class | What it does |
|---|---|---|
| **Panel item** | `PanelPlugin` | Adds a new item type to the expression list (via the `+ Add` menu) |
| **Sidebar panel** | `SidebarPlugin` | Adds a widget to the bottom sidebar area |
| **Menu actions** | `MenuPlugin` | Registers `QAction` objects into existing menus |

Plugins are distributed as `.dll` files — zip archives containing Python
source, loadable by Python's built-in `zipimport` mechanism without extraction.

---

## Plugin file format

A `.dll` plugin is a zip archive with this structure:

```
my_plugin.dll (zip)
└── my_plugin/
    ├── __init__.py   ← must export PLUGIN_META and get_plugin()
    └── widgets.py    ← any additional modules
```

### Required exports in `__init__.py`

```python
from core.plugin_base import PanelPlugin, PluginMeta

PLUGIN_META = PluginMeta(
    id="com.yourname.myplugin",  # unique reverse-DNS id
    name="My Plugin",
    version="1.0.0",
    author="Your Name",
    description="What this plugin does.",
)

class MyPlugin(PanelPlugin):
    meta = PLUGIN_META

    def create_item(self, context):
        return MyWidget()          # must return a QWidget

def get_plugin():
    return MyPlugin()
```

---

## Packaging a plugin

```bash
python pack_plugin.py plugins/my_plugin_dir --out plugins/
```

This creates `plugins/my_plugin_dir.dll`, which ZCalc loads automatically
on the next launch.

---

## Installing a plugin

Drop the `.dll` file into the `plugins/` directory next to `ZCalc.py`.
Open **Plugins → Manage Plugins** to enable/disable without restarting.

---

## AppContext API

Every plugin receives an `AppContext` with access to:

| Property / method | Type | Description |
|---|---|---|
| `context.chart` | `ChartWidget` | The plot widget |
| `context.panel` | `FunctionPanel` | The expression panel |
| `context.history` | `History` | Undo/redo stack |
| `context.config` | `Config` | Persistent settings |
| `context.request_replot()` | method | Trigger a replot |
| `context.show_status(msg)` | method | Show status bar message |
| `context.get_menu(name)` | method | Get a top-level QMenu |
| `context.register_service(key, obj)` | method | Share objects between plugins |
| `context.get_service(key)` | method | Retrieve a shared object |

---

## Item widget contract (PanelPlugin)

Item widgets returned by `create_item()` should implement:

- `changed` pyqtSignal — emitted when the item changes (triggers replot)
- `removed` pyqtSignal(object) — emitted when the user clicks remove
- `to_state() -> dict` — serialise to a plain dict for session save
- `apply_state(state: dict)` — restore from a saved dict

---

## Built-in plugins

### Comments (`zcalc.comments`)

Adds colour-coded sticky-note style text items to the expression list.
Click `◉` to cycle through five colour themes.

### Folders (`zcalc.folders`)

Adds collapsible folder headers (Desmos-style) to visually group items.
Click the arrow to collapse/expand, `◉` to cycle folder colour,
and `👁` to toggle visibility of contents.
