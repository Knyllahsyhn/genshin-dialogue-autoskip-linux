"""State machine, main loop, and CLI of the auto-skipper."""
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
    """State shared between the hotkey thread and the main loop."""

    def __init__(self) -> None:
        self.status: str = "pause"


def main_loop(
    get_window: Callable[[], object | None],
    keyboard,
    state: AppState,
    rng: Random,
    *,
    reporter,
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
            last_break_check = now()
            continue

        if window is None:
            window = get_window()
            if window is None:
                reporter.window_missing()
                sleep(2.0)
                continue
            reporter.window_found(window.size())

        px = window.read_checkpoints()
        if px is None:
            reporter.window_lost()
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
                reporter.break_started(duration)
                sleep(duration)
                last_press = now()
                next_interval = timing.random_press_interval(rng)
                continue

        if current - last_press >= next_interval:
            if dry_run:
                reporter.dry_run_action(action)
            else:
                keyboard.press()
                reporter.pressed(action)
            last_press = current
            next_interval = timing.random_press_interval(rng)

        sleep(0.05)

    if window is not None:
        window.close()


def _preflight(dry_run: bool) -> list[str]:
    """Check preconditions; return a list of human-readable error messages."""
    from genshin_autoskip import hotkeys

    errors = []
    try:
        from Xlib import display

        display.Display().close()
    except Exception:
        errors.append(
            "No X display reachable. Is the session running with XWayland (DISPLAY set)?"
        )
    if not hotkeys.find_keyboards():
        errors.append(
            "No keyboard readable under /dev/input. Are you in the 'input' group? "
            "(sudo usermod -aG input $USER, then log in again)"
        )
    if not dry_run and not os.access("/dev/uinput", os.W_OK):
        errors.append(
            "/dev/uinput not writable. Missing udev rule? See README, Setup section."
        )
    return errors


def cli() -> None:
    parser = argparse.ArgumentParser(description="Genshin dialogue auto-skipper for Linux")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="log detection live, but do not send any keys",
    )
    args = parser.parse_args()

    errors = _preflight(args.dry_run)
    if errors:
        print("Setup incomplete:\n")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    from genshin_autoskip import ui
    from genshin_autoskip.hotkeys import HotkeyListener
    from genshin_autoskip.window import GenshinWindow

    state = AppState()
    reporter = ui.PlainReporter(dry_run=args.dry_run)

    def on_action(action: str) -> None:
        state.status = {"run": "run", "pause": "pause", "exit": "exit"}[action]
        reporter.status_changed(state.status)

    keyboard = None
    if not args.dry_run:
        from genshin_autoskip.injector import VirtualKeyboard

        keyboard = VirtualKeyboard()

    HotkeyListener(on_action).start()

    with reporter:
        try:
            main_loop(
                GenshinWindow.find, keyboard, state, Random(),
                reporter=reporter, dry_run=args.dry_run,
            )
        except KeyboardInterrupt:
            pass
        finally:
            if keyboard is not None:
                keyboard.close()
    print("Done.")


if __name__ == "__main__":
    cli()
