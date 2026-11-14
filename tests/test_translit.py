import pytest

from misheard import UnsupportedScriptError, distance, plain, script_of, to_roman


@pytest.mark.parametrize("native, roman", [
    ("मोहन", "mohan"),                 # final schwa dropped
    ("बाड़मेर", "baaṛmer"),             # flap, medial schwa dropped
    ("मिश्र", "mishra"),                # schwa kept after a conjunct
    ("नरेंद्र", "narendra"),
    ("सरस्वती", "sarasvatee"),
    ("முருகன்", "murugan"),            # Tamil stop voiced between vowels
    ("கார்த்திக்", "kaarttik"),         # geminate and final stops stay voiceless
    ("மீனாட்சி", "meenaakshi"),        # Tamil ட்ச is ksh
    ("சரவணன்", "saravaṇan"),           # initial ச is s
    ("Rohan", "rohan"),                # Roman passes through, lowercased
])
def test_to_roman(native, roman):
    assert to_roman(native) == roman


def test_mixed_scripts_word_by_word():
    assert to_roman("Rohan वर्मा") == "rohan varmaa"


def test_plain_drops_retroflex_marks():
    assert plain("baaṛmer") == "baarmer"


def test_script_of():
    assert script_of("मोहन") == "devanagari"
    assert script_of("முருகன்") == "tamil"
    assert script_of("Mohan") == "latin"


@pytest.mark.parametrize("native, roman", [
    ("सिंह", "singh"),                 # anusvara before h is ng
    ("चंपा", "champaa"),               # ... before labials m
    ("संत", "sant"),                   # ... otherwise n
    ("हँसी", "hansee"),                # chandrabindu stays n
    ("ज्ञान", "gyaan"),                 # ज्ञ is gy
    ("यज्ञ", "yagya"),
    ("வெங்கடேஷ்", "vengaḍesh"),        # ங்க is ng, not ngg
    ("பஞ்சு", "panju"),                # ஞ்ச is nj, not njj
])
def test_nasals_and_conjuncts(native, roman):
    assert to_roman(native) == roman


def test_unsupported_script_fails_loudly():
    assert script_of("గణేష్") == "telugu"
    with pytest.raises(UnsupportedScriptError, match="Telugu"):
        to_roman("Ganesh గణేష్")
    with pytest.raises(ValueError):          # UnsupportedScriptError is a ValueError
        distance("Ganesh", "গণেশ")


def test_latin_with_marks_is_still_latin():
    assert to_roman("café") == "café"
    assert script_of("baaṛmer") == "latin"
