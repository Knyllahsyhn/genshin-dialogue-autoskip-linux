"""Globale Hotkeys über evdev — funktioniert unabhängig vom Fenster-Fokus."""
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
    """Mappt ein rohes Input-Event auf eine Aktion (nur Key-Down, value == 1)."""
    if etype != e.EV_KEY or value != 1:
        return None
    return HOTKEY_ACTIONS.get(code)


def find_keyboards() -> list[InputDevice]:
    """Echte Tastaturen: haben F8 UND Buchstabentasten.

    Der Buchstaben-Check schließt unsere eigene virtuelle Tastatur aus
    (die kann nur F) — sonst hören wir unsere eigenen Events.
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
    """Liest Key-Events aller Tastaturen und ruft callback("run"/"pause"/"exit")."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        super().__init__(daemon=True)
        self._callback = callback
        self._devices = find_keyboards()

    def run(self) -> None:
        devices = {dev.fd: dev for dev in self._devices}
        while devices:
            readable, _, _ = select(devices, [], [])
            for fd in readable:
                try:
                    for event in devices[fd].read():
                        action = action_for(event.type, event.code, event.value)
                        if action is not None:
                            self._callback(action)
                except OSError:
                    devices.pop(fd, None)
