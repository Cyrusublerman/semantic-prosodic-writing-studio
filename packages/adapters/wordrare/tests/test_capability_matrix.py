"""WordRare adapter capability matrix (D015) — package-local mirror."""

from __future__ import annotations

from spws_wordrare_adapter import (
    ADAPTER_VERSION,
    DisabledCapability,
    form_scaffold,
    is_unsupported,
    lexical_record,
    lexical_snapshot,
    rare_reword_line,
    wordrare_version,
)


def test_capability_matrix():
    assert isinstance(wordrare_version(), str) and wordrare_version()
    assert ADAPTER_VERSION
    snap = lexical_snapshot("bright quiet river")
    assert isinstance(snap, dict)
    lex = lexical_record("river")
    assert lex["status"] == "ok" and "record" in lex
    assert is_unsupported(DisabledCapability("lexical").lexical_record("x"))
    scaffold = form_scaffold("haiku")
    assert scaffold["status"] in {"ok", "unsupported"}
    revised = rare_reword_line("The bright river is quiet.")
    assert revised is None or isinstance(revised, str)
