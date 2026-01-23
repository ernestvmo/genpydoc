import os.path
import sys

from git import Diff, Repo

from analyzer.git_utils import process_git_diff
from extractor.visit import CovNode


class Analyzer:
    def __init__(
        self,
        root: str,
        covered_nodes: dict[str, list[CovNode]],
        nodes: dict[str, list[CovNode]],
    ):
        self.root = root
        self.repo = Repo(root)
        self.covered_nodes = covered_nodes
        self.nodes = nodes
        self.lines = {}
        self.__add_all()
        self._diffed_map = self.__build_diffed_map()

        if not self._diffed_map or all(
            k not in self.covered_nodes.keys() for k in self._diffed_map.keys()
        ):
            self.__stop_early()

    def __add_all(self):
        self.repo.git.add(all=True)

    def __build_diffed_map(self):
        def _reverse_mapping(ct: str | None) -> str:
            mapping = {"D": "A", "A": "D"}
            if ct not in mapping:
                return ct
            return mapping[ct]

        d = self.repo.index.diff("HEAD")
        return {
            os.path.join(self.root, c.a_path): _reverse_mapping(c.change_type)
            for c in d
        }

    @staticmethod
    def __stop_early():
        """Ends the program early"""
        sys.exit()

    @staticmethod
    def _process_diff(diff: Diff):
        return process_git_diff(diff)

    def _extract_lines(self):
        lines_for_evaluation = {}
        for k in self._diffed_map.keys():
            # for k in self.covered_nodes.keys():
            diff = self.repo.index.diff("HEAD", paths=k, create_patch=True)
            if len(diff) > 1:
                raise ValueError
            if len(diff):
                diff = diff[0]

            if self._diffed_map.get(k, "A") == "A":
                lines_for_evaluation[k] = {"*"}
            else:
                lines = self._match_lines_to_ast(k, self._process_diff(diff))
                lines_for_evaluation[k] = lines
        return lines_for_evaluation

    def _match_lines_to_ast(self, k: str, lines: set[int]) -> set[str]:
        print(lines)
        definitions = set()
        for line in lines:
            traversed_nodes: list[CovNode] = []
            for node in self.nodes[k]:
                if node.level == 0:
                    continue
                if node.lineno <= line < node.lineno + len(node.code.splitlines()):
                    traversed_nodes.append(node)
            if len(traversed_nodes) > 0:
                for n in traversed_nodes:
                    definitions.add(n.name)
            else:
                continue

        return definitions

    def process(self):
        definitions_diffed = self._extract_lines()
        print(definitions_diffed)
