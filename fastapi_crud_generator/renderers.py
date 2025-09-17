from __future__ import annotations

from collections.abc import Mapping
from importlib import resources as pkg_resources
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATE_SCHEMA = "schema.py.j2"
TEMPLATE_MODEL = "model.py.j2"
TEMPLATE_REPOSITORY = "repository.py.j2"
TEMPLATE_ROUTES = "routes.py.j2"


def _default_templates_dir() -> Path:
    """Auto-detect templates directory from package or fallback to relative path."""
    try:
        import fastapi_crud_generator  # noqa
        return Path(pkg_resources.files(fastapi_crud_generator)) / "templates"
    except (ImportError, AttributeError):
        return Path("fastapi_crud_generator") / "templates"


def create_environment(templates_dir: Path | None = None) -> Environment:
    """
    Create a Jinja2 Environment loading from the given templates directory.
    If templates_dir is None, auto-detect from package or use relative path.
    """
    if templates_dir is None:
        templates_dir = _default_templates_dir()

    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_schema(env: Environment, context: Mapping[str, Any]) -> str:
    return env.get_template(TEMPLATE_SCHEMA).render(**context)


def render_model(env: Environment, context: Mapping[str, Any]) -> str:
    return env.get_template(TEMPLATE_MODEL).render(**context)


def render_repository(env: Environment, context: Mapping[str, Any]) -> str:
    return env.get_template(TEMPLATE_REPOSITORY).render(**context)


def render_routes(env: Environment, context: Mapping[str, Any]) -> str:
    return env.get_template(TEMPLATE_ROUTES).render(**context)
