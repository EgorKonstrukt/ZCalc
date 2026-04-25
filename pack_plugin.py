"""
pack_plugin.py  --  package a plugin directory into a .dll zip archive.

Usage:
    python pack_plugin.py plugins/your_plugin
    python pack_plugin.py plugins/your_plugin --out dist/

The resulting .dll is a standard zip archive importable by zipimport.
Python can import it directly; no extraction needed.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path


def pack(plugin_dir: Path, out_dir: Path) -> Path:
    """Bundle plugin_dir into out_dir/<plugin_dir.name>.dll."""
    if not (plugin_dir / "__init__.py").exists():
        sys.exit(f"Error: {plugin_dir} has no __init__.py")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{plugin_dir.name}.dll"
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for py_file in sorted(plugin_dir.rglob("*.py")):
            arc_name = py_file.relative_to(plugin_dir.parent)
            zf.write(py_file, arc_name)
    print(f"Packed  {plugin_dir.name}  ->  {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Pack a ZCalc plugin into a .dll")
    parser.add_argument("plugin_dir", help="Path to the plugin directory")
    parser.add_argument("--out", default="plugins", help="Output directory (default: plugins/)")
    args = parser.parse_args()
    pack(Path(args.plugin_dir).resolve(), Path(args.out).resolve())


if __name__ == "__main__":
    main()
