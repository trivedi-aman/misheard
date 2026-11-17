# Changelog

## Unreleased

- New `Confusions`: change the confusion table without touching the package. Start from `Confusions.default()`, then `.merged({("v", "b"): 0.1})`, `.without(("v", "b"))`, or read your own with `Confusions.from_csv(path)`. Pass it as `confusions=` to `distance`, `explain`, `Matcher` and `best_match`. The default is unchanged and just as fast.
- New `misheard.SOUNDS`: every sound a confusion row may name.

- Property tests (Hypothesis) on random Latin, Devanagari and Tamil names: `distance` is symmetric and zero on itself, `explain` adds up to `distance`, `to_roman` raises nothing but `UnsupportedScriptError`, and `Matcher` equals brute-force scoring. Hypothesis is now in the `dev` extra.

## 0.1.0 (2026-11-14): first release as `misheard`

Renamed from `indic-phonetic`. The code is the same as `indic-phonetic` 0.1.0; only the names changed:
`pip install misheard`, `from misheard import ...`.

## indic-phonetic 0.1.0 (2026-11-13)

First release on PyPI.

- Web demo (`demo/app.py`, Gradio): match against districts, people or your own list; compare two names.
- New `explain(a, b)`: the steps and reasons behind a distance.
- New `Matcher` class: prepare references once, match many times. About 5× faster (25 ms → 5 ms against 780 places).
- Equal distances now keep the order of the reference list.
- Fix: anusvara before h is ng (सिंह = singh) and before labials m (चंपा = champa).
- Fix: ज्ञ is gy (ज्ञान = gyaan).
- Fix: Tamil ங்க and ஞ்ச no longer double the consonant (வெங்கடேஷ் = vengaḍesh, was venggaḍesh).
- New confusion row t/ḍ for Tamil ட romanised t (Natarajan, Venkatesh).
- Unsupported scripts raise `UnsupportedScriptError` instead of being silently dropped; `script_of` names them.
- Titles and honorifics are ignored (Shri, Smt, Dr, ji, sahab, bhai, திரு, श्री…); joined honorifics (Rameshbhai) and Devi/Kumar/Kumari are optional for a small penalty.
- Initials match words with the same first letter (R. Kumar / Ramesh Kumar).
- Names of up to 4 words are compared in any order (was: 2).
- `distance` is rounded to 6 decimal places.
- New `sound_range`; `best_match` pruning uses it and stays exact.

## 0.0.1 (not published)

- Extracted from Vaani: transliteration (Devanagari, Tamil → phonetic Roman) and feature-weighted phonetic distance.
- `best_match` with exact length-bound pruning and key-grouped aliases.
- Benchmark against Levenshtein and Metaphone.
