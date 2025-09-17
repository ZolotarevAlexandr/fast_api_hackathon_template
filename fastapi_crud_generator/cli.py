from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from fastapi_crud_generator.codemods import ensure_model_export, ensure_repository_dependency, ensure_router_registered
from fastapi_crud_generator.mappings import map_field_types, render_default_repr
from fastapi_crud_generator.parser import FieldSpec, parse_field_tokens
from fastapi_crud_generator.postgen import run_ruff_fix
from fastapi_crud_generator.renderers import (
    create_environment,
    render_model,
    render_repository,
    render_routes,
    render_schema,
)
from fastapi_crud_generator.writers import FileWriteResult, compute_target_paths, write_generated_files

app = typer.Typer(help="FastAPI CRUD generator")


def _build_context(
    model_name: str,
    module_name: str,
    table_name: str | None,
    id_param_name: str | None,
    field_specs: list[FieldSpec],
) -> dict[str, Any]:
    # Derivations
    ModelName = model_name
    resource_singular = module_name
    resource_plural = f"{module_name}s"
    tag_name = ModelName + "s"
    table = table_name or module_name
    id_param = id_param_name or f"{module_name}_id"

    fields_ctx: list[dict[str, Any]] = []
    for fs in field_specs:
        ty = map_field_types(fs.logical_type, fs.params)
        unique = bool(fs.params.get("unique", False))
        nullable = bool(fs.params.get("nullable", False))
        index = bool(fs.params.get("index", False))
        default = fs.params.get("default", None if "default" not in fs.params else fs.params["default"])
        default_repr, has_default = render_default_repr(default if "default" in fs.params else object())
        fields_ctx.append(
            {
                "name": fs.name,
                "pydantic_annotation": ty["pydantic_annotation"],
                "route_param_annotation": ty["route_param_annotation"],
                "repo_annotation": ty["repo_annotation"],
                "orm_type_annotation": ty["orm_type_annotation"],
                "sa_type_expr": ty["sa_type_expr"],
                "unique": unique,
                "nullable": nullable,
                "index": index,
                # For templates: treat "no default" as None with has_default flag distinguished if needed
                "default": default if "default" in fs.params else None,
                "default_repr": default_repr if has_default else "None",
            }
        )
    unique_fields = [f for f in fields_ctx if f["unique"]]

    return {
        "ModelName": ModelName,
        "module_name": module_name,
        "resource_singular": resource_singular,
        "resource_plural": resource_plural,
        "tag_name": tag_name,
        "table_name": table,
        "id_param_name": id_param,
        "fields": fields_ctx,
        "unique_fields": unique_fields,
    }


@app.callback()
def main_callback():
    pass


@app.command("generate")
def generate(
    model_name: str = typer.Argument(..., help="Name of the model/class (e.g., User)"),
    field_tokens: list[str] = typer.Argument(
        ..., help='Field specs: name:type[:params], e.g., "name:str:unique" "email:email:unique"'
    ),
    module_name: str | None = typer.Option(
        None, "--module", "-m", help="Module name/package (default: model name lowercased)"
    ),
    table_name: str | None = typer.Option(None, "--table-name", help="SQL table name (default: module name)"),
    id_param_name: str | None = typer.Option(None, "--id-param", help="Path param name (default: <module>_id)"),
    src_dir: Path = typer.Option(Path("src"), "--src-dir", help="Path to src directory"),
    templates_dir: Path | None = typer.Option(
        None, "--templates-dir", help="Path to Jinja2 templates directory (auto-detected if omitted)"
    ),
    app_file: Path = typer.Option(Path("src/api/app.py"), "--app-file", help="Path to FastAPI app module"),
    app_name: str = typer.Option("app", "--app-name", help="FastAPI instance variable name inside app_file"),
    register: bool = typer.Option(True, "--register/--no-register", help="Auto-include router in app.py"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
    ruff_strict: bool = typer.Option(False, "--ruff-strict", help="Fail generation if Ruff reports errors"),
    use_uv: bool = typer.Option(True, "--uv/--no-uv", help="Run post-gen Ruff via 'uv run' if available"),
) -> None:
    """
    Generate CRUD: schemas, model, repository, and routes for a resource.
    """
    mod_name = module_name or model_name.lower()
    specs = parse_field_tokens(field_tokens)

    # Build context
    ctx = _build_context(
        model_name=model_name,
        module_name=mod_name,
        table_name=table_name,
        id_param_name=id_param_name,
        field_specs=specs,
    )

    # Render
    env = create_environment(templates_dir)
    contents = {
        "schema": render_schema(env, ctx),
        "model": render_model(env, ctx),
        "repository": render_repository(env, ctx),
        "routes": render_routes(env, ctx),
    }

    # Write
    targets = compute_target_paths(src_dir, mod_name)
    results: list[FileWriteResult] = write_generated_files(targets, contents, force=force)

    # Codemod registration
    app_modified = False
    deps_modified = False
    if register:
        app_modified = ensure_router_registered(app_file, module_name=mod_name, app_name=app_name)
        deps_file = src_dir / "api" / "repositories" / "dependencies.py"
        if deps_file.exists():
            deps_modified = ensure_repository_dependency(deps_file, module_name=mod_name, model_name=model_name)

    models_init = src_dir / "db" / "models" / "__init__.py"
    models_init_modified = False
    if models_init.exists():
        models_init_modified = ensure_model_export(models_init, module_name=mod_name, model_name=model_name)

    # Post-gen lint/format
    run_ruff_fix(project_root=Path("."), strict=ruff_strict, use_uv=use_uv)

    # Output results
    typer.echo("Files written:")
    for r in results:
        # Show relative paths when possible
        try:
            rel = r.path.relative_to(Path(".").resolve())
            path_str = str(rel)
        except Exception:
            path_str = str(r.path)
        typer.echo(f" - {r.action}: {path_str}")

    if models_init.exists():
        typer.echo(f" - {'modified' if models_init_modified else 'unchanged'}: {models_init}")

    if register:
        typer.echo(f" - {'modified' if app_modified else 'unchanged'}: {app_file}")
        deps_file = src_dir / "api" / "repositories" / "dependencies.py"
        if deps_file.exists():
            typer.echo(f" - {'modified' if deps_modified else 'unchanged'}: {deps_file}")

    typer.echo(f"Generated CRUD for {model_name} in module '{mod_name}'.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
