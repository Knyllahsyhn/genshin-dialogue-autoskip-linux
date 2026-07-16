"""Virtuelle uinput-Tastatur — Kernel-Level-Input, für Wine wie echte Hardware."""
import time

from evdev import UInput, ecodes as e


class VirtualKeyboard:
    def __init__(self, keycode: int = e.KEY_F) -> None:
        self._keycode = keycode
        self._ui = UInput({e.EV_KEY: [keycode]}, name="genshin-autoskip-kbd")

    def press(self, hold: float = 0.03) -> None:
        self._ui.write(e.EV_KEY, self._keycode, 1)
        self._ui.syn()
        if hold > 0:
            time.sleep(hold)
        self._ui.write(e.EV_KEY, self._keycode, 0)
        self._ui.syn()

    def close(self) -> None:
        self._ui.close()
