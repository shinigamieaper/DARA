import json

from loaders import wiktionary


def _line(**kwargs) -> str:
    return json.dumps(kwargs, ensure_ascii=False)


def test_parse_jsonl_skips_blank_lines():
    text = _line(word="ile", pos="noun") + "\n\n" + _line(word="ojo", pos="noun") + "\n"
    entries = wiktionary.parse_jsonl(text)
    assert len(entries) == 2
    assert entries[0]["word"] == "ile"
    assert entries[1]["word"] == "ojo"


def test_build_rows_groups_same_word_across_multiple_pos_lines():
    raw = [
        {
            "word": "ile", "pos": "noun", "lang_code": "yo",
            "senses": [{"glosses": ["house"], "examples": [{"text": "Ile mi dara."}]}],
            "sounds": [{"ipa": "/ile/"}],
        },
        {
            "word": "ile", "pos": "verb", "lang_code": "yo",
            "senses": [{"glosses": ["to pound"]}],
        },
    ]
    rows = wiktionary.build_rows(raw, dialect_id=1, source_tag="Wiktionary Yoruba")
    assert len(rows) == 1
    headword, pos, dialect_id, jsonb = rows[0]
    assert headword == "ile"
    assert pos == "noun"  # first line's pos
    assert dialect_id == 1
    assert jsonb["source"] == "Wiktionary Yoruba"
    assert jsonb["license"] == "CC BY-SA"
    assert jsonb["attribution"] == "Wiktionary via kaikki.org"
    assert jsonb["definitions"] == ["house", "to pound"]
    assert jsonb["parts_of_speech"] == ["noun", "verb"]
    assert jsonb["ipa"] == ["/ile/"]
    assert jsonb["examples"] == ["Ile mi dara."]
    assert jsonb["dialect_assigned_default"] is True


def test_build_rows_drops_word_with_no_gloss():
    raw = [
        {"word": "ojo", "pos": "noun", "lang_code": "yo", "senses": [{"glosses": []}]},
    ]
    rows = wiktionary.build_rows(raw, dialect_id=1, source_tag="Wiktionary Yoruba")
    assert rows == []


def test_build_rows_character_pos_with_no_gloss_does_not_survive():
    raw = [
        {"word": ".", "pos": "punctuation", "lang_code": "yo", "senses": [{"glosses": []}]},
        {"word": "a", "pos": "character", "lang_code": "yo", "senses": []},
    ]
    rows = wiktionary.build_rows(raw, dialect_id=1, source_tag="Wiktionary Yoruba")
    assert rows == []


def test_build_rows_keeps_character_pos_if_it_has_a_gloss():
    raw = [
        {
            "word": "a", "pos": "character", "lang_code": "yo",
            "senses": [{"glosses": ["first letter of the Yoruba alphabet"]}],
        },
    ]
    rows = wiktionary.build_rows(raw, dialect_id=1, source_tag="Wiktionary Yoruba")
    assert len(rows) == 1
    assert rows[0][0] == "a"


def test_build_rows_dedups_one_row_per_word():
    raw = [
        {"word": "ile", "pos": "noun", "senses": [{"glosses": ["house"]}]},
        {"word": "ile", "pos": "noun", "senses": [{"glosses": ["home"]}]},
    ]
    rows = wiktionary.build_rows(raw, dialect_id=1, source_tag="Wiktionary Yoruba")
    assert len(rows) == 1
    assert rows[0][3]["definitions"] == ["house", "home"]


def test_build_rows_ignores_entries_missing_word():
    raw = [{"pos": "noun", "senses": [{"glosses": ["nothing"]}]}]
    rows = wiktionary.build_rows(raw, dialect_id=1, source_tag="Wiktionary Yoruba")
    assert rows == []
