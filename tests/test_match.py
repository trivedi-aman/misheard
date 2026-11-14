import pytest

from misheard import Match, Matcher, best_match, distance

PLACES = ["Barmer", "Jaipur", "Jodhpur", "Sikar", "Chennai", "Lucknow", "Mangalore", "Bengaluru"]


def test_plain_strings():
    m = best_match("Baadmer", PLACES)
    assert m[0].text == "Barmer" and m[0].key == "Barmer"
    assert len(m) == 3
    assert [x.distance for x in m] == sorted(x.distance for x in m)


def test_native_script_heard():
    assert best_match("बाड़मेर", PLACES, top=1)[0].text == "Barmer"
    assert best_match("லக்னோ", PLACES, top=1)[0].text == "Lucknow"


def test_keys_dedupe_aliases():
    refs = [("BLR", "Bengaluru"), ("BLR", "Bangalore"), ("IXE", "Mangalore")]
    m = best_match("Bangalor", refs)
    assert [x.key for x in m] == ["BLR", "IXE"]
    assert m[0].text == "Bangalore"


def test_sound_alike_people():
    people = [("C1", "Rohan Verma"), ("C2", "Mohan Verma"), ("C3", "Sohan Verma")]
    assert best_match("Rohun Varma", people, top=1)[0].key == "C1"
    assert best_match("Verma Rohan", people, top=1)[0].key == "C1"


def test_pruning_gives_the_same_result_as_scoring_everything():
    refs = PLACES + ["Tiruchirappalli", "Thiruvananthapuram", "Ara", "Una", "Pune"]
    for heard in ["Trichy", "Puna", "Chenai", "Seekar", "Thiruvanantapuram"]:
        brute = sorted(refs, key=lambda r: distance(heard, r))[:3]
        assert [round(m.distance, 9) for m in best_match(heard, refs)] == \
               [round(distance(heard, r), 9) for r in brute]


def test_nothing_heard():
    assert best_match("", PLACES) == []
    assert best_match("Barmer", []) == []


def test_top_must_be_positive():
    with pytest.raises(ValueError):
        best_match("Barmer", PLACES, top=0)


def _brute(heard, refs, top):
    """Score everything, keep each key's best, stable on ties: the reference behaviour."""
    best = {}
    for r in refs:
        key, text = (r, r) if isinstance(r, str) else r
        d = distance(heard, text)
        if d != float("inf") and (key not in best or d < best[key].distance):
            best[key] = Match(key, text, d)
    return sorted(best.values(), key=lambda m: m.distance)[:top]


def test_matcher_equals_brute_force_on_random_lists():
    import csv
    import random
    from pathlib import Path

    rng = random.Random(1)
    data = Path(__file__).resolve().parents[1] / "benchmarks" / "data"
    with open(data / "districts.csv", encoding="utf-8") as f:
        districts = [r["district"] for r in csv.DictReader(f)]
    extras = ["R. Kumar", "Ramesh Kumar", "Sunita Devi", "Shri Mohan Lal", "बाड़मेर", "முருகன்", "Mohan", "Rohan"]
    for trial in range(30):
        refs = rng.sample(districts, 60) + extras
        refs = [(rng.randrange(40), t) if rng.random() < 0.3 else t for t in refs]    # shared keys
        heard = rng.choice(districts + extras)
        heard = heard[:-1] if rng.random() < 0.5 else heard + "a"
        top = rng.choice([1, 3, 5])
        assert Matcher(refs).best_match(heard, top) == _brute(heard, refs, top), (trial, heard)


def test_matcher_is_reusable():
    m = Matcher(PLACES)
    assert len(m) == len(PLACES)
    assert m.best_match("Baadmer", top=1)[0].text == "Barmer"
    assert m.best_match("Chenai", top=1)[0].text == "Chennai"
