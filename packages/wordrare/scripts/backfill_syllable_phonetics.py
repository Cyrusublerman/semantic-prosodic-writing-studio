"""Backfill syllable_phones / keys on Phonetics and WordRecord."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import text

from wordrare.database import Phonetics, WordRecord, get_session
from wordrare.database.session import get_session_manager
from wordrare.phonetics.ipa_processor import IPAProcessor

logger = logging.getLogger(__name__)

PHON_COLS = [
    ("syllable_phones", "JSON"),
    ("syllable_keys", "JSON"),
    ("assonance_keys", "JSON"),
    ("end_keys", "JSON"),
]
WORD_COLS = [
    ("syllable_keys", "JSON"),
    ("end_key_2", "VARCHAR(256)"),
    ("end_key_3", "VARCHAR(256)"),
]


def backfill(limit: int | None = None):
    get_session_manager().ensure_schema()
    proc = IPAProcessor()
    with get_session() as session:
        q = session.query(WordRecord.lemma)
        if limit:
            q = q.limit(limit)
        lemmas = [row[0] for row in q.all()]

    updated = 0
    for lemma in lemmas:
        data = proc.process_word(lemma)
        if not data:
            continue
        phon_payload = {
            k: data[k]
            for k in (
                "lemma",
                "ipa_us_cmu",
                "ipa_dict_uk",
                "ipa_dict_us",
                "stress_pattern",
                "syllable_count",
                "rhyme_key",
                "onset",
                "nucleus",
                "coda",
                "syllable_phones",
                "syllable_keys",
                "assonance_keys",
                "end_keys",
            )
            if k in data
        }
        ek = data.get("end_keys") or {}
        with get_session() as session:
            phon = session.query(Phonetics).filter_by(lemma=lemma).first()
            if phon:
                for k, v in phon_payload.items():
                    if k != "lemma":
                        setattr(phon, k, v)
            else:
                session.add(Phonetics(**phon_payload))
            wr = session.query(WordRecord).filter_by(lemma=lemma).first()
            if wr:
                wr.syllable_keys = data.get("syllable_keys")
                wr.end_key_2 = ek.get("2")
                wr.end_key_3 = ek.get("3")
                if data.get("rhyme_key"):
                    wr.rhyme_key = data["rhyme_key"]
                if data.get("stress_pattern"):
                    wr.stress_pattern = data["stress_pattern"]
                if data.get("syllable_count"):
                    wr.syllable_count = data["syllable_count"]
        updated += 1
    logger.info("Backfilled %s records", updated)
    return updated


def main():
    import argparse

    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    args = p.parse_args()
    backfill(args.limit)


if __name__ == "__main__":
    main()
