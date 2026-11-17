"""
Find the closest references to something heard.

    m = Matcher(districts)          # once
    m.best_match("Baadmer")         # per utterance

`Matcher` holds a list of references (names, places, anything spoken),
prepared once, and ranks them by phonetic distance to the heard text,
returning the closest few. `best_match` does the same for a one-off list. It does not
decide whether the best one is "good enough": that depends on the
application, so the distances and the gap between the first and second
match are returned for the caller to judge.

Every sound missing from one side costs at least the cheapest deletion, so a
reference much longer or shorter than what was heard cannot beat matches
already found. Lengths are ranges (a dropped "Devi", an initial standing for
a whole word), and the gap between the two ranges gives the lower bound.
References are visited in order of that gap and the search stops once the
bound exceeds the current `top`-th best. Each distance computation also
stops early once it can't beat that. The result is exactly what scoring
every reference would give, with far fewer computations.
"""
from bisect import insort
from collections.abc import Hashable, Iterable
from dataclasses import dataclass

from .distance import INDEL_CHEAP, INF, Confusions, _table, _variants, _variants_distance, sound_range

_FLOOR = min(INDEL_CHEAP.values())      # cheapest cost of one missing sound
_EPS = 1e-6                             # distances are rounded to 6 places


@dataclass(frozen=True)
class Match:
    key: Hashable       # the key given with the reference, or the text itself
    text: str           # the reference text
    distance: float     # phonetic distance from what was heard; 0 is identical


Reference = str | tuple[Hashable, str]


class Matcher:
    """
    A list of references, prepared once for many lookups.

    references: plain strings, or (key, text) pairs when several texts lead
    to one thing (an id for a person, aliases for one city). With pairs,
    each key appears at most once in a result, at its best distance.

    confusions: a `Confusions` table to use instead of the default one.

    Raises UnsupportedScriptError if a reference is in a script the library
    can't read, so bad data shows up when the list is loaded, not mid-call.
    """

    def __init__(self, references: Iterable[Reference], *, confusions: Confusions | None = None):
        self.confusions = _table(confusions)
        self._sub = self.confusions._sub
        self._refs = []
        order: dict[Hashable, int] = {}
        for r in references:
            key, text = (r, r) if isinstance(r, str) else (r[0], r[1])
            variants = _variants(text)
            if variants:
                rank = order.setdefault(key, len(order))   # equal distances keep list order
                self._refs.append((key, text, variants, sound_range(text), rank))

    def __len__(self) -> int:
        return len(self._refs)

    def best_match(self, heard: str, top: int = 3) -> list[Match]:
        """The `top` references closest to `heard`, nearest first; ties in list order."""
        if top < 1:
            raise ValueError("top must be at least 1")
        heard_variants = _variants(heard)
        if not heard_variants or not self._refs:
            return []
        lo, hi = sound_range(heard)

        def gap(ref) -> float:
            r_lo, r_hi = ref[3]
            return max(0, r_lo - hi, lo - r_hi)

        best: dict[Hashable, Match] = {}
        ranked: list[tuple[float, int, Hashable]] = []
        for ref in sorted(self._refs, key=gap):
            key, text, variants, _, rank = ref
            full = len(ranked) >= top
            cutoff = ranked[-1][0] if full else INF
            if full and _FLOOR * gap(ref) > cutoff + _EPS:
                break
            d = _variants_distance(heard_variants, variants, cutoff + _EPS, self._sub)
            if d > cutoff + _EPS:
                continue
            d = round(d, 6)
            if key in best and best[key].distance <= d:
                continue
            best[key] = Match(key, text, d)
            ranked = [e for e in ranked if e[2] != key]
            insort(ranked, (d, rank, key))
            del ranked[top:]
        return [best[k] for _, _, k in ranked]


def best_match(heard: str, references: Iterable[Reference], top: int = 3, *,
               confusions: Confusions | None = None) -> list[Match]:
    """
    The `top` references closest to `heard`, nearest first.

    A shortcut for `Matcher(references).best_match(heard, top)`. When matching
    many utterances against one list, build the Matcher once.
    """
    if top < 1:
        raise ValueError("top must be at least 1")
    return Matcher(references, confusions=confusions).best_match(heard, top)
