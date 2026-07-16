"""Terminal UI: status reporting, echo suppression, desktop notifications."""
from __future__ import annotations

import subprocess
import sys
import termios
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

ACTION_LABELS = {"skip": "skip dialogue", "confirm": "confirm option 1"}


@dataclass
class UiState:
    status: str = "pause"
    dry_run: bool = False
    presses: int = 0
    breaks: int = 0
    last_action: str | None = None
    window_size: tuple[int, int] | None = None
    started_at: float = field(default_factory=time.monotonic)


def format_uptime(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@contextmanager
def terminal_echo_off():
    """Suppress terminal echo (hotkeys like F8 otherwise print ^[[19~)."""
    if not sys.stdin.isatty():
        yield
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = list(old)
    new[3] = new[3] & ~termios.ECHO
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, new)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def notify(text: str) -> None:
    """Best-effort desktop notification; silently ignores any failure."""
    try:
        subprocess.run(
            ["notify-send", "--app-name=genshin-autoskip", "Genshin Auto-Skip", text],
            timeout=2,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


class PlainReporter:
    """Simple line output — non-TTY fallback (pipes, background jobs)."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def __enter__(self) -> "PlainReporter":
        print("Genshin Dialogue Auto-Skipper")
        print("  [F8]  Start    [F9]  Pause    [F12] Quit")
        if self.dry_run:
            print("  Mode: DRY-RUN (no keys will be sent)")
        print("\nWaiting for F8...")
        return self

    def __exit__(self, *exc) -> None:
        return None

    def status_changed(self, status: str) -> None:
        print(f"\n>>> Status: {status.upper()}")

    def pressed(self, action: str) -> None:
        pass

    def dry_run_action(self, action: str) -> None:
        print(f"[dry-run] Would now: {ACTION_LABELS.get(action, action)}")

    def break_started(self, duration: float) -> None:
        print(f"Human-like break: {duration:.1f}s...")

    def window_missing(self) -> None:
        print("Genshin window not found — waiting...")

    def window_found(self, size: tuple[int, int] | None) -> None:
        pass

    def window_lost(self) -> None:
        print("Window lost — searching again...")
