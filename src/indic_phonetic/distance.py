"""
Phoneme-weighted distance for Indian names and places.

Plain edit distance treats every letter swap as equally bad. For speech that
is wrong in both directions:

  - "Barmer" vs "Baadmer" are the same place: a vowel-length change plus the
    retroflex flap (ड़) written two different ways. Should be cheap.
  - "Mohan" vs "Rohan" are different people: m and r sound nothing alike,
    even though only one letter differs. Should be expensive.

So each sound carries articulatory features (where and how it is made,
voicing, aspiration; vowel height, backness, length), and substituting one
sound for another costs the weighted difference of those features. A small
table of confusions specific to Indian languages (data/confusions.csv)
overrides the feature cost where linguistics says two sounds are routinely
mixed up.
"""
import csv
import io
import re
from functools import lru_cache
from itertools import permutations, product
from typing import NamedTuple
from importlib.resources import files

from .translit import plain, to_roman

# ---- sound inventory -------------------------------------------------------

# consonants: (place, manner, voiced, aspirated)
#   place: 0 bilabial, 1 labiodental, 2 dental/alveolar, 3 retroflex,
#          4 palatal, 5 velar, 6 glottal
#   manner: 0 stop, 1 nasal, 2 fricative, 3 approximant, 4 trill/flap, 5 affricate
CONSONANTS = {
    "p": (0, 0, 0, 0), "ph": (0, 0, 0, 1), "b": (0, 0, 1, 0), "bh": (0, 0, 1, 1), "m": (0, 1, 1, 0),
    "f": (1, 2, 0, 0), "v": (1, 3, 1, 0), "w": (0, 3, 1, 0),
    "t": (2, 0, 0, 0), "th": (2, 0, 0, 1), "d": (2, 0, 1, 0), "dh": (2, 0, 1, 1),
    "n": (2, 1, 1, 0), "s": (2, 2, 0, 0), "z": (2, 2, 1, 0), "l": (2, 3, 1, 0), "r": (2, 4, 1, 0),
    "ṭ": (3, 0, 0, 0), "ṭh": (3, 0, 0, 1), "ḍ": (3, 0, 1, 0), "ḍh": (3, 0, 1, 1),
    "ṇ": (3, 1, 1, 0), "ḷ": (3, 3, 1, 0), "ṛ": (3, 4, 1, 0), "ṛh": (3, 4, 1, 1), "zh": (3, 3, 1, 0),
    "ch": (4, 5, 0, 0), "chh": (4, 5, 0, 1), "j": (4, 5, 1, 0), "jh": (4, 5, 1, 1),
    "sh": (4, 2, 0, 0), "y": (4, 3, 1, 0),
    "k": (5, 0, 0, 0), "kh": (5, 0, 0, 1), "g": (5, 0, 1, 0), "gh": (5, 0, 1, 1),
    "h": (6, 2, 0, 0),
}
# vowels: (height 0 low..2 high, backness 0 front..2 back, length 0 short/1 long)
VOWELS = {
    "a": (0, 1, 0), "aa": (0, 1, 1),
    "i": (2, 0, 0), "ee": (2, 0, 1),
    "u": (2, 2, 0), "oo": (2, 2, 1),
    "e": (1, 0, 0), "ai": (1, 0, 1),
    "o": (1, 2, 0), "au": (1, 2, 1),
}

W_PLACE, W_MANNER, W_VOICE, W_ASP = 0.45, 0.45, 0.25, 0.15
W_HEIGHT, W_BACK, W_LEN = 0.35, 0.35, 0.25
CROSS_CLASS = 1.8          # a vowel replaced by a consonant
INDEL = 0.85               # a consonant missing or added
INDEL_CHEAP = {"a": 0.4, "h": 0.4, "y": 0.5}   # silent schwa, aspiration spellings
INDEL_VOWEL = 0.6

_TOKENS = sorted(set(CONSONANTS) | set(VOWELS), key=len, reverse=True)

def _load_confusions() -> dict[frozenset, float]:
    text = files(__package__).joinpath("data", "confusions.csv").read_text(encoding="utf-8")
    return {frozenset((r["a"], r["b"])): float(r["cost"]) for r in csv.DictReader(io.StringIO(text))}


CONFUSIONS = _load_confusions()

# ---- tokenizer -------------------------------------------------------------

# English-style spellings of Indian names, folded before tokenizing.
_SPELLING = [
    ("ck", "k"), ("x", "ks"), ("q", "k"), ("ii", "ee"), ("uu", "oo"),
    ("ou", "au"),
]


