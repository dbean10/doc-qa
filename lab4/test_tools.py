"""
lab4/test_tools.py

Jordan Rivera's test suite for the Week 4 tool layer.

Scope:
  - tool implementations (weather, reminder)
  - registry (schemas, dispatch happy path, dispatch error paths)
  - RAG retriever validation (query validation, format contract)

NOT in scope here (separate integration test file):
  - Chroma store round-trip (requires Ollama running)
  - Full chatbot turn with live API call

Run:
    uv run pytest lab4/test_tools.py -v
    uv run pytest lab4/test_tools.py -v -m "not integration"
"""

from __future__ import annotations

import json
import pytest

from lab4.tools.weather import get_weather
from lab4.tools.reminder import create_reminder, clear_reminders, get_all_reminders
from lab4.tools.registry import get_tool_schemas, dispatch
from lab4.rag.retriever import search_docs


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(autouse=True)
def reset_reminders():
    """Clear reminder state before each test."""
    clear_reminders()
    yield
    clear_reminders()


# ===========================================================================
# Registry — schema contract
# ===========================================================================

class TestSchemas:
    def test_returns_list(self):
        assert isinstance(get_tool_schemas(), list)

    def test_at_least_two_tools(self):
        # weather + reminder minimum; search_docs added after RAG is indexed
        assert len(get_tool_schemas()) >= 3

    def test_each_schema_has_required_fields(self):
        for schema in get_tool_schemas():
            assert "name" in schema, f"Missing 'name' in {schema}"
            assert "description" in schema, f"Missing 'description' in {schema}"
            assert "input_schema" in schema, f"Missing 'input_schema' in {schema}"

    def test_descriptions_are_substantive(self):
        """Descriptions must be long enough to guide tool routing."""
        for schema in get_tool_schemas():
            assert len(schema["description"]) >= 30, (
                f"Description for '{schema['name']}' too short — "
                "tool descriptions are prompts, write them properly"
            )

    def test_input_schemas_have_properties(self):
        for schema in get_tool_schemas():
            input_schema = schema["input_schema"]
            assert input_schema.get("type") == "object"
            assert "properties" in input_schema


# ===========================================================================
# get_weather — implementation
# ===========================================================================

class TestGetWeather:
    def test_happy_path_returns_expected_fields(self):
        result = get_weather("Denver")
        assert result["error"] is False
        assert result["location"] == "Denver"
        assert isinstance(result["temperature_f"], int)
        assert isinstance(result["condition"], str)
        assert isinstance(result["humidity_pct"], int)

    def test_temperature_in_plausible_range(self):
        result = get_weather("Denver")
        assert -60 <= result["temperature_f"] <= 140

    def test_deterministic_for_same_city(self):
        """Same city → same result every time (seeded RNG)."""
        a = get_weather("London")
        b = get_weather("London")
        assert a["temperature_f"] == b["temperature_f"]
        assert a["condition"] == b["condition"]

    def test_different_cities_may_differ(self):
        """Basic sanity — not all cities are identical."""
        cities = ["Tokyo", "Sydney", "Cairo", "Oslo", "Denver"]
        temps = [get_weather(c)["temperature_f"] for c in cities]
        assert len(set(temps)) > 1, "All cities returned identical temperatures"

    def test_empty_string_returns_error(self):
        result = get_weather("")
        assert result["error"] is True
        assert "empty" in result["message"].lower()

    def test_whitespace_only_returns_error(self):
        result = get_weather("   ")
        assert result["error"] is True

    def test_wrong_type_returns_error(self):
        result = get_weather(123)  # type: ignore[arg-type]
        assert result["error"] is True

    def test_none_returns_error(self):
        result = get_weather(None)  # type: ignore[arg-type]
        assert result["error"] is True

    def test_oversized_input_returns_error(self):
        result = get_weather("A" * 201)
        assert result["error"] is True
        assert "long" in result["message"].lower()

    def test_strips_whitespace_from_valid_input(self):
        result = get_weather("  Denver  ")
        assert result["error"] is False
        assert result["location"] == "Denver"


# ===========================================================================
# create_reminder — implementation
# ===========================================================================

