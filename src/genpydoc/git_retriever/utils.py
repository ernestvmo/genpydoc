import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from git import Diff

HUNK_REGEX = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class DiffChangeType(StrEnum):
    # '+', '-', ' '
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
    # C = "C"
    MODIFIED = "M"
    RENAMED = "R"
    TYPE_PATH = "T"
    # U = "U"


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
            # skip file headers
            continue

        if old_lineno is None or new_lineno is None:
            # not inside a hunk yet
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
            # e.g. "\ No newline at end of file"
            pass
    return changes


def process_changes(changes: list[DiffChange]) -> set[int]:
    lines = set()
    for change in changes:
        if change.kind == DiffChangeType.BLANK:
            continue
        if change.text.strip() == "":
            # whitespace or blank line
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
        and diff.a_path != diff.b_path
    ):
        return ChangeType.RENAMED
    elif (
        diff.a_path is not None
        and diff.b_path is not None
        and diff.a_path == diff.b_path
    ):
        return ChangeType.MODIFIED
    else:
        raise ValueError(diff)