def _fold(word: str) -> str:
    w = word.lower()
    for a, b in _SPELLING:
        w = w.replace(a, b)
    if w.endswith("ow"):                      # Lucknow
        w = w[:-2] + "au"
    if w.endswith("ey"):                      # Pandey, Dubey
        w = w[:-2] + "e"
    w = re.sub(r"ay(?=[^aeiou]|$)", "ai", w)   # Sanjay/संजय, Jaipur/जयपुर
    # c without h is k (Vincent, Deepcika); keep ch
    w = "".join("k" if c == "c" and not w[i + 1:i + 2] == "h" else c for i, c in enumerate(w))
    # doubled consonants are not contrastive in romanised names (Pillai/Pilai)
    out = []
    for c in w:
        if out and c == out[-1] and c not in "aeo":
            continue
        out.append(c)
    return "".join(out)


@lru_cache(maxsize=50_000)
def tokenize(word: str) -> tuple[str, ...]:
    """One word in any script -> tuple of sounds, greedy longest match."""
    s = _fold(to_roman(word))
    i, out = 0, []
    while i < len(s):
        for tok in _TOKENS:
            if s.startswith(tok, i):
                out.append(tok)
                i += len(tok)
                break
        else:
            i += 1                            # digits, punctuation, unknown marks
    return tuple(out)


# ---- costs -----------------------------------------------------------------

def sub_cost(a: str, b: str) -> float:
    if a == b:
        return 0.0
    override = CONFUSIONS.get(frozenset((a, b)))
    if override is not None:
        return override
    a_vowel, b_vowel = a in VOWELS, b in VOWELS
    if a_vowel != b_vowel:
        return CROSS_CLASS
    if a_vowel:
        h1, k1, l1 = VOWELS[a]
        h2, k2, l2 = VOWELS[b]
        return W_HEIGHT * abs(h1 - h2) + W_BACK * abs(k1 - k2) + W_LEN * abs(l1 - l2)
    p1, m1, v1, s1 = CONSONANTS[a]
    p2, m2, v2, s2 = CONSONANTS[b]
    return W_PLACE * abs(p1 - p2) + W_MANNER * min(abs(m1 - m2), 2) + W_VOICE * abs(v1 - v2) + W_ASP * abs(s1 - s2)


def indel_cost(tok: str) -> float:
    if tok in INDEL_CHEAP:
        return INDEL_CHEAP[tok]
    return INDEL_VOWEL if tok in VOWELS else INDEL


def sequence_distance(pa: tuple[str, ...], pb: tuple[str, ...]) -> float:
    """Weighted edit distance between two sound sequences."""
    n, m = len(pa), len(pb)
    prev = [0.0] * (m + 1)
    for j in range(1, m + 1):
        prev[j] = prev[j - 1] + indel_cost(pb[j - 1])
    for i in range(1, n + 1):
        cur = [prev[0] + indel_cost(pa[i - 1])] + [0.0] * m
        for j in range(1, m + 1):
            cur[j] = min(
                prev[j - 1] + sub_cost(pa[i - 1], pb[j - 1]),
                prev[j] + indel_cost(pa[i - 1]),
                cur[j - 1] + indel_cost(pb[j - 1]),
            )
        prev = cur
    return prev[m]


# ---- words -----------------------------------------------------------------
#
# A spoken name is more than its sounds: people add titles ("Shri Mohan Lal"),
# honorifics ("Mohan ji", "Rameshbhai"), use initials ("R. Kumar") and change
# word order ("Kumar Ramesh Singh"). Each name is expanded into a few
# variants, each with a small penalty, and the cheapest pairing wins.

# Dropped whenever another word remains. Listed in any script; they are
# compared after romanising, so श्री, Shri and Sri all match.
TITLES = [
    "shri", "shree", "sri", "sree", "sh", "shrimati", "srimati", "smt", "dr", "doctor",
    "mr", "mrs", "ms", "miss", "thiru", "tiru", "thirumathi", "tirumathi",
    "श्री", "श्रीमती", "डॉ", "डॉक्टर", "திரு", "திருமதி", "ஸ்ரீ",
]
# Honorific words, said after (or before) a name. Also dropped.
HONORIFICS = [
    "ji", "jee", "sahab", "saheb", "sahib", "sir", "madam", "bhai", "bhaiya", "ben", "behen", "didi",
    "जी", "साहब", "भाई", "भैया", "बहन", "बेन", "दीदी",
]
# Honorifics written joined to the name (Gujarati Rameshbhai, Hansaben).
# Optional, because the joined form can be the whole name. "ji" is not here:
# Balaji, Shivaji.
SUFFIXES = ["bhai", "ben", "भाई", "बेन"]
SUFFIX_PENALTY = 0.1
# Often part of a legal name and often left out when spoken.
OPTIONAL_WORDS = ["devi", "kumar", "kumari", "देवी", "कुमार", "कुमारी", "தேவி", "குமார்", "குமாரி"]
OPTIONAL_PENALTY = 0.5

INITIAL_COST = 0.3         # "R." standing for a word starting with r
INITIAL_MISMATCH = 1.5     # an initial against a word starting with another letter
SWAP_PENALTY = 0.2         # words in a different order
MAX_PERMUTED_WORDS = 4     # up to 4! = 24 orders


