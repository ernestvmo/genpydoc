import ast
import subprocess
from pathlib import Path

from config.config import Config

DocumentableFunc = ast.AsyncFunctionDef | ast.FunctionDef
DocumentableFuncOrClass = DocumentableFunc | ast.ClassDef
DocumentableNode = DocumentableFuncOrClass | ast.Module


class Transformer(ast.NodeTransformer):
    config: Config
    comments: dict[str, str]

    def __init__(self, config: Config, comments: dict[str, str]):
        super().__init__()
        self.config = config
        self.comments = comments

    def _visit_helper(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    ):
        # self.generic_visit(node)
        # print(node.name)
        if node.name not in self.comments:
            return node

        new_docstring = self.comments[node.name].removeprefix('"""').removesuffix('"""')
        new_doc_code = ast.Expr(value=ast.Constant(value=new_docstring))

        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(getattr(node.body[0], "value", None), ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body[0] = new_doc_code
        else:
            node.body.insert(0, new_doc_code)

        return node

    def visit_ClassDef(self, node: DocumentableFuncOrClass) -> None:
        # if self._is_class_ignored(node):
        #     return
        return self._visit_helper(node=node)

    def visit_FunctionDef(self, node: DocumentableFuncOrClass) -> None:
        #         if self._is_func_ignored(node):
        #             return
        return self._visit_helper(node=node)

    def visit_AsyncFunctionDef(self, node: DocumentableFuncOrClass) -> None:
        # if self._is_func_ignored(node):
        #     return
        return self._visit_helper(node=node)


class Parser:
    def __init__(self, config: Config):
        self.config = config

    def process(self, filepath: Path, comments: dict[str, str]):
        with open(filepath) as file:
            source = file.read()

        parsed_tree = ast.parse(source)
        t = Transformer(config=self.config, comments=comments)
        t.visit(parsed_tree)

        filepath.write_text(ast.unparse(parsed_tree))

        if self.config.post_processing.cleanup or self.config.post_processing.convert:
            self.post_process(
                filepath,
                cleanup=self.config.post_processing.cleanup,
                convert=self.config.post_processing.convert,
            )

    def post_process(
        self, filepath: str | Path, cleanup: bool = True, convert: bool = True
    ):
        if cleanup:
            subprocess.run(f"black {filepath} -q", shell=True)
        if convert:
            if self.config.docstring_style not in ["google", "numpy"]:
                raise ValueError(
                    "Style cannot be converted to with docstripy."
                )  # todo other package?
            subprocess.run(
                f"docstripy {filepath} -s={self.config.docstring_style} -w --noadd",
                shell=True,
            )


if __name__ == "__main__":
    config_ = Config(run_on_diff=False, docstring_style="google")
    comments_ = {
        "../test/file.py": {
            "process_git_diff": '"""\nProcess a git diff and return the set of integers representing the identifiers of changes.\n\nGiven a Diff object, this function reads the textual patch from the ``diff`` attribute,\nparses it into a structured representation, and computes the set of integer identifiers\nthat correspond to changes detected in the patch.\n\n:param diff: Diff object containing the patch to process. The diff patch is expected to be\n             accessible via ``diff.diff``.\n:return: A set of integer identifiers representing the changes extracted from the diff.\n:rtype: set[int]\n"""',
            "get_change_type": '"""\nReturn the ChangeType corresponding to the given diff.\n\nThis function inspects a diff object and returns a ChangeType enumeration\nvalue describing the kind of change it represents. The resolution order is:\n\n- If diff.change_type is set (truthy), return ChangeType(diff.change_type).\n- If a_path is None and b_path is not None: return ChangeType.DELETED.\n- If a_path is not None and b_path is None: return ChangeType.ADDED.\n- If both a_path and b_path are set and differ: return ChangeType.RENAMED.\n- If both a_path and b_path are set and equal: return ChangeType.MODIFIED.\n\nIf none of the above conditions apply, a ValueError is raised (and the diff is printed for debugging).\n\n:param diff: The diff describing changes between two versions/file states.\n:type diff: Diff\n:return: The ChangeType representing the kind of change.\n:rtype: ChangeType\n:raises ValueError: If the diff cannot be mapped to any known ChangeType.\n"""',
        }
    }
    p = Parser(config=config_)
    for k in comments_:
        print(k)
        p.process(Path(k), comments_[k])
