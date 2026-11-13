import pytest

from indic_phonetic import best_match, distance

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
