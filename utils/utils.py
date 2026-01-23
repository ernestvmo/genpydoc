from os.path import commonprefix
from pathlib import Path


def get_common_base(files: list[str]) -> str:
    """TEST"""
    commonbase = Path(commonprefix(files))
    while not commonbase.exists():
        commonbase = commonbase.parent
    return str(commonbase)


def test():
    print()
