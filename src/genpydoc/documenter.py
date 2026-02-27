from genpydoc.commenter.commenter import Commenter
from genpydoc.config.config import Config
from genpydoc.extractor.extract import Extract
from genpydoc.git_retriever.git_retriever import GitRetriever


class Documenter:
    """Documenter coordinates the end-to-end process of generating documentation or comments
    from a set of paths, based on a given Config.

    This class orchestrates:
    - extraction of coverage information using Extract,
    - selection of nodes to consider (all nodes or only covered nodes) based on the configuration,
    - optional filtering by git changes via GitRetriever when run_on_diff is enabled,
    - delegation to a Commenter to produce the actual comments if any nodes remain.

    The class does not implement the extraction, diffing, or commenting logic itself; it simply
    glues these components together according to the configuration.

    Attributes:
        config (Config): The configuration object controlling how documentation is produced,
            including flags such as include_only_covered and run_on_diff.
    """

    config: Config

    def __init__(self, config: Config):
        self.config = config

    def document(self, paths):
        """Process code paths to generate documentation comments based on coverage and diffs.

        This method orchestrates the following steps:
        - Build coverage information from the given paths using the Extract component.
        - Select the set of nodes to consider based on configuration (all nodes or only covered ones).
        - Optionally filter the selected nodes to those changed in the current Git diff.
        - For the resulting subset of nodes, invoke the Commenter to produce documentation comments.

        Args:
            paths: A sequence of filesystem paths to analyze for coverage.

        Attributes:
            config: The configuration object used to control behavior. Expected to expose:
                include_only_covered (bool): If True, operate only on nodes that are covered.
                run_on_diff (bool): If True, restrict processing to nodes that differ in git changes.

        Raises:
            Exceptions raised by the underlying components (Extract, GitRetriever, Commenter) may propagate upward,
            such as ValueError, RuntimeError, or IO-related errors, depending on the input and the environment.
        """
        extract = Extract(paths, self.config)
        all_nodes, covered_nodes = extract.get_coverage()
        if self.config.include_only_covered:
            nodes = covered_nodes
        else:
            nodes = all_nodes
        if self.config.run_on_diff:
            print("Filtering on git changes...")
            gitter = GitRetriever(
                covered_nodes=covered_nodes, nodes=nodes, config=self.config
            )
            nodes = gitter.extract_diff()
        if nodes:
            commenter = Commenter(config=self.config)
            commenter.document(nodes=nodes)
        else:
            print("Nothing to comment.")
