"""Lightweight monitor for VPNSentinel components.

Contract:
- Monitor provides a Monitor class with start(), stop(), and is_running()
- Configurable heartbeat interval and a callback invoked on each heartbeat.
- Emits JSON-serializable heartbeat dicts via the callback when provided.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Callable, Optional, Dict, Any


class Monitor:
    """Simple monitor that emits heartbeats on a background thread.

    Example heartbeat payload:
    {
        "ts": 1690000000.0,
        "component": "server",
        "status": "ok",
        "info": { ... }
    }

    The callback receives the heartbeat dict as its only argument.
    """

    def __init__(
        self,
        component: str = "component",
        interval: float = 5.0,
        on_heartbeat: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.component = component
        self.interval = float(interval)
        self.on_heartbeat = on_heartbeat

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            t = self._thread
        if t:
            t.join(timeout=2.0)

    def is_running(self) -> bool:
        with self._lock:
            return bool(self._thread and self._thread.is_alive())

    def _run(self) -> None:
        while not self._stop_event.is_set():
            hb = self._make_heartbeat()
            try:
                if self.on_heartbeat:
                    self.on_heartbeat(hb)
            except Exception:
                # Avoid crashing the thread on callback errors
                pass
            # Wait for the interval, but exit early if stopped
            finished = self._stop_event.wait(self.interval)
            if finished:
                break

    def _make_heartbeat(self) -> Dict[str, Any]:
        payload = {
            "ts": time.time(),
            "component": self.component,
            "status": "ok",
            "info": {},
        }
        return payload

    def heartbeat_json(self) -> str:
        return json.dumps(self._make_heartbeat())
