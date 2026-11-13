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

- [x] **1.1 Anusvara before ह / fricatives.** `सिंह` → `sinh`, should be `singh` (distance to *Singh* is 1.25 today). Anusvara takes the place of the following consonant: ng before velars and h, m before labials, n otherwise.
- [x] **1.2 ज्ञ.** `ज्ञान` → `jnaan`, distance 2.85 to *Gyan*. Map ज्ञ to `gy`. Marathi says `dny` (*Dnyaneshwar*), so either add a confusion row gy/dny or take a language hint. *Done for Hindi; Marathi `dny` left to the language hint (4.4).*
- [ ] **1.3 Final-syllable vowels in surnames.** *Patil* / *Patel* = 0.35, the one false accept in Vaani's eval. Options: weight vowel changes higher in the last syllable, or add confusion rows that make specific pairs more expensive. Check that this doesn't break *Gupta/Gupt* or *Amit/Amita*.
- [x] **1.4 Fail loudly on unsupported scripts.** Telugu, Kannada, Bengali, … are silently dropped today. Raise an error, or return a result that says what was dropped. *Now raises `UnsupportedScriptError` (a `ValueError`) naming the script.*
- [ ] **1.5 Audit `_fold`.** The English-spelling rules (`-ey`, `-ow`, `c→k`) were written for the names in Vaani. Collect counterexamples. Found so far: *Verma* / वर्मा = 0.95 (English writes the schwa as *e*; also *Varma*), so the same name spelled two ways only gets a read-back.
- [x] **1.6 Tamil nasal + stop clusters.** `வெங்கடேஷ்` → `venggaḍesh` (distance 0.95 to *Venkatesh*, should be near 0): ங் gives `ng` and the following க is voiced to `g` as well. Check ஞ்ச, ந்த, ண்ட, ம்ப too. *Fixed ங்க and ஞ்ச (the others were already right); added confusion row t/ḍ 0.30 for Tamil voiced ட written t, so Venkatesh/வெங்கடேஷ் is 0.55.*
- [x] **1.7 Titles and honorifics.** *Shri Mohan Lal* vs *Mohan Lal* was 2.3, worse than *Mohan* vs *Rohan* (1.7). Titles (Shri, Smt, Dr, திரு, …) and honorific words (ji, sahab, bhai, …) are now dropped; joined honorifics (*Rameshbhai*, *Hansaben*) cost 0.1 to drop; *Devi*, *Kumar*, *Kumari* cost 0.5 to drop. Joined *ji* is kept (*Balaji*, *Shivaji*).
- [x] **1.8 Word order beyond two words.** *Kumar Ramesh Singh* vs *Ramesh Kumar Singh* was 10.2. Names of up to 4 words are now compared in every order, with a 0.2 penalty for any reorder.
- [x] **1.9 Initials.** *R. Kumar* vs *Ramesh Kumar* was 2.7. An initial now matches a word starting with the same letter for 0.3 (1.5 otherwise); *R.K.* splits into two initials. `best_match` pruning uses length ranges so it stays exact.
- [x] **1.10 Round `distance`.** It returned 1.7999999999999998; now rounded to 6 places like `best_match`.
- [ ] **1.11 Property tests** (Hypothesis): symmetry, `distance(a, a) == 0`, `to_roman` never raises on random Unicode, `best_match` equals brute force on random lists. Also the safety net for the Rust kernel (3.4).

## Phase 2: Honest benchmark (0.2.0)

This phase decides whether the library is actually better, so it matters more than any feature.

