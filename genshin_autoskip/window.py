"""X11 access to the Genshin XWayland window (search, geometry, pixels)."""
from __future__ import annotations

from Xlib import X, display
from Xlib.error import XError

from genshin_autoskip import detector

# Wine sets WM_CLASS to the exe name; the variants cover Lutris setups.
WM_CLASS_TOKENS = ("genshinimpact", "genshin impact", "yuanshen")

# Under Steam/HoYoPlay, launcher and helper windows share the WM_CLASS
# (steam_app_genshin) — only the window title identifies the game window.
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


class GenshinWindow:
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

    def read_checkpoints(self) -> dict[str, detector.Pixel] | None:
        size = self.size()
        if size is None:
            return None
        result: dict[str, detector.Pixel] = {}
        for name, (x, y) in detector.scaled_checkpoints(*size).items():
            pixel = self.read_pixel(x, y)
            if pixel is None:
                return None
            result[name] = pixel
        return result

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
