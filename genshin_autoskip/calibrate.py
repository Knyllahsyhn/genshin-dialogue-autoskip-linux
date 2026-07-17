"""Calibration: window screenshot with marked checkpoints + actual colors.

Usage: bring Genshin into a dialogue scene, then:
    uv run python -m genshin_autoskip.calibrate
"""
import sys

from PIL import ImageDraw

from genshin_autoskip import config, detector
from genshin_autoskip.window import GenshinWindow


def main() -> int:
    try:
        cfg = config.load()
    except config.ConfigError as err:
        print(f"Configuration error: {err}")
        return 1

    expected = {
        "playing_icon": cfg.playing_icon_color,
        "dialogue_icon_lower": detector.WHITE,
        "dialogue_icon_higher": detector.WHITE,
        "loading_screen": detector.WHITE,
    }

    win = GenshinWindow.find()
    if win is None:
        print("Genshin window not found. Is the game running?")
        return 1

    size = win.size()
    image = win.screenshot()
    if size is None or image is None:
        print("Window found, but screenshot failed.")
        return 1

    width, height = size
    print(f"Window found: {width}x{height}")

    draw = ImageDraw.Draw(image)
    print(f"\n{'Checkpoint':<22} {'Coordinate':<12} {'Actual':<16} Expected")
    for name, (x, y) in detector.scaled_checkpoints(width, height, cfg.checkpoints).items():
        actual = win.read_pixel(x, y)
        marker = (
            "?"
            if actual is None
            else ("OK" if detector.color_matches(actual, expected[name], cfg.color_tolerance) else "!!")
        )
        print(f"{name:<22} ({x},{y})    {str(actual):<16} {expected[name]}  [{marker}]")
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), outline=(255, 0, 0), width=3)

    image.save("calibration.png")
    print("\nScreenshot with markers: calibration.png")
    print("Note: 'loading_screen' should be white ONLY on loading screens,")
    print("'playing_icon' should match only during a running dialogue, and the")
    print("dialogue_icons only while answer options are visible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
