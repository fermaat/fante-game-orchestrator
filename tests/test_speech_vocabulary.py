"""Tests for the vocabulary YAML loader."""

import pytest

from fante.speech.vocabulary import load_vocabulary


@pytest.mark.unit
def test_loads_spanish_words(tmp_path):
    p = tmp_path / "vocab.yaml"
    p.write_text("es:\n  actions: [trepar, saltar]\n  objects: [muro]\n")
    out = load_vocabulary(p, "es")
    assert "trepar" in out and "saltar" in out and "muro" in out


@pytest.mark.unit
def test_loads_english_words(tmp_path):
    p = tmp_path / "vocab.yaml"
    p.write_text("en:\n  actions: [climb, jump]\n")
    out = load_vocabulary(p, "en")
    assert "climb" in out and "jump" in out


@pytest.mark.unit
def test_mixed_combines_both(tmp_path):
    p = tmp_path / "vocab.yaml"
    p.write_text("es:\n  actions: [trepar]\nen:\n  actions: [climb]\n")
    out = load_vocabulary(p, "mixed")
    assert "trepar" in out and "climb" in out


@pytest.mark.unit
def test_missing_file_returns_empty(tmp_path):
    assert load_vocabulary(tmp_path / "nope.yaml", "es") == ""


@pytest.mark.unit
def test_dedupes_preserving_order(tmp_path):
    p = tmp_path / "vocab.yaml"
    p.write_text("es:\n  a: [hola, mundo]\n  b: [hola, fante]\n")
    out = load_vocabulary(p, "es")
    parts = [w.strip() for w in out.split(",")]
    assert parts == ["hola", "mundo", "fante"]


@pytest.mark.unit
def test_production_vocabulary_loads_for_all_languages():
    from pathlib import Path

    p = Path("data/speech_vocabulary.yaml")
    for lang in ("es", "en", "mixed"):
        out = load_vocabulary(p, lang)
        assert out  # non-empty
        assert "," in out  # is a comma-joined list
