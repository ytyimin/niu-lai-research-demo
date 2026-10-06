"""Small dependency-free validator for the schema subset used by this prototype."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RecordValidationError(ValueError):
    pass


TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
    "null": type(None),
}


def validate_value(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected_type = schema.get("type")
    if expected_type:
        expected = TYPE_MAP[expected_type]
        if expected_type in {"integer", "number"} and isinstance(value, bool):
            raise RecordValidationError(f"{path} must be {expected_type}")
        if not isinstance(value, expected):
            raise RecordValidationError(f"{path} must be {expected_type}")

    if "enum" in schema and value not in schema["enum"]:
        raise RecordValidationError(f"{path} must be one of {schema['enum']}")

    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        raise RecordValidationError(f"{path} is shorter than minLength")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise RecordValidationError(f"{path} has too few items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_value(item, item_schema, f"{path}[{index}]")

    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                raise RecordValidationError(f"{path}.{required} is required")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                validate_value(child, properties[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                raise RecordValidationError(f"{path}.{key} is not allowed")


def validate_record(schema_root: Path, record_type: str, value: dict[str, Any]) -> None:
    path = schema_root / f"{record_type}.schema.json"
    with path.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    validate_value(value, schema)

