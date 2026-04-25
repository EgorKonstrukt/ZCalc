from __future__ import annotations
import os
import sys
import time
import threading
from typing import Dict, Optional

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


def _get_process():
    if _PSUTIL:
        return psutil.Process(os.getpid())
    return None


def get_memory_mb() -> float:
    """Return current process RSS memory in megabytes."""
    if _PSUTIL:
        try:
            return _get_process().memory_info().rss / 1024 / 1024
        except Exception:
            pass
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:
        pass
    return 0.0


def get_cpu_percent() -> float:
    """Return current process CPU usage percent (0-100*n_cores)."""
    if _PSUTIL:
        try:
            return _get_process().cpu_percent(interval=None)
        except Exception:
            pass
    return 0.0


class ScriptProfiler:
    """
    Measures wall-clock time, CPU time, and memory delta for one script run.
    Thread-safe. Sampling runs in a background thread at ~200ms intervals.
    """
    def __init__(self):
        self._wall_start: float = 0.0
        self._cpu_start: float = 0.0
        self._mem_start: float = 0.0
        self._wall_elapsed: float = 0.0
        self._cpu_elapsed: float = 0.0
        self._mem_peak: float = 0.0
        self._mem_current: float = 0.0
        self._cpu_current: float = 0.0
        self._running = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start profiling."""
        self._wall_start = time.perf_counter()
        self._cpu_start = time.process_time()
        self._mem_start = get_memory_mb()
        self._mem_peak = self._mem_start
        self._mem_current = self._mem_start
        self._cpu_current = 0.0
        self._wall_elapsed = 0.0
        self._cpu_elapsed = 0.0
        self._running = True
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop profiling and record final measurements."""
        self._running = False
        self._wall_elapsed = time.perf_counter() - self._wall_start
        self._cpu_elapsed = time.process_time() - self._cpu_start
        if self._thread:
            self._thread.join(timeout=0.5)

    def _sample_loop(self):
        if not _PSUTIL:
            return
        proc = _get_process()
        if proc is None:
            return
        proc.cpu_percent(interval=None)
        while self._running:
            time.sleep(0.2)
            try:
                mem = proc.memory_info().rss / 1024 / 1024
                cpu = proc.cpu_percent(interval=None)
                with self._lock:
                    self._mem_current = mem
                    self._cpu_current = cpu
                    if mem > self._mem_peak:
                        self._mem_peak = mem
            except Exception:
                break

    @property
    def wall_s(self) -> float:
        """Wall-clock elapsed seconds (final after stop, live during run)."""
        if self._running:
            return time.perf_counter() - self._wall_start
        return self._wall_elapsed

    @property
    def cpu_s(self) -> float:
        """Process CPU seconds consumed."""
        if self._running:
            return time.process_time() - self._cpu_start
        return self._cpu_elapsed

    @property
    def mem_mb(self) -> float:
        """Current RSS memory in MB."""
        with self._lock:
            return self._mem_current

    @property
    def mem_delta_mb(self) -> float:
        """Memory growth since start in MB."""
        with self._lock:
            return self._mem_current - self._mem_start

    @property
    def mem_peak_mb(self) -> float:
        """Peak RSS memory since start in MB."""
        with self._lock:
            return self._mem_peak

    @property
    def cpu_percent(self) -> float:
        """Live CPU percent (requires psutil)."""
        with self._lock:
            return self._cpu_current

    def summary(self) -> Dict[str, float]:
        return {
            "wall_s":       self.wall_s,
            "cpu_s":        self.cpu_s,
            "mem_mb":       self.mem_mb,
            "mem_delta_mb": self.mem_delta_mb,
            "mem_peak_mb":  self.mem_peak_mb,
            "cpu_pct":      self.cpu_percent,
        }