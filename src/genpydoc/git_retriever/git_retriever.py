import os.path
import sys
from fnmatch import fnmatch
from typing import Iterator

from git import Diff, Repo

from genpydoc.config.config import Config
from genpydoc.extractor.visit import CovNode
from genpydoc.git_retriever.utils import process_git_diff


class GitRetriever:
    def __init__(
        self,
        covered_nodes: dict[str, list[CovNode]],
        nodes: dict[str, list[CovNode]],
        config: Config,
    ):
        self.root = config.root
        self.repo = Repo(self.root)
        self.covered_nodes = covered_nodes
        self.nodes = nodes
        self.lines = {}
        self.current_branch = self.repo.active_branch
        self.config = config

        self.__add_all()
        self._diffed_map = self.__build_diffed_map()
        print(self._diffed_map)

        if not self._diffed_map or all(
            (
                k not in self.covered_nodes.keys()
                for k in self._diffed_map.keys()
            )
        ):
            self.__stop_early()

    def __add_all(self) -> None:
        self.repo.git.add(all=True)

    def _filter_files(self, files: list[str]) -> Iterator[str]:
        for file in files:
            has_valid_ext = any([file.endswith(ext) for ext in set(".py")])
            if not has_valid_ext:
                continue
            basename = os.path.basename(file)
            if basename == "__init__":  # always ignore __init__ files
                continue
            if any(fnmatch(file, exc + "*") for exc in self.config.exclude):
                continue
            yield file

    def __build_diffed_map(self) -> dict[str, str]:
        def _reverse_mapping(ct: str | None) -> str:
            mapping = {"D": "A", "A": "D"} if self.config.run_staged else {}
            if ct not in mapping:
                return ct
            return mapping[ct]

        if self.config.run_staged:
            d = self.repo.index.diff(self.config.target_branch)
        else:
            d = self.repo.commit(self.config.target_branch).diff(
                self.current_branch
            )

        return {
            os.path.join(self.root, c.a_path): _reverse_mapping(c.change_type)
            for c in d
            if c.a_path.endswith(".py")
            and not any(
                fnmatch(os.path.join(self.root, c.a_path), exc + "*")
                for exc in self.config.exclude
            )
        }

    @staticmethod
    def __stop_early() -> None:
        """Ends the program early"""
        sys.exit()

    @staticmethod
    def _process_diff(diff: Diff) -> set[str]:
        return process_git_diff(diff)

    def _extract_lines(self) -> dict[str, set[CovNode]]:
        lines_for_evaluation: dict[str, set[CovNode]] = {}
        for k in self._diffed_map.keys():
            if self.config.run_staged:
                diff = self.repo.index.diff(
                    self.config.target_branch, paths=k, create_patch=True
                )
            else:
                diff = self.repo.commit(self.config.target_branch).diff(
                    self.current_branch, paths=k, create_patch=True
                )
            if len(diff) > 1:
                raise ValueError
            if len(diff):
                diff = diff[0]
            if self._diffed_map.get(k, "A") == "A" and k in self.nodes:
                lines_for_evaluation[k] = self.nodes[k]
            else:
                print(k, self._diffed_map.get(k))
                diffed_node_names = self._match_node_name_to_ast_node(
                    k, self._process_diff(diff)
                )
                lines_for_evaluation[k] = diffed_node_names
        return lines_for_evaluation

    def _match_node_name_to_ast_node(
        self, k: str, names: set[str]
    ) -> set[CovNode]:
        definitions = set()
        for name in names:
            traversed_nodes: list[CovNode] = []
            if k in self.nodes:
                for node in self.nodes[k]:
                    if node.level == 0:
                        continue

                    if node.name == name:
                        traversed_nodes.append(node)
            if len(traversed_nodes) > 0:
                for n in traversed_nodes:
                    definitions.add(n)
            else:
                continue
        return definitions

    def _analyze_covered_nodes(
        self,
        diffed_nodes: dict[str, set[CovNode]],
    ) -> dict[str, set[CovNode]]:
        keys = list(diffed_nodes.keys())
        for k in keys:
            nodes = diffed_nodes[k]
            if self.config.include_only_covered:
                nodes = {node for node in nodes if node.covered}
            if not nodes:
                del diffed_nodes[k]
                continue
            diffed_nodes[k] = nodes
        return diffed_nodes

    def extract_diff(self) -> dict[str, set[CovNode]]:
        nodes_diffed = self._extract_lines()
        print(nodes_diffed)
        return self._analyze_covered_nodes(nodes_diffed)
