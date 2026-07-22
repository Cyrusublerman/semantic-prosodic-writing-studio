"""Seed WordRecord/Phonetics from CMU via pronouncing (no Phrontistery scrape)."""

from __future__ import annotations

import logging
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pronouncing

from wordrare.database import Phonetics, WordRecord, get_session
from wordrare.database.session import get_session_manager
from wordrare.phonetics.ipa_processor import IPAProcessor

logger = logging.getLogger(__name__)

ARTICLES = ["the", "a", "an"]
PREPS = [
    "in", "on", "at", "by", "to", "of", "for", "with", "from", "into",
    "over", "under", "above", "below", "through", "across", "between",
    "among", "against", "without", "within", "upon", "about", "after",
    "before", "behind", "beside", "near", "along", "around", "during",
]
CONJS = ["and", "or", "but", "nor", "yet", "so", "as", "if", "when", "while", "than"]
ADVERBS = [
    "softly", "slowly", "quietly", "deeply", "gently", "still", "now", "then",
    "here", "there", "never", "always", "often", "seldom", "again", "away",
    "alone", "apart", "aside", "afar", "aboard", "above", "below",
]
# High-yield open-class seeds to boost rhyme cohorts
SEED_OPEN = """
river stone flame dream night light shadow hollow mist forest garden ocean
breeze willow ember grave mist wave mist oak leaf root wind sky dew bloom
moss grave dust veil bone tomb mourn hour dawn dusk tide year age moment
silence echo memory sorrow joy love time death nature water fire earth air
mountain valley meadow brook stream rain snow frost thunder lightning star
moon sun cloud bird wing song heart soul mind eye hand path road gate wall
door window home field tree flower grass sand shore wave crest foam pearl
crystal amber silver gold iron steel glass mirror candle lantern bell drum
voice word name breath spirit ghost angel devil king queen child mother
father brother sister friend stranger traveler pilgrim hermit poet singer
hunter fisher sailor soldier farmer builder painter dancer dreamer sleeper
whisper murmur linger tremble vanish remember forget awaken sleep walk run
fall rise turn burn shine fade grow die live love hate fear hope seek find
hold keep lose give take make see hear feel know think speak sing dance
cry laugh smile weep bleed heal break mend bind free bind cut tear sew
dark bright solemn ancient silent verdant hollow crepuscular luminous
petrichor susurrus sylvan ember willow shadow forest river ocean garden
gleam stream mist wave grave mist hollow oak stone flame dream night
""".split()

# Suffix heuristics for POS when not in closed lists
_ADJ_SFX = ("ous", "ful", "less", "ish", "ive", "al", "ic", "able", "ible", "ent", "ant", "ary", "ory", "y")
_ADV_SFX = ("ly",)
_VERB_SFX = ("ing", "ed", "ize", "ise", "ate", "ify", "en")


def guess_pos(lemma: str) -> str:
    w = lemma.lower()
    if w in ARTICLES:
        return "article"
    if w in PREPS:
        return "preposition"
    if w in CONJS:
        return "conjunction"
    if w in ADVERBS or w.endswith(_ADV_SFX):
        return "adverb"
    if any(w.endswith(s) for s in _ADJ_SFX):
        return "adjective"
    if any(w.endswith(s) for s in _VERB_SFX) and len(w) > 4:
        return "verb"
    # default open class split
    if random.random() < 0.25:
        return "verb"
    if random.random() < 0.35:
        return "adjective"
    return "noun"


def rarity_for(lemma: str, syl: int) -> float:
    # Longer / rarer orthography → higher rarity; clamp
    base = min(0.95, 0.25 + 0.08 * max(0, len(lemma) - 4) + 0.05 * max(0, syl - 1))
    return round(base, 3)


