"""Tests for Jovaltus plugin — JSON schemas."""

from jovaltus import schemas


def test_implement_schema_has_required_fields():
    s = schemas.IMPLEMENT_SCHEMA
    assert s["name"] == "jovaltus_implement"
    assert "description" in s
    assert "parameters" in s
    assert s["parameters"]["type"] == "object"
    assert "project_dir" in s["parameters"]["properties"]


def test_verify_schema_requires_task_id():
    s = schemas.VERIFY_SCHEMA
    assert s["name"] == "jovaltus_verify"
    assert "task_id" in s["parameters"]["required"]


def test_simplify_schema_requires_task_id():
    s = schemas.SIMPLIFY_SCHEMA
    assert s["name"] == "jovaltus_simplify"
    assert "task_id" in s["parameters"]["required"]


def test_all_schemas_mention_subagent_spawning():
    """All tool descriptions should mention that they spawn subagents."""
    for schema in [
        schemas.IMPLEMENT_SCHEMA,
        schemas.VERIFY_SCHEMA,
        schemas.SIMPLIFY_SCHEMA,
    ]:
        assert "spawn" in schema["description"].lower()
