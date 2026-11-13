"""
Compare indic-phonetic against Levenshtein and Metaphone on names and places
as speech-to-text hears them.

Sources, reported separately because they test different things:

  handwritten  ~110 variants written by hand: STT-style misspellings,
               surname-first, old city names, native script.
  native       300 synthetic people's names in Devanagari or Tamil script,
               as STT returns Hindi, Marathi and Tamil speech.
  rules        Roman spelling variants made by rules (vowel length, v/w,
               sh/s, dropped final a, doubled letters...). These rules
               describe the same confusions the engine was built around,
               so this set flatters it: it checks the engine does what it
               was designed to do, not that it is better.

None of this is real STT output yet; see PLAN.md, phase 2.

    pip install -e '.[bench]'
    python benchmarks/run.py            # writes benchmarks/results/latest.md
"""
import csv
import random
import re
import time
from collections import defaultdict
from pathlib import Path

import jellyfish
from rapidfuzz.distance import Levenshtein

from indic_phonetic import best_match, plain, to_roman

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
rng = random.Random(7)


def read(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


PEOPLE = read("people.csv")
DISTRICTS = [r["district"] for r in read("districts.csv")]
ALIASES = [(r["alias"], r["district"]) for r in read("place_aliases.csv")]
PLACE_REFS = [(d, d) for d in DISTRICTS] + [(d, a) for a, d in ALIASES]      # (key, spoken)
NAME_REFS = [(p["full_name"], p["full_name"]) for p in PEOPLE]

RULES = [
    (r"aa", "a"), (r"ee", "i"), (r"oo", "u"), (r"i(?!i)", "ee"), (r"u(?!u)", "oo"),
    (r"(?<=[^aeiou])a(?=[^aeiou])", "aa"), (r"v", "w"), (r"w", "v"), (r"sh", "s"),
    (r"th", "t"), (r"(?<!h)t(?!h)", "th"), (r"dh", "d"), (r"ph", "f"), (r"a$", ""),
    (r"([bcdfgjklmnprstvz])$", r"\1a"), (r"ai", "ay"), (r"ay", "ai"), (r"kh", "k"),
    (r"bh", "b"), (r"(.)\1", r"\1"), (r"([lnt])(?!\1)", r"\1\1"), (r"ksh", "x"), (r"z", "j"),
]


def rule_variant(text: str) -> str | None:
    out, changed = [], False
    for w in text.lower().split():
        for _ in range(rng.choice([1, 1, 2])):
            options = [(p, r) for p, r in RULES if re.search(p, w)]
            if options and rng.random() < 0.8:
                p, r = rng.choice(options)
                new = re.sub(p, r, w, count=1)
                changed |= new != w
                w = new
        out.append(w)
    return " ".join(out).title() if changed else None


def items() -> list[tuple[str, str, str, str]]:
    """(source, kind, heard, expected)"""
    out = [("handwritten", r["kind"], r["heard"], r["expected"]) for r in read("handwritten_variants.csv")]
    out += [("native", "name", p["name_native"], p["full_name"]) for p in PEOPLE if p["name_native"]]
    for p in rng.sample(PEOPLE, 250):
        if v := rule_variant(p["full_name"]):
            out.append(("rules", "name", v, p["full_name"]))
    for d in rng.sample(DISTRICTS, 200):
        if v := rule_variant(d):
            out.append(("rules", "place", v, d))
    return out


# ---- matchers: each returns keys, best first ---------------------------------

def _letters(heard: str, refs, code) -> list:
    h = code(plain(to_roman(heard)))
    scored = sorted(refs, key=lambda kt: Levenshtein.distance(h, code(kt[1].lower())))
    seen, keys = set(), []
    for k, _ in scored:
        if k not in seen:
            seen.add(k)
            keys.append(k)
        if len(keys) == 3:
            break
    return keys


def levenshtein(heard, refs):
    return _letters(heard, refs, lambda s: s)


def metaphone(heard, refs):
    return _letters(heard, refs, lambda s: " ".join(jellyfish.metaphone(w) for w in s.split()))


def phonetic(heard, refs):
    return [m.key for m in best_match(heard, refs, top=3)]


MATCHERS = {"Levenshtein": levenshtein, "Metaphone": metaphone, "indic-phonetic": phonetic}


def main() -> None:
    data = items()
    stats = defaultdict(lambda: [0, 0, 0])          # (source, kind, matcher) -> [n, top1, top3]
    misses, elapsed = [], defaultdict(float)
    for source, kind, heard, expected in data:
        refs = NAME_REFS if kind == "name" else PLACE_REFS
        for name, fn in MATCHERS.items():
            t = time.perf_counter()
            keys = fn(heard, refs)
            elapsed[name] += time.perf_counter() - t
            s = stats[(source, kind, name)]
            s[0] += 1
            s[1] += bool(keys) and keys[0] == expected
            s[2] += expected in keys
            if name == "indic-phonetic" and (not keys or keys[0] != expected):
                misses.append((source, kind, heard, expected, keys))

    lines = ["# Benchmark", "",
             f"{len(data)} items. Names are matched against {len(NAME_REFS)} synthetic people; "
             f"places against {len(DISTRICTS)} Indian districts plus {len(ALIASES)} aliases.", "",
             "**Not real speech-to-text output yet** (see PLAN.md). The `rules` rows flatter indic-phonetic "
             "because the variants are generated from the same confusions it models.", "",
             "| Source | Kind | Items | Levenshtein top-1 | Metaphone top-1 | indic-phonetic top-1 | indic-phonetic top-3 |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for source in ("handwritten", "native", "rules"):
        for kind in ("name", "place"):
            n = stats[(source, kind, "indic-phonetic")][0]
            if not n:
                continue

            def pct(m, i=1, source=source, kind=kind, n=n):
                return f"{100 * stats[(source, kind, m)][i] / n:.1f}%"
            lines.append(f"| {source} | {kind} | {n} | {pct('Levenshtein')} | {pct('Metaphone')} "
                         f"| {pct('indic-phonetic')} | {pct('indic-phonetic', 2)} |")
    lines += ["", "Levenshtein and Metaphone get the same romanisation of native script that indic-phonetic uses, "
              "so the comparison is about matching, not transliteration.", "",
              "## Time per lookup", "", "| Matcher | ms per item |", "| --- | --- |"]
    lines += [f"| {m} | {1000 * t / len(data):.2f} |" for m, t in elapsed.items()]
    lines += ["", "## indic-phonetic misses", ""]
    if misses:
        lines += ["| Source | Kind | Heard | Expected | Top 3 |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {s} | {k} | {h} | {e} | {', '.join(map(str, t))} |" for s, k, h, e, t in misses]
    else:
        lines.append("None.")
    out = HERE / "results" / "latest.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
