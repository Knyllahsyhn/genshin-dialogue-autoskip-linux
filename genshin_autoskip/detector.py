"""Pixel-basierte Dialog-Erkennung, Prüfpunkte portiert aus dem Original."""

Pixel = tuple[int, int, int]

REF_WIDTH = 1920
REF_HEIGHT = 1080

CHECKPOINTS: dict[str, tuple[int, int]] = {
    "playing_icon": (84, 46),
    "dialogue_icon_lower": (1301, 808),
    "dialogue_icon_higher": (1301, 790),
    "loading_screen": (1200, 700),
}

PLAYING_ICON_COLOR: Pixel = (236, 229, 216)
WHITE: Pixel = (255, 255, 255)
COLOR_TOLERANCE = 10


def scale_point(point: tuple[int, int], width: int, height: int) -> tuple[int, int]:
    """1080p-Referenzkoordinate auf die tatsächliche Fenstergröße umrechnen."""
    x, y = point
    return (int(x / REF_WIDTH * width), int(y / REF_HEIGHT * height))


def scaled_checkpoints(width: int, height: int) -> dict[str, tuple[int, int]]:
    return {name: scale_point(p, width, height) for name, p in CHECKPOINTS.items()}


def color_matches(actual: Pixel, expected: Pixel, tolerance: int = COLOR_TOLERANCE) -> bool:
    """Wine/Farbprofile verschieben Farben leicht — deshalb Toleranz statt Gleichheit."""
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))
