import pytest

from misheard import Confusions, Matcher, best_match, distance, explain
from misheard.distance import feature_cost


def test_default_table_gives_todays_distances():
    d = Confusions.default()
    for a, b in [("Barmer", "बाड़मेर"), ("Vinod", "Binod"), ("Mohan", "Rohan"), ("Venkatesh", "வெங்கடேஷ்")]:
        assert distance(a, b, confusions=d) == distance(a, b)
    assert len(d) > 20 and ("v", "b") in d and ("b", "v") in d


def test_merged_overrides_a_row():
    bihar = Confusions.default().merged({("b", "v"): 0.1})
    assert bihar.cost("v", "b") == 0.1
    assert distance("Vinod", "Binod", confusions=bihar) == 0.1
    assert distance("Vinod", "Binod") == 0.45                   # default unchanged
    assert len(bihar) == len(Confusions.default())              # same pair, not a new row


def test_merged_adds_a_row_with_a_reason():
    table = Confusions.default().merged({("m", "n"): (0.2, "nasals mixed up by this STT engine")})
    assert distance("Suman", "Sunan", confusions=table) < distance("Suman", "Sunan")
    step = next(s for s in explain("Suman", "Sunan", confusions=table).steps if s.kind == "swap")
    assert (step.cost, step.why) == (0.2, "nasals mixed up by this STT engine")


def test_without_falls_back_to_feature_cost():
    table = Confusions.default().without(("v", "b"))
    assert ("v", "b") not in table
    assert table.cost("v", "b") == feature_cost("v", "b") > 0.45
    assert distance("Vinod", "Binod", confusions=table) > distance("Vinod", "Binod")


def test_empty_table_is_features_only():
    assert distance("Barmer", "Barmeṛ", confusions=Confusions()) == feature_cost("r", "ṛ")


def test_from_csv(tmp_path):
    path = tmp_path / "mine.csv"
    path.write_text("a,b,cost,why\nv,b,0.05,Bengali\nsh, s ,0.1\n", encoding="utf-8")
    table = Confusions.from_csv(path)
    assert len(table) == 2
    assert table.cost("s", "sh") == 0.1
    assert table.why("b", "v") == "Bengali"
    assert list(table)[0] == ("v", "b", 0.05, "Bengali")
    assert Confusions.default().merged(table).cost("v", "b") == 0.05


def test_from_csv_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("x,y,cost\nv,b,0.1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing column"):
        Confusions.from_csv(path)


@pytest.mark.parametrize("rows, message", [
    ({("v", "q"): 0.1}, "unknown sound 'q'"),
    ({("v", "v"): 0.1}, "itself"),
    ({("v", "b"): -1}, ">= 0"),
    ({("v", "b"): float("nan")}, ">= 0"),
])
def test_bad_rows_are_rejected(rows, message):
    with pytest.raises(ValueError, match=message):
        Confusions(rows)


def test_matcher_and_best_match_use_the_table():
    people = [("V", "Vinod Kumar"), ("B", "Binod Kumar")]
    # without v/b as a known confusion, the two people are further apart
    table = Confusions.default().without(("v", "b"))
    assert Matcher(people, confusions=table).best_match("Vinod Kumar", top=2)[1].distance > \
           Matcher(people).best_match("Vinod Kumar", top=2)[1].distance
    cheap = Confusions.default().merged({("v", "b"): 0.0})
    m = best_match("Vinod Kumar", people, top=2, confusions=cheap)
    assert [x.distance for x in m] == [0.0, 0.0] and m[0].key == "V"   # tie keeps list order


def test_explain_agrees_with_distance_under_a_custom_table():
    table = Confusions.default().merged({("m", "r"): 0.3})
    for a, b in [("Mohan", "Rohan"), ("Shri Mohan Lal", "Rohan Lal ji"), ("R. Kumar", "Ramesh Kumar")]:
        assert explain(a, b, confusions=table).distance == distance(a, b, confusions=table)


def test_wrong_type_is_a_type_error():
    with pytest.raises(TypeError):
        distance("a", "b", confusions={("v", "b"): 0.1})
