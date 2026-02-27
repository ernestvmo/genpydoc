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
    common_base = min((Path(src).resolve() for src in srcs))
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
    """Reads and applies a configuration file for the given Click context.

    Purpose
        Determines the configuration file path to be used for the current command.
        If the provided value is empty or None, it attempts to locate a project
        configuration by inspecting paths from the context (ctx.params["paths"])
        or the current working directory. If a configuration file ends with ".toml",
        it is parsed via parse_pyproject_toml. In case of parsing or I/O errors, a
        click.FileError is raised with the filename and an informative hint.

    Side effects
        If a configuration is found and parsed, its contents are merged into
        ctx.default_map, allowing command-line options to be overridden by the
        configuration values.

    Parameters
        ctx: Context object containing runtime parameters and a default_map. Used to
             locate configuration paths and to store the loaded configuration.
        _param: The click.Parameter object associated with this callback (unused).
        value: The current value for the configuration option. If falsy, the function
               attempts to discover a configuration file; otherwise, this value is
               returned (after potential TOML parsing).

    Raises
        click.FileError: If the TOML configuration file cannot be read or parsed.

    Returns
        Optional[str]
            The path to the configuration file that was used, or None if no configuration
            could be determined.
    """
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
    return None


def get_common_base(files: list[str]) -> str:
    commonbase = Path(commonprefix(files))
    while not commonbase.exists():
        commonbase = commonbase.parent
    return str(commonbase)
