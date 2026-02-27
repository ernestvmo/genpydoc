import os.path
import tomllib
from typing import Any, Literal

import attr
from genpydoc.git_retriever.utils import is_git_repo, branch_exists
from genpydoc.utils.utils import find_project_root


class PostProcessingConfig:
    cleanup: bool = attr.ib(default=True)
    convert: bool = attr.ib(default=True)


@attr.s
class Config:
    VALID_STYLES = ("sphinx", "google")  # FIXME needed?
    VALID_LLM_PROVIDERS = ("openai",)

    root: str = find_project_root((os.path.dirname(__file__),))

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
    include_only_covered: bool = attr.ib(default=False)
    run_on_diff: bool = attr.ib(default=False)
    run_staged: bool = attr.ib(default=False)
    target_branch: str | None = attr.ib(default="main")
    use_llm_provider: Literal["openai"] = attr.ib(default="openai")
    use_model: str = attr.ib(default="gpt-5-nano")  # TODO validate
    post_processing: PostProcessingConfig = attr.ib(
        default=PostProcessingConfig()
    )

    @run_on_diff.validator
    def _validate_run_on_diff(self, _attribute, _value) -> None:
        if not is_git_repo(self.root):
            raise ValueError("Project is not connected to git.")

    @target_branch.validator
    def _validate_target_branch(self, _attribute, value) -> None:
        if not branch_exists(self.root, value):
            raise ValueError(
                f'Target branch "{value}" does not exist.{_attribute}'
            )

    @use_llm_provider.validator
    def _validate_llm_provider(self, _attribute, value) -> None:
        if value not in self.VALID_LLM_PROVIDERS:
            raise ValueError(
                f"Invalid LLM provider '{value}'.\nSelect one of the following: {', '.join(self.VALID_LLM_PROVIDERS)}"
            )

    @docstring_style.validator
    def _validate_style(self, _attribute, value) -> None:
        if value not in self.VALID_STYLES:
            raise ValueError(
                f"invalid docstring_style '{value}'.\nSelect one of the following: {', '.join(self.VALID_STYLES)}"
            )


def parse_pyproject_toml(path_config: str) -> dict[str, Any] | None:
    with open(path_config, "rb") as file:
        toml = tomllib.load(file)
    config = toml.get("tool", {}).get("genpydoc", {})
    return {k.replace("-", "_"): v for k, v in config.items()}
