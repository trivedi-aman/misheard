"""
Properties that must hold for any input, checked on random names (PLAN.md 1.11).

These are also the safety net for a compiled kernel (PLAN.md 3.4): whatever
replaces the pure-Python DP must keep every one of them.
"""
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from misheard import SOUNDS, Confusions, Matcher, Match, UnsupportedScriptError, distance, explain, to_roman, tokenize  # noqa: E402

# Letters names are actually written with, in the three supported scripts,
# plus the marks that make the transliterators branch (nukta, virama,
# anusvara, pulli, vowel signs).
LATIN = "abcdefghijklmnopqrstuvwxyz"
DEVANAGARI = "कखगघचछजझटठडढणतथदधनपफबभमयरलवशषसहअआइईउऊएऐओऔािीुूेैोौंँ़्ः"
TAMIL = "கஙசஞடணதநபமயரலவழளறனஜஷஸஹஅஆஇஈஉஊஎஏஐஒஓஔாிீுூெேைொோௌ்"

words = st.one_of(
    st.text(LATIN, min_size=1, max_size=10),
    st.text(DEVANAGARI, min_size=1, max_size=8),
    st.text(TAMIL, min_size=1, max_size=8),
    st.sampled_from(["R.", "K", "Shri", "ji", "Devi", "Kumar", "Rameshbhai", "श्री", "திரு"]),
)
names = st.lists(words, min_size=1, max_size=4).map(" ".join)

SETTINGS = settings(max_examples=300, deadline=None)


@SETTINGS
@given(names)
def test_distance_to_itself_is_zero(a):
    assert distance(a, a) in (0.0, float("inf"))


@SETTINGS
@given(names, names)
def test_distance_is_symmetric(a, b):
    assert distance(a, b) == distance(b, a)


@SETTINGS
@given(names, names)
def test_distance_is_non_negative(a, b):
    assert distance(a, b) >= 0


@SETTINGS
@given(names, names)
def test_explain_adds_up_to_distance(a, b):
    e = explain(a, b)
    assert e.distance == distance(a, b)
    if e.steps:
        assert round(sum(s.cost for s in e.steps), 6) == e.distance


@SETTINGS
@given(st.text(max_size=20))
def test_to_roman_never_fails_except_on_unsupported_scripts(text):
    try:
        out = to_roman(text)
    except UnsupportedScriptError:
        return
    assert isinstance(out, str)
    for word in out.split():
        tokenize(word)


def _brute(heard, refs, top):
    best = {}
    for r in refs:
        key, text = (r, r) if isinstance(r, str) else r
        d = distance(heard, text)
        if d != float("inf") and (key not in best or d < best[key].distance):
            best[key] = Match(key, text, d)
    return sorted(best.values(), key=lambda m: m.distance)[:top]


@settings(max_examples=150, deadline=None)
@given(
    names,
    st.lists(st.one_of(names, st.tuples(st.integers(0, 5), names)), max_size=15),
    st.integers(1, 5),
)
def test_matcher_equals_brute_force(heard, refs, top):
    assert Matcher(refs).best_match(heard, top) == _brute(heard, refs, top)


tables = st.dictionaries(
    st.tuples(st.sampled_from(sorted(SOUNDS)), st.sampled_from(sorted(SOUNDS))).filter(lambda p: p[0] != p[1]),
    st.floats(0, 3),
    max_size=20,
).map(Confusions.default().merged)


@settings(max_examples=100, deadline=None)
@given(names, st.lists(names, max_size=12), tables)
def test_matcher_equals_brute_force_with_any_confusion_table(heard, refs, table):
    got = Matcher(refs, confusions=table).best_match(heard, 3)
    best = {}
    for r in refs:
        d = distance(heard, r, confusions=table)
        if d != float("inf") and r not in best:
            best[r] = Match(r, r, d)
    assert got == sorted(best.values(), key=lambda m: m.distance)[:3]
    for m in got:
        assert explain(heard, m.text, confusions=table).distance == m.distance
