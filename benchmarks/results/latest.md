# Benchmark

782 items. Names are matched against 300 synthetic people; places against 745 Indian districts plus 35 aliases.

**Not real speech-to-text output yet** (see PLAN.md). The `rules` rows flatter indic-phonetic because the variants are generated from the same confusions it models.

| Source | Kind | Items | Levenshtein top-1 | Metaphone top-1 | indic-phonetic top-1 | indic-phonetic top-3 |
| --- | --- | --- | --- | --- | --- | --- |
| handwritten | name | 62 | 96.8% | 96.8% | 100.0% | 100.0% |
| handwritten | place | 50 | 92.0% | 74.0% | 100.0% | 100.0% |
| native | name | 254 | 97.6% | 97.6% | 100.0% | 100.0% |
| rules | name | 246 | 99.6% | 96.3% | 100.0% | 100.0% |
| rules | place | 170 | 97.6% | 90.0% | 100.0% | 100.0% |

Levenshtein and Metaphone get the same romanisation of native script that indic-phonetic uses, so the comparison is about matching, not transliteration.

## Time per lookup

| Matcher | ms per item |
| --- | --- |
| Levenshtein | 0.12 |
| Metaphone | 0.37 |
| indic-phonetic | 25.44 |

## indic-phonetic misses

None.
