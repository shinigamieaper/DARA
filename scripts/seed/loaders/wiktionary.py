"""Shared parsing helpers for kaikki.org Wiktextract JSONL dictionaries.

Both `yoruba_dict.py` and `hausa_dict.py` are thin wrappers around this
module: they differ only in dialect_id, SOURCE_TAG, and download URL.
"""
import json


def parse_jsonl(text: str) -> list[dict]:
    """Parse a kaikki JSONL blob (one JSON object per line) into a list of dicts.

    Blank lines are skipped.
    """
    entries: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(json.loads(line))
    return entries


def build_rows(
    raw_entries: list[dict], dialect_id: int, source_tag: str
) -> list[tuple[str, str, int, dict]]:
    """Group kaikki entries by `word` and produce standard 4-tuple rows.

    A word may appear on multiple JSONL lines (one per part of speech).
    All lines for a word are merged into a single output row. Words with
    zero non-empty glosses across all their lines are dropped entirely.
    """
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for entry in raw_entries:
        word = entry.get("word")
        if not word:
            continue
        if word not in groups:
            groups[word] = []
            order.append(word)
        groups[word].append(entry)

    rows: list[tuple[str, str, int, dict]] = []
    for word in order:
        lines = groups[word]

        definitions: list[str] = []
        parts_of_speech: list[str] = []
        ipa: list[str] = []
        examples: list[str] = []

        for line in lines:
            pos = line.get("pos")
            if pos and pos not in parts_of_speech:
                parts_of_speech.append(pos)

            for sense in line.get("senses") or []:
                for gloss in sense.get("glosses") or []:
                    if gloss and gloss.strip():
                        definitions.append(gloss)
                for example in sense.get("examples") or []:
                    text = example.get("text")
                    if text and text.strip():
                        examples.append(text)

            for sound in line.get("sounds") or []:
                sound_ipa = sound.get("ipa")
                if sound_ipa and sound_ipa.strip():
                    ipa.append(sound_ipa)

        if not definitions:
            # No word survives without at least one non-empty gloss. This
            # also enforces the spec's non-lexical-pos rule: a line whose
            # pos is "character"/"punctuation"/"symbol" and carries no
            # gloss contributes nothing here, so it can't keep a word alive
            # on its own.
            continue

        pos = lines[0].get("pos") or "unknown"
        jsonb = {
            "source": source_tag,
            "license": "CC BY-SA",
            "attribution": "Wiktionary via kaikki.org",
            "definitions": definitions,
            "parts_of_speech": parts_of_speech,
            "ipa": ipa,
            "examples": examples,
            "dialect_assigned_default": True,
        }
        rows.append((word, pos, dialect_id, jsonb))

    return rows
