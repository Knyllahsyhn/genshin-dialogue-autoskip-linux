from evdev import ecodes as e

from genshin_autoskip.injector import VirtualKeyboard


class FakeUInput:
    def __init__(self):
        self.events = []

    def write(self, etype, code, value):
        self.events.append((etype, code, value))

    def syn(self):
        self.events.append("SYN")

    def close(self):
        self.events.append("CLOSE")


def _keyboard_with_fake():
    kb = VirtualKeyboard.__new__(VirtualKeyboard)
    kb._ui = FakeUInput()
    kb._keycode = e.KEY_F
    return kb


def test_press_sendet_down_syn_up_syn():
    kb = _keyboard_with_fake()
    kb.press(hold=0)
    assert kb._ui.events == [
        (e.EV_KEY, e.KEY_F, 1),
        "SYN",
        (e.EV_KEY, e.KEY_F, 0),
        "SYN",
    ]


def test_close_schliesst_uinput():
    kb = _keyboard_with_fake()
    kb.close()
    assert "CLOSE" in kb._ui.events
