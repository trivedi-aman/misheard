# indic-phonetic has been renamed to misheard

```bash
pip install misheard
```

```python
from misheard import distance, Matcher, explain   # was: from indic_phonetic import ...
```

The code is the same; only the name changed. This package (0.1.1) installs `misheard` and keeps
`import indic_phonetic` working with a deprecation warning, so existing code doesn't break.

New releases are published as [misheard](https://pypi.org/project/misheard/) only.
Source: [github.com/trivedi-aman/misheard](https://github.com/trivedi-aman/misheard).
