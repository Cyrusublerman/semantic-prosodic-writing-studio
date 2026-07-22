"""WordRare generation integration tests (packaged imports)."""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from wordrare.forms import FormLibrary, MeterEngine, SoundEngine
from wordrare.generation import GenerationSpec, PoemGenerator


@pytest.fixture
def form_library() -> FormLibrary:
    return FormLibrary()


def test_load_shipped_forms(form_library: FormLibrary) -> None:
    forms = form_library.list_forms()
    assert forms
    for form_id in forms:
        form = form_library.get_form(form_id)
        assert form is not None
        assert form.form_id


def test_haiku_structure(form_library: FormLibrary) -> None:
    haiku = form_library.get_form("haiku")
    assert haiku is not None
    assert haiku.stanza_specs


def test_meter_engine_analyse_line() -> None:
    engine = MeterEngine()
    result = engine.analyze_line("The quiet river bends toward light", "iambic_pentameter")
    assert result.syllable_count > 0


def test_sound_engine_rhyme_keys() -> None:
    engine = SoundEngine()
    assert hasattr(engine, "classify_rhyme") or hasattr(engine, "find_rhymes")


def test_poem_generator_debug_haiku() -> None:
    generator = PoemGenerator()
    spec = GenerationSpec(
        form="haiku",
        theme="nature",
        rarity_bias=0.3,
        min_rarity=0.0,
        max_rarity=1.0,
        debug_mode=True,
        steering_policy="free_verse",
    )
    poem = generator.generate(spec)
    assert poem.text
    assert poem.lines
