"""Global hotkeys via evdev — works regardless of window focus."""
from __future__ import annotations

from select import select
from threading import Thread
from typing import Callable

from evdev import InputDevice, ecodes as e, list_devices

HOTKEY_ACTIONS = {
    e.KEY_F8: "run",
    e.KEY_F9: "pause",
    e.KEY_F12: "exit",
}


def action_for(etype: int, code: int, value: int) -> str | None:
    """Map a raw input event to an action (key-down only, value == 1)."""
    if etype != e.EV_KEY or value != 1:
        return None
    return HOTKEY_ACTIONS.get(code)


def find_keyboards() -> list[InputDevice]:
    """Real keyboards: have F8 AND letter keys.

    The letter-key check excludes our own virtual keyboard (which only
    has F) — otherwise we would listen to our own events.
    """
    keyboards = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue
        keys = dev.capabilities().get(e.EV_KEY, [])
        if e.KEY_F8 in keys and e.KEY_A in keys:
            keyboards.append(dev)
        else:
            dev.close()
    return keyboards


class HotkeyListener(Thread):
    """Reads key events from all keyboards and calls callback("run"/"pause"/"exit")."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        super().__init__(daemon=True)
        self._callback = callback
        self._devices = find_keyboards()

    def run(self) -> None:
        if not self._devices:
            print("Warning: no readable keyboard devices — hotkeys inactive.")
            return
        devices = {dev.fd: dev for dev in self._devices}
        while devices:
            readable, _, _ = select(devices, [], [])
            for fd in readable:
                try:
                    for event in devices[fd].read():
                        action = action_for(event.type, event.code, event.value)
                        if action is not None:
                            self._callback(action)
                except BlockingIOError:
                    continue
                except OSError:
                    dev = devices.pop(fd, None)
                    if dev is not None:
                        try:
                            dev.close()
                        except OSError:
                            pass
                    if not devices:
                        print("Warning: last keyboard lost — hotkeys inactive.")
