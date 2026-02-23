from os.path import commonprefix
from pathlib import Path
import os
import tomllib
from typing import Any, Sequence

import click
from click import Context, Parameter


def find_project_root(srcs: list[str]) -> Path:
    if not srcs:
        return Path("/").resolve()
    common_base = min(Path(src).resolve() for src in srcs)
    if common_base.is_dir():
        common_base /= "_"

    for directory in common_base.parents:
        if (directory / ".git").exists():
            return directory
        if (directory / "pyproject.toml").is_file():
            return directory

    return directory


def parse_pyproject_toml(path_config: str) -> dict[str, Any] | None:
    with open(path_config, "rb") as file:
        toml = tomllib.load(file)
    config = toml.get("tool", {}).get("genpydoc")
    return {k.replace("-", "_"): v for k, v in config.items()}


def read_config_file(
    ctx: Context, _param: Parameter, value: str | None
) -> str | None:
    if not value:
        paths = ctx.params.get("paths")
        if not paths:
            paths = (os.path.abspath(os.getcwd()),)
        value = find_project_config(paths)
        if value is None:
            return None

    if value.endswith(".toml"):
        try:
            config = parse_pyproject_toml(value)
        except (tomllib.TOMLDecodeError, OSError) as err:
            raise click.FileError(
                filename=value,
                hint=f"Error reading configuration file: {err}.",
            )

    if ctx.default_map is None:
        ctx.default_map = {}

    ctx.default_map.update(config)
    return value


def find_project_config(path_search_start: Sequence[str]) -> str | None:
    """Find the absolute filepath to a pyproject.toml if it exists."""
    project_root = find_project_root(path_search_start)
    pyproject_toml = project_root / "pyproject.toml"
    if pyproject_toml.is_file():
        return str(pyproject_toml)
    print()
    return None


def get_common_base(files: list[str]) -> str:
    commonbase = Path(commonprefix(files))
    while not commonbase.exists():
        commonbase = commonbase.parent
    return str(commonbase)
