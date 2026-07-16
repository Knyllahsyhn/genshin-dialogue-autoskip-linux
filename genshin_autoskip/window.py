"""X11-Zugriff auf das Genshin-XWayland-Fenster (Suche, Geometrie, Pixel)."""
from __future__ import annotations

from Xlib import X, display
from Xlib.error import XError

from genshin_autoskip import detector

# Wine setzt WM_CLASS auf den exe-Namen; Varianten decken Lutris-Setups ab.
WM_CLASS_TOKENS = ("genshinimpact", "genshin impact", "yuanshen")


def matches_genshin(wm_class: tuple[str, str] | None) -> bool:
    if not wm_class:
        return False
    return any(token in part.lower() for part in wm_class for token in WM_CLASS_TOKENS)


def decode_zpixmap_rgb(data: bytes) -> tuple[int, int, int]:
    """Erstes Pixel eines 32-bit-ZPixmap (little-endian BGRX) als RGB."""
    return (data[2], data[1], data[0])


class GenshinWindow:
    def __init__(self, disp: display.Display, win) -> None:
        self._display = disp
        self._window = win

    @classmethod
    def find(cls, disp: display.Display | None = None) -> "GenshinWindow | None":
        disp = disp or display.Display()
        root = disp.screen().root
        win = cls._search(root)
        return cls(disp, win) if win is not None else None

    @staticmethod
    def _search(win):
        try:
            if matches_genshin(win.get_wm_class()):
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
        """Ganzes Fenster als PIL-Image (nur für calibrate.py)."""
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
