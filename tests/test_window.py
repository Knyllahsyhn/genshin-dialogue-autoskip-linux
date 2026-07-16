from genshin_autoskip import window


def test_matches_genshin_wine_klasse():
    assert window.matches_genshin(("genshinimpact.exe", "genshinimpact.exe"))


def test_matches_genshin_case_insensitive():
    assert window.matches_genshin(("GenshinImpact.exe", "Wine"))


def test_matches_genshin_andere_fenster_nicht():
    assert not window.matches_genshin(("firefox", "Firefox"))
    assert not window.matches_genshin(None)


def test_decode_zpixmap_bgrx():
    # 32-bit ZPixmap little-endian: Byte-Reihenfolge B, G, R, X
    assert window.decode_zpixmap_rgb(bytes([10, 20, 30, 0])) == (30, 20, 10)
