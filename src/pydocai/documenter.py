import os

from pydocai.commenter.commenter import Commenter
from pydocai.config.config import Config
from pydocai.utils.utils import find_project_root
from pydocai.extractor.extract import Extract
from pydocai.git_retriever.git_retriever import GitRetriever


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
            print("Filtering on git changes...")
            root = find_project_root((os.path.dirname(__file__),))
            gitter = GitRetriever(root, covered_nodes, nodes)
            nodes = gitter.extract_diff()

        if nodes:
            commenter = Commenter(config=self.config)
            commenter.document(nodes=nodes)
        else:
            print("Nothing to comment.")
