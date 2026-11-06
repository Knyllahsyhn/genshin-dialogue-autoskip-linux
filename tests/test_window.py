from genshin_autoskip import window


def test_matches_genshin_wine_class():
    assert window.matches_genshin(("genshinimpact.exe", "genshinimpact.exe"))


def test_matches_genshin_case_insensitive():
    assert window.matches_genshin(("GenshinImpact.exe", "Wine"))


def test_matches_genshin_rejects_other_windows():
    assert not window.matches_genshin(("firefox", "Firefox"))
    assert not window.matches_genshin(None)


def test_matches_title_genshin():
    assert window.matches_title("Genshin Impact")
    assert window.matches_title(b"Genshin Impact")
    assert window.matches_title("  genshin impact  ")


def test_matches_title_rejects_other_windows():
    # Steam/HoYoPlay setup: launcher and helper windows share the WM_CLASS
    # steam_app_genshin — only the title identifies the game window.
    assert not window.matches_title(None)
    assert not window.matches_title("")
    assert not window.matches_title("HoYoPlay")
    assert not window.matches_title("Wuthering Waves  ")
    assert not window.matches_title(b"\xff\xfe")


def test_decode_zpixmap_bgrx():
    # 32-bit ZPixmap little-endian: byte order B, G, R, X
    assert window.decode_zpixmap_rgb(bytes([10, 20, 30, 0])) == (30, 20, 10)


def test_clamp_patch_inside():
    assert window.clamp_patch(10, 10, 2, (100, 50)) == (8, 8, 5, 5)


def test_clamp_patch_at_edges():
    assert window.clamp_patch(0, 49, 2, (100, 50)) == (0, 47, 3, 3)


def test_clamp_patch_outside_window():
    assert window.clamp_patch(200, 10, 2, (100, 50)) is None


def test_patch_from_frame_respects_stride():
    # 3x2 frame, BGRx, stride padded to 16 bytes per row
    width, stride = 3, 16
    rows = []
    for y in range(2):
        row = b"".join(bytes([x, y, 100 + x + 10 * y, 0]) for x in range(width))
        rows.append(row + b"\xee" * (stride - len(row)))
    frame = b"".join(rows)
    patch = window.patch_from_frame(frame, stride, 1, 0, 2, 2)
    assert patch == [(101, 0, 1), (102, 0, 2), (111, 1, 1), (112, 1, 2)]


def test_uses_wayland_proton():
    assert window.uses_wayland({"PROTON_ENABLE_WAYLAND": "1"})
    assert window.uses_wayland({"WINE_GRAPHICS_DRIVER": "wayland"})
    assert not window.uses_wayland({"PROTON_ENABLE_WAYLAND": "0"})
    assert not window.uses_wayland({})


def _fake_proc(tmp_path, pid, cmdline, environ, start_ticks=None):
    d = tmp_path / str(pid)
    d.mkdir()
    if start_ticks is not None:
        rest = " ".join(["S"] + ["0"] * 18 + [str(start_ticks)] + ["0"] * 5)
        (d / "stat").write_text(f"{pid} (Genshin Impact) {rest}\n")
    (d / "cmdline").write_bytes(cmdline.encode() + b"\0")
    (d / "environ").write_bytes(b"".join(f"{k}={v}".encode() + b"\0" for k, v in environ.items()))


def test_game_mode_detects_wayland_game(tmp_path):
    _fake_proc(tmp_path, 1, "C:\\HoYoPlay\\HYP.exe", {"PROTON_ENABLE_WAYLAND": "1"})
    _fake_proc(
        tmp_path, 2, "W:\\Games\\Genshin Impact game\\GenshinImpact.exe login=1",
        {"PROTON_ENABLE_WAYLAND": "1"},
    )
    (tmp_path / "self").mkdir()
    assert window.find_game(tmp_path) == ("wayland", 0.0)


def test_game_mode_x11_and_missing(tmp_path):
    assert window.find_game(tmp_path) is None
    _fake_proc(tmp_path, 3, "Z:\\YuanShen.exe", {})
    assert window.find_game(tmp_path) == ("x11", 0.0)


def test_find_game_reports_process_age(tmp_path):
    import os

    hz = os.sysconf("SC_CLK_TCK")
    (tmp_path / "uptime").write_text("1000.00 5000.00\n")
    _fake_proc(tmp_path, 4, "GenshinImpact.exe", {}, start_ticks=900 * hz)
    mode, age = window.find_game(tmp_path)
    assert mode == "x11"
    assert age == 100.0


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _finder(mode, portal, clock, x11=lambda: None, age=0.0):
    return window.WindowFinder(
        x11_find=x11, portal_open=portal,
        find_game=lambda: None if mode is None else (mode, age),
        clock=clock, grace=10.0,
    )


def test_finder_prefers_x11():
    calls = []
    finder = _finder("wayland", lambda: calls.append(1), _Clock(), x11=lambda: "x11win")
    assert finder() == "x11win"
    assert calls == []


def test_finder_waits_grace_before_portal():
    clock = _Clock()
    finder = _finder("wayland", lambda: "portalwin", clock)
    assert finder() is None
    clock.t = 5.0
    assert finder() is None
    clock.t = 10.5
    assert finder() == "portalwin"


def test_finder_skips_portal_for_x11_game():
    clock = _Clock()
    finder = _finder("x11", lambda: "portalwin", clock)
    clock.t = 100.0
    assert finder() is None


def test_finder_resets_grace_when_game_exits():
    clock = _Clock()
    mode = {"m": "wayland"}
    finder = window.WindowFinder(
        x11_find=lambda: None, portal_open=lambda: "w",
        find_game=lambda: None if mode["m"] is None else (mode["m"], 0.0),
        clock=clock, grace=10.0,
    )
    finder()
    mode["m"] = None
    clock.t = 20.0
    assert finder() is None
    mode["m"] = "wayland"
    assert finder() is None
    clock.t = 31.0
    assert finder() == "w"


def test_finder_stops_after_cancel():
    clock = _Clock()
    calls = []

    def portal():
        calls.append(1)
        raise window.PortalCancelled("user cancelled")

    finder = _finder("wayland", portal, clock)
    finder()
    clock.t = 11.0
    assert finder() is None
    clock.t = 50.0
    assert finder() is None
    assert len(calls) == 1
    assert finder.portal_cancelled


def test_finder_retries_after_portal_error():
    clock = _Clock()
    calls = []

    def portal():
        calls.append(1)
        raise window.PortalError("no frame")

    finder = _finder("wayland", portal, clock)
    finder()
    clock.t = 11.0
    finder()
    clock.t = 12.0
    finder()  # backing off, no new dialog
    assert len(calls) == 1
    clock.t = 22.0
    finder()
    assert len(calls) == 2


def test_finder_portal_due():
    clock = _Clock()
    clock.t = 3.0
    finder = _finder("wayland", lambda: None, clock)
    assert finder.portal_due() is None
    finder()
    assert finder.portal_due() == 13.0
    cancelled = _finder("wayland", lambda: (_ for _ in ()).throw(window.PortalCancelled("x")), clock)
    cancelled()
    clock.t = 20.0
    cancelled()
    assert cancelled.portal_due() is None


def test_finder_skips_grace_for_running_game():
    finder = _finder("wayland", lambda: "portalwin", _Clock(), age=300.0)
    assert finder() == "portalwin"


def test_finder_waits_rest_of_grace_for_fresh_game():
    clock = _Clock()
    finder = _finder("wayland", lambda: "portalwin", clock, age=4.0)
    assert finder() is None
    assert finder.portal_due() == 6.0
    clock.t = 6.5
    assert finder() == "portalwin"
