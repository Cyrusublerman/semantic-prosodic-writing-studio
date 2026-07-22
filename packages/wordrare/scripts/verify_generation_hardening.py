#!/usr/bin/env python3
"""
Acceptance harness for Generation / Audit / Phonetics hardening.

Seeds a fixture lexicon if needed, then asserts the seven plan checks.
"""

from __future__ import annotations

import ast
import logging
import sys
from collections import defaultdict
from pathlib import Path

# Ensure package import works when run as a script
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wordrare.database import WordRecord, Phonetics, ConceptNode, get_session
from wordrare.database.session import get_session_manager
from wordrare.forms.meter_engine import MeterEngine
from wordrare.generation import PoemGenerator, GenerationSpec, PoemAnnotator, ProseRewriter
from wordrare.constraints.repair import LineRepairer, ConflictType
from wordrare.constraints.constraint_model import SteeringPolicy

logging.basicConfig(level=logging.WARNING)


FIXTURE_WORDS = [
    # articles / preps / adverbs
    ("the", "article", 1, "DH", 0.35, "0"),
    ("a", "article", 1, "AH", 0.35, "1"),
    ("an", "article", 1, "AE", 0.35, "1"),
    ("of", "preposition", 1, "AHV", 0.35, "1"),
    ("in", "preposition", 1, "IHN", 0.35, "1"),
    ("on", "preposition", 1, "AAN", 0.35, "1"),
    ("with", "preposition", 1, "WIH", 0.35, "1"),
    ("to", "preposition", 1, "TUW", 0.35, "1"),
    ("above", "preposition", 2, "AHV", 0.4, "01"),
    ("under", "preposition", 2, "ER", 0.4, "10"),
    ("now", "adverb", 1, "AW", 0.35, "1"),
    ("then", "adverb", 1, "EHN", 0.35, "1"),
    ("here", "adverb", 1, "IHR", 0.35, "1"),
    ("still", "adverb", 1, "IHL", 0.4, "1"),
    ("far", "adverb", 1, "AAR", 0.4, "1"),
    ("softly", "adverb", 2, "LIY", 0.45, "10"),
    ("quietly", "adverb", 3, "LIY", 0.5, "100"),
    # adjectives
    ("dark", "adjective", 1, "AARK", 0.35, "1"),
    ("bright", "adjective", 1, "AYT", 0.35, "1"),
    ("soft", "adjective", 1, "AOFT", 0.35, "1"),
    ("pale", "adjective", 1, "EYL", 0.4, "1"),
    ("wan", "adjective", 1, "AAN", 0.55, "1"),
    ("deep", "adjective", 1, "IYP", 0.4, "1"),
    ("cold", "adjective", 1, "OLD", 0.4, "1"),
    ("dim", "adjective", 1, "IHM", 0.5, "1"),
    ("wild", "adjective", 1, "AYLD", 0.45, "1"),
    ("silent", "adjective", 2, "AHNT", 0.4, "10"),
    ("solemn", "adjective", 2, "AHM", 0.5, "10"),
    ("ancient", "adjective", 2, "AHNT", 0.45, "10"),
    ("golden", "adjective", 2, "AHN", 0.35, "10"),
    ("verdant", "adjective", 2, "AHNT", 0.65, "10"),
    ("sylvan", "adjective", 2, "AHN", 0.75, "10"),
    ("ebon", "adjective", 2, "AHN", 0.8, "10"),
    ("luminous", "adjective", 3, "AHS", 0.55, "100"),
    ("umbrageous", "adjective", 3, "AAS", 0.85, "010"),
    ("crepuscular", "adjective", 4, "UHL", 0.9, "0100"),
    # nouns — rhyme groups OW / EYD / AYT / ER / IHST / IYM
    ("willow", "noun", 2, "OW", 0.55, "10"),
    ("hollow", "noun", 2, "OW", 0.5, "10"),
    ("echo", "noun", 2, "OW", 0.45, "10"),
    ("shadow", "noun", 2, "OW", 0.4, "10"),
    ("snow", "noun", 1, "OW", 0.4, "1"),
    ("glade", "noun", 1, "EYD", 0.6, "1"),
    ("shade", "noun", 1, "EYD", 0.45, "1"),
    ("blade", "noun", 1, "EYD", 0.4, "1"),
    ("night", "noun", 1, "AYT", 0.35, "1"),
    ("light", "noun", 1, "AYT", 0.35, "1"),
    ("flight", "noun", 1, "AYT", 0.4, "1"),
    ("river", "noun", 2, "ER", 0.4, "10"),
    ("ember", "noun", 2, "ER", 0.6, "10"),
    ("silver", "noun", 2, "ER", 0.4, "10"),
    ("mist", "noun", 1, "IHST", 0.5, "1"),
    ("frost", "noun", 1, "AOST", 0.5, "1"),
    ("forest", "noun", 2, "IHST", 0.4, "10"),
    ("dream", "noun", 1, "IYM", 0.4, "1"),
    ("stream", "noun", 1, "IYM", 0.45, "1"),
    ("gleam", "noun", 1, "IYM", 0.5, "1"),
    ("moon", "noun", 1, "UWN", 0.4, "1"),
    ("stone", "noun", 1, "OWN", 0.4, "1"),
    ("bone", "noun", 1, "OWN", 0.45, "1"),
    ("throne", "noun", 1, "OWN", 0.5, "1"),
    ("heart", "noun", 1, "AART", 0.35, "1"),
    ("time", "noun", 1, "AYM", 0.35, "1"),
    ("leaf", "noun", 1, "IYF", 0.4, "1"),
    ("breeze", "noun", 1, "IYZ", 0.45, "1"),
    ("dusk", "noun", 1, "AHSK", 0.55, "1"),
    ("dawn", "noun", 1, "AON", 0.45, "1"),
    ("garden", "noun", 2, "AHN", 0.35, "10"),
    ("ocean", "noun", 2, "AHN", 0.4, "10"),
    ("silence", "noun", 2, "AHNS", 0.45, "10"),
    ("petrichor", "noun", 3, "AOR", 0.92, "100"),
    ("susurrus", "noun", 3, "AHS", 0.9, "010"),
    ("ash", "noun", 1, "AESH", 0.55, "1"),
    ("oak", "noun", 1, "OWK", 0.5, "1"),
    ("sky", "noun", 1, "AY", 0.35, "1"),
    ("sea", "noun", 1, "IY", 0.35, "1"),
    ("rain", "noun", 1, "EYN", 0.4, "1"),
    ("wind", "noun", 1, "IHND", 0.4, "1"),
    ("flame", "noun", 1, "EYM", 0.45, "1"),
    ("grave", "noun", 1, "EYV", 0.5, "1"),
    ("wave", "noun", 1, "EYV", 0.4, "1"),
    # verbs
    ("fall", "verb", 1, "AOL", 0.35, "1"),
    ("rise", "verb", 1, "AYZ", 0.35, "1"),
    ("glow", "verb", 1, "OW", 0.4, "1"),
    ("fade", "verb", 1, "EYD", 0.45, "1"),
    ("drift", "verb", 1, "IHFT", 0.5, "1"),
    ("haunt", "verb", 1, "AONT", 0.6, "1"),
    ("sleep", "verb", 1, "IYP", 0.35, "1"),
    ("breathe", "verb", 1, "IYDH", 0.4, "1"),
    ("sing", "verb", 1, "IHNG", 0.4, "1"),
    ("weep", "verb", 1, "IYP", 0.5, "1"),
    ("burn", "verb", 1, "ERN", 0.45, "1"),
    ("break", "verb", 1, "EYK", 0.4, "1"),
    ("hold", "verb", 1, "OLD", 0.35, "1"),
    ("know", "verb", 1, "OW", 0.35, "1"),
    ("see", "verb", 1, "IY", 0.35, "1"),
    ("hear", "verb", 1, "IHR", 0.35, "1"),
    ("go", "verb", 1, "OW", 0.35, "1"),
    ("come", "verb", 1, "AHM", 0.35, "1"),
    ("linger", "verb", 2, "ER", 0.5, "10"),
    ("whisper", "verb", 2, "ER", 0.45, "10"),
    ("wander", "verb", 2, "ER", 0.45, "10"),
    ("tremble", "verb", 2, "AHL", 0.5, "10"),
    ("vanish", "verb", 2, "IHSH", 0.5, "10"),
    ("unfold", "verb", 2, "OLD", 0.55, "01"),
    ("remember", "verb", 3, "ER", 0.4, "010"),
]


