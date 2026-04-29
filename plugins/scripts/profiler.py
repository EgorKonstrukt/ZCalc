from __future__ import annotations
import atexit
import os
import time
import threading
from typing import Dict, Optional

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_SAMPLE_INTERVAL_S = 0.2
_JOIN_TIMEOUT_S = 0.5

_active_profilers: list = []
_profilers_lock = threading.Lock()


def _cleanup_all_profilers():
    with _profilers_lock:
        refs = list(_active_profilers)
    for ref in refs:
        try:
            ref._running = False
            if ref._thread and ref._thread.is_alive():
                ref._thread.join(timeout=_JOIN_TIMEOUT_S)
        except Exception:
            pass


atexit.register(_cleanup_all_profilers)


def _get_process():
    if _PSUTIL:
        return psutil.Process(os.getpid())
    return None


def get_memory_mb() -> float:
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


class ScriptProfiler:
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
        with _profilers_lock:
            _active_profilers.append(self)

    def start(self):
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
        self._running = False
        self._wall_elapsed = time.perf_counter() - self._wall_start
        self._cpu_elapsed = time.process_time() - self._cpu_start
        if self._thread:
            self._thread.join(timeout=_JOIN_TIMEOUT_S)
            self._thread = None

    def _sample_loop(self):
        if not _PSUTIL:
            return
        proc = _get_process()
        if proc is None:
            return
        proc.cpu_percent(interval=None)
        while self._running:
            time.sleep(_SAMPLE_INTERVAL_S)
            if not self._running:
                break
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
        if self._running:
            return time.perf_counter() - self._wall_start
        return self._wall_elapsed

    @property
    def cpu_s(self) -> float:
        if self._running:
            return time.process_time() - self._cpu_start
        return self._cpu_elapsed

    @property
    def mem_mb(self) -> float:
        with self._lock:
            return self._mem_current

    @property
    def mem_delta_mb(self) -> float:
        with self._lock:
            return self._mem_current - self._mem_start

    @property
    def mem_peak_mb(self) -> float:
        with self._lock:
            return self._mem_peak

    @property
    def cpu_percent(self) -> float:
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