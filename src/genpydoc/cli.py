import os

import click
from genpydoc.config.config import Config
from genpydoc.documenter import Documenter
from genpydoc.utils.utils import read_config_file


@click.command()
@click.option(
    "-m",
    "--ignore-magic",
    is_flag=True,
    default=False,
    show_default=False,
    help=(
        "Ignore all magic methods of classes.  [default: False]\n\nNOTE: This "
        "does not include the `__init__` method. To ignore `__init__` methods, "
        "use `--ignore-init-method`."
    ),
)
@click.option(
    "-C",
    "--ignore-nested-classes",
    is_flag=True,
    default=False,
    show_default=True,
    help="Ignore nested classes.",
)
@click.option(
    "-n",
    "--ignore-nested-functions",
    is_flag=True,
    default=False,
    show_default=True,
    help="Ignore nested functions and methods.",
)
@click.option(
    "-O",
    "--ignore-overloaded-functions",
    is_flag=True,
    default=False,
    show_default=True,
    help="Ignore `@typing.overload`-decorated functions.",
)
@click.option(
    "-p",
    "--ignore-private",
    is_flag=True,
    default=False,
    show_default=False,
    help=(
        "Ignore private classes, methods, and functions starting with two "
        "underscores.  [default: False]"
        "\n\nNOTE: This does not include magic methods; use `--ignore-magic` "
        "and/or `--ignore-init-method` instead."
    ),
)
@click.option(
    "-P",
    "--ignore-property-decorators",
    is_flag=True,
    default=False,
    show_default=True,
    help="Ignore methods with property setter/getter/deleter decorators.",
)
@click.option(
    "-S",
    "--ignore-setters",
    is_flag=True,
    default=False,
    show_default=True,
    help="Ignore methods with property setter decorators.",
)
@click.option(
    "-s",
    "--ignore-semiprivate",
    is_flag=True,
    default=False,
    show_default=True,
    help=(
        "Ignore semiprivate classes, methods, and functions starting with a "
        "single underscore."
    ),
)
@click.option(
    "-o",
    "--include-only-covered",
    is_flag=True,
    default=False,
    show_default=True,
    help="Only include Node that have a docstring in the processing.",
)
@click.option(
    "-D",
    "--run-on-diff",
    is_flag=True,
    default=False,
    show_default=True,
    help="Only run the evaluator on Git diffed Nodes.",
)
@click.option(
    "-d",
    "--run-staged",
    is_flag=True,
    default=False,
    show_default=True,
    help="Only run the evaluator on Git diffed Nodes.",
)
@click.option(
    "--use-llm-provider",
    type=click.Choice(["openai"]),
    default="openai",
    show_default=True,
    help="Select the LLM provider.",
)
@click.option(
    "--target-branch",
    type=click.STRING,
    default="main",
    show_default=True,
    help="Provide the target branch for running git comparison.",
)
@click.option(
    "--use-model",
    type=click.Choice(["gpt-5-nano"]),
    default="gpt-5-nano",
    show_default=True,
    help="Select which LLM model to use for documenting.",
)
@click.option(
    "--style",
    type=click.Choice(["google", "numpy", "epytext", "reST"]),
    default="google",
    show_default=True,
    help="Docstring types allowed.",
)
@click.help_option("-h", "--help")
@click.argument(
    "paths",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=True,
        writable=False,
        readable=True,
        resolve_path=True,
    ),
    is_eager=True,
    nargs=-1,
)
@click.option(
    "-c",
    "--config",
    type=click.Path(
        exists=False, file_okay=True, dir_okay=False, readable=True
    ),
    is_eager=True,
    callback=read_config_file,
    help="Read configuration from `pyproject.toml` or `setup.cfg`.",
)
def main(
    paths: list[str] | None,
    ignore_magic: bool,
    ignore_private: bool,
    ignore_semiprivate: bool,
    ignore_nested_classes: bool,
    ignore_nested_functions: bool,
    ignore_setters: bool,
    ignore_property_decorators: bool,
    ignore_overloaded_functions: bool,
    include_only_covered: bool,
    run_on_diff: bool,
    run_staged: bool,
    target_branch: str,
    use_llm_provider: str,
    use_model: str,
    style: str,
    config: str | None,
):
    config = Config(
        docstring_style=style,
        ignore_magic=ignore_magic,
        ignore_private=ignore_private,
        ignore_semiprivate=ignore_semiprivate,
        ignore_nested_classes=ignore_nested_classes,
        ignore_nested_functions=ignore_nested_functions,
        ignore_property_setters=ignore_setters,
        ignore_property_decorators=ignore_property_decorators,
        ignore_overloaded_functions=ignore_overloaded_functions,
        include_only_covered=include_only_covered,
        run_on_diff=run_on_diff,
        run_staged=run_staged,
        target_branch=target_branch,
        use_llm_provider=use_llm_provider,
        use_model=use_model,
    )
    if not paths:
        paths = [os.path.abspath(os.getcwd())]

    print(target_branch)

    doc = Documenter(config)
    doc.document(paths)
