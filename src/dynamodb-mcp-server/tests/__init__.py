"""Tests package - sets up import path for local modules."""
import sys
import os

# Add the project root to Python path so tests can import local modules when running pytest
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
