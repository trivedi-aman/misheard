import csv
import random
from pathlib import Path

from misheard import distance, explain

DATA = Path(__file__).resolve().parents[1] / "benchmarks" / "data"


def test_steps_add_up_to_the_distance():
    with open(DATA / "people.csv", encoding="utf-8") as f:
        people = list(csv.DictReader(f))
    names = [p["full_name"] for p in people] + [p["name_native"] for p in people if p["name_native"]]
    names += ["Shri Mohan Lal ji", "R. Kumar", "Sunita Devi", "Rameshbhai Patel", "Kumar Ramesh Singh"]
    rng = random.Random(3)
    for _ in range(200):
        a, b = rng.choice(names), rng.choice(names)
        e = explain(a, b)
        assert e.distance == distance(a, b)
        assert round(sum(s.cost for s in e.steps), 6) == e.distance, (a, b)


def test_reasons_come_from_the_confusion_table():
    e = explain("Vinod", "Binod")
    swap = [s for s in e.steps if s.kind == "swap"]
    assert len(swap) == 1 and (swap[0].a, swap[0].b) == ("v", "b")
    assert "Bihar" in swap[0].why


def test_word_level_steps():
    kinds = [s.kind for s in explain("Shri Kumar Ramesh ji", "Ramesh Kumar").steps]
    assert kinds.count("title") == 2 and "reorder" in kinds
    assert [s.kind for s in explain("R. Kumar", "Ramesh Kumar").steps][0] == "initial"


def test_printable():
    text = str(explain("Barmer", "बाड़मेर"))
    assert text.startswith("Barmer ↔ बाड़मेर (baaṛmer)   distance 0.4")
    assert "retroflex flap" in text


def test_nothing_to_explain():
    assert explain("", "Mohan").distance == float("inf")