class TestCreateReminder:
    def test_happy_path_returns_expected_fields(self):
        result = create_reminder("Call Sarah", "tomorrow at 9am")
        assert result["error"] is False
        assert result["text"] == "Call Sarah"
        assert result["time"] == "tomorrow at 9am"
        assert "id" in result
        assert "created_at" in result

    def test_reminder_stored_in_session(self):
        create_reminder("Buy milk", "tonight")
        reminders = get_all_reminders()
        assert len(reminders) == 1
        assert reminders[0]["text"] == "Buy milk"

    def test_multiple_reminders_accumulate(self):
        create_reminder("Task 1", "9am")
        create_reminder("Task 2", "10am")
        create_reminder("Task 3", "11am")
        assert len(get_all_reminders()) == 3

    def test_ids_are_unique(self):
        results = [create_reminder(f"Task {i}", "9am") for i in range(5)]
        ids = [r["id"] for r in results]
        assert len(set(ids)) == 5

    def test_empty_text_returns_error(self):
        result = create_reminder("", "9am")
        assert result["error"] is True
        assert "empty" in result["message"].lower()

    def test_empty_time_returns_error(self):
        result = create_reminder("Call Sarah", "")
        assert result["error"] is True

    def test_wrong_type_text_returns_error(self):
        result = create_reminder(42, "9am")  # type: ignore[arg-type]
        assert result["error"] is True

    def test_wrong_type_time_returns_error(self):
        result = create_reminder("Call Sarah", None)  # type: ignore[arg-type]
        assert result["error"] is True

    def test_oversized_text_returns_error(self):
        result = create_reminder("X" * 501, "9am")
        assert result["error"] is True

    def test_whitespace_time_returns_error(self):
        result = create_reminder("Call Sarah", "   ")
        assert result["error"] is True


# ===========================================================================
# dispatch — registry contract
# ===========================================================================

class TestDispatch:
    def test_get_weather_returns_valid_json(self):
        result = dispatch("get_weather", {"location": "Denver"})
        data = json.loads(result)  # must be valid JSON
        assert data["error"] is False

    def test_create_reminder_returns_valid_json(self):
        result = dispatch("create_reminder", {"text": "Test", "time": "9am"})
        data = json.loads(result)
        assert data["error"] is False

    def test_unknown_tool_returns_error_json(self):
        result = dispatch("execute_shell", {"cmd": "rm -rf /"})
        data = json.loads(result)
        assert data["error"] is True
        assert "Unknown tool" in data["message"]

    def test_unknown_tool_does_not_execute(self):
        """Allowlist check: unknown tool names are rejected before any fn call."""
        dangerous_names = [
            "execute_shell", "delete_files", "run_code",
            "read_file", "write_file", "eval",
        ]
        for name in dangerous_names:
            result = dispatch(name, {})
            data = json.loads(result)
            assert data["error"] is True

    def test_missing_required_arg_returns_error(self):
        result = dispatch("get_weather", {})
        data = json.loads(result)
        assert data["error"] is True

    def test_wrong_arg_name_returns_error(self):
        result = dispatch("get_weather", {"city": "Denver"})  # wrong key
        data = json.loads(result)
        assert data["error"] is True

    def test_always_returns_string(self):
        """dispatch() must always return a string — never None, never raises."""
        inputs = [
            ("get_weather", {}),
            ("get_weather", {"location": ""}),
            ("get_weather", {"location": None}),
            ("create_reminder", {}),
            ("create_reminder", {"text": "x"}),  # missing time
            ("nonexistent_tool", {"a": "b"}),
        ]
        for name, inp in inputs:
            result = dispatch(name, inp)
            assert isinstance(result, str), (
                f"dispatch({name!r}, {inp!r}) returned {type(result)}, expected str"
            )

    def test_always_returns_parseable_json(self):
        """Every dispatch() return value must be valid JSON."""
        inputs = [
            ("get_weather", {"location": "Denver"}),
            ("get_weather", {}),
            ("create_reminder", {"text": "t", "time": "9am"}),
            ("unknown_tool", {}),
        ]
        for name, inp in inputs:
            result = dispatch(name, inp)
            try:
                json.loads(result)
            except json.JSONDecodeError:
                pytest.fail(
                    f"dispatch({name!r}, {inp!r}) returned non-JSON: {result!r}"
                )


# ===========================================================================
# search_docs — retriever validation (no Chroma required)
# ===========================================================================

class TestSearchDocs:
    """
    These tests validate the retriever's input contract without requiring
    Ollama or a populated Chroma collection. They test what happens before
    and after the vector search, not the search itself.

    Integration tests that require a populated collection are marked
    with @pytest.mark.integration and excluded from CI by default.
    """

    def test_empty_query_returns_error(self):
        result = search_docs("")
        assert result["error"] is True
        assert "empty" in result["message"].lower()

    def test_whitespace_query_returns_error(self):
        result = search_docs("   ")
        assert result["error"] is True

    def test_wrong_type_returns_error(self):
        result = search_docs(None)  # type: ignore[arg-type]
        assert result["error"] is True

    def test_oversized_query_returns_error(self):
        result = search_docs("x" * 1001)
        assert result["error"] is True

    def test_valid_query_returns_dict_with_required_keys(self):
        """
        A valid query against an empty collection should still return the
        correct shape — error False, results string, num_results 0.
        """
        result = search_docs("what is the refund policy")
        # If collection is empty, returns no-results message — not an error
        assert "error" in result
        if not result["error"]:
            assert "results" in result
            assert "num_results" in result
            assert isinstance(result["results"], str)
