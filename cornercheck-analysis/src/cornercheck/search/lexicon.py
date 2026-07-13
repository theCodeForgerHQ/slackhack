"""Combat-sports injury lexicon. RTS keyword mode has NO synonyms (verified spike B),
so this is an explicit term list, not semantic matching."""

INJURY_TERMS = (
    "concussed",
    "concussion",
    "rocked",
    "wobbly",
    "dropped",
    "stitches",
    "ko'd",
    "knocked out",
    "dizzy",
    "headache",
    "not right",
    "hospital",
    "scan",
    "sat him",
    "sitting him",
    "didn't spar",
    "no spar",
    "head",
)


def mentions_injury(text: str) -> bool:
    low = text.lower()
    return any(term in low for term in INJURY_TERMS)
