# indic-phonetic

Match Indian names and places by how they **sound**, not how they are spelled, across Devanagari, Tamil and Roman script. Pure Python, no dependencies.

```python
from indic_phonetic import distance, best_match, to_roman

to_roman("बाड़मेर")                  # 'baaṛmer'
to_roman("முருகன்")                  # 'murugan'

distance("Barmer", "बाड़मेर")         # 0.4   same place
distance("Barmer", "Baadmer")         # 0.6   same place, different spelling
distance("Mohan", "Rohan")            # 1.7   different people

best_match("Rohun Varma", [("C1", "Rohan Verma"), ("C2", "Mohan Verma"), ("C3", "Sohan Verma")])
# [Match(key='C1', text='Rohan Verma', distance=1.7),
#  Match(key='C3', text='Sohan Verma', distance=2.85),
#  Match(key='C2', text='Mohan Verma', distance=3.4)]
```

> **Status: pre-alpha (0.0.x).** The API may change. Known gaps are listed in [PLAN.md](PLAN.md).

## Try it

```bash
pip install -e '.[demo]'
python demo/app.py          # opens http://127.0.0.1:7860
```

Type a name or place as it was heard, in any supported script, and see the closest matches from Indian districts or a sample list of people, why the top one matched, and what a voice agent might do with it (accept, read back, ask again). A second tab compares two names step by step.

## Why

Speech-to-text and hand-typed records spell Indian names in many ways: *Barmer / Baadmer / बाड़मेर*, *Lakshmi / Laxmi / லட்சுமி*, *Vikram / Wikram*. Edit distance counts every letter change as equally bad, so it is wrong in both directions:

- **Barmer** and **Baadmer** are the same place: a long vowel plus the retroflex flap ड़ spelled two ways. That should be cheap.
- **Mohan** and **Rohan** are different people: *m* and *r* sound nothing alike, even though only one letter differs. That should be expensive.

English phonetic codes (Soundex, Metaphone) follow English spelling rules and don't know about retroflex consonants, aspiration or the silent *a* in Hindi.

## How it works

1. **Transliterate** Devanagari and Tamil into one phonetic Roman form. Hindi drops the silent *a* (schwa deletion: मोहन → *mohan*). Tamil voices stops between vowels (முருகன் → *murugan*). Retroflex sounds stay marked (ṭ ḍ ṇ ḷ ṛ).
2. **Tokenize** into sounds, folding English-style spellings first (*x→ks*, *-ey→e*, doubled letters).
3. **Score substitutions by articulatory features**: place and manner of articulation, voicing and aspiration for consonants; height, backness and length for vowels. A swap between similar sounds is cheap, a swap between unrelated sounds is expensive.
4. **Override with known confusions** ([`data/confusions.csv`](src/indic_phonetic/data/confusions.csv)): v/w, t/ṭ, ph/f, Tamil k/g, and so on. Each row says why it's there.
5. **Weighted edit distance** over the sounds. Dropping a silent *a* or an *h* costs little.
6. **Words as people say them.** Titles and honorifics are ignored (*Shri*, *Smt*, *Dr*, *ji*, *sahab*). A joined honorific (*Rameshbhai*) costs 0.1 to drop, and *Devi* or *Kumar* cost 0.5. An initial matches a word with the same first letter (*R. Kumar* / *Ramesh Kumar* = 0.3). Words may come in any order (*Kumar Ramesh Singh*) for 0.2.

`best_match` skips references whose length alone rules them out. It gives the same result as scoring every reference, with far fewer comparisons.

## API

| | |
| --- | --- |
| `distance(a, b) -> float` | Phonetic distance between two names, in any mix of scripts. 0 means the same sounds. |
| `Matcher(references)` | Prepare a reference list once. References are strings or `(key, text)` pairs; keys group aliases (*Bangalore*, *Bengaluru*) under one result. |
| `Matcher.best_match(heard, top=3) -> list[Match]` | Closest references, nearest first; equal distances keep list order. |
| `best_match(heard, references, top=3)` | Shortcut for a one-off list. |
| `explain(a, b) -> Explanation` | The steps behind a distance: each sound kept, swapped, added or dropped, with the reason from the confusion table, plus titles ignored, words left out, initials and reordering. `print()` it for a readable table. |
| `to_roman(text) -> str` | Devanagari / Tamil / Latin → phonetic Roman. |
| `plain(text) -> str` | Remove the retroflex marks: *baaṛmer* → *baarmer*. |
| `script_of(text) -> str` | `"devanagari"`, `"tamil"` or `"latin"`. |
| `tokenize(word) -> tuple[str, ...]` | The sounds the distance is computed over. |

The library does not decide whether a match is good enough, because that threshold depends on your application. A voice agent might accept a match below about 0.8 when it is at least 1.0 ahead of the next candidate, read back anything below 1.8, and ask again otherwise. Those values come from the project this library was extracted from; tune them on your own data.

## Benchmark

782 items: 300 synthetic people, and 745 Indian districts plus aliases. Run it with `python benchmarks/run.py`. Full results are in [benchmarks/results/latest.md](benchmarks/results/latest.md).

| Source | Kind | Items | Levenshtein top-1 | Metaphone top-1 | indic-phonetic top-1 |
| --- | --- | --- | --- | --- | --- |
| handwritten | name | 62 | 96.8% | 96.8% | 100.0% |
| handwritten | place | 50 | 92.0% | 74.0% | 100.0% |
| native script | name | 254 | 97.6% | 97.6% | 100.0% |
| rule-generated | name | 246 | 99.6% | 96.3% | 100.0% |
| rule-generated | place | 170 | 97.6% | 90.0% | 100.0% |

**Read these numbers with care.** None of the items are real speech-to-text output yet. The rule-generated variants use the same confusions the engine models, and the handwritten ones were written by the author. Building a benchmark from data the engine wasn't designed around is the top item in [PLAN.md](PLAN.md). Speed is still behind: about 5 ms per lookup against 780 places with a `Matcher`, compared with 0.1 ms for Levenshtein. A compiled core is planned.

## Scope

- **Scripts:** Devanagari (Hindi, Marathi, …), Tamil, Latin. Other scripts are not supported yet and raise `UnsupportedScriptError`.
- **Made for:** names of people and places, short spoken phrases. It is not a general transliterator: use [indic-transliteration](https://pypi.org/project/indic-transliteration/) or [IndicXlit](https://github.com/AI4Bharat/IndicXlit) for running text.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev,bench]'
pytest                     # tests marked xfail are known gaps from PLAN.md
python benchmarks/run.py
```

## License

MIT. The district list in `benchmarks/data` is derived from India Post's public pincode directory. All people in `benchmarks/data/people.csv` are synthetic.
