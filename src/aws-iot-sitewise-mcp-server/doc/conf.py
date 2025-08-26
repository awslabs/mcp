# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sphinx configuration."""

import datetime
import os
import shutil
import sys
from importlib.metadata import version as get_version


# Add the project source to the path for autodoc
sys.path.insert(0, os.path.abspath('../src/'))

# Basic project information
project = 'site-wise-mcp-poc'
author = 'SiteWiseMCP-PoC Contributors'
copyright = f'{datetime.datetime.now().year}, {author}'

# The full version, including alpha/beta/rc tags

try:
    release = get_version(project)
    # Major.Minor version
    version = '.'.join(release.split('.')[:2])
except Exception:
    release = '0.1.0'  # Fallback if package is not installed
    version = '0.1'


def run_apidoc(app):
    """Generate doc stubs using sphinx-apidoc."""
    module_dir = os.path.join(app.srcdir, '../src/')
    output_dir = os.path.join(app.srcdir, '_apidoc')
    excludes = []

    # Ensure that any stale apidoc files are cleaned up first.
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    cmd = [
        '--separate',
        '--module-first',
        '--doc-project=API Reference',
        '-o',
        output_dir,
        module_dir,
    ]
    cmd.extend(excludes)

    try:
        from sphinx.ext import apidoc  # Sphinx >= 1.7

        apidoc.main(cmd)
    except ImportError:
        from sphinx import apidoc  # Sphinx < 1.7

        cmd.insert(0, apidoc.__file__)
        apidoc.main(cmd)


def setup(app):
    """Register our sphinx-apidoc hook."""
    app.connect('builder-inited', run_apidoc)


# Sphinx configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'boto3': ('https://boto3.amazonaws.com/v1/documentation/api/latest/', None),
}

source_suffix = '.rst'
master_doc = 'index'

autoclass_content = 'class'
autodoc_member_order = 'bysource'
default_role = 'py:obj'

# HTML options
html_theme = 'haiku'
htmlhelp_basename = '{}doc'.format(project)

# Napoleon settings
napoleon_use_rtype = False
