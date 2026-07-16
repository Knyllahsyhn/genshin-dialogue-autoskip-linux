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


def is_loading_screen(px: dict[str, Pixel]) -> bool:
    return color_matches(px["loading_screen"], WHITE)


def is_dialogue_playing(px: dict[str, Pixel]) -> bool:
    return color_matches(px["playing_icon"], PLAYING_ICON_COLOR)


def is_dialogue_option_visible(px: dict[str, Pixel]) -> bool:
    return color_matches(px["dialogue_icon_lower"], WHITE) or color_matches(
        px["dialogue_icon_higher"], WHITE
    )


def decide(px: dict[str, Pixel] | None) -> str | None:
    """Was ist in diesem Tick zu tun?

    None = nichts, "skip" = Dialog läuft weiterklicken,
    "confirm" = erste Antwortoption bestätigen.
    """
    if px is None:
        return None
    if is_loading_screen(px):
        return None
    if is_dialogue_option_visible(px):
        return "confirm"
    if is_dialogue_playing(px):
        return "skip"
    return None