def _key(word: str) -> str:
    """Romanised, folded, unmarked letters only: for comparing with the word lists above."""
    return re.sub(r"[^a-z]", "", plain(_fold(to_roman(word))))


_TITLES = {_key(w) for w in TITLES} | {_key(w) for w in HONORIFICS}
_SUFFIXES = sorted({_key(w) for w in SUFFIXES}, key=len, reverse=True)
_OPTIONAL = {_key(w) for w in OPTIONAL_WORDS}


class _Word(NamedTuple):
    sounds: tuple[str, ...]
    initial: str | None     # the letter, when the word is an initial like "R."
    first: str              # first letter of the romanised word


def _word(text: str) -> _Word | None:
    sounds = tokenize(text)
    if not sounds:
        return None
    is_initial = len(text) == 1 and text.isascii() and text.isalpha()
    key = _key(text)
    return _Word(sounds, text.lower() if is_initial else None, key[:1])


@lru_cache(maxsize=50_000)
def _variants(text: str) -> tuple[tuple[float, tuple[_Word, ...]], ...]:
    """The ways a name may be said, each with its penalty."""
    raw = text.replace(".", " ").split()                 # "R.K. Narayan" -> R K Narayan
    raw = [w for w in raw if _word(w)]
    core = [w for w in raw if _key(w) not in _TITLES] or raw
    options: list[list[tuple[float, _Word | None]]] = []
    for w in core:
        word = _word(w)
        choices: list[tuple[float, _Word | None]] = [(0.0, word)]
        key = _key(w)
        if key in _OPTIONAL and len(core) > 1:
            choices.append((OPTIONAL_PENALTY, None))
        elif word.initial is None:
            roman = _fold(to_roman(w))
            for suf in _SUFFIXES:
                if key.endswith(suf) and len(key) - len(suf) >= 3 and plain(roman).endswith(suf):
                    stem = _word(roman[: len(roman) - len(suf)])
                    if stem:
                        choices.append((SUFFIX_PENALTY, stem))
                    break
        options.append(choices)
    out = {}
    for combo in product(*options):
        words = tuple(w for _, w in combo if w is not None)
        if words:
            pen = round(sum(p for p, _ in combo), 6)
            if words not in out or out[words] > pen:
                out[words] = pen
    return tuple((p, w) for w, p in out.items())


def _word_cost(x: _Word, y: _Word) -> float:
    if x.initial or y.initial:
        if x.initial and y.initial:
            return 0.0 if x.initial == y.initial else INITIAL_MISMATCH
        letter, other = (x.initial, y) if x.initial else (y.initial, x)
        return INITIAL_COST if other.first == letter else INITIAL_MISMATCH
    return sequence_distance(x.sounds, y.sounds)


def _words_distance(wa: tuple[_Word, ...], wb: tuple[_Word, ...]) -> float:
    n = len(wa)
    if n == len(wb):
        cost = [[_word_cost(x, y) for y in wb] for x in wa]
        best = sum(cost[i][i] for i in range(n))
        if 1 < n <= MAX_PERMUTED_WORDS:
            for perm in permutations(range(n)):
                best = min(best, sum(cost[i][p] for i, p in enumerate(perm)) + SWAP_PENALTY)
        return best
    # A different number of words (a dropped surname, "Meenakshisundaram" as
    # one word): compare as one joined sequence, so every missing sound costs.
    return sequence_distance(tuple(t for w in wa for t in w.sounds), tuple(t for w in wb for t in w.sounds))


def distance(a: str, b: str) -> float:
    """
    Distance between two names of one or more words, in any mix of scripts.

    Titles and honorifics are ignored (Shri, Smt, Dr, ji, sahab, bhai), joined
    honorifics (Rameshbhai) and words like Devi or Kumar may be left out for a
    small penalty, initials match words that start with the same letter, and
    words may come in any order for a small penalty.
    """
    va, vb = _variants(a), _variants(b)
    if not va or not vb:
        return float("inf")
    best = min(pa + pb + _words_distance(wa, wb) for pa, wa in va for pb, wb in vb)
    return round(best, 6)       # 1.8, not 1.7999999999999998


@lru_cache(maxsize=50_000)
def sound_length(text: str) -> int:
    """Number of sounds in a name or place, all words together."""
    return sum(len(tokenize(w)) for w in text.split())


@lru_cache(maxsize=50_000)
def sound_range(text: str) -> tuple[int, float]:
    """
    Fewest and most sounds any variant of `text` can stand for.

    An initial stands for a word of any length, so a name with one has no
    upper bound. `best_match` uses this to skip references that cannot be
    close.
    """
    lo, hi = float("inf"), 0.0
    for _, words in _variants(text):
        n = sum(len(w.sounds) for w in words)
        lo = min(lo, n)
        hi = max(hi, float("inf") if any(w.initial for w in words) else n)
    return (int(lo), hi) if lo != float("inf") else (0, 0.0)
