from random import Random

from genshin_autoskip import timing


def test_press_interval_stays_within_bounds():
    rng = Random(1)
    values = [timing.random_press_interval(rng) for _ in range(1000)]
    assert all(0.12 <= v <= 0.2 for v in values)
    # Both branches (normal and the 1-in-6 slow branch) occur
    assert any(v >= 0.18 for v in values)
    assert any(v < 0.18 for v in values)


def test_should_take_break():
    rng = Random(2)
    results = [timing.should_take_break(rng) for _ in range(1000)]
    hits = sum(results)
    # 1-in-25 chance: roughly 40 out of 1000 attempts, safely between 10 and 100
    assert 10 <= hits <= 100


def test_break_duration_within_bounds():
    rng = Random(3)
    values = [timing.random_break_duration(rng) for _ in range(100)]
    assert all(3.0 <= v <= 8.0 for v in values)
