import pytest

from indic_phonetic import plain, script_of, to_roman


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


# ---- known gaps, tracked in PLAN.md; remove xfail when fixed -----------------

@pytest.mark.xfail(reason="anusvara before ह should be 'ng' (PLAN.md 1.1)", strict=True)
def test_singh():
    assert to_roman("सिंह") == "singh"


@pytest.mark.xfail(reason="ज्ञ is spoken gy (Hindi) / dny (Marathi) (PLAN.md 1.2)", strict=True)
def test_gya():
    assert to_roman("ज्ञान") == "gyaan"
