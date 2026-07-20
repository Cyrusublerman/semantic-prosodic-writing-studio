import pytest
from pydantic import ValidationError

from spws_contracts_core.identifiers import new_uuid7
from spws_contracts_core.references import ObjectReference, ReferenceSet, VersionReference


def test_version_reference_converts_to_object_reference():
    ref = VersionReference(object_id=new_uuid7(), version_id=new_uuid7(), object_type="spws.object.raw_source")
    assert ref.as_object_reference().version_id == ref.version_id


def test_reference_set_rejects_duplicate_versions():
    version = new_uuid7()
    ref = VersionReference(object_id=new_uuid7(), version_id=version)
    with pytest.raises(ValidationError):
        ReferenceSet(references=(ref, ref))
