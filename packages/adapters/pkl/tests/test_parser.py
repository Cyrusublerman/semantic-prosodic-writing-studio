from spws_pkl_adapter.parser.parser import parse_pkl_text, resolve_identity


SAMPLE = """\
---
uid: "uid-primary"
id: "legacy-id"
title: "Sample"
object_type: note
rights: public
privacy: internal
relationships:
  - type: cites
    target: uid-other
---

Body text here.
"""


def test_resolve_identity_prefers_uid():
    doc = parse_pkl_text(SAMPLE)
    assert resolve_identity(doc.metadata) == "uid-primary"
    assert doc.uid == "uid-primary"
    assert doc.source_id == "legacy-id"


def test_resolve_identity_falls_back_to_id():
    text = """\
---
id: "only-legacy"
title: "Legacy"
rights: public
privacy: public
---
Body.
"""
    doc = parse_pkl_text(text)
    assert doc.uid == "only-legacy"


def test_parse_extracts_frontmatter_fields():
    doc = parse_pkl_text(SAMPLE)
    assert doc.title == "Sample"
    assert doc.object_type == "note"
    assert doc.rights == "public"
    assert doc.privacy == "internal"
    assert doc.body.strip() == "Body text here."
    assert len(doc.relationships) == 1
    assert doc.relationships[0].type == "cites"
    assert doc.relationships[0].target == "uid-other"
