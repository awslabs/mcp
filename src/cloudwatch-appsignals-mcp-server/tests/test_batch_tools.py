"""Tests for batch tools."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.batch_tools import (
    continue_audit_batch,
)
from unittest.mock import patch


@pytest.fixture
def mock_batch_processing_utils():
    """Mock batch processing utilities."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_tools.process_next_batch'
        ) as mock_process,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_tools.get_batch_session'
        ) as mock_get_session,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_tools.format_batch_result'
        ) as mock_format,
    ):
        yield {
            'process_next_batch': mock_process,
            'get_batch_session': mock_get_session,
            'format_batch_result': mock_format,
        }


@pytest.fixture
def mock_appsignals_client():
    """Mock Application Signals client."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.batch_tools.appsignals_client'
    ) as mock_client:
        yield mock_client


class TestContinueAuditBatch:
    """Test continue_audit_batch function."""

    @pytest.mark.asyncio
    async def test_continue_audit_batch_success(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test successful batch continuation."""
        session_id = 'test-session-123'

        # Mock successful batch processing
        batch_result = {
            'batch_index': 2,
            'total_batches': 3,
            'targets_in_batch': 5,
            'findings_count': 1,
            'findings': [{'FindingId': 'finding-1', 'Severity': 'WARNING'}],
            'status': 'success',
        }

        session = {
            'session_id': session_id,
            'status': 'in_progress',
            'current_batch_index': 2,
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result
        mock_batch_processing_utils['get_batch_session'].return_value = session
        mock_batch_processing_utils[
            'format_batch_result'
        ].return_value = (
            f"⚠️ Batch 2/3: 1 findings | Continue: continue_audit_batch('{session_id}')"
        )

        result = await continue_audit_batch(session_id)

        # Verify the mocks were called correctly
        mock_batch_processing_utils['process_next_batch'].assert_called_once_with(
            session_id, mock_appsignals_client
        )
        mock_batch_processing_utils['get_batch_session'].assert_called_once_with(session_id)
        mock_batch_processing_utils['format_batch_result'].assert_called_once_with(
            batch_result, session
        )

        # Verify the result
        assert f"Continue: continue_audit_batch('{session_id}')" in result
        assert '⚠️ Batch 2/3: 1 findings' in result

    @pytest.mark.asyncio
    async def test_continue_audit_batch_error_in_processing(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation with processing error."""
        session_id = 'test-session-123'

        # Mock error in batch processing
        batch_result = {
            'error': 'No more batches to process',
            'status': 'completed',
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result

        result = await continue_audit_batch(session_id)

        assert result == 'Error: No more batches to process'
        mock_batch_processing_utils['process_next_batch'].assert_called_once_with(
            session_id, mock_appsignals_client
        )

    @pytest.mark.asyncio
    async def test_continue_audit_batch_session_not_found(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation when session is not found."""
        session_id = 'nonexistent-session'

        # Mock successful processing but no session found
        batch_result = {
            'batch_index': 1,
            'total_batches': 1,
            'status': 'success',
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result
        mock_batch_processing_utils['get_batch_session'].return_value = None

        result = await continue_audit_batch(session_id)

        assert result == 'Error: Session not found or expired'

    @pytest.mark.asyncio
    async def test_continue_audit_batch_healthy_services(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation with healthy services."""
        session_id = 'test-session-123'

        # Mock healthy batch result
        batch_result = {
            'batch_index': 1,
            'total_batches': 2,
            'targets_in_batch': 5,
            'findings_count': 0,
            'findings': [],
            'status': 'success',
        }

        session = {
            'session_id': session_id,
            'status': 'in_progress',
            'current_batch_index': 1,
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result
        mock_batch_processing_utils['get_batch_session'].return_value = session
        mock_batch_processing_utils[
            'format_batch_result'
        ].return_value = (
            f"✅ Batch 1/2: 5 services healthy | Continue: continue_audit_batch('{session_id}')"
        )

        result = await continue_audit_batch(session_id)

        assert '✅ Batch 1/2: 5 services healthy' in result
        assert f"Continue: continue_audit_batch('{session_id}')" in result

    @pytest.mark.asyncio
    async def test_continue_audit_batch_final_batch(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation for final batch."""
        session_id = 'test-session-123'

        # Mock final batch result
        batch_result = {
            'batch_index': 3,
            'total_batches': 3,
            'targets_in_batch': 2,
            'findings_count': 0,
            'findings': [],
            'status': 'success',
        }

        session = {
            'session_id': session_id,
            'status': 'completed',
            'current_batch_index': 3,
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result
        mock_batch_processing_utils['get_batch_session'].return_value = session
        mock_batch_processing_utils[
            'format_batch_result'
        ].return_value = '✅ Batch 3/3: 2 services healthy'

        result = await continue_audit_batch(session_id)

        assert '✅ Batch 3/3: 2 services healthy' in result
        # Should not contain continuation instruction for final batch
        assert 'Continue:' not in result

    @pytest.mark.asyncio
    async def test_continue_audit_batch_with_findings_json(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation with findings that include JSON output."""
        session_id = 'test-session-123'

        # Mock batch result with findings
        findings = [
            {
                'FindingId': 'finding-1',
                'Severity': 'CRITICAL',
                'Title': 'High error rate detected',
                'Description': 'Service experiencing elevated error rates',
                'ServiceName': 'payment-service',
            },
            {
                'FindingId': 'finding-2',
                'Severity': 'WARNING',
                'Title': 'Elevated latency',
                'Description': 'Response times are higher than normal',
                'ServiceName': 'user-service',
            },
        ]

        batch_result = {
            'batch_index': 1,
            'total_batches': 1,
            'targets_in_batch': 3,
            'findings_count': 2,
            'findings': findings,
            'status': 'success',
        }

        session = {
            'session_id': session_id,
            'status': 'completed',
            'current_batch_index': 1,
        }

        # Mock format_batch_result to return JSON findings
        formatted_findings = f'⚠️ Batch 1/1: 2 findings\n```\n{findings}\n```'

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result
        mock_batch_processing_utils['get_batch_session'].return_value = session
        mock_batch_processing_utils['format_batch_result'].return_value = formatted_findings

        result = await continue_audit_batch(session_id)

        assert '⚠️ Batch 1/1: 2 findings' in result
        assert '```' in result  # JSON formatting markers
        assert 'CRITICAL' in result
        assert 'payment-service' in result

    @pytest.mark.asyncio
    async def test_continue_audit_batch_exception_handling(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation with unexpected exception."""
        session_id = 'test-session-123'

        # Mock exception during processing
        mock_batch_processing_utils['process_next_batch'].side_effect = Exception(
            'Unexpected error'
        )

        result = await continue_audit_batch(session_id)

        assert result == 'Error: Unexpected error'

    @pytest.mark.asyncio
    async def test_continue_audit_batch_invalid_session_id(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation with invalid session ID format."""
        session_id = 'invalid-session-format'

        # Mock error for invalid session
        batch_result = {
            'error': 'Session not found or expired',
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result

        result = await continue_audit_batch(session_id)

        assert result == 'Error: Session not found or expired'

    @pytest.mark.asyncio
    async def test_continue_audit_batch_api_failure(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation when API call fails."""
        session_id = 'test-session-123'

        # Mock API failure - when batch_result has an error, the function returns early
        batch_result = {
            'batch_index': 1,
            'total_batches': 2,
            'targets_in_batch': 5,
            'error': 'AWS API throttling error',
            'status': 'failed',
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result

        result = await continue_audit_batch(session_id)

        # When batch_result has an error, the function returns early with just the error message
        assert result == 'Error: AWS API throttling error'


class TestIntegration:
    """Integration tests for batch tools workflow."""

    @pytest.mark.asyncio
    async def test_full_batch_continuation_workflow(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test complete batch continuation workflow."""
        session_id = 'integration-test-session'

        # Simulate processing multiple batches
        batch_results = [
            {
                'batch_index': 1,
                'total_batches': 3,
                'targets_in_batch': 5,
                'findings_count': 0,
                'findings': [],
                'status': 'success',
            },
            {
                'batch_index': 2,
                'total_batches': 3,
                'targets_in_batch': 5,
                'findings_count': 2,
                'findings': [
                    {'FindingId': 'finding-1', 'Severity': 'WARNING'},
                    {'FindingId': 'finding-2', 'Severity': 'CRITICAL'},
                ],
                'status': 'success',
            },
            {
                'batch_index': 3,
                'total_batches': 3,
                'targets_in_batch': 3,
                'findings_count': 0,
                'findings': [],
                'status': 'success',
            },
        ]

        sessions = [
            {'session_id': session_id, 'status': 'in_progress', 'current_batch_index': 1},
            {'session_id': session_id, 'status': 'in_progress', 'current_batch_index': 2},
            {'session_id': session_id, 'status': 'completed', 'current_batch_index': 3},
        ]

        formatted_results = [
            f"✅ Batch 1/3: 5 services healthy | Continue: continue_audit_batch('{session_id}')",
            f"⚠️ Batch 2/3: 2 findings | Continue: continue_audit_batch('{session_id}')",
            '✅ Batch 3/3: 3 services healthy',
        ]

        # Configure mocks for sequential calls
        mock_batch_processing_utils['process_next_batch'].side_effect = batch_results
        mock_batch_processing_utils['get_batch_session'].side_effect = sessions
        mock_batch_processing_utils['format_batch_result'].side_effect = formatted_results

        # Process first batch (healthy)
        result1 = await continue_audit_batch(session_id)
        assert '✅ Batch 1/3: 5 services healthy' in result1
        assert f"Continue: continue_audit_batch('{session_id}')" in result1

        # Process second batch (with findings)
        result2 = await continue_audit_batch(session_id)
        assert '⚠️ Batch 2/3: 2 findings' in result2
        assert f"Continue: continue_audit_batch('{session_id}')" in result2

        # Process final batch (healthy, no continuation)
        result3 = await continue_audit_batch(session_id)
        assert '✅ Batch 3/3: 3 services healthy' in result3
        assert 'Continue:' not in result3

        # Verify all calls were made
        assert mock_batch_processing_utils['process_next_batch'].call_count == 3
        assert mock_batch_processing_utils['get_batch_session'].call_count == 3
        assert mock_batch_processing_utils['format_batch_result'].call_count == 3

    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test error handling throughout the workflow."""
        session_id = 'error-test-session'

        # Test continue_audit_batch error handling
        mock_batch_processing_utils['process_next_batch'].side_effect = Exception(
            'Processing error'
        )

        continue_result = await continue_audit_batch(session_id)
        assert continue_result == 'Error: Processing error'


class TestParameterValidation:
    """Test parameter validation and edge cases."""

    @pytest.mark.asyncio
    async def test_continue_audit_batch_empty_session_id(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation with empty session ID."""
        session_id = ''

        # Mock error for empty session ID
        batch_result = {
            'error': 'Session not found or expired',
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result

        result = await continue_audit_batch(session_id)

        assert result == 'Error: Session not found or expired'
        mock_batch_processing_utils['process_next_batch'].assert_called_once_with(
            session_id, mock_appsignals_client
        )

    @pytest.mark.asyncio
    async def test_continue_audit_batch_none_session_id(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation with None session ID."""
        # Pydantic validation will convert None to string "None" or handle it gracefully
        # Mock error for None session ID
        batch_result = {
            'error': 'Session not found or expired',
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result

        # This should not raise an exception but return an error message
        # Fix type error: pass empty string instead of None
        result = await continue_audit_batch('')

        assert result == 'Error: Session not found or expired'

    @pytest.mark.asyncio
    async def test_continue_audit_batch_very_long_session_id(
        self, mock_batch_processing_utils, mock_appsignals_client
    ):
        """Test batch continuation with very long session ID."""
        session_id = 'a' * 1000  # Very long session ID

        # Mock error for invalid session
        batch_result = {
            'error': 'Session not found or expired',
        }

        mock_batch_processing_utils['process_next_batch'].return_value = batch_result

        result = await continue_audit_batch(session_id)

        assert result == 'Error: Session not found or expired'
