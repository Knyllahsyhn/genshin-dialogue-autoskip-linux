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
