import ast


class LineVisitor(ast.NodeVisitor):
    """LineVisitor is an AST NodeVisitor that computes the dotted path of the innermost
    scope (class or function) that contains a given line in the source code.

    The visitor traverses the AST, maintains a stack of active scope names, and records
    the current dotted path whenever the target line falls inside a scope. The final
    result represents the nearest enclosing scope path for the specified line.

    Attributes:
        line: int
            The target line number for which to determine the containing scope path.
        stack: list[str]
            The stack of currently active scope names (e.g., class and function names).
        result: str | None
            The most recent dotted scope path containing the target line, or None if the
            line is not inside any tracked scope.
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
            if not node.lineno <= self.line <= node.end_lineno:
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
