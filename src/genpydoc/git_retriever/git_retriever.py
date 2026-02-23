import os.path
import sys

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
        self.target_branch = config.target_branch
        self.config = config

        self.__add_all()
        self._diffed_map = self.__build_diffed_map()
        if not self._diffed_map or all(
            (
                k not in self.covered_nodes.keys()
                for k in self._diffed_map.keys()
            )
        ):
            self.__stop_early()

    def __add_all(self) -> None:
        self.repo.git.add(all=True)

    def __build_diffed_map(self) -> dict[str, str]:
        def _reverse_mapping(ct: str | None) -> str:
            mapping = {"D": "A", "A": "D"}
            if ct not in mapping:
                return ct
            return mapping[ct]

        d = self.repo.index.diff(self.target_branch)
        return {
            os.path.join(self.root, c.a_path): _reverse_mapping(c.change_type)
            for c in d
            if c.a_path.endswith(".py")
        }

    @staticmethod
    def __stop_early() -> None:
        """Ends the program early"""
        sys.exit()

    @staticmethod
    def _process_diff(diff: Diff) -> set[int]:
        return process_git_diff(diff)

    def _extract_lines(self) -> dict[str, set[CovNode]]:
        lines_for_evaluation: dict[str, set[CovNode]] = {}
        for k in self._diffed_map.keys():
            diff = self.repo.index.diff(
                self.target_branch, paths=k, create_patch=True
            )
            if len(diff) > 1:
                raise ValueError
            if len(diff):
                diff = diff[0]
            if self._diffed_map.get(k, "A") == "A" and k in self.nodes:
                lines_for_evaluation[k] = self.nodes[k]
            else:
                lines = self._match_lines_to_ast(k, self._process_diff(diff))
                lines_for_evaluation[k] = lines
        return lines_for_evaluation

    def _match_lines_to_ast(self, k: str, lines: set[int]) -> set[CovNode]:
        definitions = set()
        for line in lines:
            traversed_nodes: list[CovNode] = []
            if k in self.nodes:
                for node in self.nodes[k]:
                    if node.level == 0:
                        continue
                    if (
                        node.lineno
                        <= line
                        < node.lineno + len(node.code.splitlines())
                    ):
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
        return self._analyze_covered_nodes(nodes_diffed)
