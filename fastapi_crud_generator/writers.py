from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class FileExistsErrorWithPath(FileExistsError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"File already exists: {path}")
        self.path = path


@dataclass(frozen=True)
class FileWriteResult:
    path: Path
    action: str  # "created" | "overwritten"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_package(dir_path: Path) -> None:
    ensure_dir(dir_path)
    init_file = dir_path / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")


def write_text(path: Path, content: str, *, force: bool = False) -> FileWriteResult:
    ensure_dir(path.parent)
    if path.exists():
        if not force:
            raise FileExistsErrorWithPath(path)
        action = "overwritten"
    else:
        action = "created"
    path.write_text(content, encoding="utf-8")
    return FileWriteResult(path=path, action=action)


def compute_target_paths(src_dir: Path, module_name: str) -> dict[str, Path]:
    return {
        "schema": src_dir / "schemas" / f"{module_name}.py",
        "model": src_dir / "db" / "models" / f"{module_name}.py",
        "repository": src_dir / "db" / "repositories" / f"{module_name}.py",
        "routes": src_dir / "api" / module_name / "routes.py",
    }


def ensure_package_structure_for_targets(paths: Mapping[str, Path]) -> None:
    # Ensure leaf packages
    ensure_package(paths["schema"].parent)
    ensure_package(paths["model"].parent)
    ensure_package(paths["repository"].parent)
    ensure_package(paths["routes"].parent)
    # Ensure top-level package dirs also have __init__.py
    ensure_package(paths["routes"].parent.parent)      # src/api
    ensure_package(paths["repository"].parent.parent)  # src/db
    ensure_package(paths["model"].parent.parent)       # src/db
    ensure_package(paths["schema"].parent)             # src/schemas


def write_generated_files(
    paths: Mapping[str, Path],
    contents: Mapping[str, str],
    *,
    force: bool = False,
) -> list[FileWriteResult]:
    ensure_package_structure_for_targets(paths)
    results: list[FileWriteResult] = []
    results.append(write_text(paths["schema"], contents["schema"], force=force))
    results.append(write_text(paths["model"], contents["model"], force=force))
    results.append(write_text(paths["repository"], contents["repository"], force=force))
    results.append(write_text(paths["routes"], contents["routes"], force=force))
    return results
