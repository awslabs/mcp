"""Tests for per-call AWS profile support."""

import inspect
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server import __version__
from unittest.mock import AsyncMock, MagicMock, patch


def test_get_aws_client_with_profile_name():
    """Explicit profile_name should create a profile-scoped boto3 session."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients import get_aws_client

    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client

    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.boto3.Session',
        return_value=mock_session,
    ) as mock_session_class:
        result = get_aws_client(
            'application-signals', region_name='us-west-2', profile_name='prod-profile'
        )

    mock_session_class.assert_called_once_with(
        profile_name='prod-profile', region_name='us-west-2'
    )
    mock_session.client.assert_called_once()
    call_args = mock_session.client.call_args
    assert call_args.args[0] == 'application-signals'
    assert call_args.kwargs['region_name'] == 'us-west-2'
    assert result == mock_client


def test_get_aws_client_profile_name_takes_precedence_over_env():
    """Explicit profile_name should override AWS_PROFILE."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients import get_aws_client

    mock_session = MagicMock()
    mock_session.client.return_value = MagicMock()

    with patch.dict('os.environ', {'AWS_PROFILE': 'env-profile'}):
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.boto3.Session',
            return_value=mock_session,
        ) as mock_session_class:
            get_aws_client('logs', profile_name='explicit-profile')

    mock_session_class.assert_called_once_with(
        profile_name='explicit-profile', region_name='us-east-1'
    )


def test_get_aws_client_uses_aws_profile_env():
    """Missing profile_name should fall back to AWS_PROFILE."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients import get_aws_client

    mock_session = MagicMock()
    mock_session.client.return_value = MagicMock()

    with patch.dict('os.environ', {'AWS_PROFILE': 'env-profile'}):
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.boto3.Session',
            return_value=mock_session,
        ) as mock_session_class:
            get_aws_client('cloudwatch')

    mock_session_class.assert_called_once_with(profile_name='env-profile', region_name='us-east-1')


def test_get_aws_client_without_profile_uses_default_credential_chain():
    """Missing profile_name and AWS_PROFILE should use a default boto3 session."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients import get_aws_client

    mock_session = MagicMock()
    mock_session.client.return_value = MagicMock()

    with patch.dict('os.environ', {}, clear=True):
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.boto3.Session',
            return_value=mock_session,
        ) as mock_session_class:
            get_aws_client('xray', region_name='eu-west-1')

    mock_session_class.assert_called_once_with(region_name='eu-west-1')


def test_get_aws_client_preserves_user_agent_and_endpoint_override():
    """Profile-scoped clients should keep existing user-agent and endpoint behavior."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients import get_aws_client

    mock_session = MagicMock()
    mock_session.client.return_value = MagicMock()

    with patch.dict(
        'os.environ',
        {'MCP_RUN_FROM': 'test-caller', 'MCP_RUM_ENDPOINT': 'https://rum.test.local'},
        clear=True,
    ):
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.boto3.Session',
            return_value=mock_session,
        ):
            get_aws_client('rum')

    call_args = mock_session.client.call_args
    assert call_args.kwargs['endpoint_url'] == 'https://rum.test.local'
    assert (
        call_args.kwargs['config'].user_agent_extra
        == f'awslabs.cloudwatch-applicationsignals-mcp-server/{__version__}/test-caller'
    )


def test_issue_tools_expose_profile_name():
    """AWS-backed AppSignals tools should include profile_name in MCP-derived signatures."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.change_tools import list_change_events
    from awslabs.cloudwatch_applicationsignals_mcp_server.group_tools import (
        audit_group_health,
        get_group_changes,
        get_group_dependencies,
        list_group_services,
        list_grouping_attribute_definitions,
    )
    from awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools import query_rum_events
    from awslabs.cloudwatch_applicationsignals_mcp_server.server import (
        analyze_canary_failures,
        audit_service_operations,
        audit_services,
        audit_slos,
        list_canaries,
    )
    from awslabs.cloudwatch_applicationsignals_mcp_server.service_tools import (
        get_service_detail,
        list_monitored_services,
        list_service_operations,
        query_service_metrics,
    )
    from awslabs.cloudwatch_applicationsignals_mcp_server.slo_tools import get_slo, list_slos
    from awslabs.cloudwatch_applicationsignals_mcp_server.trace_tools import (
        list_slis,
        query_sampled_traces,
        search_transaction_spans,
    )

    tools = [
        audit_services,
        audit_slos,
        audit_service_operations,
        analyze_canary_failures,
        list_canaries,
        list_monitored_services,
        get_service_detail,
        query_service_metrics,
        list_service_operations,
        get_slo,
        list_slos,
        search_transaction_spans,
        query_sampled_traces,
        list_slis,
        list_change_events,
        list_group_services,
        audit_group_health,
        get_group_dependencies,
        get_group_changes,
        list_grouping_attribute_definitions,
        query_rum_events,
    ]

    for tool in tools:
        assert 'profile_name' in inspect.signature(tool).parameters


