import ast


class LineVisitor(ast.NodeVisitor):
    """
    AST Node visitor for extracting the source of a specific line number.
    """

    line: int
    stack: list[str]
    result: str | None

    def __init__(self, source: str):
        self.tree = ast.parse(source)

    def get_scope(self, line: int) -> str:
        self.line = line
        self.stack = []
        self.result = None
        self.visit(self.tree)
        return self.result

    def visit(self, node) -> None:
        if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
            if not (node.lineno <= self.line <= node.end_lineno):
                return
        super().visit(node)

    def _visit_helper(
        self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        self.stack.append(node.name)
        self.result = ".".join(self.stack)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_helper(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_helper(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_helper(node)
