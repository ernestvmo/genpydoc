import ast
import subprocess
from pathlib import Path
from genpydoc.config.config import Config

DocumentableFunc = ast.AsyncFunctionDef | ast.FunctionDef
DocumentableFuncOrClass = DocumentableFunc | ast.ClassDef
DocumentableNode = DocumentableFuncOrClass | ast.Module


class Transformer(ast.NodeTransformer):
    config: Config
    comments: dict[str, str]

    def __init__(self, config: Config, comments: dict[str, str]):
        super().__init__()
        self.config = config
        self.comments = comments

    def _visit_helper(self, node: DocumentableNode) -> DocumentableNode:
        if node.name not in self.comments:
            return node
        new_docstring = (
            self.comments[node.name].removeprefix('"""').removesuffix('"""')
        )
        new_doc_code = ast.Expr(value=ast.Constant(value=new_docstring))
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(getattr(node.body[0], "value", None), ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body[0] = new_doc_code
        else:
            node.body.insert(0, new_doc_code)
        return node

    def visit_ClassDef(
        self, node: DocumentableFuncOrClass
    ) -> DocumentableFuncOrClass:
        return self._visit_helper(node=node)

    def visit_FunctionDef(
        self, node: DocumentableFuncOrClass
    ) -> DocumentableFuncOrClass:
        return self._visit_helper(node=node)

    def visit_AsyncFunctionDef(
        self, node: DocumentableFuncOrClass
    ) -> DocumentableFuncOrClass:
        return self._visit_helper(node=node)


class Parser:
    def __init__(self, config: Config):
        self.config = config

    def process(self, filepath: Path, comments: dict[str, str]) -> None:
        with open(filepath) as file:
            source = file.read()
        parsed_tree = ast.parse(source)
        t = Transformer(config=self.config, comments=comments)
        t.visit(parsed_tree)
        filepath.write_text(ast.unparse(parsed_tree))
        if (
            self.config.post_processing.cleanup
            or self.config.post_processing.convert
        ):
            self.post_process(
                filepath,
                cleanup=self.config.post_processing.cleanup,
                convert=self.config.post_processing.convert,
            )

    def post_process(
        self, filepath: str | Path, cleanup: bool = True, convert: bool = True
    ) -> None:
        if cleanup:
            subprocess.run(f'black "{filepath}" -q', shell=True)
        if convert:
            if self.config.docstring_style not in [
                "google",
                "numpy",
                "epytext",
                "reST",
            ]:
                raise ValueError(
                    "Style cannot be converted to with docconvert."
                )
            subprocess.run(
                f'docconvert "{filepath}" --output {self.config.docstring_style} --in-place',
                shell=True,
                input="y\n",
                text=True,
            )
