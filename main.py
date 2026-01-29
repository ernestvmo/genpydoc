import os
from pprint import pprint

from config.config import Config
from git_retriever.git_retriever import GitRetriever
from extractor.extract import Extract

root = os.path.dirname(__file__)

if __name__ == "__main__":
    config = Config(run_on_diff=False)
    e = Extract(["./utils"], config=config)
    nodes, covered_nodes = e.get_coverage()
    if config.run_on_diff:
        a = GitRetriever(root, covered_nodes, nodes)
        nodes = a.extract_diff()

    pprint(covered_nodes)
