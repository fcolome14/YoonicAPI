# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('../../app'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'YoonicAPI'
copyright = '2024, Ferran Colome'
author = 'Ferran Colome'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Supports Google and NumPy style docstrings
    'sphinx.ext.viewcode',  # Adds links to view source code
    'sphinx_autodoc_typehints',  # Supports type hints in documentation
    'm2r2'  # Enables Markdown support
]

html_theme = 'sphinx_rtd_theme'

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
