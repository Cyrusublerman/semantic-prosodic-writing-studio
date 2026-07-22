#!/usr/bin/env python3
"""Pre-LLM acceptance harness — exit 1 on any FAIL. No soft asserts."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FAILS = 0


def check(section: str, name: str, ok: bool, detail: str = ""):
    global FAILS
    status = "PASS" if ok else "FAIL"
    if not ok:
        FAILS += 1
    extra = f" — {detail}" if detail else ""
    print(f"[{status}] {section}/{name}{extra}")


def _failed_line_count(poem) -> int:
    return sum(
        1 for ln in poem.lines if ln.startswith("[") and "generation failed" in ln
    )


def _has_paren_seed(text: str) -> bool:
    import re

    return bool(re.search(r"\([A-Za-z][A-Za-z\-']{1,24}\)", text))


def section_phon():
    print("\n=== PHON ===")
    from wordrare.phonetics.ipa_processor import IPAProcessor

    p = IPAProcessor()
    ok = hasattr(p, "syllabify_arpabet")
    check("PHON", "syllabify_exists", ok)
    if not ok:
        return
    n = p.get_cmu_phones("nation")
    s = p.get_cmu_phones("station")
    check("PHON", "cmu_nation_station", bool(n and s))
    if n and s:
        check(
            "PHON",
            "end2_nation_station",
            p.end_span_key(n, 2) == p.end_span_key(s, 2),
            f"{p.end_span_key(n,2)!r} vs {p.end_span_key(s,2)!r}",
        )
    cat = p.get_cmu_phones("cat")
    check("PHON", "extract_rhyme_key_cat", bool(cat and p.extract_rhyme_key(cat)))


def section_schema():
    print("\n=== SCHEMA ===")
    from sqlalchemy import create_engine, text
    from wordrare.database.session import SessionManager

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "old.db"
        eng = create_engine(f"sqlite:///{db}")
        with eng.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE phonetics (id INTEGER PRIMARY KEY, lemma VARCHAR(128))"
                )
            )
            conn.execute(
                text(
                    "CREATE TABLE word_record (id INTEGER PRIMARY KEY, lemma VARCHAR(128))"
                )
            )
            conn.commit()
        sm = SessionManager(database_url=f"sqlite:///{db}")
        sm.ensure_schema()
        with eng.connect() as conn:
            phon_cols = {
                r[1] for r in conn.execute(text("PRAGMA table_info(phonetics)")).fetchall()
            }
            word_cols = {
                r[1]
                for r in conn.execute(text("PRAGMA table_info(word_record)")).fetchall()
            }
        check(
            "SCHEMA",
            "ensure_schema_phon",
            "end_keys" in phon_cols and "syllable_keys" in phon_cols,
            str(sorted(phon_cols)),
        )
        check(
            "SCHEMA",
            "ensure_schema_word",
            "end_key_2" in word_cols and "end_key_3" in word_cols,
            str(sorted(word_cols)),
        )


def section_lexicon():
    print("\n=== LEXICON ===")
    from collections import defaultdict
    from wordrare.database import WordRecord, get_session

    with get_session() as session:
        n = session.query(WordRecord).count()
        rows = (
            session.query(WordRecord.rhyme_key, WordRecord.pos_primary)
            .filter(WordRecord.rhyme_key.isnot(None))
            .all()
        )
    by_key = defaultdict(list)
    for key, pos in rows:
        by_key[key].append(pos)
    multi = sum(1 for k, poss in by_key.items() if len(poss) >= 2)
    multi_noun = sum(
        1
        for k, poss in by_key.items()
        if sum(1 for p in poss if p == "noun") >= 2
    )
    check("LEXICON", "word_records_ge_2000", n >= 2000, f"n={n}")
    check("LEXICON", "multi_rhyme_keys", multi >= 100, f"multi={multi}")
    check("LEXICON", "multi_noun_keys", multi_noun >= 50, f"multi_noun={multi_noun}")


def section_forms():
    print("\n=== FORMS ===")
    from wordrare.forms import FormLibrary

    lib = FormLibrary()
    ids = set(lib.list_forms())
    check("FORMS", "haiku", "haiku" in ids)
    check("FORMS", "sonnet", "shakespearean_sonnet" in ids)
    for fid in (
        "positional_rhyme",
        "positional_coalesced",
        "sonnet_multisyl",
        "line_rhyme_couplet",
    ):
        check("FORMS", fid, fid in ids)
    pos = lib.get_form("positional_rhyme")
    if pos:
        rm = pos.get_rhyme_map() or {}
        check("FORMS", "positional_map_lens", len(rm.get("lines", [])) == 3)


def section_rhyme_plan():
    print("\n=== RHYME_PLAN ===")
    from wordrare.forms.rhyme_plan import compile_rhyme_plan
    from wordrare.generation import PoemGenerator, GenerationSpec

    plan = compile_rhyme_plan(
        line_symbols=["A", "B", "A", "B"],
        line_targets=[10, 10, 10, 10],
        rhyme_span={"mode": "end", "syllables": 1},
    )
    check("RHYME_PLAN", "legacy_slots", len(plan.slots) == 4)
    plan2 = compile_rhyme_plan(
        rhyme_map={
            "lines": ["AACABD", "ABACCAB", "ACCABBA"],
            "coalesce_runs": False,
        },
        line_targets=[6, 7, 7],
    )
    check("RHYME_PLAN", "map_slots", len(plan2.slots) == 20)
    plan3 = compile_rhyme_plan(
        rhyme_map={"lines": ["AAB"], "coalesce_runs": True},
        line_targets=[3],
    )
    check("RHYME_PLAN", "coalesce", len(plan3.slots) == 2)
    plan4 = compile_rhyme_plan(
        rhyme_spans=[{"line": 1, "syl_start": 0, "syl_end": 2, "class": "A"}],
        line_targets=[5],
    )
    check("RHYME_PLAN", "explicit_spans", len(plan4.slots) == 1 and plan4.source == "spans")

    gen = PoemGenerator()
    sc = gen.scaffolder.build_scaffold(
        GenerationSpec(form="positional_rhyme", debug_mode=True, min_rarity=0, max_rarity=1)
    )
    check("RHYME_PLAN", "scaffold_attach", sc.rhyme_plan is not None and sc.rhyme_plan.slots)


def section_repair():
    print("\n=== REPAIR ===")
    from wordrare.constraints.constraint_model import SteeringPolicy
    from wordrare.constraints.repair import ConflictType, LineRepairer

    repairer = LineRepairer(SteeringPolicy.loose_tercet())
    line = "the quiet river stone"
    target = {
        "meter": "syllabic",
        "target_syllables": 5,
        "rhyme_word": "bone",
        "rhyme_class": "A",
        "palette_lemmas": ["moss", "leaf", "oak", "dew"],
    }
    pivoted = repairer._rhyme_class_pivot(line, target)
    check(
        "REPAIR",
        "pivot_changes_class_keys",
        bool(pivoted and repairer.last_pivot and repairer.last_pivot[0] == "A"),
        str(repairer.last_pivot),
    )
    slant = repairer._slant_rhyme_tolerance(
        "the quiet river cat", {"rhyme_word": "hat", "meter": "syllabic"}
    )
    # May return line or a slant substitute; must not be a no-op None when cohort exists
    check("REPAIR", "slant_returns", slant is not None, str(slant))
    smooth = repairer._coherence_smoothing(
        "the quiet river stone",
        {"palette_lemmas": ["moss", "leaf", "oak"]},
    )
    check("REPAIR", "coherence_smoothing", smooth is not None and smooth != line, str(smooth))


def section_meter_haiku():
    print("\n=== METER / HAIKU ===")
    from wordrare.forms.meter_engine import expected_stress_bits
    from wordrare.generation import PoemGenerator, GenerationSpec

    bits = expected_stress_bits("iambic_pentameter", 10)
    check("METER", "expected_iambic", bits == "0101010101", bits)

    gen = PoemGenerator()
    poem = gen.generate(
        GenerationSpec(
            form="haiku",
            theme="nature",
            min_rarity=0,
            max_rarity=1,
            debug_mode=True,
            steering_policy="free_verse",
            optimize_attempts=3,
        )
    )
    failed = _failed_line_count(poem)
    check("HAIKU", "zero_failed_lines", failed == 0, f"failed={failed} text={poem.text!r}")
    check("HAIKU", "no_paren_seed", not _has_paren_seed(poem.text), poem.text)

    targets = {1: 5, 2: 7, 3: 5}
    ok_syl = True
    detail = []
    for pl in poem.annotations.get("per_line", []):
        ln = int(pl.get("line_number") or 0)
        want = targets.get(ln)
        got = pl.get("syllable_count")
        if want is not None and got != want:
            ok_syl = False
            detail.append(f"L{ln}:{got}!={want}")
    check("HAIKU", "syllables_5_7_5", ok_syl, ";".join(detail) or poem.text)


def section_fill_rate():
    print("\n=== FILL_RATE ===")
    from wordrare.generation import PoemGenerator, GenerationSpec

    gen = PoemGenerator()
    rates = []
    for _ in range(5):
        poem = gen.generate(
            GenerationSpec(
                form="haiku",
                theme="nature",
                min_rarity=0,
                max_rarity=1,
                debug_mode=True,
                steering_policy="free_verse",
                optimize_attempts=1,
                max_iterations=20,
            )
        )
        failed = _failed_line_count(poem)
        rates.append(failed / max(1, len(poem.lines)))
    mean = sum(rates) / len(rates)
    check("FILL_RATE", "haiku_mean_lt_10pct", mean < 0.10, f"mean={mean:.3f} rates={rates}")


def section_positional():
    print("\n=== POSITIONAL ===")
    from wordrare.generation import PoemGenerator, GenerationSpec
    from wordrare.forms import SoundEngine

    gen = PoemGenerator()
    poem = None
    failed = 99
    for _ in range(5):
        cand = gen.generate(
            GenerationSpec(
                form="positional_rhyme",
                theme="nature",
                min_rarity=0,
                max_rarity=1,
                debug_mode=True,
                steering_policy="loose_tercet",
                optimize_attempts=1,
                max_iterations=25,
            )
        )
        f = _failed_line_count(cand)
        if f < failed:
            poem, failed = cand, f
        if failed == 0:
            break
    flags = poem.annotations.get("flags") or []
    false_r = [f for f in flags if f.startswith("false_rhyme")]
    check("POSITIONAL", "zero_failed", failed == 0, f"failed={failed} {poem.text!r}")
    check("POSITIONAL", "zero_false_rhyme", len(false_r) == 0, str(false_r[:5]))
    check("POSITIONAL", "no_paren_seed", not _has_paren_seed(poem.text), poem.text)

    # Multi-member classes share keys via class_keys annotation if present
    class_keys = poem.annotations.get("class_keys") or {}
    plan = poem.annotations.get("rhyme_plan") or {}
    slots = plan.get("slots") or []
    by_class = {}
    for s in slots:
        cid = s.get("class") or s.get("class_id")
        if cid:
            by_class.setdefault(cid, 0)
            by_class[cid] += 1
    multi_classes = [c for c, n in by_class.items() if n >= 2]
    if multi_classes and class_keys:
        ok_share = all(c in class_keys for c in multi_classes)
        check("POSITIONAL", "multi_class_keys_bound", ok_share, str(class_keys))
    else:
        # Fall back: end lemmas of same symbol must share rhyme key
        sound = SoundEngine()
        by_sym = {}
        for pl in poem.annotations.get("per_line", []):
            sym = pl.get("rhyme_symbol")
            end = pl.get("end_lemma")
            if sym and sym != "null" and end and not str(pl.get("text", "")).startswith("["):
                by_sym.setdefault(sym, []).append(end)
        ok = True
        for sym, ends in by_sym.items():
            if len(ends) < 2:
                continue
            keys = [sound.get_rhyme_key(e) for e in ends]
            if not all(keys) or len(set(keys)) != 1:
                ok = False
        check("POSITIONAL", "shared_end_keys", ok, str(by_sym))


def section_couplet():
    print("\n=== COUPLET ===")
    from wordrare.generation import PoemGenerator, GenerationSpec
    from wordrare.forms import SoundEngine

    gen = PoemGenerator()
    poem = None
    failed = 99
    for _ in range(8):
        cand = gen.generate(
            GenerationSpec(
                form="line_rhyme_couplet",
                theme="nature",
                min_rarity=0,
                max_rarity=1,
                debug_mode=True,
                steering_policy="loose_tercet",
                optimize_attempts=2,
                max_iterations=25,
            )
        )
        f = _failed_line_count(cand)
        if f < failed:
            poem, failed = cand, f
        if failed == 0:
            break
    check("COUPLET", "zero_failed", failed == 0, f"failed={failed}")
    check("COUPLET", "two_lines", len(poem.lines) == 2)
    check("COUPLET", "no_paren_seed", not _has_paren_seed(poem.text), poem.text)
    sound = SoundEngine()
    ends = []
    for ln in poem.lines:
        if ln.startswith("["):
            continue
        parts = ln.split()
        if parts:
            ends.append(parts[-1].lower().strip(".,!?;:"))
    if len(ends) == 2:
        k1, k2 = sound.get_rhyme_key(ends[0]), sound.get_rhyme_key(ends[1])
        check(
            "COUPLET",
            "end_keys_match",
            bool(k1 and k2 and k1 == k2 and ends[0] != ends[1]),
            f"{ends} keys={k1!r}/{k2!r}",
        )
    else:
        check("COUPLET", "end_keys_match", False, f"ends={ends}")


def section_sonnet():
    print("\n=== SONNET ===")
    from wordrare.generation import PoemGenerator, GenerationSpec

    gen = PoemGenerator()
    poem = None
    failed = 99
    id_flags = []
    for _ in range(3):
        cand = gen.generate(
            GenerationSpec(
                form="shakespearean_sonnet",
                theme="nature",
                min_rarity=0,
                max_rarity=1,
                debug_mode=True,
                steering_policy="loose_tercet",
                optimize_attempts=1,
                max_iterations=12,
            )
        )
        f = _failed_line_count(cand)
        flags = cand.annotations.get("flags") or []
        ids = [x for x in flags if x.startswith("identical_rhyme")]
        if f < failed or (f == failed and len(ids) <= len(id_flags)):
            poem, failed, id_flags = cand, f, ids
        if failed <= 2 and not id_flags:
            break
    check("SONNET", "no_identical", len(id_flags) == 0, str(id_flags[:5]))
    check("SONNET", "failed_le_2", failed <= 2, f"failed={failed}")


def section_motif():
    print("\n=== MOTIF ===")
    from wordrare.generation import PoemGenerator, GenerationSpec

    gen = PoemGenerator()
    rates = []
    for dens in (0.1, 0.6):
        poem = gen.generate(
            GenerationSpec(
                form="haiku",
                theme="nature",
                motif_density=dens,
                min_rarity=0,
                max_rarity=1,
                debug_mode=True,
                steering_policy="free_verse",
                optimize_attempts=2,
            )
        )
        check(
            "MOTIF",
            f"no_paren_d{dens}",
            not _has_paren_seed(poem.text),
            poem.text,
        )
        rates.append(float(poem.annotations.get("motif_hit_rate") or 0.0))
    check(
        "MOTIF",
        "density_increases_hits",
        rates[1] >= rates[0] and rates[1] > 0,
        f"rates={rates}",
    )


def section_devices():
    print("\n=== DEVICES ===")
    from wordrare.generation.devices import DeviceEnforcer, merge_device_profile

    merged = merge_device_profile({"alliteration_rate": 0.2}, {"caesura_rate": 0.5})
    check(
        "DEVICES",
        "merge",
        merged.get("alliteration_rate") == 0.2 and merged.get("caesura_rate") == 0.5,
    )
    enf = DeviceEnforcer({"caesura_rate": 1.0, "alliteration_rate": 0.0})
    out = enf.apply(["the solemn river willow hollow mist"])
    check(
        "DEVICES",
        "caesura_rate_1",
        "," in out[0] and enf.stats["caesura_hits"] >= 1,
        out[0],
    )


def section_semantics():
    print("\n=== SEMANTICS ===")
    from wordrare.generation.theme_selector import ThemeSelector
    from wordrare.generation import GenerationSpec

    pal = ThemeSelector().build_semantic_palette(
        GenerationSpec(theme="nature", motif_density=0.5, min_rarity=0, max_rarity=1)
    )
    pools = pal.get("word_pools") or pal.get("motif_words") or []
    check("SEMANTICS", "palette_nonempty", bool(pools), str(type(pools)))
    check("SEMANTICS", "motif_density_echo", pal.get("motif_density") == 0.5)
    check("SEMANTICS", "volta_pool", "volta_pool" in pal)


def section_grammar():
    print("\n=== GRAMMAR ===")
    from wordrare.forms.grammar_engine import choose_indefinite_article, resolve_articles

    check("GRAMMAR", "an_echo", choose_indefinite_article("echo") == "an")
    check("GRAMMAR", "a_sylvan", choose_indefinite_article("sylvan") == "a")
    fixed = resolve_articles("an sylvan echo vanish a echo".split())
    check("GRAMMAR", "resolve", fixed[0] == "a" and fixed[4] == "an")


def section_generate():
    print("\n=== GENERATE ===")
    from wordrare.generation import PoemGenerator, GenerationSpec

    gen = PoemGenerator()
    poem = gen.generate(
        GenerationSpec(
            form="line_rhyme_couplet",
            theme="nature",
            min_rarity=0,
            max_rarity=1,
            debug_mode=True,
            steering_policy="loose_tercet",
            optimize_attempts=2,
        )
    )
    check("GENERATE", "couplet_lines", len(poem.lines) == 2)
    check("GENERATE", "has_rhyme_plan_ann", "rhyme_plan" in poem.annotations)
    cols = gen.annotator.format_columns(poem.annotations)
    check("GENERATE", "columns_code", "code=" in cols or "LINE META" in cols)


def section_prose():
    print("\n=== PROSE ===")
    try:
        from wordrare.generation.prose_rewrite import ProseRewriter
        from wordrare.generation import GenerationSpec

        r = ProseRewriter(GenerationSpec(min_rarity=0, max_rarity=1, rarity_bias=0.5))
        out = r.rewrite("The dark forest holds a silent dream.")
        check("PROSE", "rewrite", bool(out.get("rewritten")))
    except Exception as e:
        check("PROSE", "rewrite", False, str(e))


def main():
    section_phon()
    section_schema()
    section_lexicon()
    section_forms()
    section_rhyme_plan()
    section_repair()
    section_meter_haiku()
    section_fill_rate()
    section_positional()
    section_couplet()
    section_sonnet()
    section_motif()
    section_devices()
    section_semantics()
    section_grammar()
    section_generate()
    section_prose()
    print(f"\n=== SUMMARY fails={FAILS} ===")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
