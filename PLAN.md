# Plan

Where the library is going, in order. Tick items off as they land; each phase ends with a release.

The engine was extracted from Vaani, a multilingual voice agent, where it matched spoken customer names and districts. Vaani-specific code (confidence thresholds, pincode cross-checks, customer data) stayed behind.

## Phase 0: Extraction ✅ (0.0.1)

- [x] Copy `translit.py` and `phonetic.py` (now `distance.py`) out of Vaani; load `confusions.csv` as package data
- [x] Generic `best_match` with length-bound pruning, `(key, text)` pairs for aliases and ids
- [x] Tests ported; known gaps recorded as strict `xfail` tests
- [x] Benchmark against Levenshtein and Metaphone, reproducing Vaani's numbers

## Phase 1: Correctness fixes (0.1.0)

Each one has an `xfail` test. Remove the marker when it's fixed.

- [ ] **1.1 Anusvara before ह / fricatives.** `सिंह` → `sinh`, should be `singh` (distance to *Singh* is 1.25 today). Anusvara takes the place of the following consonant: ng before velars and h, m before labials, n otherwise.
- [ ] **1.2 ज्ञ.** `ज्ञान` → `jnaan`, distance 2.85 to *Gyan*. Map ज्ञ to `gy`. Marathi says `dny` (*Dnyaneshwar*), so either add a confusion row gy/dny or take a language hint.
- [ ] **1.3 Final-syllable vowels in surnames.** *Patil* / *Patel* = 0.35, the one false accept in Vaani's eval. Options: weight vowel changes higher in the last syllable, or add confusion rows that make specific pairs more expensive. Check that this doesn't break *Gupta/Gupt* or *Amit/Amita*.
- [ ] **1.4 Fail loudly on unsupported scripts.** Telugu, Kannada, Bengali, … are silently dropped today. Raise an error, or return a result that says what was dropped.
- [ ] **1.5 Audit `_fold`.** The English-spelling rules (`-ey`, `-ow`, `c→k`) were written for the names in Vaani. Collect counterexamples.

## Phase 2: Honest benchmark (0.2.0)

This phase decides whether the library is actually better, so it matters more than any feature.

- [ ] **2.1 Real speech-to-text data.** Record or collect 100+ spoken names and places (Hindi, Marathi, Tamil, Indian English), run them through one or two STT services (Sarvam, Google, Whisper), and keep the transcripts with the intended name. Store the transcripts, not the audio.
- [ ] **2.2 Real spelling variants.** Find a public source of name variants (electoral rolls are not OK; look for open datasets, Wikipedia/Wikidata labels in several scripts, census place names).
- [ ] **2.3 Non-match test.** Names that are *not* in the reference list should get no close match. Report the distribution of best distances for them (Vaani's eval did this; port it).
- [ ] **2.4 Report precision at a threshold**, not just top-1. A matcher that always returns something looks good on top-1.
- [ ] **2.5 Compare against stronger baselines:** Jaro-Winkler, libindic soundex, and transliterate-then-Levenshtein using IndicXlit.

## Phase 3: Speed (0.3.0)

25 ms per lookup against 780 places, about 200× slower than Levenshtein.

- [ ] **3.1 Profile.** The likely costs are the pure-Python DP and `sub_cost` lookups. Precompute a token → int index and a dense cost matrix.
- [ ] **3.2 Cache tokenized references** inside `best_match` (or a `Matcher` object built once from the references).
- [ ] **3.3 Blocking for large lists** (10⁵+ names): index the first consonant classes or a coarse phonetic key, and only score that bucket.
- [ ] **3.4 Optional compiled core** (Cython / Rust via PyO3 / numba) only if 3.1–3.3 aren't enough. The pure-Python fallback must remain.

## Phase 4: API and configurability (0.4.0)

- [ ] **4.1 `Matcher` class** holding references, costs and confusions: `Matcher(refs, confusions=...)`. The module-level functions remain as shortcuts.
- [ ] **4.2 Custom confusion tables**: merge with or replace the defaults.
- [ ] **4.3 Optional `explain(a, b)`** that returns the alignment and each step's cost. Useful for debugging and for the README.
- [ ] **4.4 Language hint** (`lang="mr"`) for Marathi ज्ञ, Bengali v→b, and similar.
- [ ] **4.5 Decide on confidence grading.** Either keep it out (current choice) or offer `grade(matches, high=..., margin=...)` as an optional helper.

## Phase 5: More scripts (0.5.0+)

Each script needs a transliterator, tests with real names, and benchmark rows.

- [ ] Telugu, Kannada (close to Tamil's structure, but voiced stops are written)
- [ ] Bengali (inherent vowel is *o*; v→b)
- [ ] Gujarati, Gurmukhi (close to Devanagari)
- [ ] Malayalam

## Phase 6: Publish (1.0.0)

- [ ] GitHub repo, CI (pytest on 3.10–3.13, benchmark on PR)
- [ ] Type-check with mypy/pyright, lint with ruff
- [ ] Docs page: how the costs work, with the confusions table rendered
- [ ] Publish to PyPI (name `indic-phonetic` was free as of 2026-11-13)
- [ ] Write-up: blog post or short paper on the method and benchmark
- [ ] Switch Vaani to depend on the library instead of its own copy

## Open questions

- **Name.** `indic-phonetic` is descriptive and easy to find in search. A more memorable name (*dhvani* is taken on PyPI) could come later.
- **Units.** Distances are unbounded floats. Normalising by length (0–1) would make thresholds portable across short and long names, but it changes every number.
- **Weights.** The feature weights were set by hand. Learning them from the phase 2 data could help, but only once that data exists.
