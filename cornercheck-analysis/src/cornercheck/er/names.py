"""The shared name-normalization vocabulary, defined ONCE.

The whole-repo audit found three private normalizers with drifting semantics across
banding, live scoring, and seeding. They live here now, with their distinct purposes
stated, so query-time matching and seed-time keying can never diverge silently.
"""

import unicodedata


def norm(name: str) -> str:
    """Whitespace/case normalization for SCORING and same-name detection. Deliberately
    preserves diacritics and punctuation: 'Peña' and 'Pena' are different STRINGS for
    similarity purposes (the scorer handles near-matches; the bander demotes ties)."""
    return " ".join(name.lower().split())


def fold(name: str) -> str:
    """Punctuation- and diacritic-insensitive KEY for seed-time case attachment:
    'T.J. Dillashaw' == 'TJ Dillashaw', 'Julianna Peña' == 'Julianna Pena'.
    Deliberately NOT fuzzy: 'Ryan Garcia' and 'Ryan Gracie' are different people and
    must stay distinct."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return "".join(ch for ch in s.casefold() if ch.isalnum())
