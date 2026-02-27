import os.path
import sys
from git import Diff, Repo
from genpydoc.config.config import Config
from genpydoc.extractor.visit import CovNode
from genpydoc.git_retriever.utils import process_git_diff


class GitRetriever:
    """GitRetriever analyzes differences between Git branches to determine
    which Python source lines have changed and should be evaluated for
    coverage.

    The class traverses the repository using GitPython, computes a diff map
    of Python files between the current branch (or staged changes) and a
    target branch defined in the provided configuration, and then maps
    changed lines back to CovNode objects using pre-existing node mappings.
    The result is a dictionary that associates file paths with sets of CovNode
    instances representing the code regions to consider during coverage
    evaluation.

    Attributes:
        root: str
            Repository root directory.
        repo: Repo
            GitPython repository object for interacting with the Git repo.
        covered_nodes: dict[str, list[CovNode]]
            Mapping from file paths to lists of CovNode objects that are already
            considered covered or of interest for coverage analysis.
        nodes: dict[str, list[CovNode]]
            Mapping from file paths to lists of CovNode objects representing
            AST-derived nodes that can be matched to changed lines.
        lines: dict[str, set[int]]
            Cache of line numbers to be evaluated per file, populated during
            line extraction.
        current_branch: git.Head
            The currently checked-out branch in the repository.
        config: Config
            Configuration object containing options such as target branch, whether
            to operate on staged changes, and inclusion rules for coverage.
        _diffed_map: dict[str, str]
            Internal mapping of file paths to a change type indicator ('A' or 'D')
            after applying diff logic, used to guide line extraction and evaluation.
    """

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
        if not self._diffed_map or all(
            (
                k not in self.covered_nodes.keys()
                for k in self._diffed_map.keys()
            )
        ):
            self.__stop_early()

    def __add_all(self) -> None:
        """Stages all changes in the repository.

        This private method stages all changes in the working tree by invoking the
        Git command 'git add --all' via the repository's Git integration. It updates
        the index to include additions, modifications, and deletions.

        Attributes:
            repo: The repository-like object used to access Git commands. It should expose
                a `git` attribute implementing the Git command interface.

        Raises:
            GitCommandError: If the underlying Git command fails.
        """
        self.repo.git.add(all=True)

    def __build_diffed_map(self) -> dict[str, str]:
        """Builds a mapping from Python file paths to their diff change type, applying
        staging-aware inversion for added/deleted files.

        The method computes the diff between either the index and the target branch
        when run_staged is True, or between the current commit and the target branch
        when run_staged is False. It filters results to Python files and returns a
        mapping where keys are absolute file paths (root joined with the diff entry's path)
        and values are the corresponding change type, with A and D swapped for staged diffs.

        Attributes:
            self.config.run_staged: Determines whether the diff is performed against the index
                                    or the current commit.
            self.config.target_branch: The target branch to diff against.
            self.repo: Git repository object used to compute diffs.
            self.current_branch: The name of the current branch used when diffing from a commit.
            self.root: The repository root directory to construct absolute paths.

        Returns:
            dict[str, str]: Mapping from absolute Python file paths to their diff change type.
                            Only Python files are included. When run_staged is True, A and D are swapped.

        Raises:
            Exceptions raised by the underlying Git library during diff computation
            (for example, if the target branch does not exist or the repository cannot diff
            the requested range). These exceptions propagate to the caller.
        """

        def _reverse_mapping(ct: str | None) -> str:
            """Reverse mapping helper.

            This method, depending on the configuration, remaps the input character ct using a
            small reverse mapping. When self.config.run_staged is True, the mapping swaps
            "D" and "A" (i.e., "D" -> "A" and "A" -> "D"). If run_staged is False or the input
            character is not in the mapping, ct is returned unchanged.

            Args:
                ct (str | None): The character to potentially remap. May be None.

            Attributes:
                config: Configuration object; must provide a boolean attribute run_staged that
                    toggles the reverse mapping behavior.

            Raises:
                None
            """
            mapping = {"D": "A", "A": "D"} if self.config.run_staged else {}
            if ct not in mapping:
                return ct
            return mapping[ct]

        if self.config.run_staged:
            d = self.repo.index.diff(self.config.target_branch)
        else:
            d = self.repo.commit(self.current_branch).diff(
                self.config.target_branch
            )
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
        """Extract the lines to evaluate for coverage from the repository diffs.

        This method builds and returns a mapping from file paths to the set of CovNode
        instances that should be evaluated for coverage on those files. It computes a
        diff per path against the target branch, either from the index (staged changes)
        or from the current branch, and derives the lines to consider based on that diff.

        For each path k in self._diffed_map:
        - If run_staged is True, diff is taken from the index against target_branch for that path
        - Otherwise, diff is taken from the commit of current_branch against target_branch for that path
        - If more than one diff is found, a ValueError is raised
        - If exactly one diff is found, it is processed
        - If the file was added (diff status 'A') and k exists in self.nodes, the corresponding
          CovNode set is taken directly from self.nodes[k]
        - Else, the diff is processed into line ranges via self._process_diff(diff) and then mapped
          to AST nodes via self._match_lines_to_ast

        The result is a dictionary mapping file paths (str) to sets of CovNode instances to evaluate.

        Returns:
            dict[str, set[CovNode]]: Mapping from file path to the set of CovNode instances to evaluate.

        Raises:
            ValueError: If a path yields more than one diff entry.

        Attributes:
        - _diffed_map: dict[str, str] mapping file path to diff status (e.g., 'A' for added)
        - config: configuration object with attributes run_staged (bool) and target_branch (str)
        - repo: repository handle used to compute diffs
        - current_branch: name of the current branch
        - nodes: dict[str, set[CovNode]] mapping file paths to CovNodes for those files
        - _process_diff: helper to convert a diff into a usable representation
        - _match_lines_to_ast: helper to map diff lines to CovNode objects via AST
        """
        lines_for_evaluation: dict[str, set[CovNode]] = {}
        for k in self._diffed_map.keys():
            if self.config.run_staged:
                diff = self.repo.index.diff(
                    self.config.target_branch, paths=k, create_patch=True
                )
            else:
                diff = self.repo.commit(self.current_branch).diff(
                    self.config.target_branch, paths=k, create_patch=True
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
        """Matches a set of source line numbers to CovNode definitions stored under a
        specific key in the internal node mapping.

        This method collects CovNode instances whose code spans any of the provided lines
        for the given key. Nodes with level equal to 0 are ignored. The result is a set
        of CovNode objects that cover at least one of the input lines.

        Args:
            self: Instance containing the node mapping.
            k (str): Key used to retrieve the list of CovNode objects from the internal
                mapping (self.nodes).
            lines (set[int]): One-based line numbers for which to find matching nodes.

        Returns:
            set[CovNode]: The unique CovNode objects whose code spans any of the provided lines.

        Attributes:
            nodes (dict[str, list[CovNode]]): Mapping from keys to lists of CovNode objects.
            CovNode attributes used:
                lineno (int): Starting line number of the node's code.
                code (str): The code snippet associated with the node.
                level (int): Nesting level; nodes with level == 0 are ignored.

        Raises:
            TypeError: If lines contains non-integer elements (not typically handled here).
            KeyError/AttributeError: If the internal structure does not contain expected keys or
                attributes on CovNode objects (usage guarded by k in self.nodes and access to attributes).
        """
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
        self, diffed_nodes: dict[str, set[CovNode]]
    ) -> dict[str, set[CovNode]]:
        """Analyze and filter diffed nodes by coverage.

        This method iterates over diffed_nodes (a mapping from strings to sets of CovNode objects) and,
        depending on the configuration, filters each set to retain only nodes that are covered. If a set
        becomes empty after filtering, the corresponding key is removed from the dictionary. The operation
        mutates diffed_nodes in place and returns the same dictionary for convenience.

        Args:
            diffed_nodes (dict[str, set[CovNode]]): Mapping from keys to sets of CovNode instances representing
                the nodes that have been diffed for each key.

        Attributes:
            self.config.include_only_covered (bool): If True, filter each set to only include nodes where node.covered is True.
            CovNode.covered (bool): Indicates whether a node is considered covered; used for filtering when enabled.

        Returns:
            dict[str, set[CovNode]]: The same dictionary after filtering and pruning empty entries.
        """
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
