from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from spws_contracts_core.domain import (
    AnalysisBundle,
    Annotation,
    AuthorshipClass,
    Candidate,
    CandidateSet,
    CandidateStatus,
    EvaluationBundle,
    EvaluationResult,
    GenerationSpecification,
    ManuscriptVersion,
    MeaningProfile,
    MeaningScale,
    MeaningUnit,
    NormalisedSource,
    RevisionOperation,
    SimilarityHit,
    SimilarityQuery,
    SimilarityResultSet,
    SourceFragment,
    StructuralScope,
    StructuralUnit,
    StudioConstraint,
    WorkPlan,
    WorkSpecification,
)


def test_meaning_unit_minimal():
    unit = MeaningUnit(unit_id="u1", scale=MeaningScale.WORD, text="light")
    assert unit.unit_id == "u1"
    assert unit.scale is MeaningScale.WORD
    assert unit.schema_version == "0.1.0"


def test_meaning_profile_minimal():
    profile = MeaningProfile(unit_id="u1")
    assert profile.confidence == 1.0
    assert profile.analyser == "spws_semantics"
    assert profile.theme_tags == []


def test_similarity_query_requires_text_or_unit():
    with pytest.raises(ValidationError):
        SimilarityQuery()
    query = SimilarityQuery(text="ember")
    assert query.result_limit == 10
    by_unit = SimilarityQuery(unit_id="u1")
    assert by_unit.unit_id == "u1"


def test_similarity_hit_and_result_set():
    query = SimilarityQuery(text="ember")
    hit = SimilarityHit(
        unit_id="u2",
        text="coal",
        scale=MeaningScale.WORD,
        score_combined=0.9,
    )
    result = SimilarityResultSet(query=query, hits=[hit])
    assert len(result.hits) == 1
    assert result.hits[0].score_vector == 0.0


def test_structural_unit_and_annotation():
    structural = StructuralUnit(unit_id="s1", scope=StructuralScope.LINE, text="a line")
    annotation = Annotation(
        annotation_id="a1",
        source_object="src1",
        feature="metre",
        analyser="spws_prosody",
    )
    assert structural.child_ids == []
    assert annotation.confidence == 1.0


def test_analysis_bundle_minimal(now: datetime):
    bundle = AnalysisBundle(
        bundle_id="b1",
        source_object_id="src1",
        created_at=now,
    )
    assert bundle.annotations == []
    assert bundle.created_at == now


def test_source_fragment_and_normalised_source():
    fragment = SourceFragment(
        fragment_id="f1",
        source_object_id="src1",
        text="quoted",
        authorship=AuthorshipClass.QUOTE,
    )
    normalised = NormalisedSource(
        normalised_id="n1",
        source_object_id="src1",
        text="quoted",
    )
    assert fragment.rights.value == "unknown"
    assert normalised.encoding == "utf-8"


def test_work_specification_and_plan():
    spec = WorkSpecification(spec_id="ws1")
    constraint = StudioConstraint(
        constraint_id="c1",
        target_scope="line",
        constraint_type="syllable_count",
    )
    plan = WorkPlan(plan_id="p1", work_spec_id=spec.spec_id, constraints=[constraint])
    assert spec.mode == "poetry_revision"
    assert plan.constraints[0].hard is False


def test_generation_and_candidates():
    gen = GenerationSpecification(gen_spec_id="g1", method_family="rewrite")
    candidate = Candidate(
        candidate_id="cand1",
        content="revised line",
        method_family="rewrite",
        generation_spec_id=gen.gen_spec_id,
    )
    candidate_set = CandidateSet(set_id="cs1", candidates=[candidate])
    assert gen.candidate_count == 3
    assert candidate.status is CandidateStatus.PROPOSED
    assert len(candidate_set.candidates) == 1


def test_evaluation_bundle(now: datetime):
    result = EvaluationResult(
        evaluation_id="e1",
        subject_id="cand1",
        criterion="coherence",
    )
    bundle = EvaluationBundle(
        bundle_id="eb1",
        subject_id="cand1",
        results=[result],
        created_at=now,
    )
    assert bundle.results[0].measured_value is None


def test_revision_operation_and_manuscript(now: datetime):
    operation = RevisionOperation(
        operation_id="op1",
        original_text="old",
        revised_text="new",
        operation="replace",
    )
    manuscript = ManuscriptVersion(
        manuscript_id="m1",
        version_id="v1",
        text="new",
        created_at=now,
    )
    assert operation.affected_constraints == []
    assert manuscript.parent_version_ids == []
    assert manuscript.created_at.tzinfo == UTC
