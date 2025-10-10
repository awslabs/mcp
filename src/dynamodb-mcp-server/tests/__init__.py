"""Tests package - sets up import path for local modules.

This configures Python's import path so pytest can import awslabs.dynamodb_mcp_server
modules during development testing before the package is installed.
Without this, test imports would fail with ModuleNotFoundError.
"""

import sys
import os

# Add the project root to Python path so tests can import local modules when running pytest
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
