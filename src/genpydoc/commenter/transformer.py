import ast
import subprocess
from pathlib import Path
from genpydoc.config.config import Config

DocumentableFunc = ast.AsyncFunctionDef | ast.FunctionDef
DocumentableFuncOrClass = DocumentableFunc | ast.ClassDef
DocumentableNode = DocumentableFuncOrClass | ast.Module


class Transformer(ast.NodeTransformer):
    """Transformer that injects or replaces docstrings on designated AST nodes.

    Overview:
    This AST transformer traverses Python code and, for nodes representing
    documentable entities (such as classes or functions) whose names are present
    in a provided mapping, it inserts a docstring at the top of the node's body
    or replaces an existing one with the corresponding content. The content is
    cleaned by removing leading and trailing triple quotes.

    Attributes:
        config: Config
            Configuration data used by the transformer.
        comments: dict[str, str]
            Mapping from node names to their docstring content. The content may
            include triple-quoted strings; surrounding quotes are removed prior
            to insertion.
    """

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
        """Visit a ClassDef node during AST traversal.

        This method visits the given ClassDef node by first delegating to the default
        visitor to traverse its child nodes, and then applies internal post-processing
        via the _visit_helper, returning the resulting node.

        Args:
            node: DocumentableFuncOrClass
                The ClassDef node to visit.

        Returns:
            DocumentableFuncOrClass
                The processed ClassDef node.

        Raises:
            Exception
                Propagates exceptions raised by the underlying visitors or helpers
                (e.g., generic_visit or _visit_helper).

        Attributes:
            _visit_helper: Internal helper used to perform post-visit transformations on the node.
        """
        self.generic_visit(node=node)
        return self._visit_helper(node=node)

    def visit_FunctionDef(
        self, node: DocumentableFuncOrClass
    ) -> DocumentableFuncOrClass:
        """Visits a FunctionDef node in the AST.

        This method first traverses the node's children by calling generic_visit, then
        delegates to _visit_helper to perform any function-definition-specific
        processing and returns its result.

        Args:
            node: DocumentableFuncOrClass
                The AST node representing a function definition or similar
                function-like element to visit.

        Attributes:
            node: DocumentableFuncOrClass
                The AST node currently being visited. This is the same object as the
                input parameter.

        Returns:
            DocumentableFuncOrClass
                The node after applying the function-specific visiting logic.

        Raises:
            Exception
                Any exception raised by generic_visit or _visit_helper during traversal
                or processing.
        """
        self.generic_visit(node=node)
        return self._visit_helper(node=node)

    def visit_AsyncFunctionDef(
        self, node: DocumentableFuncOrClass
    ) -> DocumentableFuncOrClass:
        """Visit an AsyncFunctionDef node.

        This visitor recursively visits the child nodes of the given AsyncFunctionDef node
        via generic_visit and then constructs a DocumentableFuncOrClass representation by
        delegating to the internal _visit_helper.

        Args:
            node (DocumentableFuncOrClass): The AST node corresponding to an asynchronous
                function (async def) or an enclosing class to process.

        Attributes:
            generic_visit (method): Inherited visitor that traverses child nodes.
            _visit_helper (method): Internal helper that builds and returns the final
                DocumentableFuncOrClass representation.

        Returns:
            DocumentableFuncOrClass: The documentable representation of the AsyncFunctionDef
                node produced by _visit_helper.

        Raises:
            Exception: Propagates any error raised during child-node visitation or during
                the transformation performed by _visit_helper.
        """
        self.generic_visit(node=node)
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
