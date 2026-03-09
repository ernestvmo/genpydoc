import datetime
import os
import sys
import tomllib

with open("../pyproject.toml", "rb") as f:
    data = tomllib.load(f)

project = data["project"]["name"]
author = "Ernest Vanmosuinck"
copyright = f"{datetime.date.today().year}, {author}"
release = data["project"]["version"]

sys.path.insert(0, os.path.abspath("../src"))

extensions = [
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "sphinx.ext.autodoc",
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}


templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
