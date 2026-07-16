"""Zustandsmaschine, Hauptloop und CLI des Autoskippers."""
from __future__ import annotations

import argparse
import os
import sys
import time
from random import Random
from typing import Callable

from genshin_autoskip import detector, timing

BREAK_CHECK_INTERVAL = 30.0


class AppState:
    """Von Hotkey-Thread und Hauptloop geteilter Zustand."""

    def __init__(self) -> None:
        self.status: str = "pause"


def main_loop(
    get_window: Callable[[], object | None],
    keyboard,
    state: AppState,
    rng: Random,
    *,
    dry_run: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.perf_counter,
) -> None:
    window = None
    last_press = now()
    next_interval = timing.random_press_interval(rng)
    last_break_check = now()

    while state.status != "exit":
        if state.status == "pause":
            sleep(0.5)
            last_press = now()
            continue

        if window is None:
            window = get_window()
            if window is None:
                print("Genshin-Fenster nicht gefunden — warte...")
                sleep(2.0)
                continue

        px = window.read_checkpoints()
        if px is None:
            print("Fenster verloren — suche neu...")
            window.close()
            window = None
            sleep(2.0)
            continue

        action = detector.decide(px)
        if action is None:
            sleep(0.1)
            continue

        current = now()
        if current - last_break_check > BREAK_CHECK_INTERVAL:
            last_break_check = current
            if timing.should_take_break(rng):
                duration = timing.random_break_duration(rng)
                print(f"Menschenpause: {duration:.1f}s...")
                sleep(duration)
                last_press = now()
                next_interval = timing.random_press_interval(rng)
                continue

        if current - last_press >= next_interval:
            if dry_run:
                label = "Option 1 bestätigen" if action == "confirm" else "Dialog skippen"
                print(f"[dry-run] Würde jetzt: {label}")
            else:
                keyboard.press()
            last_press = current
            next_interval = timing.random_press_interval(rng)

        sleep(0.05)


def _preflight(dry_run: bool) -> list[str]:
    """Vorbedingungen prüfen; Liste verständlicher Fehlermeldungen zurückgeben."""
    from genshin_autoskip import hotkeys

    errors = []
    try:
        from Xlib import display

        display.Display().close()
    except Exception:
        errors.append(
            "Kein X-Display erreichbar. Läuft die Sitzung mit XWayland (DISPLAY gesetzt)?"
        )
    if not hotkeys.find_keyboards():
        errors.append(
            "Keine Tastatur unter /dev/input lesbar. Bist du in der 'input'-Gruppe? "
            "(sudo usermod -aG input $USER, dann neu einloggen)"
        )
    if not dry_run and not os.access("/dev/uinput", os.W_OK):
        errors.append(
            "/dev/uinput nicht beschreibbar. udev-Regel fehlt? Siehe README, Abschnitt Setup."
        )
    return errors


def cli() -> None:
    parser = argparse.ArgumentParser(description="Genshin Dialog-Autoskipper für Linux")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Erkennung live loggen, aber keine Tasten senden",
    )
    args = parser.parse_args()

    errors = _preflight(args.dry_run)
    if errors:
        print("Setup unvollständig:\n")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    from genshin_autoskip.hotkeys import HotkeyListener
    from genshin_autoskip.window import GenshinWindow

    state = AppState()

    def on_action(action: str) -> None:
        state.status = {"run": "run", "pause": "pause", "exit": "exit"}[action]
        print(f"\n>>> Status: {state.status.upper()}")

    keyboard = None
    if not args.dry_run:
        from genshin_autoskip.injector import VirtualKeyboard

        keyboard = VirtualKeyboard()

    HotkeyListener(on_action).start()

    print("Genshin Dialog-Autoskipper")
    print("  [F8]  Start    [F9]  Pause    [F12] Beenden")
    if args.dry_run:
        print("  Modus: DRY-RUN (es werden keine Tasten gesendet)")
    print("\nWarte auf F8...")

    try:
        main_loop(GenshinWindow.find, keyboard, state, Random(), dry_run=args.dry_run)
    finally:
        if keyboard is not None:
            keyboard.close()
    print("Beendet.")


if __name__ == "__main__":
    cli()
