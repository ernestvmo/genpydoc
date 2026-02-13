import ast
import os.path
from typing import Self
import attr
from pydocai.config.config import Config

DocumentableFunc = ast.AsyncFunctionDef | ast.FunctionDef
DocumentableFuncOrClass = DocumentableFunc | ast.ClassDef
DocumentableNode = DocumentableFuncOrClass | ast.Module


@attr.s(eq=False)
class CovNode:
    """Coverage of an AST Node.

    Args:
        str name: Name of node (module, class, method or function
            names).
        str path: Pseudo-import path to node (i.e. ``sample.py:
            MyClass.my_method``).
        int level: Level of recursiveness/indentation.
        int lineno: Line number of class, method, or function.
        bool covered: Has a docstring.
        str node_type: Type of node (e.g "module", "class", or
            "function").
        bool is_nested_func: If the node itself is a nested function
            or method.
        bool is_nested_cls: If the node itself is a nested class.
        str docstring: The docstring of the node.
        str code: The source code of the node.
        CovNode parent: Parent node of current CovNode, if any.
    """

    name: str = attr.field()
    path: str = attr.field()
    level: int = attr.field()
    lineno: int = attr.field()
    covered: bool = attr.field()
    node_type: str = attr.field()
    is_nested_func: bool = attr.field()
    is_nested_cls: bool = attr.field()
    parent: Self = attr.field()
    file: str = attr.field()
    docstring: str | None = attr.field(default=None)
    code: str | None = attr.field(default=None)


