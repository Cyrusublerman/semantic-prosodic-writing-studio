import pytest
from pydantic import ValidationError

from spws_contracts_core.identifiers import new_uuid7
from spws_contracts_core.quality import (
    AlternativeRecord,
    ConfidenceKind,
    ConfidenceRecord,
    FailureRecord,
    PresenceState,
    QualifiedValue,
    Severity,
    WarningRecord,
)
from spws_contracts_core.references import VersionReference


def test_calibrated_probability_requires_calibration_set():
    with pytest.raises(ValidationError):
        ConfidenceRecord(kind=ConfidenceKind.CALIBRATED_PROBABILITY, value=0.8, method="model")


def test_confidence_ranges():
    with pytest.raises(ValidationError):
        ConfidenceRecord(kind=ConfidenceKind.PROBABILITY, value=1.5, method="model")


def test_qualified_value_presence_contract():
    present = QualifiedValue[str](presence=PresenceState.PRESENT, value="x")
    assert present.value == "x"
    with pytest.raises(ValidationError):
        QualifiedValue[str](presence=PresenceState.UNKNOWN, value="x")
    ambiguous = QualifiedValue[str](
        presence=PresenceState.AMBIGUOUS,
        alternatives=(AlternativeRecord(value="a"), AlternativeRecord(value="b")),
    )
    assert len(ambiguous.alternatives) == 2


def test_warning_and_failure_registry_validation():
    warning = WarningRecord(
        warning_id=new_uuid7(),
        code="COC-W-001",
        name="unknown_rights",
        severity=Severity.WARNING,
        scope="rights",
    )
    failure = FailureRecord(
        failure_id=new_uuid7(),
        code="COC-F-004",
        name="digest_mismatch",
        scope="payload",
    )
    assert warning.name == "unknown_rights"
    assert failure.name == "digest_mismatch"
    with pytest.raises(ValidationError):
        WarningRecord(
            warning_id=new_uuid7(),
            code="COC-W-001",
            name="wrong",
            severity=Severity.WARNING,
            scope="rights",
        )


def test_failed_qualified_value_requires_failure_record():
    with pytest.raises(ValidationError):
        QualifiedValue[str](presence=PresenceState.FAILED)
    failure = FailureRecord(
        failure_id=new_uuid7(),
        code="COC-F-020",
        name="corrupt_or_missing_payload",
        scope="payload",
    )
    value = QualifiedValue[str](presence=PresenceState.FAILED, failures=(failure,))
    assert value.failures[0].code == "COC-F-020"
