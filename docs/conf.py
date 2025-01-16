"""Sphinx configuration for EarnORM documentation."""

import os
import sys
from datetime import datetime

# Add earnorm to path for autodoc
sys.path.insert(0, os.path.abspath(".."))

# Project information
project = "EarnORM"
copyright = f"{datetime.now().year}, EarnBase"
author = "EarnBase Team"

# The full version, including alpha/beta/rc tags
release = "0.1.0"
version = "0.1"

# General configuration
extensions = [
    "sphinx.ext.autodoc",  # Generate documentation from docstrings
    "sphinx.ext.napoleon",  # Support for NumPy and Google style docstrings
    "sphinx.ext.intersphinx",  # Link to other project's documentation
    "sphinx.ext.viewcode",  # Add links to highlighted source code
    "sphinx.ext.todo",  # Support for todo items
    "sphinx_rtd_theme",  # Read the Docs theme
    "myst_parser",  # Support for Markdown
]

# Add any paths that contain templates here, relative to this directory
templates_path = ["_templates"]

# The suffix(es) of source filenames
source_suffix = [".rst", ".md"]

# The master toctree document
master_doc = "index"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use
pygments_style = "sphinx"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages
html_theme = "sphinx_rtd_theme"

# Theme options
html_theme_options = {
    "canonical_url": "",
    "analytics_id": "",
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "style_nav_header_background": "#2980B9",
    # Toc options
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

# Add any paths that contain custom static files (such as style sheets)
html_static_path = ["_static"]

# These paths are either relative to html_static_path or fully qualified paths (eg. https://...)
html_css_files = [
    "custom.css",
]

# Custom sidebar templates
html_sidebars = {
    "**": [
        "globaltoc.html",
        "relations.html",
        "sourcelink.html",
        "searchbox.html",
    ]
}

# -- Extension configuration -------------------------------------------------

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "motor": ("https://motor.readthedocs.io/en/stable/", None),
    "pymongo": ("https://pymongo.readthedocs.io/en/stable/", None),
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# Todo settings
todo_include_todos = True
