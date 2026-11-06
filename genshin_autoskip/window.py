"""Access to the Genshin window: X11 backend, backend selection, shared helpers.

The X11 backend reads XWayland windows directly. A game running as a native
Wayland client is invisible to X11; ``WindowFinder`` then falls back to the
ScreenCast portal backend in ``portal.py``.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable

from Xlib import X, display
from Xlib.error import XError

from genshin_autoskip import detector

# Wine sets WM_CLASS to the exe name; the variants cover Lutris setups.
WM_CLASS_TOKENS = ("genshinimpact", "genshin impact", "yuanshen")

# Under Steam/HoYoPlay, launcher and helper windows share the WM_CLASS
# (steam_app_genshin) - only the window title identifies the game window.
GAME_TITLE = "genshin impact"


def matches_genshin(wm_class: tuple[str, str] | None) -> bool:
    if not wm_class:
        return False
    return any(token in part.lower() for part in wm_class for token in WM_CLASS_TOKENS)


def matches_title(wm_name: str | bytes | None) -> bool:
    if isinstance(wm_name, bytes):
        wm_name = wm_name.decode("utf-8", errors="ignore")
    if not wm_name:
        return False
    return wm_name.strip().casefold() == GAME_TITLE


def decode_zpixmap_rgb(data: bytes) -> tuple[int, int, int]:
    """First pixel of a 32-bit ZPixmap (little-endian BGRX) as RGB."""
    return (data[2], data[1], data[0])


def decode_zpixmap_patch(data: bytes, count: int) -> list[tuple[int, int, int]]:
    """All ``count`` pixels of a 32-bit ZPixmap (little-endian BGRX) as RGB."""
    return [(data[i + 2], data[i + 1], data[i]) for i in range(0, count * 4, 4)]


# Executable of the game client (global and CN build) at the start of argv[0].
GAME_EXE_RE = re.compile(r"(?:^|[/\\])(?:genshinimpact|yuanshen)\.exe(?:\s|$)", re.IGNORECASE)


class PortalError(Exception):
    """Portal capture could not be set up (retried on the next search)."""


class PortalCancelled(PortalError):
    """The user dismissed the portal dialog (not retried until restart)."""


def clamp_patch(
    cx: int, cy: int, radius: int, size: tuple[int, int]
) -> tuple[int, int, int, int] | None:
    """(x0, y0, w, h) of the (2*radius+1) square around (cx, cy), clamped to size."""
    width, height = size
    x0 = max(0, cx - radius)
    y0 = max(0, cy - radius)
    x1 = min(width, cx + radius + 1)
    y1 = min(height, cy + radius + 1)
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return None
    return x0, y0, w, h


def patch_from_frame(
    data: bytes, stride: int, x0: int, y0: int, w: int, h: int
) -> list[tuple[int, int, int]]:
    """RGB pixels of a rectangle inside a BGRx frame with the given row stride."""
    pixels: list[tuple[int, int, int]] = []
    for y in range(y0, y0 + h):
        start = y * stride + x0 * 4
        pixels.extend(decode_zpixmap_patch(data[start : start + w * 4], w))
    return pixels


def uses_wayland(environ: dict[str, str]) -> bool:
    """Whether a Wine/Proton process runs with the native Wayland driver."""
    if environ.get("PROTON_ENABLE_WAYLAND") == "1":
        return True
    return "wayland" in environ.get("WINE_GRAPHICS_DRIVER", "").lower()


def _read_environ(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for entry in path.read_bytes().split(b"\0"):
        key, sep, value = entry.decode("utf-8", errors="ignore").partition("=")
        if sep:
            env[key] = value
    return env


def _process_age(proc: Path, entry: Path) -> float:
    """Seconds since the process started (0.0 if /proc cannot tell)."""
    try:
        stat = (entry / "stat").read_text()
        # Fields after the "(comm)" part; starttime is field 22 overall.
        start_ticks = int(stat.rsplit(")", 1)[1].split()[19])
        uptime = float((proc / "uptime").read_text().split()[0])
        return max(0.0, uptime - start_ticks / os.sysconf("SC_CLK_TCK"))
    except (OSError, IndexError, ValueError):
        return 0.0


def find_game(proc: Path = Path("/proc")) -> tuple[str, float] | None:
    """(mode, age in seconds) of the game process, mode 'wayland' or 'x11'."""
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv0 = (entry / "cmdline").read_bytes().split(b"\0")[0]
            if not GAME_EXE_RE.search(argv0.decode("utf-8", errors="ignore")):
                continue
            mode = "wayland" if uses_wayland(_read_environ(entry / "environ")) else "x11"
        except OSError:
            continue
        return mode, _process_age(proc, entry)
    return None


class WindowFinder:
    """Picks the capture backend: X11 window if present, otherwise the portal.

    The portal opens a dialog, so it is only tried once the game process has
    run in Wayland mode for ``grace`` seconds (its window exists by then), and
    never again after the user cancelled it. A game that was started earlier
    is captured right away.
    """

    def __init__(
        self,
        x11_find: Callable[[], object | None] | None = None,
        portal_open: Callable[[], object] | None = None,
        find_game: Callable[[], tuple[str, float] | None] = find_game,
        clock: Callable[[], float] = time.monotonic,
        grace: float = 10.0,
    ) -> None:
        self._x11_find = x11_find or _x11_find
        self._portal_open = portal_open or _portal_open
        self._find_game = find_game
        self._clock = clock
        self._grace = grace
        self._wayland_since: float | None = None
        self.portal_cancelled = False
        self.last_error: str | None = None

    def portal_due(self) -> float | None:
        """Clock time of the next portal attempt, None if none is pending."""
        if self._wayland_since is None or self.portal_cancelled:
            return None
        return self._wayland_since + self._grace

    def __call__(self):
        win = self._x11_find()
        if win is not None:
            return win
        game = self._find_game()
        if game is None or game[0] != "wayland":
            self._wayland_since = None
            return None
        now = self._clock()
        if self._wayland_since is None:
            # count the grace period from the process start
            self._wayland_since = now - game[1]
        if self.portal_cancelled or now - self._wayland_since < self._grace:
            return None
        try:
            return self._portal_open()
        except PortalCancelled as err:
            self.portal_cancelled = True
            self.last_error = str(err)
        except PortalError as err:
            self.last_error = str(err)
            # back off: wait another grace period before the next dialog
            self._wayland_since = now
        return None


def _x11_find():
    if not os.environ.get("DISPLAY"):
        return None
    try:
        return GenshinWindow.find()
    except Exception:
        return None


def _portal_open():
    try:
        from genshin_autoskip import portal
    except ImportError as err:
        raise PortalCancelled(f"portal backend unavailable: {err}") from err
    return portal.PortalWindow.open()


class _PatchReader:
    """read_checkpoints on top of size() and read_patch(), shared by backends."""

    def read_checkpoints(
        self,
        checkpoints: dict[str, tuple[int, int]] | None = None,
        radius: int = 3,
    ) -> dict[str, list[detector.Pixel]] | None:
        size = self.size()
        if size is None:
            return None
        result: dict[str, list[detector.Pixel]] = {}
        for name, (x, y) in detector.scaled_checkpoints(*size, checkpoints).items():
            patch = self.read_patch(x, y, radius, size)
            if patch is None:
                return None
            result[name] = patch
        return result


class GenshinWindow(_PatchReader):
    """X11 backend (game running through XWayland)."""

    def __init__(self, disp: display.Display, win) -> None:
        self._display = disp
        self._window = win

    @classmethod
    def find(cls, disp: display.Display | None = None) -> "GenshinWindow | None":
        owns_display = disp is None
        disp = disp or display.Display()
        root = disp.screen().root
        win = cls._search(root)
        if win is None:
            if owns_display:
                disp.close()
            return None
        return cls(disp, win)

    @staticmethod
    def _search(win):
        try:
            if matches_genshin(win.get_wm_class()) or matches_title(win.get_wm_name()):
                return win
            for child in win.query_tree().children:
                found = GenshinWindow._search(child)
                if found is not None:
                    return found
        except XError:
            pass
        return None

    def size(self) -> tuple[int, int] | None:
        try:
            geo = self._window.get_geometry()
            return geo.width, geo.height
        except XError:
            return None

    def read_pixel(self, x: int, y: int) -> detector.Pixel | None:
        try:
            img = self._window.get_image(x, y, 1, 1, X.ZPixmap, 0xFFFFFFFF)
            return decode_zpixmap_rgb(img.data)
        except XError:
            return None

    def read_patch(
        self, cx: int, cy: int, radius: int, size: tuple[int, int] | None = None
    ) -> list[detector.Pixel] | None:
        """Sample a (2*radius+1) square around (cx, cy), clamped to the window."""
        size = size or self.size()
        if size is None:
            return None
        rect = clamp_patch(cx, cy, radius, size)
        if rect is None:
            return None
        x0, y0, w, h = rect
        try:
            img = self._window.get_image(x0, y0, w, h, X.ZPixmap, 0xFFFFFFFF)
            return decode_zpixmap_patch(img.data, w * h)
        except XError:
            return None

    def screenshot(self):
        """The whole window as a PIL image (only used by calibrate.py)."""
        from PIL import Image

        size = self.size()
        if size is None:
            return None
        w, h = size
        try:
            img = self._window.get_image(0, 0, w, h, X.ZPixmap, 0xFFFFFFFF)
        except XError:
            return None
        return Image.frombytes("RGB", (w, h), img.data, "raw", "BGRX")

    def close(self) -> None:
        try:
            self._display.close()
        except Exception:
            pass
