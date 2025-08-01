"""Pytest configuration for CloudWatch Application Signals MCP Server tests."""

import os


# Set test environment variables before any imports
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'  # pragma: allowlist secret
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ.pop('AWS_PROFILE', None)
