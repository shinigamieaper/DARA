"""Constants for the seed pipeline. Single source of truth for dialect IDs,
sampling seed, per-dataset caps, and source tags."""

DIALECT_MAP: dict[int, tuple[str, str]] = {
    1: ("Standard Yoruba", "Yoruba"),
    2: ("Ife", "Yoruba"),
    3: ("Ilaje", "Yoruba"),
    4: ("Ijebu", "Yoruba"),
    5: ("Central Igbo", "Igbo"),
    6: ("Ehugbo", "Igbo"),
    7: ("Enuani", "Igbo"),
    8: ("Standard Hausa", "Hausa"),
    9: ("Sokoto Hausa", "Hausa"),
}

RNG_SEED = 42

# Per-source volume caps. A value of None means "no cap": the loader keeps
# every verified, de-duplicated row from the raw data instead of sampling
# down. Phase 1 corpus expansion (2026-07-06) set all caps to None to load
# the full downloaded corpus (~60k rows). Numeric caps are still honoured
# when a caller passes one explicitly to a loader's transform().
CAPS = {
    "igbo_api":    {"total": None},
    "yorulect":    {"per_dialect": None},
    "voa_ner":     {"total": None},
    "naijasenti":  {"yor": None, "ibo": None, "hau": None},
    "yoruba_dict": {"total": None},
    "hausa_dict":  {"total": None},
    # dialect_seeds ships hand-curated CSVs; its transform ignores the cap.
    "dialect_seeds": {"total": None},
    "ehugbo_nt": {"total": None},
    "yoruba_proverbs": {"total": None},
    "hausa_proverbs": {"total": None},
    # content_seeds ships hand-curated CSVs; its transform ignores the cap.
    "content_seeds": {"total": None},
}

SOURCE_TAGS = {
    "igbo_api":    "IgboAPI",
    "yorulect":    "YorùLect",
    "voa_ner":     "VOA Hausa",
    "naijasenti":  "NaijaSenti",
    "yoruba_dict": "Wiktionary Yoruba",
    "hausa_dict":  "Wiktionary Hausa",
    "dialect_seeds": "Dialect Seed",
    "ehugbo_nt": "Ehugbo NT",
    "yoruba_proverbs": "Yoruba Proverbs",
    "hausa_proverbs": "Hausa Proverbs",
    "content_seeds": "Content Seed",
}

DATASET_ORDER = ["igbo_api", "yorulect", "voa_ner", "naijasenti",
                 "yoruba_dict", "hausa_dict", "dialect_seeds", "ehugbo_nt",
                 "yoruba_proverbs", "hausa_proverbs", "content_seeds"]
