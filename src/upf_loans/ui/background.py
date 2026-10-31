"""Run a slow function (network, file copy) off the UI thread."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)


class _Task(QRunnable):
    def __init__(self, fn: Callable[..., Any], signals: _Signals, with_progress: bool):
        super().__init__()
        self.fn = fn
        self.signals = signals
        self.with_progress = with_progress

    def run(self) -> None:
        try:
            result = self.fn(self.signals.progress.emit) if self.with_progress else self.fn()
        except Exception as exc:  # noqa: BLE001 - reported to the UI
            self.signals.failed.emit(str(exc))
            return
        self.signals.done.emit(result)


_alive: set[_Signals] = set()


def run(fn: Callable[..., Any], on_done: Callable[[Any], None], on_error: Callable[[str], None],
        on_progress: Callable[[int, int], None] | None = None) -> None:
    signals = _Signals()
    _alive.add(signals)
    signals.done.connect(on_done)
    signals.failed.connect(on_error)
    signals.done.connect(lambda _r: _alive.discard(signals))
    signals.failed.connect(lambda _e: _alive.discard(signals))
    if on_progress:
        signals.progress.connect(on_progress)
    QThreadPool.globalInstance().start(_Task(fn, signals, on_progress is not None))
