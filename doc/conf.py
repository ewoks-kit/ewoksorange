"""rm -rf doc/_generated/; sphinx-build doc build/sphinx/html -E -a
"""

import importlib.metadata

release = importlib.metadata.version("ewoksorange")

project = "ewoksorange"
version = ".".join(release.split(".")[:2])
copyright = "2021-2025, ESRF"
author = "ESRF"
docstitle = f"{project} {version}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_togglebutton",
    "sphinx_design",
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

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = []
html_logo = "img/ewoksorange.svg"
html_theme_options = {
    "icon_links": [
        {
            "name": "pypi",
            "url": "https://pypi.org/project/ewoksorange",
            "icon": "fa-brands fa-python",
        },
    ],
    "gitlab_url": "https://gitlab.esrf.fr/workflow/ewoks/ewoksorange",
    "navbar_start": ["navbar-logo", "navbar_start"],
    "footer_start": ["copyright"],
    "footer_end": ["footer_end"],
}
