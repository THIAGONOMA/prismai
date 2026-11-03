"""Unit tests for extraction schema loading and validation."""
from __future__ import annotations

import pytest

from prismai.core.extraction_schema import COCHRANE_DEFAULT, carregar_schema
from prismai.core.models import ExtractionSchema


def test_default_schema_loads():
    schema = carregar_schema(None)
    assert isinstance(schema, ExtractionSchema)
    assert schema.version == "cochrane-default-v2"
    assert len(schema.fields) > 0


def test_default_schema_has_expected_blocks():
    schema = COCHRANE_DEFAULT
    blocks = {f.block for f in schema.fields}
    assert "populacao" in blocks
    assert "intervencao" in blocks
    assert "comparador" in blocks
    assert "desfechos" in blocks
    assert "estatisticas" in blocks
    assert "metadados" in blocks


def test_custom_schema_validates():
    raw = {
        "version": "custom-v1",
        "fields": [
            {"name": "campo1", "block": "bloco1", "tipo": "text", "descricao": "Um campo"},
            {"name": "campo2", "block": "bloco1", "tipo": "integer", "descricao": "Outro campo"},
        ],
    }
    schema = carregar_schema(raw)
    assert schema.version == "custom-v1"
    assert len(schema.fields) == 2


def test_invalid_schema_raises():
    raw = {"version": "bad", "fields": [{"name": "x"}]}
    with pytest.raises(Exception):
        carregar_schema(raw)


def test_empty_fields_validates():
    raw = {"version": "empty-v1", "fields": []}
    schema = carregar_schema(raw)
    assert len(schema.fields) == 0


def test_field_types():
    for f in COCHRANE_DEFAULT.fields:
        assert f.tipo in ("text", "number", "integer", "boolean", "list")


def test_roundtrip():
    schema = COCHRANE_DEFAULT
    raw = schema.model_dump()
    loaded = carregar_schema(raw)
    assert loaded.version == schema.version
    assert len(loaded.fields) == len(schema.fields)
