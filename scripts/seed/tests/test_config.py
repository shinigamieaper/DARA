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


def test_caps_match_spec():
    assert config.CAPS == {
        "igbo_api":   {"total": 1000},
        "yorulect":   {"per_dialect": 250},
        "voa_ner":    {"total": 750},
        "naijasenti": {"yor": 500, "ibo": 500, "hau": 750},
    }


def test_source_tags_match_spec():
    assert config.SOURCE_TAGS == {
        "igbo_api":   "IgboAPI",
        "yorulect":   "YorùLect",
        "voa_ner":    "VOA Hausa",
        "naijasenti": "NaijaSenti",
    }


def test_dataset_order():
    assert config.DATASET_ORDER == ["igbo_api", "yorulect", "voa_ner", "naijasenti"]
