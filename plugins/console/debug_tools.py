from __future__ import annotations
import gc
import sys
import inspect
import traceback
import time
import threading
from typing import Any, Dict, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .console_api import ConsoleAPI

def _sizeof(obj: Any, seen=None) -> int:
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum(_sizeof(v, seen) + _sizeof(k, seen) for k, v in obj.items())
    elif hasattr(obj, "__dict__"):
        size += _sizeof(obj.__dict__, seen)
    elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, bytearray)):
        try:
            size += sum(_sizeof(i, seen) for i in obj)
        except Exception:
            pass
    return size

class DebugTools:
    """Collection of debug utilities exposed on the console API."""
    def __init__(self, api: "ConsoleAPI") -> None:
        self._api = api

    def inspect(self, obj: Any) -> None:
        """Print detailed type, size, and attribute info for obj."""
        lines = [
            f"type      : {type(obj).__name__}",
            f"id        : {id(obj):#x}",
            f"repr      : {repr(obj)[:200]}",
            f"sys.size  : {sys.getsizeof(obj)} bytes",
        ]
        if hasattr(obj, "__dict__"):
            attrs = list(obj.__dict__.keys())[:30]
            lines.append(f"attrs     : {attrs}")
        if hasattr(obj, "__len__"):
            try:
                lines.append(f"len       : {len(obj)}")
            except Exception:
                pass
        self._api.log_info("\n".join(lines))

    def memory_summary(self) -> None:
        """Print top object types by count in the GC."""
        counts: Dict[str, int] = {}
        for obj in gc.get_objects():
            t = type(obj).__name__
            counts[t] = counts.get(t, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
        lines = ["GC object type counts (top 20):"]
        for name, cnt in top:
            lines.append(f"  {cnt:>8}  {name}")
        self._api.log_info("\n".join(lines))

    def traceback(self) -> None:
        """Print all active thread stacks."""
        lines = ["Active thread stacks:"]
        for tid, frame in sys._current_frames().items():
            tname = next((t.name for t in threading.enumerate() if t.ident == tid), str(tid))
            lines.append(f"\nThread: {tname} (id={tid})")
            lines.extend(traceback.format_stack(frame))
        self._api.log_info("\n".join(lines))

    def watch(self, expr: str, interval_s: float = 1.0) -> None:
        """Repeatedly evaluate expr in the REPL namespace and log it."""
        ns = self._api._executor.namespace
        def _tick():
            try:
                val = eval(expr, ns)
                self._api.log_debug(f"watch({expr}) = {val!r}")
            except Exception as exc:
                self._api.log_error(f"watch({expr}) error: {exc}")
        from PyQt5.QtCore import QTimer
        timer = QTimer()
        timer.setInterval(int(interval_s * 1000))
        timer.timeout.connect(_tick)
        timer.start()
        self._api._watch_timers.append(timer)
        self._api.log_info(f"Watching '{expr}' every {interval_s}s")

    def stop_watches(self) -> None:
        """Stop all active watch() timers."""
        for t in self._api._watch_timers:
            t.stop()
        self._api._watch_timers.clear()
        self._api.log_info("All watches stopped.")

    def sizeof(self, obj: Any) -> int:
        """Return recursive memory size estimate for obj in bytes."""
        size = _sizeof(obj)
        self._api.log_info(f"sizeof({type(obj).__name__}) = {size} bytes ({size/1024:.1f} KB)")
        return size

    def time_it(self, expr: str, n: int = 100) -> None:
        """Time expression evaluation n times and report."""
        ns = self._api._executor.namespace
        try:
            compiled = compile(expr, "<timeit>", "eval")
            start = time.perf_counter()
            for _ in range(n):
                eval(compiled, ns)
            elapsed = time.perf_counter() - start
            avg_us = elapsed / n * 1_000_000
            self._api.log_info(
                f"timeit({expr!r}, n={n}): total={elapsed*1000:.2f}ms avg={avg_us:.2f}us"
            )
        except Exception as exc:
            self._api.log_error(f"timeit error: {exc}")

    def gc_collect(self) -> None:
        """Force a garbage collection cycle and report counts."""
        before = len(gc.get_objects())
        collected = gc.collect()
        after = len(gc.get_objects())
        self._api.log_info(
            f"GC collect: {collected} collected, objects {before} -> {after}"
        )