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


class RichReporter:
    """Live status panel rendered with rich; same interface as PlainReporter."""

    def __init__(self, dry_run: bool = False) -> None:
        from rich.console import Console
        from rich.live import Live

        self.state = UiState(dry_run=dry_run)
        self._live = Live(self, console=Console(), refresh_per_second=4)

    def __enter__(self) -> "RichReporter":
        self._live.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        self._live.__exit__(*exc)

    def __rich__(self):
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        colors = {"run": "green", "pause": "yellow", "exit": "red"}
        names = {"run": "RUNNING", "pause": "PAUSED", "exit": "EXITING"}
        status = Text(
            f"● {names[self.state.status]}",
            style=f"bold {colors[self.state.status]}",
        )
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="dim", min_width=8)
        grid.add_column()
        grid.add_row("status", status)
        grid.add_row("uptime", format_uptime(time.monotonic() - self.state.started_at))
        grid.add_row("presses", str(self.state.presses))
        grid.add_row("breaks", str(self.state.breaks))
        grid.add_row("last", self.state.last_action or "—")
        if self.state.window_size:
            window = f"{self.state.window_size[0]}x{self.state.window_size[1]}"
        else:
            window = "searching..."
        grid.add_row("window", window)
        grid.add_row("", Text("[F8] start   [F9] pause   [F12] quit", style="dim"))

        title = "Genshin Dialogue Auto-Skipper"
        if self.state.dry_run:
            title += "  [DRY-RUN]"
        return Panel(grid, title=title, border_style="cyan", expand=False)

    def _log(self, text: str) -> None:
        self._live.console.print(text)

    def status_changed(self, status: str) -> None:
        self.state.status = status

    def pressed(self, action: str) -> None:
        self.state.presses += 1
        self.state.last_action = ACTION_LABELS.get(action, action)

    def dry_run_action(self, action: str) -> None:
        self.state.presses += 1
        self.state.last_action = ACTION_LABELS.get(action, action)
        self._log(f"[dim]\\[dry-run][/dim] would now: {ACTION_LABELS.get(action, action)}")

    def break_started(self, duration: float) -> None:
        self.state.breaks += 1
        self._log(f"Human-like break: {duration:.1f}s...")

    def window_missing(self) -> None:
        self.state.window_size = None

    def window_found(self, size: tuple[int, int] | None) -> None:
        self.state.window_size = size

    def window_lost(self) -> None:
        self.state.window_size = None
        self._log("Window lost — searching again...")


def make_reporter(dry_run: bool = False):
    """Rich panel on a real terminal, plain lines otherwise."""
    if sys.stdout.isatty():
        return RichReporter(dry_run=dry_run)
    return PlainReporter(dry_run=dry_run)
