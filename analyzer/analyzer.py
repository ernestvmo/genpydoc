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
        self._renamed_map = self.__build_renamed_map()

    def __add_all(self):
        self.repo.git.add(all=True)

    def __build_renamed_map(self):
        def _reverse_mapping(ct: str | None) -> str:
            mapping = {"D": "A", "A": "D"}
            if ct not in mapping:
                return ct
            return mapping[ct]

        d = self.repo.index.diff("HEAD")
        return {c.a_path: _reverse_mapping(c.change_type) for c in d}

    @staticmethod
    def _process_diff(diff: Diff):
        return process_git_diff(diff)

    def _extract_lines(self):
        """Comment"""
        lines_for_evaluation = {}
        for k in self.covered_nodes.keys():
            diff = self.repo.index.diff("HEAD", paths=k, create_patch=True)
            if len(diff) > 1:
                raise ValueError
            if len(diff):
                diff = diff[0]

            if self._renamed_map[k.removeprefix(self.root + "/")] == "A":
                lines_for_evaluation[k] = {"*"}
            else:
                lines = self._match_lines_to_ast(k, self._process_diff(diff))
                lines_for_evaluation[k] = lines
        return lines_for_evaluation

    def _match_lines_to_ast(self, k: str, lines: set[int]) -> set[str]:
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
