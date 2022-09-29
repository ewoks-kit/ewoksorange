"""rm -rf doc/_generated/; python setup.py build_sphinx -E -a
"""

project = "ewoksorange"
release = "0.1"
copyright = "2021, ESRF"
author = "ESRF"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]
templates_path = ["_templates"]
source_suffix = [".rst", ".md"]
exclude_patterns = ["build", "**.ipynb_checkpoints"]

always_document_param_types = True

autosummary_generate = True
autodoc_default_flags = [
    "members",
    "undoc-members",
    "show-inheritance",
]

html_theme = "classic"
html_logo = "img/ewoksorange.png"
