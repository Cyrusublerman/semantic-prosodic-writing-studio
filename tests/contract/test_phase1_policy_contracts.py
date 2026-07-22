"""Phase 1: rights pending_review, dialect, LexicalRecord, fail-closed retrieval."""

from __future__ import annotations

from pathlib import Path

from datetime import UTC, datetime

from spws_contracts_core.domain import (
    Classification,
    ClassificationBundle,
    DialectCode,
    DialectPolicy,
    ExchangeEnvelope,
    GenerationSpecification,
    LexicalRecord,
    MeaningScale,
    PrivacyState,
    PronunciationStatus,
    PronunciationVariant,
    PublicationBundle,
    RightsState,
    SimilarityQuery,
    WorkSpecification,
    normalize_rights_ingest,
    rights_allows_retrieval,
)
from spws_semantics import MeaningGauge


def test_normalize_rights_ingest_aliases():
    assert normalize_rights_ingest("restricted") is RightsState.RESTRICTED_PENDING_REVIEW
    assert normalize_rights_ingest(RightsState.RESTRICTED) is RightsState.RESTRICTED_PENDING_REVIEW
    assert normalize_rights_ingest("public") is RightsState.PUBLIC
    assert normalize_rights_ingest(None) is RightsState.RESTRICTED_PENDING_REVIEW


def test_rights_allows_retrieval_fail_closed():
    assert rights_allows_retrieval(RightsState.PUBLIC)
    assert rights_allows_retrieval(RightsState.INTERNAL)
    assert not rights_allows_retrieval(RightsState.UNKNOWN)
    assert not rights_allows_retrieval(RightsState.RESTRICTED_PENDING_REVIEW)
    assert not rights_allows_retrieval(RightsState.RESTRICTED)
    assert not rights_allows_retrieval(RightsState.PRIVATE)


def test_dialect_policy_default_au():
    policy = DialectPolicy()
    assert policy.primary is DialectCode.EN_AU
    assert policy.spelling_convention is DialectCode.EN_AU
    spec = WorkSpecification(spec_id="wspec-1")
    assert spec.dialect_policy.primary is DialectCode.EN_AU


def test_lexical_record_and_envelope():
    record = LexicalRecord(
        record_id="lex-1",
        lemma="metre",
        rarity=0.4,
        pronunciation_variants=[
            PronunciationVariant(
                dialect=DialectCode.EN_AU,
                ipa="ˈmiːtə",
                status=PronunciationStatus.SOURCED,
                confidence=0.9,
            )
        ],
        rhyme_keys=["iːtə"],
        field_confidence={"rarity": 0.8, "ipa": 0.9},
    )
    assert record.syllable_count is None
    env = ExchangeEnvelope(
        object_id="env-1",
        object_type="LexicalRecord",
        dialect=DialectCode.EN_AU,
        payload=record.model_dump(mode="json"),
    )
    assert env.review_state == "unreviewed"
    assert env.payload["lemma"] == "metre"


def test_generation_spec_llm_slots_unused():
    spec = GenerationSpecification(gen_spec_id="gs-1", method_family="rare_lexical")
    assert spec.provider is None
    assert spec.retention_policy is None


def test_classification_and_publication_bundle():
    now = datetime.now(UTC)
    classification = Classification(
        classification_id="cls-1",
        label="pastoral",
        category="theme",
        confidence=0.8,
        subject_id="ms-1",
    )
    bundle = ClassificationBundle(
        bundle_id="cb-1",
        subject_id="ms-1",
        classifications=[classification],
        created_at=now,
    )
    pub = PublicationBundle(
        bundle_id="pub-1",
        manuscript_id="ms-1",
        version_id="msv-1",
        clean_text="quiet river",
        export_files={"clean.txt": "/tmp/clean.txt"},
        classification_bundle_id=bundle.bundle_id,
        created_at=now,
    )
    assert bundle.classifications[0].label == "pastoral"
    assert pub.export_files["clean.txt"]
    assert pub.classification_bundle_id == "cb-1"


def test_unknown_rights_never_retrieve(tmp_path: Path):
    gauge = MeaningGauge(tmp_path / "meaning", debug_hash_embeddings=True, require_model=False)
    gauge.index_text(
        "A quiet river under leaf shadow.",
        source_object_id="u1",
        object_uid="unknown-frag",
        rights=RightsState.UNKNOWN,
        privacy=PrivacyState.PUBLIC,
        scales=[MeaningScale.SENTENCE, MeaningScale.PHRASE],
    )
    gauge.index_text(
        "Pending review pastoral line about dusk.",
        source_object_id="u2",
        object_uid="pending-frag",
        rights=RightsState.RESTRICTED_PENDING_REVIEW,
        privacy=PrivacyState.PRIVATE,
        scales=[MeaningScale.SENTENCE, MeaningScale.PHRASE],
    )
    hits = gauge.similar(SimilarityQuery(text="quiet river dusk", result_limit=10))
    assert hits.hits == []
