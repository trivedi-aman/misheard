"""
Why two names are as close as they are.

    >>> print(explain("Barmer", "बाड़मेर"))
    Barmer ↔ बाड़मेर (baaṛmer)   distance 0.4
      b  =  b
      a  →  aa    0.25  vowel length
      r  →  ṛ     0.15  retroflex flap ड़ is heard and written as r (Baadmer/Barmer)
      m  =  m
      e  =  e
      r  =  r

`explain` returns the same distance as `distance`, broken into steps: each
sound kept, swapped, added or dropped, plus word-level steps (a title
ignored, Devi left out, an initial, a change of word order). The step costs
add up to the distance.
"""
from dataclasses import dataclass
from itertools import permutations

from .distance import (
    CONSONANTS, INDEL_CHEAP, INF, INITIAL_COST, MAX_PERMUTED_WORDS, SWAP_PENALTY, VOWELS,
    Confusions, _table, _variants_detailed, _Word, _word_cost, indel_cost,
)
from .translit import to_roman


@dataclass(frozen=True)
class Step:
    kind: str       # same, swap, add, drop, initial, reorder, title, optional, suffix
    a: str          # sound or word on the first side ("" if none)
    b: str          # sound or word on the second side ("" if none)
    cost: float
    why: str = ""   # human-readable reason, when there is one


@dataclass(frozen=True)
class Explanation:
    a: str
    b: str
    distance: float
    steps: tuple[Step, ...]

    def __str__(self) -> str:
        def label(text: str) -> str:
            roman = to_roman(text)
            return text if roman == text.lower() else f"{text} ({roman})"

        lines = [f"{label(self.a)} ↔ {label(self.b)}   distance {self.distance:g}"]
        sym = {"same": "=", "swap": "→", "add": "+", "drop": "-", "initial": "≈"}
        width = max([len(s.a) for s in self.steps if s.kind in sym] + [1])
        for s in self.steps:
            if s.kind in sym:
                cost = f"{s.cost:g}" if s.cost else ""
                lines.append(f"  {s.a or '·':<{width}}  {sym[s.kind]}  {s.b or '·':<{width}}  {cost:>5}  {s.why}".rstrip())
            else:
                lines.append(f"  [{s.kind}] {s.why}  {s.cost:g}".rstrip())
        return "\n".join(lines)


def _sub_why(a: str, b: str, table: Confusions) -> str:
    if (a, b) in table:
        return table.why(a, b) or "listed confusion"
    if (a in VOWELS) != (b in VOWELS):
        return "vowel for consonant"
    if a in VOWELS:
        names = ("height", "front/back", "length")
        diff = [n for n, x, y in zip(names, VOWELS[a], VOWELS[b]) if x != y]
        return "vowel " + ", ".join(diff)
    names = ("place", "manner", "voicing", "aspiration")
    return ", ".join(n for n, x, y in zip(names, CONSONANTS[a], CONSONANTS[b]) if x != y)


def _indel_why(tok: str) -> str:
    if tok == "a":
        return "short a (often silent)"
    if tok in INDEL_CHEAP:
        return "often silent or only in spelling"
    return ""


def _align(pa: tuple[str, ...], pb: tuple[str, ...], table: Confusions) -> list[Step]:
    """Backtrace of the weighted edit distance, same arithmetic as the matcher."""
    sub_cost = table.cost
    n, m = len(pa), len(pb)
    d = [[0.0] * (m + 1) for _ in range(n + 1)]
    for j in range(1, m + 1):
        d[0][j] = d[0][j - 1] + indel_cost(pb[j - 1])
    for i in range(1, n + 1):
        d[i][0] = d[i - 1][0] + indel_cost(pa[i - 1])
        for j in range(1, m + 1):
            d[i][j] = min(
                d[i - 1][j - 1] + sub_cost(pa[i - 1], pb[j - 1]),
                d[i - 1][j] + indel_cost(pa[i - 1]),
                d[i][j - 1] + indel_cost(pb[j - 1]),
            )
    steps: list[Step] = []
    i, j = n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + sub_cost(pa[i - 1], pb[j - 1]):
            x, y = pa[i - 1], pb[j - 1]
            c = sub_cost(x, y)
            steps.append(Step("same", x, y, 0.0) if x == y else Step("swap", x, y, c, _sub_why(x, y, table)))
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + indel_cost(pa[i - 1]):
            steps.append(Step("drop", pa[i - 1], "", indel_cost(pa[i - 1]), _indel_why(pa[i - 1])))
            i -= 1
        else:
            steps.append(Step("add", "", pb[j - 1], indel_cost(pb[j - 1]), _indel_why(pb[j - 1])))
            j -= 1
    return steps[::-1]


def _word_steps(x: _Word, y: _Word, table: Confusions) -> list[Step]:
    if x.initial or y.initial:
        c = _word_cost(x, y, sub=table._sub)
        a, b = "".join(x.sounds), "".join(y.sounds)
        why = "initial" if c in (0.0, INITIAL_COST) else "initial with a different letter"
        return [Step("initial", a, b, c, why)]
    return _align(x.sounds, y.sounds, table)


def _words_steps(wa: tuple[_Word, ...], wb: tuple[_Word, ...], table: Confusions) -> tuple[float, list[Step]]:
    n = len(wa)
    if n != len(wb):
        joined = _align(tuple(t for w in wa for t in w.sounds), tuple(t for w in wb for t in w.sounds), table)
        return sum(s.cost for s in joined), joined
    cost = [[_word_cost(x, y, sub=table._sub) for y in wb] for x in wa]
    best, best_perm = sum(cost[i][i] for i in range(n)), tuple(range(n))
    if 1 < n <= MAX_PERMUTED_WORDS:
        for perm in permutations(range(n)):
            c = sum(cost[i][p] for i, p in enumerate(perm)) + SWAP_PENALTY
            if c < best:
                best, best_perm = c, perm
    steps: list[Step] = []
    if best_perm != tuple(range(n)):
        order = " ".join("".join(wb[p].sounds) for p in best_perm)
        steps.append(Step("reorder", "", "", SWAP_PENALTY, f"words in a different order: {order}"))
    for i, p in enumerate(best_perm):
        steps.extend(_word_steps(wa[i], wb[p], table))
    return best, steps


def _note_steps(notes, side: str) -> list[Step]:
    what = {"title": "title or honorific ignored", "optional": "left out", "suffix": "honorific suffix split off"}
    return [Step(kind, w if side == "a" else "", w if side == "b" else "", cost, f"{w}: {what[kind]}")
            for w, kind, cost in notes]


def explain(a: str, b: str, *, confusions: Confusions | None = None) -> Explanation:
    """The steps that make up `distance(a, b)`, cheapest alignment first."""
    table = _table(confusions)
    va, vb = _variants_detailed(a), _variants_detailed(b)
    if not va or not vb:
        return Explanation(a, b, INF, ())
    best, best_steps = INF, []
    for pa, wa, na in va:
        for pb, wb, nb in vb:
            d, steps = _words_steps(wa, wb, table)
            if pa + pb + d < best:
                best = pa + pb + d
                best_steps = _note_steps(na, "a") + _note_steps(nb, "b") + steps
    return Explanation(a, b, round(best, 6), tuple(best_steps))


__all__ = ["explain", "Explanation", "Step"]
