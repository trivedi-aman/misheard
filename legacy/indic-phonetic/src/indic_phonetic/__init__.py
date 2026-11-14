"""indic-phonetic has been renamed to misheard. Use `import misheard`."""
import warnings

warnings.warn(
    "indic-phonetic has been renamed to misheard: pip install misheard, then import misheard",
    DeprecationWarning,
    stacklevel=2,
)

from misheard import *  # noqa: E402,F401,F403
from misheard import __all__, __version__  # noqa: E402,F401
