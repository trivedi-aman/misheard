# Changelog

## Unreleased

- Titles and honorifics are ignored (Shri, Smt, Dr, ji, sahab, bhai, திரு, श्री…); joined honorifics (Rameshbhai) and Devi/Kumar/Kumari are optional for a small penalty.
- Initials match words with the same first letter (R. Kumar / Ramesh Kumar).
- Names of up to 4 words are compared in any order (was: 2).
- `distance` is rounded to 6 decimal places.
- New `sound_range`; `best_match` pruning uses it and stays exact.

## 0.0.1 (unreleased)

- Extracted from Vaani: transliteration (Devanagari, Tamil → phonetic Roman) and feature-weighted phonetic distance.
- `best_match` with exact length-bound pruning and key-grouped aliases.
- Benchmark against Levenshtein and Metaphone.
