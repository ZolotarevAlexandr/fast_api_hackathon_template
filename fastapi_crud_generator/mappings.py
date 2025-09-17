from __future__ import annotations

from typing import Any

_NO_DEFAULT = object()


def _coerce_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def normalize_logical_type(t: str) -> str:
    """
    Normalize a user-provided logical type token.
    Examples: "String" -> "str", "EMAIL" -> "email".
    """
    t_norm = (t or "").strip().lower()
    if t_norm in {"string"}:
        return "str"
    if t_norm in {"boolean"}:
        return "bool"
    return t_norm


def map_field_types(logical_type: str, params: dict[str, Any] | None = None) -> dict[str, str]:
    """
    Map a logical type + params to code-generation annotations and SQLAlchemy type expressions.

    Returns a dict with:
      - pydantic_annotation: for Pydantic models
      - route_param_annotation: for FastAPI route parameters
      - repo_annotation: for repository method signatures (no Pydantic-specifics)
      - orm_type_annotation: for SQLAlchemy Mapped[...] type hint
      - sa_type_expr: SQLAlchemy type expression for mapped_column(...)
    """
    lt = normalize_logical_type(logical_type)
    params = params or {}
    length = _coerce_int(params.get("length"))
    # base mappings
    if lt == "str":
        return {
            "pydantic_annotation": "str",
            "route_param_annotation": "str",
            "repo_annotation": "str",
            "orm_type_annotation": "str",
            "sa_type_expr": f"String({length})" if length is not None else "String()",
        }
    if lt == "email":
        # Keep EmailStr only at validation edges (schemas/routes); repos accept str.
        return {
            "pydantic_annotation": "EmailStr",
            "route_param_annotation": "EmailStr",
            "repo_annotation": "str",
            "orm_type_annotation": "str",
            "sa_type_expr": f"String({length})" if length is not None else "String()",
        }
    if lt == "int":
        return {
            "pydantic_annotation": "int",
            "route_param_annotation": "int",
            "repo_annotation": "int",
            "orm_type_annotation": "int",
            "sa_type_expr": "Integer()",
        }
    if lt == "bool":
        return {
            "pydantic_annotation": "bool",
            "route_param_annotation": "bool",
            "repo_annotation": "bool",
            "orm_type_annotation": "bool",
            "sa_type_expr": "Boolean()",
        }
    if lt == "float":
        return {
            "pydantic_annotation": "float",
            "route_param_annotation": "float",
            "repo_annotation": "float",
            "orm_type_annotation": "float",
            "sa_type_expr": "Float()",
        }
    # Fallback: treat as str
    return {
        "pydantic_annotation": "str",
        "route_param_annotation": "str",
        "repo_annotation": "str",
        "orm_type_annotation": "str",
        "sa_type_expr": f"String({length})" if length is not None else "String()",
    }


def render_default_repr(value: Any) -> tuple[str, bool]:
    """
    Return (code_repr, has_default) for a default value suitable for direct code emission.
    - Strings are quoted with repr, booleans and numbers are passed through, None becomes 'None'.
    - If value indicates 'no default' (e.g., None sentinel), has_default=False is returned.
    """
    if value is _NO_DEFAULT:
        return "", False
    if value is None:
        return "None", True
    return repr(value), True
