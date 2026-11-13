"""
indic-phonetic: match Indian names and places by how they sound.

    >>> from indic_phonetic import distance, best_match, to_roman
    >>> to_roman("बाड़मेर")
    'baaṛmer'
    >>> distance("Barmer", "बाड़मेर") < distance("Mohan", "Rohan")
    True
"""
from .distance import distance, sound_length, tokenize
from .match import Match, best_match
from .translit import plain, script_of, to_roman

__all__ = ["distance", "best_match", "Match", "to_roman", "plain", "script_of", "tokenize", "sound_length"]
__version__ = "0.0.1"
