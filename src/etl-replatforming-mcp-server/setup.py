#!/usr/bin/env python3
"""
Backward compatibility setup.py for pip installations.
Modern installations should use pyproject.toml.
"""

from setuptools import setup

# This setup.py exists for backward compatibility with older pip versions.
# All configuration is in pyproject.toml
setup()