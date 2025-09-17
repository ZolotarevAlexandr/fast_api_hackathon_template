from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import libcst as cst
from libcst import Module
from libcst.helpers import get_full_name_for_node


@dataclass
class RouterSpec:
    module_name: str
    import_module: str
    import_name: str
    alias: str
    app_name: str = "app"


class _RouterTransformer(cst.CSTTransformer):
    def __init__(self, spec: RouterSpec) -> None:
        super().__init__()
        self.spec = spec
        self.seen_import = False
        self.seen_include = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        full_module: str | None = get_full_name_for_node(node.module) if node.module else None
        if full_module == self.spec.import_module:
            for alias in node.names:
                if not isinstance(alias, cst.ImportAlias):
                    continue
                imported_name = getattr(alias.name, "value", None)
                asname = getattr(alias.asname.name, "value", None) if alias.asname else None
                if imported_name == self.spec.import_name and (asname in {None, self.spec.alias}):
                    self.seen_import = True

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:
        for small in node.body:
            if not isinstance(small, cst.Expr):
                continue
            call = small.value
            if not isinstance(call, cst.Call):
                continue
            func_name = get_full_name_for_node(call.func) or ""
            if func_name == f"{self.spec.app_name}.include_router":
                if (
                    call.args
                    and isinstance(call.args[0].value, cst.Name)
                    and call.args[0].value.value == self.spec.alias
                ):
                    self.seen_include = True

    def leave_Module(self, original_node: Module, updated_node: Module) -> Module:
        new_body = list(updated_node.body)

        if not self.seen_import:
            import_stmt = cst.parse_statement(
                f"from {self.spec.import_module} import {self.spec.import_name} as {self.spec.alias}  # noqa: E402\n"
            )
            insert_index = 0
            for i, stmt in enumerate(new_body):
                if isinstance(stmt, cst.SimpleStatementLine):
                    if any(isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body):
                        insert_index = i + 1
            new_body.insert(insert_index, import_stmt)

        if not self.seen_include:
            include_stmt = cst.parse_statement(f"{self.spec.app_name}.include_router({self.spec.alias})\n")
            new_body.append(include_stmt)

        return updated_node.with_changes(body=new_body)


def ensure_router_registered(app_py: Path, module_name: str, *, app_name: str = "app") -> bool:
    """
    Ensure src/api/app.py imports and includes the router for module_name.
    Returns True if the file was modified.
    """
    text = app_py.read_text(encoding="utf-8")
    mod = cst.parse_module(text)
    spec = RouterSpec(
        module_name=module_name,
        import_module=f"src.api.{module_name}.routes",
        import_name="router",
        alias=f"{module_name}_router",
        app_name=app_name,
    )
    transformer = _RouterTransformer(spec)
    new_mod = mod.visit(transformer)
    changed = new_mod.code != text
    if changed:
        app_py.write_text(new_mod.code, encoding="utf-8")
    return changed


@dataclass
class DepsSpec:
    module_name: str
    model_name: str
    import_module: str
    import_name: str
    func_name: str


class _DepsTransformer(cst.CSTTransformer):
    def __init__(self, spec: DepsSpec) -> None:
        super().__init__()
        self.spec = spec
        self.seen_import = False
        self.seen_func = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        full_module: str | None = get_full_name_for_node(node.module) if node.module else None
        if full_module == self.spec.import_module:
            for alias in node.names:
                if isinstance(alias, cst.ImportAlias):
                    if getattr(alias.name, "value", None) == self.spec.import_name:
                        self.seen_import = True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.name.value == self.spec.func_name:
            self.seen_func = True

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        new_body = list(updated_node.body)

        # Insert repository import if missing
        if not self.seen_import:
            import_stmt = cst.parse_statement(f"from {self.spec.import_module} import {self.spec.import_name}\n")
            insert_index = 0
            for i, stmt in enumerate(new_body):
                if isinstance(stmt, cst.SimpleStatementLine) and any(
                    isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
                ):
                    insert_index = i + 1
            new_body.insert(insert_index, import_stmt)

        # Append dependency getter if missing
        if not self.seen_func:
            func_src = (
                f"def {self.spec.func_name}(\n"
                f"    storage: AbstractSQLAlchemyStorage = Depends(get_storage),\n"
                f") -> {self.spec.import_name}:\n"
                f"    return {self.spec.import_name}(storage)\n"
            )
            func_stmt = cst.parse_statement(func_src)

            trailing_blanks = 0
            for node in reversed(new_body):
                if isinstance(node, cst.EmptyLine):
                    trailing_blanks += 1
                else:
                    break

            needed = max(0, 2 - trailing_blanks)
            for _ in range(needed):
                new_body.append(cst.EmptyLine())

            new_body.append(func_stmt)

        return updated_node.with_changes(body=new_body)


