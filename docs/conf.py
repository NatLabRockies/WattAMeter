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
    "myst_parser",  # This is for markdown support
    "sphinx_multiversion",  # This is for multiple version support
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

# myst_parser
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

# sphinx_multiversion
smv_latest_version = "main"
smv_tag_whitelist = r"^v\d+\.\d+\.\d+$"
smv_rename_latest_version = "dev"

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
logo_dst = os.path.abspath(os.path.join(html_static_path[0], "wattameter_logo.png"))
if os.path.exists(logo_src) and not os.path.exists(logo_dst):
    import shutil

    os.makedirs(os.path.dirname(logo_dst), exist_ok=True)
    shutil.copyfile(logo_src, logo_dst)

# Copy markdown structured README from root to docs
readme_src = os.path.abspath(os.path.join("..", "README.md"))
readme_dst = os.path.abspath(os.path.join(".", "README.md"))
license_src = os.path.abspath(os.path.join("..", "LICENSE"))
license_dst = os.path.abspath(os.path.join(".", "LICENSE"))
if os.path.exists(readme_src) and os.path.exists(license_src):
    from pathlib import Path
    import shutil

    shutil.copyfile(readme_src, readme_dst)
    shutil.copyfile(license_src, license_dst)

    text = Path(readme_src).read_text()
    for old, new in {
        "](src/": "](../src/",
        "](examples/": "](../examples/",
        "](wattameter_logo": "](_static/wattameter_logo",
    }.items():
        text = text.replace(old, new)

    Path(readme_dst).write_text(text)
