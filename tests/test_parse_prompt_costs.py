"""Unit tests for otel/parse_prompt_costs.py's attribute-flattening helpers."""

from parse_prompt_costs import attr_value, flatten_attrs


def test_attr_value_string() -> None:
    assert attr_value({"stringValue": "api_request"}) == "api_request"


def test_attr_value_int_from_proto_json_string() -> None:
    # Proto3 JSON encodes int64 as a string; callers must get a Python int back.
    assert attr_value({"intValue": "123"}) == 123
    assert isinstance(attr_value({"intValue": "123"}), int)


def test_attr_value_double() -> None:
    assert attr_value({"doubleValue": 0.0042}) == 0.0042


def test_attr_value_bool() -> None:
    assert attr_value({"boolValue": True}) is True


def test_attr_value_unknown_returns_none() -> None:
    assert attr_value({}) is None


def test_flatten_attrs_builds_dict() -> None:
    attrs = [
        {"key": "event.name", "value": {"stringValue": "api_request"}},
        {"key": "input_tokens", "value": {"intValue": "42"}},
        {"key": "cost_usd", "value": {"doubleValue": 0.0013}},
    ]
    result = flatten_attrs(attrs)
    assert result == {
        "event.name": "api_request",
        "input_tokens": 42,
        "cost_usd": 0.0013,
    }


def test_flatten_attrs_handles_empty_or_none() -> None:
    assert flatten_attrs([]) == {}
    assert flatten_attrs(None) == {}
