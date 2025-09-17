from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

from fastapi_crud_generator.mappings import normalize_logical_type


@dataclass
class FieldSpec:
    name: str
    logical_type: str
    params: dict[str, Any]


def parse_field_token(token: str) -> FieldSpec:
    """
    Parse a single field token: name:type[:param][=value]...
    Examples:
      - name:str:unique
      - email:email:unique
      - title:str:length=120
      - is_active:bool:default=True
      - age:int:nullable
    """
    parts = [p for p in token.split(":") if p != ""]
    if len(parts) < 2:
        raise ValueError(f"Invalid field spec (need at least name:type): {token}")
    name = parts[0].strip()
    logical_type = normalize_logical_type(parts[1].strip())
    params: dict[str, Any] = {}

    for raw in parts[2:]:
        if "=" in raw:
            key, val = raw.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            # Try literal eval for numbers, bools, strings, None
            try:
                lit = ast.literal_eval(val)
            except Exception:
                lit = val  # fallback to raw string
            params[key] = lit
        else:
            # flag param
            key = raw.strip().lower()
            params[key] = True

    return FieldSpec(name=name, logical_type=logical_type, params=params)


def parse_field_tokens(tokens: list[str]) -> list[FieldSpec]:
    return [parse_field_token(t) for t in tokens]
