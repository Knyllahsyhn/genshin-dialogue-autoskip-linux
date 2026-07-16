from evdev import ecodes as e

from genshin_autoskip import hotkeys


def test_f8_key_down_ist_run():
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F8, 1) == "run"


def test_f9_und_f12():
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F9, 1) == "pause"
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F12, 1) == "exit"


def test_key_up_und_autorepeat_ignoriert():
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F8, 0) is None
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F8, 2) is None


def test_andere_tasten_und_eventtypen_ignoriert():
    assert hotkeys.action_for(e.EV_KEY, e.KEY_A, 1) is None
    assert hotkeys.action_for(e.EV_ABS, e.KEY_F8, 1) is None