class Visitor(ast.NodeVisitor):
    """Visitor is a NodeVisitor that traverses a Python AST to collect information about
    docstrings for modules, classes, and functions. During traversal, it builds
    CovNode records for each visitable node, including metadata such as the node's
    name, path, type, location, and associated docstring (when present). It also
    provides sanitized code with any docstrings removed and applies configuration
    driven ignore rules (e.g., private/semiprivate, __init__, magic methods,
    property decorators, overloads).

    Attributes:
        filename (str): The name of the file being analyzed.
        config (Config): Configuration controlling ignore rules and options.
        source (str): The full source code corresponding to the AST being visited.
        stack (list[CovNode]): Stack of CovNodes representing the current nesting context.
        nodes (list[CovNode]): All CovNodes discovered during traversal.
    """

    def __init__(self, filename: str, config: Config, source: str):
        self.filename = filename
        self.config = config
        self.source: str = source
        self.stack: list[CovNode] = []
        self.nodes: list[CovNode] = []

    @staticmethod
    def _has_doc(node: DocumentableNode) -> bool:
        """Return whether the node has docstrings."""
        return (
            ast.get_docstring(node) is not None
            and ast.get_docstring(node).strip() != ""
        )

    @staticmethod
    def _get_sanitized_docstring(node: DocumentableNode) -> str:
        """Returns a sanitized (stripped of whitespace) version of the docstring."""
        return ast.get_docstring(node).strip()

    @staticmethod
    def _remove_docstring_from_source(code: str, docstring: str) -> str:
        """Removes docstrings from the source code."""
        docstring = ['"""', *docstring.splitlines()]
        return "\n".join(
            (
                line
                for line in code.splitlines()
                if line.strip() not in docstring
            )
        )

    def _get_sanitized_code(self, node: DocumentableNode) -> str | None:
        """Returns a code segment for a node, sanitized of any docstrings."""
        code = ast.get_source_segment(self.source, node)
        if self._has_doc(node) and code:
            code = self._remove_docstring_from_source(
                code=code, docstring=self._get_sanitized_docstring(node)
            )
        return code

    def _visit_helper(self, node: DocumentableNode) -> None:
        """Recursively visit AST node for docstrings."""
        file = os.path.basename(self.filename)
        if not hasattr(node, "name"):
            node_name = os.path.basename(self.filename)
        else:
            node_name = node.name
        parent = None
        path = node_name
        if self.stack:
            parent = self.stack[-1]
            parent_path: str = parent.path
            path = (":" if parent_path.endswith(".py") else ".").join(
                [parent_path, node_name]
            )
        lineno = None
        if hasattr(node, "lineno"):
            lineno = node.lineno
        node_type = type(node).__name__
        cov_node = CovNode(
            name=node_name,
            path=path,
            covered=self._has_doc(node),
            level=len(self.stack),
            node_type=node_type,
            lineno=lineno,
            is_nested_func=self._is_nested_func(parent, node_type),
            is_nested_cls=self._is_nested_cls(parent, node_type),
            parent=parent,
            file=file,
            docstring=(
                self._get_sanitized_docstring(node)
                if self._has_doc(node)
                else None
            ),
            code=self._get_sanitized_code(node),
        )
        self.stack.append(cov_node)
        self.nodes.append(cov_node)
        self.generic_visit(node)
        self.stack.pop()

    @staticmethod
    def _is_nested_func(parent: CovNode | None, node_type: str) -> bool:
        """Is node a nested func/method of another func/method."""
        if parent is None:
            return False
        if parent.node_type == "FunctionDef" and node_type == "FunctionDef":
            return True
        return False

    @staticmethod
    def _is_nested_cls(parent: CovNode | None, node_type: str) -> bool:
        """Is node a nested func/method of another func/method."""
        if parent is None:
            return False
        if (
            parent.node_type in ["ClassDef", "FunctionDef"]
            and node_type == "ClassDef"
        ):
            return True
        return False

    @staticmethod
    def _is_private(node: DocumentableFuncOrClass) -> bool:
        """Is node private (i.e. __MyClass, __my_func)."""
        if node.name.endswith("__"):
            return False
        if not node.name.startswith("__"):
            return False
        return True

    @staticmethod
    def _is_semiprivate(node: DocumentableFuncOrClass) -> bool:
        """Is node semiprivate (i.e. _MyClass, _my_func)."""
        if node.name.endswith("__"):
            return False
        if node.name.startswith("__"):
            return False
        if not node.name.startswith("_"):
            return False
        return True

    def _is_ignored_common(self, node: DocumentableFuncOrClass) -> bool:
        """Commonly-shared ignore checkers."""
        is_private = self._is_private(node)
        is_semiprivate = self._is_semiprivate(node)
        if self.config.ignore_private and is_private:
            return True
        if self.config.ignore_semiprivate and is_semiprivate:
            return True
        return False

    def _is_class_ignored(self, node: DocumentableFuncOrClass) -> bool:
        """Should the AST visitor ignore this class node."""
        return self._is_ignored_common(node)

    def _is_func_ignored(self, node: DocumentableFuncOrClass) -> bool:
        """Should the AST visitor ignore this func/method node."""
        is_init = node.name == "__init__"
        is_magic = all(
            [
                node.name != "__init__",
                node.name.startswith("__"),
                node.name.endswith("__"),
            ]
        )
        has_property_decorators = self._has_property_decorators(node)
        has_setters = self._has_setters(node)
        has_overload = self._has_overload(node)
        if self.config.ignore_init_method and is_init:
            return True
        if self.config.ignore_magic and is_magic:
            return True
        if self.config.ignore_property_decorators and has_property_decorators:
            return True
        if self.config.ignore_property_setters and has_setters:
            return True
        if self.config.ignore_overloaded_functions and has_overload:
            return True
        return self._is_ignored_common(node)

    @staticmethod
    def _has_property_decorators(node: DocumentableFuncOrClass) -> bool:
        """Detect if node has property get/setter/deleter decorators."""
        if not hasattr(node, "decorator_list"):
            return False
        else:
            for dec in node.decorator_list:
                if hasattr(dec, "id"):
                    if dec.id == "property":
                        return True
                if hasattr(dec, "attr"):
                    if dec.attr == "setter":
                        return True
                    if dec.attr == "deleter":
                        return True
            return False

    @staticmethod
    def _has_setters(node: DocumentableFuncOrClass) -> bool:
        """Detect if node has property get/setter decorators."""
        if not hasattr(node, "decorator_list"):
            return False
        else:
            for dec in node.decorator_list:
                if hasattr(dec, "attr"):
                    if dec.attr == "setter":
                        return True
            return False

    @staticmethod
    def _has_overload(node: DocumentableFuncOrClass) -> bool:
        """Detect if node has a typing.overload decorator."""
        if not hasattr(node, "decorator_list"):
            return False
        else:
            for dec in node.decorator_list:
                if (
                    hasattr(dec, "attr")
                    and hasattr(dec, "value")
                    and hasattr(dec.value, "id")
                    and dec.value.id
                    and (dec.attr == "overload")
                ):
                    return True
                if hasattr(dec, "id") and dec.id == "overload":
                    return True
            return False

    def visit_Module(self, node: DocumentableNode) -> None:
        """Visit module for docstrings.

        Args:
            node (ast.Module): a module AST node.
        """
        self._visit_helper(node=node)

    def visit_ClassDef(self, node: DocumentableFuncOrClass) -> None:
        """Visit class for docstrings.

        Args:
            node (ast.ClassDef): a class AST node.
        """
        if self._is_class_ignored(node):
            return
        self._visit_helper(node=node)

    def visit_FunctionDef(self, node: DocumentableFuncOrClass) -> None:
        """Visit function or method for docstrings.

        Args:
            node (ast.FunctionDef): a function/method AST node.
        """
        if self._is_func_ignored(node):
            return
        self._visit_helper(node=node)

    def visit_AsyncFunctionDef(self, node: DocumentableFuncOrClass) -> None:
        """Visit async function or method for docstrings.

        Args:
            node (ast.AsyncFunctionDef): an async function/method AST
                node.
        """
        if self._is_func_ignored(node):
            return
        self._visit_helper(node=node)
