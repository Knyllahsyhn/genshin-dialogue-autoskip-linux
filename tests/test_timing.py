from random import Random

from genshin_autoskip import timing


def test_press_interval_bleibt_in_grenzen():
    rng = Random(1)
    values = [timing.random_press_interval(rng) for _ in range(1000)]
    assert all(0.12 <= v <= 0.2 for v in values)
    # Beide Zweige (normal und 1-in-6-Langsamzweig) kommen vor
    assert any(v >= 0.18 for v in values)
    assert any(v < 0.18 for v in values)


def test_should_take_break_ist_selten_aber_existiert():
    rng = Random(2)
    results = [timing.should_take_break(rng) for _ in range(1000)]
    hits = sum(results)
    # 1-in-25-Chance: bei 1000 Versuchen grob 40, sicher zwischen 10 und 100
    assert 10 <= hits <= 100


def test_break_dauer_in_grenzen():
    rng = Random(3)
    values = [timing.random_break_duration(rng) for _ in range(100)]
    assert all(3.0 <= v <= 8.0 for v in values)
