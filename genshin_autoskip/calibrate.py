"""Kalibrierung: Fenster-Screenshot mit markierten Prüfpunkten + Ist-Farben.

Nutzung: Genshin in eine Dialogszene bringen, dann:
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
        print("Genshin-Fenster nicht gefunden. Läuft das Spiel?")
        return 1

    size = win.size()
    image = win.screenshot()
    if size is None or image is None:
        print("Fenster gefunden, aber Screenshot fehlgeschlagen.")
        return 1

    width, height = size
    print(f"Fenster gefunden: {width}x{height}")

    draw = ImageDraw.Draw(image)
    print(f"\n{'Prüfpunkt':<22} {'Koordinate':<12} {'Ist-Farbe':<16} Soll-Farbe")
    for name, (x, y) in detector.scaled_checkpoints(width, height).items():
        actual = win.read_pixel(x, y)
        expected = EXPECTED[name]
        marker = "?" if actual is None else ("OK" if detector.color_matches(actual, expected) else "!!")
        print(f"{name:<22} ({x},{y})    {str(actual):<16} {expected}  [{marker}]")
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), outline=(255, 0, 0), width=3)

    image.save("calibration.png")
    print("\nScreenshot mit Markierungen: calibration.png")
    print("Hinweis: 'loading_screen' soll NUR im Ladebildschirm weiß sein,")
    print("'playing_icon' nur bei laufendem Dialog stimmen, die dialogue_icons")
    print("nur bei sichtbaren Antwortoptionen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
