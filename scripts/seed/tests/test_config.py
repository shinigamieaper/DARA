import config


def test_dialect_map_matches_railway_seed():
    assert config.DIALECT_MAP == {
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


def test_rng_seed_is_42():
    assert config.RNG_SEED == 42


def test_caps_are_uncapped():
    # Phase 1 corpus expansion (2026-07-06): all caps are None, meaning each
    # loader keeps every verified, de-duplicated row instead of sampling down.
    assert config.CAPS == {
        "igbo_api":    {"total": None},
        "yorulect":    {"per_dialect": None},
        "voa_ner":     {"total": None},
        "naijasenti":  {"yor": None, "ibo": None, "hau": None},
        "yoruba_dict": {"total": None},
        "hausa_dict":  {"total": None},
        "dialect_seeds": {"total": None},
        "ehugbo_nt": {"total": None},
    }


def test_source_tags_match_spec():
    assert config.SOURCE_TAGS == {
        "igbo_api":    "IgboAPI",
        "yorulect":    "YorùLect",
        "voa_ner":     "VOA Hausa",
        "naijasenti":  "NaijaSenti",
        "yoruba_dict": "Wiktionary Yoruba",
        "hausa_dict":  "Wiktionary Hausa",
        "dialect_seeds": "Dialect Seed",
        "ehugbo_nt": "Ehugbo NT",
    }


def test_dataset_order():
    assert config.DATASET_ORDER == [
        "igbo_api", "yorulect", "voa_ner", "naijasenti",
        "yoruba_dict", "hausa_dict", "dialect_seeds", "ehugbo_nt",
    ]
