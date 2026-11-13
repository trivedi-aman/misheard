"""
Find the closest references to something heard.

`best_match` ranks a list of references (names, places, anything spoken) by
phonetic distance to the heard text and returns the closest few. It does not
decide whether the best one is "good enough": that depends on the
application, so the distances and the gap between the first and second
match are returned for the caller to judge.

Every sound missing from one side costs at least the cheapest deletion, so a
reference much longer or shorter than what was heard cannot beat matches
already found. Lengths are ranges (a dropped "Devi", an initial standing for
a whole word), and the gap between the two ranges gives the lower bound.
References are visited in order of that gap and the search stops once the
bound exceeds the current `top`-th best. The
result is exactly what scoring every reference would give, with far fewer
distance computations.
"""
from collections.abc import Hashable, Iterable
from dataclasses import dataclass

from .distance import INDEL_CHEAP, distance, sound_range


@dataclass(frozen=True)
class Match:
    key: Hashable       # the key given with the reference, or the text itself
    text: str           # the reference text
    distance: float     # phonetic distance from what was heard; 0 is identical


def best_match(heard: str, references: Iterable[str | tuple[Hashable, str]], top: int = 3) -> list[Match]:
    """
    The `top` references closest to `heard`, nearest first.

    references: plain strings, or (key, text) pairs when several texts lead
    to one thing (an id for a person, aliases for one city). With pairs,
    each key appears at most once in the result, at its best distance.
    """
    if top < 1:
        raise ValueError("top must be at least 1")
    refs = [(r, r) if isinstance(r, str) else (r[0], r[1]) for r in references]
    lo, hi = sound_range(heard)
    if lo == 0 or not refs:
        return []
    floor = min(INDEL_CHEAP.values())

    def gap(text: str) -> float:
        r_lo, r_hi = sound_range(text)
        return max(0, r_lo - hi, lo - r_hi)

    best: dict[Hashable, Match] = {}
    ranked: list[Match] = []
    for key, text in sorted(refs, key=lambda kt: gap(kt[1])):
        if len(ranked) >= top and floor * gap(text) > ranked[top - 1].distance:
            break
        d = distance(heard, text)
        if key in best and best[key].distance <= d:
            continue
        best[key] = Match(key, text, d)
        ranked = sorted(best.values(), key=lambda m: m.distance)
    return ranked[:top]
