import tomllib
from typing import Any, Literal, Sequence

import attr
from genpydoc.utils.utils import find_project_root


class PostProcessingConfig:
    cleanup: bool = attr.ib(default=True)
    convert: bool = attr.ib(default=True)


@attr.s
class Config:
    VALID_STYLES = ("sphinx", "google")  # FIXME needed?
    VALID_MODELS = ("openai",)

    docstring_style: str = attr.ib(default="sphinx")
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
    include_only_covered: bool = attr.ib(default=True)
    run_on_diff: bool = attr.ib(default=True)
    use_llm_provider: Literal["openai"] = attr.ib(
        default="openai"
    )  # TODO validate
    use_model: str = attr.ib(default="gpt-5-nano")  # TODO validate
    post_processing: PostProcessingConfig = attr.ib(
        default=PostProcessingConfig()
    )

    @docstring_style.validator
    def _validate_style(self, _attribute, value) -> None:
        if value not in self.VALID_STYLES:
            raise ValueError(
                f"invalid docstring_style '{value}'.\nSelect one of the following: {', '.join(self.VALID_STYLES)}"
            )


def find_project_config(path_search_start: Sequence[str]) -> str | None:
    """Find the absolute filepath to a pyproject.toml if it exists."""
    project_root = find_project_root(path_search_start)
    pyproject_toml = project_root / "pyproject.toml"
    if pyproject_toml.is_file():
        return str(pyproject_toml)

    setup_cfg = project_root / "setup.cfg"
    return str(setup_cfg) if setup_cfg.is_file() else None


def parse_pyproject_toml(path_config: str) -> dict[str, Any] | None:
    with open(path_config, "rb") as file:
        toml = tomllib.load(file)
    config = toml.get("tool", {}).get("genpydoc")
    return {k.replace("-", "_"): v for k, v in config.items()}
