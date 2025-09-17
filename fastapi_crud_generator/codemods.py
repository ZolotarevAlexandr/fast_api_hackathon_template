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