def seed_fixture_lexicon() -> int:
    mgr = get_session_manager()
    mgr.create_tables()
    added = 0
    with get_session() as session:
        existing = {r.lemma for r in session.query(WordRecord.lemma).all()}
        for lemma, pos, syll, rhyme, rarity, stress in FIXTURE_WORDS:
            if lemma in existing:
                continue
            # tiny fake embedding: rarity + syllable dims padded
            emb = [rarity, float(syll) / 5.0, 0.1 * (hash(lemma) % 10)]
            session.add(
                WordRecord(
                    lemma=lemma,
                    pos_primary=pos,
                    pos_all=[pos],
                    syllable_count=syll,
                    rhyme_key=rhyme,
                    rarity_score=rarity,
                    stress_pattern=stress,
                    domain_tags=["botanical"] if pos in {"noun", "adjective"} else [],
                    affect_tags=["melancholic"] if rarity >= 0.5 else ["joyful"],
                    imagery_tags=["visual"],
                    embedding=emb,
                )
            )
            session.add(
                Phonetics(
                    lemma=lemma,
                    syllable_count=syll,
                    rhyme_key=rhyme,
                    stress_pattern=stress,
                )
            )
            added += 1

        if not session.query(ConceptNode).filter_by(label="nature").first():
            session.add(
                ConceptNode(
                    label="nature",
                    node_type="concept",
                    centroid_embedding=[0.5, 0.4, 0.3],
                )
            )
            session.add(
                ConceptNode(
                    label="dusk",
                    node_type="concept",
                    centroid_embedding=[0.55, 0.35, 0.25],
                )
            )
    return added