- [ ] **2.1 Real speech-to-text data.** Record or collect 100+ spoken names and places (Hindi, Marathi, Tamil, Indian English), run them through one or two STT services (Sarvam, Google, Whisper), and keep the transcripts with the intended name. Store the transcripts, not the audio.
- [ ] **2.2 Real spelling variants.** Find a public source of name variants (electoral rolls are not OK; look for open datasets, Wikipedia/Wikidata labels in several scripts, census place names).
- [ ] **2.3 Non-match test.** Names that are *not* in the reference list should get no close match. Report the distribution of best distances for them (Vaani's eval did this; port it).
- [ ] **2.4 Report precision at a threshold**, not just top-1. A matcher that always returns something looks good on top-1.
- [ ] **2.5 Compare against stronger baselines:** Jaro-Winkler, libindic soundex, and transliterate-then-Levenshtein using IndicXlit.

## Phase 3: Speed (0.3.0)

Was 25 ms per lookup against 780 places; 3.1, 3.2 and 4.1 brought it to about 5 ms (Levenshtein: 0.1 ms).

- [x] **3.1 Profile.** The biggest cost was `best_match` re-sorting all results after every reference (quadratic), then the DP and `sub_cost` lookups. Now: top-k kept incrementally, a token → int index with a dense cost matrix, and the DP stops early once it can't beat the current top-k.
- [x] **3.2 Cache tokenized references** inside `best_match` (or a `Matcher` object built once from the references).
- [ ] **3.3 Blocking for large lists** (10⁵+ names): index the first consonant classes or a coarse phonetic key, and only score that bucket.
- [ ] **3.4 Rust kernel (PyO3 + maturin).** Compile only the hot loop: weighted edit distance over int token ids, the word-swap logic, and batch scoring with pruning over a `Matcher`'s references. Cost tables are passed in as arrays, so tuning weights or learning them (phase 5) never touches Rust. Transliteration, folding and tokenizing stay in Python: they change often, contributors can fix them without Rust, and with 3.2 they run once per reference. Ship `abi3` wheels (Linux/macOS/Windows, x86 and ARM) from CI. The pure-Python kernel stays as the fallback and as the reference: a property test checks both give identical distances on random inputs. Not C/C++: Rust's packaging via maturin is simpler and the parser input is untrusted.

Order: 3.1 and 3.2 first (they define the kernel boundary), then 3.4, then 3.3. Blocking removes most comparisons, the kernel makes the rest about 100× cheaper; large lists need both.

## Phase 4: API and configurability (0.4.0)

- [x] **4.1 `Matcher` class** holding prepared references: `Matcher(refs).best_match(heard)`. `best_match` remains as a shortcut. Costs and confusions as parameters come with 4.2 / 5.1.
- [ ] **4.2 Custom confusion tables**: merge with or replace the defaults.
- [x] **4.3 `explain(a, b)`** that returns the alignment and each step's cost. Useful for debugging and for the README, and required by 5.4: learning counts substitutions from these alignments.
- [ ] **4.4 Language hint** (`lang="mr"`) for Marathi ज्ञ, Bengali v→b, and similar.
- [ ] **4.5 Decide on confidence grading.** Either keep it out (current choice) or offer `grade(matches, high=..., margin=...)` as an optional helper.
- [ ] **4.6 Command-line tool.** `python -m indic_phonetic Barmer बाड़मेर` prints the distance (and the alignment, once 4.3 exists); `python -m indic_phonetic --refs places.txt Baadmer` prints the best matches. For trying the library without writing code.

## Phase 5: Context and learned costs (0.5.0)

The engine is already a small model: feature weights and confusion costs, set by hand. Accents reach this library as systematic speech-to-text errors (Bengali v→b, Tamil voicing, sh/s in Bihar and eastern UP), which are exactly what those parameters describe. So learn the parameters from data and select them with metadata, rather than replacing the engine with a neural model. It stays fast, explainable and deterministic.

Depends on 4.1/4.2 (costs as a parameter object), 4.3 (alignments) and phase 2 data.

Regional patterns to start the profiles from (already in `confusions.csv` with one all-India cost; a profile makes them cheaper where they're common and leaves them alone elsewhere):

| Pattern | Where | Examples |
| --- | --- | --- |
| v → b | Bihar, Bengal, Odisha, Assam | Vinod/Binod, Vikas/Bikash, Vishnoi/Bishnoi |
| ड़ / ड / र | Bihar, eastern UP | ghoḍa/ghora, paḍhai/parhai, saḍak/sarak |
| sh → s | Bihar, eastern UP, Tamil | Shyam/Syam, Shiva/Siva |
| voiced/unvoiced stops | Tamil | Kannan/Gannan, Palani/Balani |

- [ ] **5.1 `Costs` object.** Feature weights, indel costs and confusions in one versioned, serialisable object. `Costs.default()` reproduces today's numbers exactly.
- [ ] **5.2 Profiles selected by metadata.** `Matcher(refs, profile=...)` or per call: conversation language (`hi`, `mr`, `ta`, `bn`, …), caller region, and STT engine. Each STT engine has its own error patterns, so an engine profile may matter as much as an accent profile. Profiles layer on the default; unknown or missing metadata falls back to it.
- [ ] **5.3 Priors over references.** `best_match(heard, prior={key: weight})` for session context (caller's state or district, a name said earlier). **Soft, not a filter:** the prior's effect is capped so wrong metadata (a migrant from Bihar giving a Bengaluru address) costs a little ranking, never the correct match.
- [ ] **5.4 `Costs.fit(pairs, base=...)`.** Learn weights and confusion costs from confirmed (transcript, true name) pairs, regularised towards `base` so a few hundred pairs are enough. Align each pair with `explain` and count substitutions per profile (record *Vinod*, heard *Binod*, confirmed → one v→b observation in that region). Also learn from **corrected** read-backs as negatives, otherwise costs only ever go down: in Bihar and Bengal *Binod* is a real name, and a list holding both a Vinod and a Binod needs v/b to stay distinguishable. Output is a plain table that can be read and diffed.
- [ ] **5.5 Benchmark with metadata.** Run each item with correct, wrong, and no metadata. Ship a profile only if it helps with correct metadata and hurts little with wrong metadata.
- [ ] **5.6 Data collection (in Vaani, not here).** Log confirmed and corrected read-backs ("Did you say Barmer?" → yes / no, Baadmer) as labelled pairs, with consent and minimal fields. The library never collects data or learns at runtime.
- [ ] **5.7 Per-person aliases (in the app, documented here).** If customer C17 is recorded as *Vinod* and confirms *Binod*, the app stores *Binod* as an alias under C17's key. `best_match` already groups `(key, text)` aliases, so the next call matches at distance 0 without touching any weights. Document this pattern in the README; it's the safe form of learning per session.

Not planned: learning live inside a session. One call has too few names to learn from, labels are noisy (an uncorrected wrong match looks like a confirmation), a few odd sessions could shift weights for everyone, and the inputs are personal data. Session context goes in through 5.2 and 5.3 instead. A neural model is worth trying only if learned tables plateau on the phase 2 benchmark.

## Phase 6: More scripts (0.6.0+)

Each script needs a transliterator, tests with real names, and benchmark rows.

- [ ] Telugu, Kannada (close to Tamil's structure, but voiced stops are written)
- [ ] Bengali (inherent vowel is *o*; v→b)
- [ ] Gujarati, Gurmukhi (close to Devanagari)
- [ ] Malayalam

## Phase 7: Publish (1.0.0)

- [ ] GitHub repo, CI (pytest on 3.10–3.13, benchmark on PR)
- [ ] Type-check with mypy/pyright, lint with ruff
- [ ] Docs page: how the costs work, with the confusions table rendered
- [ ] Publish to PyPI (name `indic-phonetic` was free as of 2026-11-13)
- [ ] Write-up: blog post or short paper on the method and benchmark
- [ ] Switch Vaani to depend on the library instead of its own copy

## Open questions

- **Name.** `indic-phonetic` is descriptive and easy to find in search. A more memorable name (*dhvani* is taken on PyPI) could come later.
- **Units.** Distances are unbounded floats. Normalising by length (0–1) would make thresholds portable across short and long names, but it changes every number.
- **Weights.** The feature weights were set by hand. Learning them is planned in phase 5 (`Costs.fit`), once phase 2 data exists.
