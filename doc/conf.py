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
]
templates_path = ["_templates"]
source_suffix = [".rst", ".md"]
exclude_patterns = ["build", "**.ipynb_checkpoints"]

pygments_style = "sphinx"
autodoc_typehints = "description"
autodoc_typehints_description_target = "all"

autosummary_generate = True
autodoc_default_flags = [
    "members",
    "undoc-members",
    "show-inheritance",
]

html_theme = "alabaster"
html_logo = "img/ewoksorange.png"