def ensure_repository_dependency(deps_py: Path, module_name: str, model_name: str) -> bool:
    """
    Ensure src/api/repositories/dependencies.py imports the new repository and
    defines a get_<module>_repository function. Returns True if modified.
    """
    text = deps_py.read_text(encoding="utf-8")
    mod = cst.parse_module(text)
    spec = DepsSpec(
        module_name=module_name,
        model_name=model_name,
        import_module=f"src.db.repositories.{module_name}",
        import_name=f"{model_name}Repository",
        func_name=f"get_{module_name}_repository",
    )
    transformer = _DepsTransformer(spec)
    new_mod = mod.visit(transformer)
    changed = new_mod.code != text
    if changed:
        deps_py.write_text(new_mod.code, encoding="utf-8")
    return changed


@dataclass
class ModelExportSpec:
    module_name: str
    model_name: str


class _ModelExportTransformer(cst.CSTTransformer):
    def __init__(self, spec: ModelExportSpec) -> None:
        super().__init__()
        self.spec = spec
        self.seen_import = False
        self.all_idx: int | None = None
        self.current_all_names: list[str] = []

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        mod = node.module
        full = get_full_name_for_node(mod) if mod else None
        if full == f"src.db.models.{self.spec.module_name}":
            for alias in node.names:
                if isinstance(alias, cst.ImportAlias) and getattr(alias.name, "value", "") == self.spec.model_name:
                    self.seen_import = True

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:
        if len(node.body) != 1 or not isinstance(node.body[0], cst.Assign):
            return
        assign = node.body[0]
        if len(assign.targets) != 1:
            return
        tgt = assign.targets[0].target
        if isinstance(tgt, cst.Name) and tgt.value == "__all__":
            # record index in leave_Module and capture current names
            self.current_all_names = []
            val = assign.value
            if isinstance(val, (cst.List, cst.Tuple)):
                for el in val.elements:
                    if isinstance(el, cst.Element) and isinstance(el.value, cst.SimpleString):
                        self.current_all_names.append(el.value.evaluated_value)

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        body = list(updated_node.body)

        # Ensure import: from src.db.models.<module> import <ModelName>
        if not self.seen_import:
            imp = cst.ImportFrom(
                module=cst.parse_expression(f"src.db.models.{self.spec.module_name}"),
                names=[cst.ImportAlias(name=cst.Name(self.spec.model_name))],
            )
            imp_stmt = cst.SimpleStatementLine(body=[imp])
            insert_idx = 0
            for i, stmt in enumerate(body):
                if isinstance(stmt, cst.SimpleStatementLine) and any(
                    isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
                ):
                    insert_idx = i + 1
            body.insert(insert_idx, imp_stmt)

        # Locate existing __all__ statement index after potential import insertion
        all_idx: int | None = None
        for i, stmt in enumerate(body):
            if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Assign):
                assign = stmt.body[0]
                if len(assign.targets) == 1 and isinstance(assign.targets[0].target, cst.Name) and assign.targets[0].target.value == "__all__":
                    all_idx = i
                    break

        # Build desired __all__ names with one-per-line
        names: list[str] = self.current_all_names[:] if all_idx is not None else []
        if "Base" not in names:
            names.insert(0, "Base")
        if self.spec.model_name not in names:
            names.append(self.spec.model_name)

        def build_all_stmt(lines: list[str]) -> cst.SimpleStatementLine:
            # Force multi-line, one item per line, with trailing commas and closing bracket on its own line
            inner = ",\n    ".join(repr(n) for n in lines) + ","
            src = "__all__ = [\n    " + inner + "\n]\n"
            return cst.parse_statement(src)

        all_stmt = build_all_stmt(names)

        if all_idx is None:
            # Insert __all__ after the last import block
            last_import_idx = -1
            for i, stmt in enumerate(body):
                if isinstance(stmt, cst.SimpleStatementLine) and any(
                    isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
                ):
                    last_import_idx = i
            insert_at = last_import_idx + 1

            # Normalize to exactly one blank line between imports and __all__
            # Remove any existing EmptyLine directly after the last import
            while insert_at < len(body) and isinstance(body[insert_at], cst.EmptyLine):
                body.pop(insert_at)
            # Insert exactly one blank line
            body.insert(insert_at, cst.EmptyLine())
            insert_at += 1
            body.insert(insert_at, all_stmt)
        else:
            # Replace existing __all__ with formatted version
            body[all_idx] = all_stmt
            # Ensure exactly one blank line before __all__
            # Remove any EmptyLine directly before __all__
            j = all_idx - 1
            removed = 0
            while j >= 0 and isinstance(body[j], cst.EmptyLine):
                body.pop(j)
                all_idx -= 1
                j -= 1
                removed += 1
            # Insert exactly one blank line
            body.insert(all_idx, cst.EmptyLine())

        return updated_node.with_changes(body=body)


def ensure_model_export(models_init_py: Path, module_name: str, model_name: str) -> bool:
    """
    Ensure src/db/models/__init__.py imports the model and formats __all__ as a multi-line list
    with a single blank line separating imports and __all__. Returns True if modified.
    """
    src = models_init_py.read_text(encoding="utf-8")
    mod = cst.parse_module(src)
    new_mod = mod.visit(_ModelExportTransformer(ModelExportSpec(module_name, model_name)))
    if new_mod.code != src:
        models_init_py.write_text(new_mod.code, encoding="utf-8")
        return True
    return False
