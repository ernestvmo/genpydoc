import ast
import os.path
import pathlib
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterator

from genpydoc.config.config import Config
from genpydoc.extractor.visit import CovNode
from genpydoc.utils.utils import get_common_base
from genpydoc.extractor import visit


class Extract:
    COMMON_EXCLUDE = [".tox", ".venv", "venv", ".git", ".hg"]
    VALID_EXTENSIONS = [".py", ".pyi"]

    def __init__(self, paths, config: Config | None = None):
        self.paths = paths
        self.extensions = set(".py")
        self.config = config if config else Config()
        self.excluded = ()
        self.common_base = pathlib.Path("/")
        self.output_formatter = None
        self._add_common_exclude()
        self.skipped_file_count = 0

    def _add_common_exclude(self) -> None:
        for path in self.paths:
            self.excluded = self.excluded + tuple(
                os.path.join(path, i) for i in self.COMMON_EXCLUDE
            )

    def _filter_files(self, files: list[str]) -> Iterator[str]:
        for file in files:
            has_valid_ext = any(
                [file.endswith(ext) for ext in self.extensions]
            )
            if not has_valid_ext:
                continue
            basename = os.path.basename(file)
            if basename == "__init__":  # always ignore __init__ files
                continue
            if any(fnmatch(file, exc + "*") for exc in self.excluded):
                continue
            yield file

    def _filter_nodes(self, nodes: list[CovNode]) -> list[CovNode]:
        if self.config.ignore_module:
            return [node for node in nodes if node.node_type != "Module"]
        return nodes

    @staticmethod
    def _filter_empty_nodes(
        nodes: list[CovNode] | None,
    ) -> list[CovNode] | None:
        if not nodes:
            return None
        return [node for node in nodes if node.covered]

    @staticmethod
    def _filter_inner_nested(nodes: list[CovNode]) -> list[CovNode]:
        nested_cls = [n for n in nodes if n.is_nested_cls]
        inner_nested_nodes = [n for n in nodes if n.parent in nested_cls]
        filtered_nodes = [n for n in nodes if n not in inner_nested_nodes]
        filtered_nodes = [n for n in filtered_nodes if n not in nested_cls]
        return filtered_nodes

    @staticmethod
    def _set_google_style(nodes: list[CovNode]) -> None:
        for node in nodes:
            if node.node_type == "FunctionDef" and node.name == "__init__":
                if not node.covered and node.parent.covered:
                    setattr(node, "covered", True)
                elif node.covered and not node.parent.covered:
                    setattr(node.parent, "covered", True)

    def get_filenames_from_path(self) -> list[str]:
        filenames = []
        for path in self.paths:
            if os.path.isfile(path):
                has_valid_extension = any(
                    path.endswith(ext) for ext in self.VALID_EXTENSIONS
                )
                if not has_valid_extension:
                    if self.config.verbose:
                        print(f"invalid file {path}")
                    return sys.exit(1)
                filenames.append(path)
                continue

            for root, _, fs in os.walk(path):
                full_paths = [os.path.join(root, f) for f in fs]
                filenames.extend(self._filter_files(full_paths))

        if not filenames:
            p = ", ".join(self.paths)
            if self.config.verbose:
                print(f"no python files found in {p}")
            return sys.exit(1)

        self.common_base = get_common_base(filenames)
        return filenames

    def _get_coverage(
        self, filenames: list[str | Path]
    ) -> tuple[dict[str, list[CovNode]], dict[str, list[CovNode]]]:
        results: dict[str, list[CovNode]] = {}
        covered_results: dict[str, list[CovNode]] = {}
        for filename in filenames:
            result = self._get_file_coverage(filename)
            covered_result = self._filter_empty_nodes(result)
            if result:
                results[filename] = result
            if covered_result:
                covered_results[filename] = covered_result
        return results, covered_results

    def _get_file_coverage(self, filename: str | Path) -> list[CovNode] | None:
        with open(filename) as f:
            source = f.read()

        parsed_tree = ast.parse(source)
        visitor = visit.Visitor(filename, self.config, source)
        visitor.visit(parsed_tree)

        filtered_nodes = self._filter_nodes(visitor.nodes)
        if len(filtered_nodes) == 0:
            return None

        if self.config.ignore_nested_functions:
            filtered_nodes = [
                node for node in filtered_nodes if node.is_nested_func
            ]

        if self.config.ignore_nested_classes:
            filtered_nodes = self._filter_inner_nested(filtered_nodes)

        if self.config.docstring_style == "google":
            self._set_google_style(filtered_nodes)

        return filtered_nodes

    def get_coverage(
        self,
    ) -> tuple[dict[str, list[CovNode]], dict[str, list[CovNode]]]:
        filenames = self.get_filenames_from_path()
        return self._get_coverage(filenames)
