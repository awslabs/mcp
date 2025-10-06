"""
AWS Labs namespace package.

This is a namespace package that allows multiple AWS Labs projects to coexist
in the same namespace without conflicts.
"""

__path__ = __import__('pkgutil').extend_path(__path__, __name__)