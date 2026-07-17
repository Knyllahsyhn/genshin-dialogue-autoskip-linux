"""Pixel-based dialogue detection; checkpoints ported from the original."""
from genshin_autoskip.config import DEFAULT_CONFIG, Config

Pixel = tuple[int, int, int]

REF_WIDTH = 1920
REF_HEIGHT = 1080

WHITE: Pixel = (255, 255, 255)


def scale_point(point: tuple[int, int], width: int, height: int) -> tuple[int, int]:
    """Convert a 1080p reference coordinate to the actual window size."""
    x, y = point
    return (int(x / REF_WIDTH * width), int(y / REF_HEIGHT * height))


def scaled_checkpoints(
    width: int, height: int, checkpoints: dict[str, tuple[int, int]] | None = None
) -> dict[str, tuple[int, int]]:
    if checkpoints is None:
        checkpoints = DEFAULT_CONFIG.checkpoints
    return {name: scale_point(p, width, height) for name, p in checkpoints.items()}


def color_matches(actual: Pixel, expected: Pixel, tolerance: int = 10) -> bool:
    """Wine/color profiles shift colors slightly, hence tolerance over equality."""
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))


def patch_matches(
    patch: list[Pixel], expected: Pixel, tolerance: int, min_fraction: float
) -> bool:
    """True when at least ``min_fraction`` of the sampled patch matches ``expected``.

    A single pixel is brittle: the speech-bubble icon holds grey dots inside white,
    and scaling nudges the sample off-center. Sampling a small box and requiring a
    fraction (not every pixel) absorbs both.
    """
    if not patch:
        return False
    hits = sum(color_matches(p, expected, tolerance) for p in patch)
    return hits / len(patch) >= min_fraction


def is_loading_screen(px: dict[str, list[Pixel]], cfg: Config = DEFAULT_CONFIG) -> bool:
    return patch_matches(px["loading_screen"], WHITE, cfg.color_tolerance, cfg.match_fraction)


def is_dialogue_playing(px: dict[str, list[Pixel]], cfg: Config = DEFAULT_CONFIG) -> bool:
    return patch_matches(
        px["playing_icon"], cfg.playing_icon_color, cfg.color_tolerance, cfg.match_fraction
    )


def is_dialogue_option_visible(
    px: dict[str, list[Pixel]], cfg: Config = DEFAULT_CONFIG
) -> bool:
    return patch_matches(
        px["dialogue_icon_lower"], WHITE, cfg.color_tolerance, cfg.match_fraction
    ) or patch_matches(
        px["dialogue_icon_higher"], WHITE, cfg.color_tolerance, cfg.match_fraction
    )


def decide(px: dict[str, list[Pixel]] | None, cfg: Config = DEFAULT_CONFIG) -> str | None:
    """What should happen this tick?

    None = do nothing, "skip" = dialogue is playing, keep advancing,
    "confirm" = confirm the first answer option.
    With auto_confirm disabled, visible options yield None so the user
    can pick an answer manually.
    """
    if px is None:
        return None
    if is_loading_screen(px, cfg):
        return None
    if is_dialogue_option_visible(px, cfg):
        return "confirm" if cfg.auto_confirm else None
    if is_dialogue_playing(px, cfg):
        return "skip"
    return None
