"""How people actually say names: titles, honorifics, initials, word order."""
import pytest

from indic_phonetic import best_match, distance


@pytest.mark.parametrize("said, record", [
    ("Shri Mohan Lal", "Mohan Lal"),
    ("Dr. Anil Sharma", "Anil Sharma"),
    ("Smt Sunita Sharma", "Sunita Sharma"),
    ("Mohan ji", "Mohan"),
    ("Sharma sahab", "Sharma"),
    ("श्री मोहन लाल", "मोहन लाल"),
    ("திரு முருகன்", "Murugan"),
])
def test_titles_and_honorifics_are_free(said, record):
    assert distance(said, record) == 0


def test_title_alone_is_still_a_name():
    assert distance("Shri", "Shri") == 0


def test_joined_honorific_is_cheap_but_not_free():
    assert 0 < distance("Rameshbhai Patel", "Ramesh Patel") <= 0.3
    assert distance("Hansaben", "Hansa") <= 0.3
    assert distance("Rameshbhai", "Rameshbhai") == 0


def test_joined_ji_is_part_of_the_name():
    assert distance("Balaji", "Bala") > 1.0
    assert distance("Shivaji", "Shiva") > 1.0


def test_devi_and_kumar_are_optional():
    assert distance("Sunita Devi", "Sunita") == 0.5
    assert distance("Ram Kumar", "Ram") == 0.5
    assert distance("Ram Kumar", "Ramkumar") == 0
    assert distance("Devi", "Devi") == 0


def test_any_word_order():
    assert distance("Kumar Ramesh Singh", "Ramesh Kumar Singh") == 0.2
    assert distance("Singh Ramesh", "Ramesh Singh") == 0.2


def test_initials():
    assert distance("R. Kumar", "Ramesh Kumar") == 0.3
    assert distance("K. Srinivasan", "Srinivasan K") == 0.2
    assert distance("R.K. Narayan", "Rasipuram Krishnaswami Narayan") == 0.6
    assert distance("R. Kumar", "Suresh Kumar") > 1.0


def test_initial_prefers_the_matching_person():
    people = [("C1", "Ramesh Kumar"), ("C2", "Suresh Kumar"), ("C3", "Mahesh Kumar")]
    assert best_match("R. Kumar", people, top=1)[0].key == "C1"


def test_honorific_does_not_tip_a_close_call():
    assert best_match("Mohan ji", ["Mohan", "Mohini", "Moji"], top=1)[0].text == "Mohan"


def test_distances_are_rounded():
    assert distance("Vinod", "Vinay") == 1.8


def test_pruning_stays_exact_with_initials_and_optional_words():
    refs = ["Ramesh Kumar", "R. Kumar", "Sunita Devi", "Sunita", "Ram", "Ram Kumar Singh", "K. Srinivasan",
            "Srinivasan", "Shri Mohan Lal", "Mohan", "Rasipuram Krishnaswami Narayan", "Rameshbhai Patel"]
    for heard in ["R Kumar", "Sunita", "Ramesh Kumar", "Srinivasan K", "Mohan Lal ji", "R K Narayan", "Ramesh"]:
        brute = sorted(distance(heard, r) for r in refs)[:3]
        assert [m.distance for m in best_match(heard, refs)] == brute
