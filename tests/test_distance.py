import math

import pytest

from indic_phonetic import distance, tokenize


def test_identical_is_zero():
    assert distance("Mohan", "Mohan") == 0
    assert distance("मोहन", "Mohan") == 0


def test_symmetric():
    assert distance("Barmer", "Baadmer") == distance("Baadmer", "Barmer")


def test_variants_are_close_and_different_names_are_far():
    close = [("Barmer", "Baadmer"), ("Barmer", "बाड़मेर"), ("Vikram", "Wikram"), ("Sultan Meena", "Meena Sultan"),
             ("Murugan", "முருகன்"), ("Jaipur", "जयपुर"), ("Meenakshi", "மீனாட்சி"), ("Lakshmi", "Laxmi")]
    far = [("Mohan", "Rohan"), ("Amit Jain", "Sumit Jain"), ("Rohan Verma", "Rohan Sharma"), ("Rohan Verma", "Rohan")]
    assert max(distance(a, b) for a, b in close) < 0.8
    assert min(distance(a, b) for a, b in far) > 1.5


def test_swapped_word_order_costs_a_little():
    assert 0 < distance("Sultan Meena", "Meena Sultan") < 0.5


def test_empty_is_infinite():
    assert math.isinf(distance("", "Mohan"))
    assert math.isinf(distance("123", "Mohan"))


def test_tokenize_longest_match():
    assert tokenize("Bhopal") == ("bh", "o", "p", "a", "l")
    assert tokenize("Lucknow") == ("l", "u", "k", "n", "au")


# ---- known gaps, tracked in PLAN.md; remove xfail when fixed -----------------

@pytest.mark.xfail(reason="Patil and Patel are different surnames (PLAN.md 1.3)", strict=True)
def test_patil_patel_are_different():
    assert distance("Patil", "Patel") > 0.8
