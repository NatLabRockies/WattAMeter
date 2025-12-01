# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#path-setup

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "WattAmeter"
copyright = "2025, Alliance for Sustainable Energy, LLC"
author = "Weslley S. Pereira"
release = "1.2.2"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # This is for automatic gen of rst and other things
    "sphinx.ext.autosummary",  # This is for automatic summary tables
    "sphinx_autodoc_typehints",  # Including typehints automatically in the docs
    # "sphinx.ext.mathjax",  # This is for LaTeX
]

# General config
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# sphinx.ext.autodoc
autodoc_default_options = {
    "special-members": "__call__",
    "exclude-members": "set_predict_request, set_score_request",
}

# sphinx.ext.autosummary
autosummary_generate = True

# sphinx_autodoc_typehints
typehints_use_signature = True
typehints_use_signature_return = True
typehints_defaults = "braces-after"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_context = {
    "display_github": True,
    "github_user": "NREL",
    "github_repo": "WattAMeter",
    "github_version": "main",
    "conf_py_path": "/docs/",
}

# Copy logo from root to _static
logo_src = os.path.abspath(os.path.join("..", "wattameter_logo.png"))
logo_dst = os.path.abspath(os.path.join(html_static_path[0], "wattameter-logo.png"))
if os.path.exists(logo_src) and not os.path.exists(logo_dst):
    import shutil

    os.makedirs(os.path.dirname(logo_dst), exist_ok=True)
    shutil.copyfile(logo_src, logo_dst)
