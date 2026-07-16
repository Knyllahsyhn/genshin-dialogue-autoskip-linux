"""Calibration: window screenshot with marked checkpoints + actual colors.

Usage: bring Genshin into a dialogue scene, then:
    uv run python -m genshin_autoskip.calibrate
"""
import sys

from PIL import ImageDraw

from genshin_autoskip import detector
from genshin_autoskip.window import GenshinWindow

EXPECTED = {
    "playing_icon": detector.PLAYING_ICON_COLOR,
    "dialogue_icon_lower": detector.WHITE,
    "dialogue_icon_higher": detector.WHITE,
    "loading_screen": detector.WHITE,
}


def main() -> int:
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
    for name, (x, y) in detector.scaled_checkpoints(width, height).items():
        actual = win.read_pixel(x, y)
        expected = EXPECTED[name]
        marker = "?" if actual is None else ("OK" if detector.color_matches(actual, expected) else "!!")
        print(f"{name:<22} ({x},{y})    {str(actual):<16} {expected}  [{marker}]")
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), outline=(255, 0, 0), width=3)

    image.save("calibration.png")
    print("\nScreenshot with markers: calibration.png")
    print("Note: 'loading_screen' should be white ONLY on loading screens,")
    print("'playing_icon' should match only during a running dialogue, and the")
    print("dialogue_icons only while answer options are visible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
