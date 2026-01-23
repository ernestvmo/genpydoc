import os

from analyzer.analyzer import Analyzer
from extractor.extract import Extract

root = os.path.dirname(__file__)

if __name__ == "__main__":
    e = Extract([root])
    nodes, covered_nodes = e.get_coverage()
    a = Analyzer(root, covered_nodes, nodes)
    a.process()
