import os.path
import re
import tomllib
from pathlib import Path
from typing import Any, Literal

import attr
import click
from click import Context, Parameter


class PostProcessingConfig:
    cleanup: bool = attr.ib(default=True)
    convert: bool = attr.ib(default=True)


@attr.s
class Config:
    VALID_STYLES = ("sphinx", "google")  # FIXME needed?
    VALID_MODELS = ("openai",)

    docstring_style: str = attr.ib(default="sphinx")
    fail_under: float = attr.ib(default=80.0)
    ignore_magic: bool = attr.ib(default=False)
    ignore_module: bool = attr.ib(default=True)
    ignore_private: bool = attr.ib(default=False)
    ignore_semiprivate: bool = attr.ib(default=False)
    ignore_init_method: bool = attr.ib(default=True)
    ignore_nested_classes: bool = attr.ib(default=False)
    ignore_nested_functions: bool = attr.ib(default=False)
    ignore_property_setters: bool = attr.ib(default=False)
    ignore_property_decorators: bool = attr.ib(default=False)
    ignore_overloaded_functions: bool = attr.ib(default=False)
    include_regex: list[re.Pattern[str]] | None = attr.ib(default=None)
    omit_covered_files: bool = attr.ib(default=False)
    include_only_covered: bool = attr.ib(default=True)
    run_on_diff: bool = attr.ib(default=True)
    use_llm_provider: Literal["openai"] = attr.ib(default="openai")  # TODO validate
    use_model: str = attr.ib(default="gpt-5-nano")  # TODO validate
    post_processing: PostProcessingConfig = attr.ib(default=PostProcessingConfig())

    @docstring_style.validator
    def _validate_style(self, _attribute, value):
        if value not in self.VALID_STYLES:
            raise ValueError(
                f"invalid docstring_style '{value}'.\nSelect one of the following: {', '.join(self.VALID_STYLES)}"
            )


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
    config = toml.get("tool", {}).get("pydocai")
    return {k.replace("-", "_"): v for k, v in config.items()}


def read_config_file(ctx: Context, _param: Parameter, value: str | None) -> str | None:
    if not value:
        paths = ctx.params.get("paths")
        if not paths:
            paths = (os.path.abspath(os.getcwd()),)
        value = find_project_root(paths)
        if value is None:
            return None

    # config = None
    if value.endswith(".toml"):
        try:
            config = parse_pyproject_toml(value)
        except (tomllib.TOMLDecodeError, OSError) as err:
            raise click.FileError(filename=value, hint=f"Error reading configuration file: {err}.")
    else:
        print("not handled now")
        return None

    if ctx.default_map is None:
        ctx.default_map = {}

    ctx.default_map.update(config)
    return value