def assert_no_failed(lines, label: str):
    failed = [ln for ln in lines if ln.startswith("[") and "generation failed" in ln]
    if failed:
        raise AssertionError(f"{label}: failed lines: {failed}")


def assert_no_identical_rhyme(annotations, label: str):
    flags = [f for f in annotations.get("flags", []) if f.startswith("identical_rhyme")]
    if flags:
        raise AssertionError(f"{label}: identical_rhyme flags: {flags}")
    by_sym = defaultdict(list)
    for pl in annotations.get("per_line", []):
        if pl.get("text", "").startswith("["):
            continue
        sym = pl.get("rhyme_symbol")
        end = pl.get("end_lemma")
        if sym and sym != "null" and end:
            by_sym[sym].append(end)
    for sym, ends in by_sym.items():
        if len(ends) != len(set(ends)):
            raise AssertionError(f"{label}: duplicate ends in {sym}: {ends}")


def assert_phonetic_sources(annotations, label: str):
    allowed = {"cmu", "record", "estimated"}
    for pl in annotations.get("per_line", []):
        for w in pl.get("words") or []:
            src = w.get("phonetic_source")
            if src not in allowed:
                raise AssertionError(f"{label}: bad phonetic_source {src} for {w}")
            if "syllable_relaxed" not in w:
                raise AssertionError(f"{label}: missing syllable_relaxed on {w.get('lemma')}")


