import os
from pprint import pprint

from commenter.commenter import Commenter
from config.config import Config
from git_retriever.git_retriever import GitRetriever
from extractor.extract import Extract

root = os.path.dirname(__file__)

if __name__ == "__main__":
    config = Config(run_on_diff=False)

    e = Extract(["./commenter"], config=config)
    all_nodes, covered_nodes = e.get_coverage()

    if config.include_only_covered:
        nodes = covered_nodes
    else:
        nodes = all_nodes

    if config.run_on_diff:
        a = GitRetriever(root, covered_nodes, nodes)
        nodes = a.extract_diff()

    commenter = Commenter(config=config)
    docs = commenter.document(nodes=nodes)
    print(docs)