@pytest.mark.asyncio
async def test_audit_slos_passes_profile_scoped_client_to_audit_api():
    """audit_slos should route AWS calls through the profile-scoped client."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.server import audit_slos

    mock_client = MagicMock()
    mock_execute = AsyncMock(return_value='audit result')

    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.server.get_aws_client',
        return_value=mock_client,
    ) as mock_get_client:
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api',
            mock_execute,
        ):
            result = await audit_slos(
                slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"checkout-slo"}}}]',
                start_time=None,
                end_time=None,
                auditors=None,
                next_token=None,
                max_slos=5,
                profile_name='prod-profile',
            )

    mock_get_client.assert_called_once_with(
        'application-signals', region_name='us-east-1', profile_name='prod-profile'
    )
    assert mock_execute.call_args.args[3] == mock_client
    assert result == 'audit result'


@pytest.mark.asyncio
async def test_get_service_detail_uses_profile_scoped_client():
    """Service tools should use the profile-scoped client when profile_name is provided."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.service_tools import get_service_detail

    mock_client = MagicMock()
    mock_client.list_services.return_value = {
        'ServiceSummaries': [{'KeyAttributes': {'Name': 'checkout', 'Type': 'Service'}}]
    }
    mock_client.get_service.return_value = {
        'Service': {'KeyAttributes': {'Name': 'checkout'}, 'MetricReferences': []}
    }

    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.service_tools.get_aws_client',
        return_value=mock_client,
    ) as mock_get_client:
        result = await get_service_detail('checkout', profile_name='prod-profile')

    mock_get_client.assert_called_once_with(
        'application-signals', region_name='us-east-1', profile_name='prod-profile'
    )
    assert 'Service Details: checkout' in result


@pytest.mark.asyncio
async def test_get_slo_uses_profile_scoped_client():
    """SLO tools should use the profile-scoped client when profile_name is provided."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.slo_tools import get_slo

    mock_client = MagicMock()
    mock_client.get_service_level_objective.return_value = {
        'Slo': {'Name': 'checkout-slo', 'Arn': 'arn:test'}
    }

    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.slo_tools.get_aws_client',
        return_value=mock_client,
    ) as mock_get_client:
        result = await get_slo('checkout-slo', profile_name='prod-profile')

    mock_get_client.assert_called_once_with(
        'application-signals', region_name='us-east-1', profile_name='prod-profile'
    )
    assert 'checkout-slo' in result


@pytest.mark.asyncio
async def test_query_rum_events_passes_profile_scoped_client_bundle():
    """RUM dispatcher should route actions through profile-scoped clients."""
    from awslabs.cloudwatch_applicationsignals_mcp_server import rum_tools

    async def handler(_clients=None):
        assert _clients is not None
        return str(sorted(_clients.keys()))

    mock_clients = [MagicMock(name=f'client-{i}') for i in range(6)]

    with patch.dict(rum_tools._ACTION_MAP, {'test_action': handler}):
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.rum_tools.get_aws_client',
            side_effect=mock_clients,
        ) as mock_get_client:
            result = await rum_tools.query_rum_events(
                action='test_action', profile_name='prod-profile'
            )

    requested_services = [call.args[0] for call in mock_get_client.call_args_list]
    assert requested_services == [
        'application-signals',
        'cloudwatch',
        'logs',
        'rum',
        'sts',
        'xray',
    ]
    assert 'applicationsignals' in result
    assert 'cloudwatch' in result
    assert 'xray' in result
