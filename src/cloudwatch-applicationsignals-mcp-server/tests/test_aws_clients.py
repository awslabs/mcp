"""Tests for aws_clients module public API."""

import pytest
from unittest.mock import MagicMock

from awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients import (
    AWS_REGION,
    _DEFAULT_REGION,
    _singleton_clients,
    clear_client_factory,
    clear_region_override,
    get_client,
    get_region,
    logs_client,
    applicationsignals_client,
    cloudwatch_client,
    xray_client,
    region_override,
    set_client_factory,
    set_region_override,
)


# ---------------------------------------------------------------------------
# get_region / set_region_override / clear_region_override
# ---------------------------------------------------------------------------


class TestGetRegion:
    def test_returns_default(self):
        clear_client_factory()
        assert get_region() == _DEFAULT_REGION

    def test_returns_override(self):
        factory = MagicMock(side_effect=lambda svc: MagicMock())
        set_client_factory(factory)
        try:
            set_region_override('eu-west-1')
            assert get_region() == 'eu-west-1'
        finally:
            clear_client_factory()

    def test_clear_region_override_reverts(self):
        factory = MagicMock(side_effect=lambda svc: MagicMock())
        set_client_factory(factory)
        try:
            set_region_override('ap-southeast-1')
            clear_region_override()
            assert get_region() == _DEFAULT_REGION
        finally:
            clear_client_factory()

    def test_set_region_override_requires_factory(self):
        clear_client_factory()
        with pytest.raises(RuntimeError, match='requires a custom client factory'):
            set_region_override('us-west-2')

    def test_region_override_context_manager(self):
        factory = MagicMock(side_effect=lambda svc: MagicMock())
        set_client_factory(factory)
        try:
            with region_override('us-west-2'):
                assert get_region() == 'us-west-2'
            assert get_region() == _DEFAULT_REGION
        finally:
            clear_client_factory()


# ---------------------------------------------------------------------------
# get_client / set_client_factory / clear_client_factory
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_returns_singleton_in_default_mode(self):
        clear_client_factory()
        client_a = get_client('logs')
        client_b = get_client('logs')
        assert client_a is client_b
        assert client_a is _singleton_clients['logs']

    def test_uses_factory_when_set(self):
        mock_client = MagicMock()
        factory = MagicMock(return_value=mock_client)
        set_client_factory(factory)
        try:
            result = get_client('logs')
            factory.assert_called_once_with('logs')
            assert result is mock_client
        finally:
            clear_client_factory()

    def test_unknown_service_raises(self):
        clear_client_factory()
        with pytest.raises(KeyError, match='Unknown service'):
            get_client('nonexistent-service')

    def test_clear_client_factory_reverts_to_singleton(self):
        factory = MagicMock(return_value=MagicMock())
        set_client_factory(factory)
        clear_client_factory()
        result = get_client('logs')
        assert result is _singleton_clients['logs']
        factory.assert_not_called()

    def test_clear_client_factory_also_clears_region(self):
        factory = MagicMock(side_effect=lambda svc: MagicMock())
        set_client_factory(factory)
        set_region_override('eu-west-1')
        clear_client_factory()
        assert get_region() == _DEFAULT_REGION


# ---------------------------------------------------------------------------
# Backward-compatible module-level exports
# ---------------------------------------------------------------------------


class TestBackwardCompatExports:
    def test_aws_region_equals_default(self):
        assert AWS_REGION == _DEFAULT_REGION

    def test_module_level_clients_exist(self):
        assert logs_client is not None
        assert applicationsignals_client is not None
        assert cloudwatch_client is not None
        assert xray_client is not None

    def test_module_level_clients_match_singletons(self):
        assert logs_client is _singleton_clients['logs']
        assert applicationsignals_client is _singleton_clients['application-signals']
        assert cloudwatch_client is _singleton_clients['cloudwatch']
        assert xray_client is _singleton_clients['xray']
