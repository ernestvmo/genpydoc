from pprint import pprint

import git
import os

from genpydoc.utils.utils import find_project_root

root = find_project_root((os.path.dirname(__file__),))
repo = git.Repo(root)


def __build_diffed_map(branch: str) -> dict[str, str]:
    def _reverse_mapping(ct: str | None) -> str:
        mapping = {"D": "A", "A": "D"}
        if ct not in mapping:
            return ct
        return mapping[ct]

    d = repo.commit("main").diff(branch)
    return {
        os.path.join(root, c.a_path): _reverse_mapping(c.change_type)
        for c in d
    }


if __name__ == "__main__":
    x = __build_diffed_map("diff_on_target")
    pprint(x)