def iter_cmu_lemmas(limit: int) -> list[str]:
    words = set()
    # Closed class always
    for w in ARTICLES + PREPS + CONJS + ADVERBS + SEED_OPEN:
        words.add(w.lower())
    # Sample from CMU
    try:
        cmu = pronouncing.cmudict.dict()
        keys = sorted(cmu.keys())
    except Exception:
        keys = []
    # Prefer alphabetic single tokens, no apostrophe variants first
    clean = [
        k for k in keys
        if re.fullmatch(r"[a-z]+", k) and 2 <= len(k) <= 12
    ]
    random.seed(42)
    random.shuffle(clean)
    for k in clean:
        words.add(k)
        if len(words) >= limit:
            break
    return sorted(words)[:limit]


def upsert_lemma(lemma: str, proc: IPAProcessor, pos: str | None = None) -> bool:
    data = proc.process_word(lemma)
    if not data:
        return False
    pos = pos or guess_pos(lemma)
    syl = int(data.get("syllable_count") or 1)
    ek = data.get("end_keys") or {}
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
            wr.pos_primary = wr.pos_primary or pos
            wr.syllable_count = syl
            wr.stress_pattern = data.get("stress_pattern")
            wr.rhyme_key = data.get("rhyme_key")
            wr.ipa_us = data.get("ipa_us_cmu")
            wr.syllable_keys = data.get("syllable_keys")
            wr.end_key_2 = ek.get("2")
            wr.end_key_3 = ek.get("3")
            if wr.rarity_score is None:
                wr.rarity_score = rarity_for(lemma, syl)
        else:
            session.add(
                WordRecord(
                    lemma=lemma,
                    pos_primary=pos,
                    pos_all=[pos],
                    ipa_us=data.get("ipa_us_cmu"),
                    stress_pattern=data.get("stress_pattern"),
                    syllable_count=syl,
                    rhyme_key=data.get("rhyme_key"),
                    syllable_keys=data.get("syllable_keys"),
                    end_key_2=ek.get("2"),
                    end_key_3=ek.get("3"),
                    rarity_score=rarity_for(lemma, syl),
                    imagery_tags=["visual"] if pos in ("noun", "adjective") else [],
                    domain_tags=["nature"] if lemma in set(SEED_OPEN) else [],
                )
            )
    return True


def seed(limit: int = 2500) -> dict:
    get_session_manager().ensure_schema()
    proc = IPAProcessor()
    lemmas = iter_cmu_lemmas(limit)
    # Force closed-class POS
    forced = {}
    for w in ARTICLES:
        forced[w] = "article"
    for w in PREPS:
        forced[w] = "preposition"
    for w in CONJS:
        forced[w] = "conjunction"
    for w in ADVERBS:
        forced[w] = "adverb"

    ok = 0
    for lemma in lemmas:
        if upsert_lemma(lemma, proc, forced.get(lemma)):
            ok += 1
        if ok % 200 == 0:
            logger.info("seeded %s...", ok)

    # Stats
    with get_session() as session:
        total = session.query(WordRecord).count()
        by_key = defaultdict(int)
        noun_keys = defaultdict(int)
        for lemma, pos, rk in session.query(
            WordRecord.lemma, WordRecord.pos_primary, WordRecord.rhyme_key
        ).all():
            if rk:
                by_key[rk] += 1
                if pos == "noun":
                    noun_keys[rk] += 1
        multi = sum(1 for k, n in by_key.items() if n >= 2)
        multi_noun = sum(1 for k, n in noun_keys.items() if n >= 2)
        closed = {
            p: session.query(WordRecord).filter_by(pos_primary=p).count()
            for p in ("article", "preposition", "conjunction", "adverb", "noun", "verb", "adjective")
        }
    stats = {
        "upserted": ok,
        "total": total,
        "multi_rhyme_keys": multi,
        "multi_noun_keys": multi_noun,
        "pos_counts": closed,
    }
    logger.info("seed complete: %s", stats)
    return stats


def main():
    import argparse

    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=2500)
    args = p.parse_args()
    print(seed(args.limit))


if __name__ == "__main__":
    main()
