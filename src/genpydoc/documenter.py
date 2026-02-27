import sys

from genpydoc.commenter.commenter import Commenter
from genpydoc.config.config import Config
from genpydoc.extractor.extract import Extract
from genpydoc.git_retriever.git_retriever import GitRetriever


class Documenter:
    config: Config

    def __init__(self, config: Config):
        self.config = config

    def document(self, paths):
        extract = Extract(paths, self.config)
        all_nodes, covered_nodes = extract.get_coverage()

        if self.config.include_only_covered:
            nodes = covered_nodes
        else:
            nodes = all_nodes

        if self.config.run_on_diff:
            if self.config.verbose:
                print("Filtering on git changes...")
            gitter = GitRetriever(
                covered_nodes=covered_nodes, nodes=nodes, config=self.config
            )
            nodes = gitter.extract_diff()

        for n, v in nodes.items():
            print(n, len(v))
        sys.exit()

        if self.config.verbose:
            if nodes:
                commenter = Commenter(config=self.config)
                commenter.document(nodes=nodes)
        else:
            if self.config.verbose:
                print("Nothing to comment.")
