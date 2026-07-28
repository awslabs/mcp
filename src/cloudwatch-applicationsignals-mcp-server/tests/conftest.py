"""Pytest configuration for CloudWatch Application Signals MCP Server tests."""

import json
import os
import pytest
from pathlib import Path


# Set test environment variables before any imports
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'  # pragma: allowlist secret
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ.pop('AWS_PROFILE', None)


FIXTURES_DIR = Path(__file__).parent / 'fixtures'


# ============================================================================
# ServiceEvents: reset module-level state between tests
# ============================================================================


@pytest.fixture(autouse=True)
def _reset_service_events_globals():
    """Reset service_events module-level state (AppSignals flag, env cache) between tests."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import state as state_mod

    orig_appsignals = state_mod._appsignals_enabled
    orig_env_cache = state_mod._service_env_cache

    yield

    state_mod._appsignals_enabled = orig_appsignals
    state_mod._service_env_cache = orig_env_cache


# ============================================================================
# ServiceEvents OTLP fixture loaders
# ============================================================================


@pytest.fixture
def fixture_endpoint_summary():
    """Raw service_events endpoint_summary OTLP record."""
    return json.loads((FIXTURES_DIR / 'serviceevents_endpoint_summary.json').read_text())


@pytest.fixture
def fixture_incident_python_exception():
    """Raw service_events incident_snapshot (Python exception) OTLP record."""
    return json.loads((FIXTURES_DIR / 'serviceevents_incident_python_exception.json').read_text())


@pytest.fixture
def fixture_incident_java_exception():
    """Raw service_events incident_snapshot (Java exception with call_path) OTLP record."""
    return json.loads((FIXTURES_DIR / 'serviceevents_incident_java_exception.json').read_text())


@pytest.fixture
def fixture_deployment():
    """Raw service_events deployment_event OTLP record."""
    return json.loads((FIXTURES_DIR / 'serviceevents_deployment.json').read_text())