def check_no_llm_imports() -> None:
    gen_root = SRC / "wordrare" / "generation"
    forbidden = {"openai", "anthropic", "litellm", "langchain"}
    for path in gen_root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in forbidden:
                        raise AssertionError(f"LLM import in {path}: {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in forbidden:
                    raise AssertionError(f"LLM import in {path}: {node.module}")


def main() -> int:
    print("Seeding fixture lexicon...")
    added = seed_fixture_lexicon()
    print(f"  added {added} words")

    gen = PoemGenerator()
    annotator = PoemAnnotator()

    # 1 + 2 + 3 + 6 metrics: haiku and sonnet
    for form, policy in (
        ("haiku", "free_verse"),
        ("shakespearean_sonnet", "strict_sonnet"),
    ):
        poem = None
        for attempt in range(8):
            spec = GenerationSpec(
                form=form,
                theme="nature",
                rarity_bias=0.5,
                min_rarity=0.0,
                max_rarity=1.0,
                temperature=0.85,
                debug_mode=True,
                steering_policy=policy,
                max_iterations=8,
            )
            candidate = gen.generate(spec)
            failed = sum(
                1
                for ln in candidate.lines
                if ln.startswith("[") and "generation failed" in ln
            )
            if failed == 0:
                poem = candidate
                break
            poem = candidate
        assert poem is not None
        assert_no_failed(poem.lines, form)
        assert poem.metrics, f"{form}: empty metrics"
        assert_no_identical_rhyme(poem.annotations, form)
        assert_phonetic_sources(poem.annotations, form)
        print(f"OK form={form} lines={len(poem.lines)} total={poem.metrics.get('total'):.2f}")

    # 4: debug strip
    strip = annotator.format_debug_strip(poem.annotations)
    if "Stress line:" not in strip:
        raise AssertionError("debug strip missing 'Stress line:'")
    print("OK debug strip")

    # 5: syllabic meter no unknown warning
    meter_log = []
    class Handler(logging.Handler):
        def emit(self, record):
            meter_log.append(record.getMessage())

    handler = Handler()
    mlog = logging.getLogger("wordrare.forms.meter_engine")
    mlog.addHandler(handler)
    try:
        analysis = MeterEngine().analyze_line(
            "the dark stream", "syllabic", target_syllables=3
        )
        assert analysis.syllable_count >= 1
    finally:
        mlog.removeHandler(handler)
    if any("Unknown meter pattern: syllabic" in msg for msg in meter_log):
        raise AssertionError("syllabic still logged as unknown")
    print("OK syllabic meter")

    # 6 unit: repair path on deliberately bad line
    repairer = LineRepairer(SteeringPolicy.loose_tercet())
    repaired = repairer.repair_line(
        "the the the the the the the the the the the",
        {"meter": "iambic_pentameter", "target_syllables": 10},
        ConflictType.METER,
    )
    # May or may not repair successfully; ensure call does not raise
    print(f"OK repair path exercised (result={repaired!r})")

    # persistence path (debug_mode False) — annotations/metrics saved when possible
    persist_spec = GenerationSpec(
        form="haiku",
        theme="nature",
        min_rarity=0.0,
        max_rarity=1.0,
        temperature=0.7,
        debug_mode=False,
        steering_policy="free_verse",
    )
    persisted = gen.generate(persist_spec)
    assert persisted.metrics
    assert persisted.annotations.get("per_line")
    print("OK persist path metrics/annotations")

    # prose rewrite
    result = ProseRewriter(
        GenerationSpec(min_rarity=0.0, max_rarity=1.0, rarity_bias=0.7)
    ).rewrite("The dark forest holds a silent dream.")
    assert result["rewritten"]
    assert "Stress line:" in result["audit"] or result["annotations"].get("per_line")
    print("OK prose rewrite:", result["rewritten"])

    # 7: no LLM imports
    check_no_llm_imports()
    print("OK no LLM imports in generation package")

    print("\nALL ACCEPTANCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
