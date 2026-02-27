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
    """Config

    Container for configuration options used by the docstring generation/validation
    tool. This class stores all user-configurable parameters, their defaults, and
    basic validation hooks to ensure the configuration remains consistent with the
    tool's capabilities.

    Attributes:
        VALID_STYLES: Tuple[str, ...]
            Supported docstring styles.
        VALID_LLM_PROVIDERS: Tuple[str, ...]
            Supported LLM providers.
        root: str
            Path to the project root determined at runtime.
        docstring_style: str
            Style used for docstrings. Must be one of VALID_STYLES.
        ignore_magic: bool
            Exclude Python magic methods/attributes from processing.
        ignore_module: bool
            Exclude module-level items from processing.
        ignore_private: bool
            Exclude private names (leading underscore) from processing.
        ignore_semiprivate: bool
            Exclude semiprivate names from processing.
        ignore_init_method: bool
            Exclude __init__ methods from processing.
        ignore_nested_classes: bool
            Exclude nested classes from processing.
        ignore_nested_functions: bool
            Exclude nested functions from processing.
        ignore_property_setters: bool
            Exclude property setter methods from processing.
        ignore_property_decorators: bool
            Exclude property decorators from processing.
        ignore_overloaded_functions: bool
            Exclude overloaded function variants from processing.
        include_only_covered: bool
            Include only items that are covered by tests.
        run_on_diff: bool
            Run the tool only when there are diffs in the repository.
        run_staged: bool
            Run the tool only on staged changes.
        target_branch: str | None
            Target branch to compare against. Defaults to "main".
        use_llm_provider: Literal["openai"]
            LLM provider to use for generation/analysis.
        use_model: str
            Model name to use for the LLM. (TODO: validate the value.)
        post_processing: PostProcessingConfig
            Configuration for post-processing steps after generation/analysis.
    """

    VALID_STYLES = ("sphinx", "google")
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
    include_only_covered: bool = attr.ib(default=True)
    run_on_diff: bool = attr.ib(default=False)
    run_staged: bool = attr.ib(default=False)
    target_branch: str | None = attr.ib(default="main")
    use_llm_provider: Literal["openai"] = attr.ib(default="openai")
    use_model: str = attr.ib(default="gpt-5-nano")
    post_processing: PostProcessingConfig = attr.ib(
        default=PostProcessingConfig()
    )

    @run_on_diff.validator
    def _validate_run_on_diff(self, _attribute, _value) -> None:
        """Validate preconditions for performing operations on diffs.

        This method ensures the current project root is a git repository. If the
        project is not connected to git, it raises a ValueError to signal the
        invalid state.

        Args:
            self: Instance of the containing class.
            _attribute: Attribute name to validate (unused; kept for interface compatibility).
            _value: Value to validate (unused; kept for interface compatibility).

        Attributes:
            root: Path to the project root directory used to determine git repository status.

        Raises:
            ValueError: If the project is not connected to git.
        """
        if not is_git_repo(self.root):
            raise ValueError("Project is not connected to git.")

    @target_branch.validator
    def _validate_target_branch(self, _attribute, value) -> None:
        """Validate the target branch by ensuring it exists in the repository.

        This method checks that the provided branch name (value) refers to an existing branch
        in the repository rooted at self.root. If the branch does not exist, a
        ValueError is raised including contextual information from _attribute.

        Attributes:
            _attribute: Contextual attribute name used in the error message to identify the
                field being validated.
            value: The target branch name to validate.

        Raises:
            ValueError: If the target branch does not exist.
        """
        if not branch_exists(self.root, value):
            raise ValueError(
                f'Target branch "{value}" does not exist.{_attribute}'
            )

    @use_llm_provider.validator
    def _validate_llm_provider(self, _attribute, value) -> None:
        """Validate that the provided LLM provider is included in the supported set.

        This validator ensures that the given provider value is present in the
        class-level VALID_LLM_PROVIDERS collection. If it is not, a ValueError is raised
        with a message that lists the allowed providers.

        Args:
            _attribute: The attribute name being validated. This parameter is part of the
                expected validator signature but is unused in this implementation.
            value: The LLM provider value to validate.

        Raises:
            ValueError: If value is not one of the valid providers. The error message includes
                the invalid value and a list of valid providers.

        Attributes:
            VALID_LLM_PROVIDERS: A collection of valid LLM provider identifiers used during
                validation.
        """
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
    """Parse configuration for genpydoc from a pyproject.toml file.

    This function opens the TOML file at path_config, parses it, and returns a
    dictionary derived from the [tool.genpydoc] table. Each key in the dictionary
    is converted to use underscores instead of hyphens to ensure valid Python
    identifiers.

    Args:
        path_config (str): Path to the pyproject.toml file to load.

    Returns:
        dict[str, Any]: A dictionary containing the configuration values found under
            the [tool.genpydoc] table, with keys hyphenated replaced by underscores.
            If the [tool.genpydoc] table is not present, an empty dictionary is returned.

    Raises:
        FileNotFoundError: If the file at path_config does not exist.
        OSError: If an OS error occurs when reading the file.
        tomllib.TOMLDecodeError: If the file content is not valid TOML.
    """
    with open(path_config, "rb") as file:
        toml = tomllib.load(file)
    config = toml.get("tool", {}).get("genpydoc", {})
    return {k.replace("-", "_"): v for k, v in config.items()}
