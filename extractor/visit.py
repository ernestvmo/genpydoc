import ast
import os.path
from typing import Self

import attr

from extractor.config import Config


@attr.s(eq=False)
class CovNode:
    name: str = attr.ib()
    path: str = attr.ib()
    level: int = attr.ib()
    lineno: int = attr.ib()
    covered: bool = attr.ib()
    node_type: str = attr.ib()
    is_nested_func: bool = attr.ib()
    is_nested_cls: bool = attr.ib()
    parent: Self = attr.ib()


class Visitor(ast.NodeVisitor):
    """
    NodeVisitor for a python file to find docstrings.
    """

    def __init__(self, filename, config: Config):
        self.filename = filename
        self.stack = []
        self.nodes = []
        self.config = config

    @staticmethod
    def _has_doc(node):
        return (
            ast.get_docstring(node) is not None
            and ast.get_docstring(node).strip() != ""
        )

    def _visit_helper(self, node):
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
        )

        self.stack.append(cov_node)
        self.nodes.append(cov_node)

        self.generic_visit(node)

        self.stack.pop()

    @staticmethod
    def _is_nested_func(parent: CovNode, node_type: str) -> bool:
        if parent is None:
            return False
        if parent.node_type == "FunctionDef" and node_type == "FunctionDef":
            return True
        return False

    @staticmethod
    def _is_nested_cls(parent: CovNode, node_type: str) -> bool:
        if parent is None:
            return False
        if parent.node_type in ["ClassDef", "FunctionDef"] and node_type == "ClassDef":
            return True
        return False

    @staticmethod
    def _is_private(node: CovNode) -> bool:
        if node.name.endswith("__"):
            return False
        if not node.name.startswith("__"):
            return False
        return True

    @staticmethod
    def _is_semiprivate(node: CovNode) -> bool:
        if node.name.endswith("__"):
            return False
        if node.name.startswith("__"):
            return False
        if not node.name.startswith("_"):
            return False
        return True

    def _is_ignored_common(self, node: CovNode) -> bool:
        is_private = self._is_private(node)
        is_semiprivate = self._is_semiprivate(node)

        if self.config.ignore_private and is_private:
            return True
        if self.config.ignore_semiprivate and is_semiprivate:
            return True

        return False

    def _is_class_ignored(self, node):
        return self._is_ignored_common(node)

    def _is_func_ignored(self, node):
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
    def _has_property_decorators(node: CovNode) -> bool:
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
    def _has_setters(node: CovNode) -> bool:
        if not hasattr(node, "decorator_list"):
            return False
        else:
            for dec in node.decorator_list:
                if hasattr(dec, "attr"):
                    if dec.attr == "setter":
                        return True
            return False

    @staticmethod
    def _has_overload(node: CovNode) -> bool:
        if not hasattr(node, "decorator_list"):
            return False
        else:
            for dec in node.decorator_list:
                if (
                    hasattr(dec, "attr")
                    and hasattr(dec, "value")
                    and hasattr(dec.value, "id")
                    and dec.value.id
                    and dec.attr == "overload"
                ):
                    return True
                if hasattr(dec, "id") and dec.id == "overload":
                    return True
            return False

    def visit_Module(self, node: CovNode):
        self._visit_helper(node=node)

    def visit_ClassDef(self, node):
        if self._is_class_ignored(node):
            return
        self._visit_helper(node=node)

    def visit_FunctionDef(self, node):
        # if self._is_func_ignored(node):
        #     return
        self._visit_helper(node)

    def visit_AsyncFunctionDef(self, node):
        #         if self._is_func_ignored(node):
        #             return
        self._visit_helper(node)
