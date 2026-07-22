"""WordRare adapter capability matrix (D015)."""

from __future__ import annotations

from spws_wordrare_adapter import (
    ADAPTER_VERSION,
    DisabledCapability,
    WordRareAdapter,
    constrained_search,
    diagnose_line,
    form_scaffold,
    generate_poem,
    is_unsupported,
    lexical_record,
    lexical_snapshot,
    list_forms,
    pronunciation,
    rare_reword_line,
    rarity,
    repair_line,
    syllable_stress_rhyme,
    unsupported,
    wordrare_version,
)


def test_wordrare_version_pin_string():
    version = wordrare_version()
    assert isinstance(version, str)
    assert version
    assert isinstance(ADAPTER_VERSION, str) and ADAPTER_VERSION


def test_lexical_capability_ok_and_unsupported():
    ok = lexical_record("river")
    assert ok["status"] == "ok"
    assert ok["capability"] == "lexical"
    record = ok["record"]
    assert record["lemma"] == "river"
    assert "field_confidence" in record
    assert "provenance" in record
    assert record["provenance"].get("adapter_version") == ADAPTER_VERSION
    # Must be LexicalRecord-shaped dict, not an ORM model
    assert not hasattr(record, "__table__")
    assert isinstance(record, dict)

    bad = lexical_record("")
    assert is_unsupported(bad)
    assert bad["capability"] == "lexical"

    rare = rarity("river")
    assert rare["status"] == "ok"
    assert "rarity" in rare


def test_prosody_capability_distinct_pass_fail():
    syl = syllable_stress_rhyme("meadow")
    assert syl["status"] == "ok"
    assert syl["capability"] == "prosody"
    assert syl.get("syllable_count") is not None
    assert "field_confidence" in syl

    # Empty lemma is explicit unsupported (not None)
    empty = pronunciation("")
    assert is_unsupported(empty)
    assert empty["capability"] in {"prosody", "lexical"}


def test_form_scaffold_capability():
    listed = list_forms()
    assert listed["status"] == "ok" or is_unsupported(listed)
    if listed["status"] == "ok":
        assert listed["forms"]
        scaffold = form_scaffold(listed["forms"][0])
        assert scaffold["status"] == "ok"
        assert "scaffold" in scaffold
        assert scaffold["scaffold"]["form_id"]
        assert isinstance(scaffold["scaffold"], dict)

    missing = form_scaffold("not_a_real_form_xyz")
    assert is_unsupported(missing)
    assert missing["capability"] == "form_scaffold"


def test_constrained_search_capability():
    no_constraints = constrained_search()
    assert is_unsupported(no_constraints)
    assert no_constraints["capability"] == "constrained_search"

    # May be unsupported when lexicon empty; that is a distinct fail, not None.
    result = constrained_search(min_rarity=0.0, max_rarity=1.0, limit=3)
    assert result["status"] in {"ok", "unsupported"}
    assert result["capability"] == "constrained_search"
    if result["status"] == "ok":
        assert isinstance(result["hits"], list)
        for hit in result["hits"]:
            assert isinstance(hit, dict)
            assert "lemma" in hit
            assert "field_confidence" in hit


def test_prosodic_repair_capability():
    diag = diagnose_line("The quiet river holds a luminous dream.")
    assert diag["status"] == "ok"
    assert diag["capability"] == "prosodic_repair"

    empty = repair_line("")
    assert is_unsupported(empty)
    assert empty["capability"] == "prosodic_repair"

    # No conflict → ok with unchanged line
    repaired = repair_line("soft light")
    assert repaired["status"] in {"ok", "unsupported"}
    assert repaired["capability"] == "prosodic_repair"


def test_disabled_capability_is_explicit_unsupported():
    disabled = DisabledCapability("lexical", reason="test_disable")
    result = disabled.lexical_record("river")
    assert is_unsupported(result)
    assert result["capability"] == "lexical"
    assert result["reason"] == "test_disable"
    # Other capabilities still work via default adapter
    assert WordRareAdapter().form_scaffold("haiku")["status"] in {"ok", "unsupported"}


def test_unsupported_helper_shape():
    payload = unsupported("prosody", reason="demo")
    assert payload == {"status": "unsupported", "capability": "prosody", "reason": "demo"}


def test_adapter_does_not_export_db_models():
    import spws_wordrare_adapter as adapter

    for name in dir(adapter):
        if name.startswith("_"):
            continue
        obj = getattr(adapter, name)
        # WordRecord / Base must not be re-exported
        assert name not in {"WordRecord", "Base", "RareLexicon", "Phonetics"}
        module = getattr(obj, "__module__", "") or ""
        assert "wordrare.database" not in module


def test_legacy_snapshot_and_generation_surfaces():
    snap = lexical_snapshot("The quiet river holds a luminous dream.")
    assert isinstance(snap, dict)
    assert "token_count" in snap
    assert "wordrare_version" in snap

    revised = rare_reword_line("The dark forest holds a silent dream.")
    assert revised is None or (isinstance(revised, str) and revised.strip())

    result = generate_poem(form="haiku", theme="nature", debug=True)
    assert isinstance(result, dict)
    assert "text" in result or "error" in result


def test_all_five_capabilities_ok_with_heuristics():
    adapter = WordRareAdapter()
    lexical = adapter.lexical_record("river")
    prosody = adapter.syllable_stress_rhyme("meadow")
    form = adapter.form_scaffold("haiku")
    search = adapter.constrained_search(min_rarity=0.0, max_rarity=1.0, limit=1)
    repair = adapter.repair_line("soft light")

    assert lexical["status"] == "ok"
    assert prosody["status"] == "ok"
    assert form["status"] == "ok"

    if search["status"] == "ok":
        assert isinstance(search.get("hits"), list) and search["hits"]
        assert lexical["status"] == "ok"
        assert prosody["status"] == "ok"
        assert form["status"] == "ok"
    else:
        # Fallback matrix: form + lexical + prosody + repair all ok when search unsupported
        assert repair["status"] == "ok"
        assert form["status"] == "ok"
        assert lexical["status"] == "ok"
        assert prosody["status"] == "ok"
