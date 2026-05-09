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

CAPS = {
    "igbo_api":   {"total": 1000},
    "yorulect":   {"per_dialect": 250},
    "voa_ner":    {"total": 750},
    "naijasenti": {"yor": 500, "ibo": 500, "hau": 750},
}

SOURCE_TAGS = {
    "igbo_api":   "IgboAPI",
    "yorulect":   "YorùLect",
    "voa_ner":    "VOA Hausa",
    "naijasenti": "NaijaSenti",
}

DATASET_ORDER = ["igbo_api", "yorulect", "voa_ner", "naijasenti"]
