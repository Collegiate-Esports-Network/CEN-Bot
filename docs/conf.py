"""Sphinx configuration for CEN Bot documentation."""

import os
import sys

# Project root on path so autodoc can import start.py and cogs.*
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -------------------------------------------------------
project = 'CEN Bot'
copyright = '2024, Justin Panchula'
author = 'Justin Panchula'
release = '1.0.0'

# -- Extensions ----------------------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'discord': ('https://discordpy.readthedocs.io/en/stable/', None),
    'asyncpg': ('https://magicstack.github.io/asyncpg/current/', None),
}

# -- Autodoc options -----------------------------------------------------------
autodoc_member_order = 'bysource'
autoclass_content = 'both'
autodoc_typehints = 'description'
autodoc_default_options = {
    'members': True,
    'show-inheritance': True,
    'undoc-members': False,
    'private-members': False,
    'special-members': '__init__',
}

# -- HTML output ---------------------------------------------------------------
html_theme = 'furo'
html_title = 'CEN Bot'
html_static_path = ['_static']
