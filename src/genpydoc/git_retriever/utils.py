import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional
from git import Diff, Repo, InvalidGitRepositoryError, NoSuchPathError

HUNK_REGEX = re.compile("^@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@")


class DiffChangeType(StrEnum):
    ADD = "+"
    REMOVE = "-"
    BLANK = " "


@dataclass
class DiffChange:
    old_lineno: Optional[int]
    new_lineno: Optional[int]
    kind: str
    text: str


class ChangeType(StrEnum):
    ADDED = "A"
    DELETED = "D"
    MODIFIED = "M"
    RENAMED = "R"
    TYPE_PATH = "T"


def parse_diff(diff_text: str | bytes | None) -> list[DiffChange]:
    changes = []
    old_lineno = None
    new_lineno = None
    if isinstance(diff_text, bytes):
        diff_text = diff_text.decode("utf-8")
    for line in diff_text.splitlines():
        m = HUNK_REGEX.match(line)
        if m:
            old_lineno = int(m.group(1))
            new_lineno = int(m.group(3))
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        if old_lineno is None or new_lineno is None:
            continue
        prefix = line[0]
        text = line[1:] if len(line) else ""
        if prefix == " ":
            changes.append(
                DiffChange(old_lineno, new_lineno, DiffChangeType.BLANK, text)
            )
            old_lineno += 1
            new_lineno += 1
        elif prefix == "+":
            changes.append(
                DiffChange(None, new_lineno, DiffChangeType.ADD, text)
            )
            new_lineno += 1
        elif prefix == "-":
            changes.append(
                DiffChange(old_lineno, None, DiffChangeType.REMOVE, text)
            )
            old_lineno += 1
        else:
            pass
    return changes


def process_changes(changes: list[DiffChange]) -> set[int]:
    lines = set()
    for change in changes:
        if change.kind == DiffChangeType.BLANK:
            continue
        if change.text.strip() == "":
            continue
        lineno = next(
            (
                item
                for item in [change.new_lineno, change.old_lineno]
                if item is not None
            ),
            -1,
        )
        if lineno == -1:
            raise
        lines.add(lineno)
    return lines


def process_git_diff(diff: Diff) -> set[int]:
    return process_changes(parse_diff(diff.diff))


def get_change_type(diff: Diff) -> ChangeType:
    if diff.change_type:
        return ChangeType(diff.change_type)
    elif diff.a_path is None and diff.b_path is not None:
        return ChangeType.DELETED
    elif diff.a_path is not None and diff.b_path is None:
        return ChangeType.ADDED
    elif (
        diff.a_path is not None
        and diff.b_path is not None
        and (diff.a_path != diff.b_path)
    ):
        return ChangeType.RENAMED
    elif (
        diff.a_path is not None
        and diff.b_path is not None
        and (diff.a_path == diff.b_path)
    ):
        return ChangeType.MODIFIED
    else:
        raise ValueError(diff)


def is_git_repo(path: str):
    """Return True if the given path is a Git repository; otherwise return False.

    Args:
        path (str): Path to the repository to check.

    Attributes:
        path (str): The input path used for the repository check.

    Returns:
        bool: True if the path points to a valid Git repository, otherwise False.

    Raises:
        Exception: Propagates exceptions raised by Repo(path) that are not InvalidGitRepositoryError or NoSuchPathError.
    """
    try:
        _ = Repo(path).git_dir
        return True
    except (InvalidGitRepositoryError, NoSuchPathError):
        return False


def branch_exists(path: str, branch: str):
    """Check if a given branch exists in the Git repository located at the specified path.

    This function opens the repository at `path` and determines whether `branch`
    is present among the repository's heads.

    Args:
        path: The filesystem path to a Git repository.
        branch: The name of the branch to check for existence.

    Returns:
        True if the branch exists in the repository, False otherwise (including when
        the path is not a valid Git repository).

    Attributes:
        None

    Raises:
        InvalidGitRepositoryError: This exception is caught within the function and does
            not propagate; in this case False is returned.
        Other exceptions may be raised by the underlying Git library when reading the
            repository and will propagate to the caller.
    """
    try:
        return branch in Repo(path).heads
    except InvalidGitRepositoryError:
        return False
