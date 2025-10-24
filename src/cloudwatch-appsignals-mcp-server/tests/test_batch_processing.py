"""Tests for batch processing functionality with proper mocking."""

import json
import pytest
from awslabs.cloudwatch_appsignals_mcp_server.server import audit_services
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_appsignals_client():
    """Create a properly mocked appsignals client."""
    mock_client = MagicMock()
    mock_client.list_audit_findings.return_value = {'AuditFindings': []}
    return mock_client


@pytest.mark.asyncio
async def test_audit_services_batch_processing_success(mock_appsignals_client):
    """Test audit_services triggers batch processing for large target lists."""
    # Create 12 targets to exceed AUDIT_SERVICE_BATCH_SIZE_THRESHOLD (5)
    service_targets = json.dumps(
        [
            {
                'Type': 'service',
                'Data': {
                    'Service': {
                        'Type': 'Service',
                        'Name': f'test-service-{i}',
                        'Environment': 'eks:test',
                    }
                },
            }
            for i in range(12)
        ]
    )

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_audit_utils.validate_and_enrich_service_targets'
        ) as mock_validate,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.appsignals_client',
            mock_appsignals_client,
        ),
    ):
        mock_validate.return_value = json.loads(service_targets)

        result = await audit_services(
            service_targets=service_targets, start_time=None, end_time=None, auditors='slo'
        )

        # Verify batch processing was triggered
        assert '📦 Batching: Processing 12 targets in batches of 5' in result


@pytest.mark.asyncio
async def test_audit_services_batch_processing_error(mock_appsignals_client):
    """Test audit_services batch processing error handling."""
    # Set up client mock to raise an exception
    mock_appsignals_client.list_audit_findings.side_effect = Exception(
        'Failed to process batch due to API error'
    )

    # Create 11 targets to exceed threshold
    service_targets = json.dumps(
        [
            {
                'Type': 'service',
                'Data': {
                    'Service': {
                        'Type': 'Service',
                        'Name': f'test-service-{i}',
                        'Environment': 'eks:test',
                    }
                },
            }
            for i in range(11)
        ]
    )

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_audit_utils.validate_and_enrich_service_targets'
        ) as mock_validate,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.appsignals_client',
            mock_appsignals_client,
        ),
    ):
        mock_validate.return_value = json.loads(service_targets)

        result = await audit_services(
            service_targets=service_targets, start_time=None, end_time=None, auditors='slo'
        )

        assert 'Error processing first batch: Failed to process batch due to API error' in result


@pytest.mark.asyncio
async def test_audit_services_batch_processing_session_not_found(mock_appsignals_client):
    """Test audit_services batch processing when session is not found."""
    # Create 11 targets to exceed threshold
    service_targets = json.dumps(
        [
            {
                'Type': 'service',
                'Data': {
                    'Service': {
                        'Type': 'Service',
                        'Name': f'test-service-{i}',
                        'Environment': 'eks:test',
                    }
                },
            }
            for i in range(11)
        ]
    )

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_audit_utils.validate_and_enrich_service_targets'
        ) as mock_validate,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.get_batch_session'
        ) as mock_get_session,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.appsignals_client',
            mock_appsignals_client,
        ),
    ):
        mock_validate.return_value = json.loads(service_targets)
        mock_get_session.return_value = None  # Session not found

        result = await audit_services(
            service_targets=service_targets, start_time=None, end_time=None, auditors='slo'
        )

        assert 'Session not found' in result


@pytest.mark.asyncio
async def test_audit_services_session_not_found_error(mock_appsignals_client):
    """Test audit_services when get_batch_session returns None (line 456)."""
    service_targets = json.dumps(
        [
            {
                'Type': 'service',
                'Data': {
                    'Service': {
                        'Type': 'Service',
                        'Name': f'test-service-{i}',
                        'Environment': 'eks:test',
                    }
                },
            }
            for i in range(11)  # Exceed threshold
        ]
    )

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_audit_utils.validate_and_enrich_service_targets'
        ) as mock_validate,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.get_batch_session',
            return_value=None,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.appsignals_client',
            mock_appsignals_client,
        ),
    ):
        mock_validate.return_value = json.loads(service_targets)

        result = await audit_services(
            service_targets=service_targets, start_time=None, end_time=None, auditors='slo'
        )

        assert 'Error processing first batch: Session not found or expired' in result


@pytest.mark.asyncio
async def test_audit_services_small_target_list_no_batching(mock_appsignals_client):
    """Test audit_services with small target list - non-batch path (lines 465-469)."""
    service_targets = json.dumps(
        [
            {
                'Type': 'service',
                'Data': {
                    'Service': {
                        'Type': 'Service',
                        'Name': 'test-service-1',
                        'Environment': 'eks:test',
                    }
                },
            },
            {
                'Type': 'service',
                'Data': {
                    'Service': {
                        'Type': 'Service',
                        'Name': 'test-service-2',
                        'Environment': 'eks:test',
                    }
                },
            },
        ]
    )  # Only 2 targets, below threshold

    mock_appsignals_client.list_audit_findings.return_value = {'AuditFindings': []}

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_audit_utils.validate_and_enrich_service_targets'
        ) as mock_validate,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.appsignals_client',
            mock_appsignals_client,
        ),
    ):
        mock_validate.return_value = json.loads(service_targets)

        result = await audit_services(
            service_targets=service_targets, start_time=None, end_time=None, auditors='slo'
        )

        assert '[MCP-SERVICE] Application Signals Service Audit' in result
        assert '📦 Batching:' not in result  # No batching message
        mock_appsignals_client.list_audit_findings.assert_called_once()
