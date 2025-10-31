"""Tests for batch processing utilities."""

import pytest
import uuid
from awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils import (
    _batch_sessions,
    _build_api_input,
    _cleanup_excess_sessions,
    _create_batch_metadata,
    _update_session_after_batch,
    create_batch_session,
    format_batch_result,
    get_batch_session,
    process_next_batch,
    update_batch_session_activity,
)
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_targets():
    """Sample targets for testing."""
    return [
        {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': f'service-{i}'}}}
        for i in range(1, 16)  # 15 services
    ]


@pytest.fixture
def sample_input_obj():
    """Sample input object for testing."""
    return {
        'StartTime': datetime.now(timezone.utc).timestamp(),
        'EndTime': datetime.now(timezone.utc).timestamp(),
        'Auditors': 'slo,operation_metric',
    }


@pytest.fixture
def mock_appsignals_client():
    """Mock Application Signals client."""
    client = MagicMock()
    client.list_audit_findings.return_value = {
        'AuditFindings': [
            {
                'FindingId': 'finding-1',
                'Severity': 'CRITICAL',
                'Title': 'High error rate detected',
                'Description': 'Service experiencing elevated error rates',
            }
        ]
    }
    return client


class TestCreateBatchSession:
    """Test create_batch_session function."""

    def test_create_batch_session_basic(self, sample_targets, sample_input_obj):
        """Test basic batch session creation."""
        session_id = create_batch_session(
            targets=sample_targets[:5],  # Small list
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=10,
        )

        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID length

        session = get_batch_session(session_id)
        assert session is not None
        assert session['session_id'] == session_id
        assert len(session['targets']) == 5
        assert len(session['batches']) == 1  # All targets fit in one batch
        assert session['current_batch_index'] == 0
        assert session['auto_complete'] is True  # Small list auto-completes
        assert session['status'] == 'created'

    def test_create_batch_session_large_list(self, sample_targets, sample_input_obj):
        """Test batch session creation with large target list."""
        session_id = create_batch_session(
            targets=sample_targets,  # 15 services
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=5,
        )

        session = get_batch_session(session_id)
        assert session is not None
        assert len(session['batches']) == 3  # 15 targets / 5 batch_size = 3 batches
        assert session['auto_complete'] is False  # Large list uses interactive mode
        assert len(session['batches'][0]) == 5
        assert len(session['batches'][1]) == 5
        assert len(session['batches'][2]) == 5

    def test_create_batch_session_explicit_auto_complete(self, sample_targets, sample_input_obj):
        """Test batch session creation with explicit auto_complete setting."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=10,
            auto_complete=False,  # Force interactive mode
        )

        session = get_batch_session(session_id)
        assert session is not None
        assert session['auto_complete'] is False

    def test_create_batch_session_without_auditors(self, sample_targets):
        """Test batch session creation without auditors in input."""
        input_obj = {
            'StartTime': datetime.now(timezone.utc).timestamp(),
            'EndTime': datetime.now(timezone.utc).timestamp(),
        }

        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        assert 'Auditors' not in session['input_obj']

    def test_create_batch_session_uneven_batches(self, sample_input_obj):
        """Test batch session creation with uneven batch sizes."""
        targets = [
            {'Type': 'service', 'Data': {'Service': {'Type': 'Service', 'Name': f'service-{i}'}}}
            for i in range(1, 8)  # 7 services
        ]

        session_id = create_batch_session(
            targets=targets,
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=3,
        )

        session = get_batch_session(session_id)
        assert session is not None
        assert len(session['batches']) == 3  # 7 targets / 3 batch_size = 3 batches
        assert len(session['batches'][0]) == 3
        assert len(session['batches'][1]) == 3
        assert len(session['batches'][2]) == 1  # Remainder


class TestGetBatchSession:
    """Test get_batch_session function."""

    def test_get_batch_session_exists(self, sample_targets, sample_input_obj):
        """Test getting an existing batch session."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        assert session['session_id'] == session_id

    def test_get_batch_session_not_exists(self):
        """Test getting a non-existent batch session."""
        fake_session_id = str(uuid.uuid4())
        session = get_batch_session(fake_session_id)
        assert session is None


class TestUpdateBatchSessionActivity:
    """Test update_batch_session_activity function."""

    def test_update_batch_session_activity_exists(self, sample_targets, sample_input_obj):
        """Test updating activity for existing session."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        original_activity = session['last_activity']

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        update_batch_session_activity(session_id)

        session = get_batch_session(session_id)
        assert session is not None
        updated_activity = session['last_activity']
        assert updated_activity != original_activity

    def test_update_batch_session_activity_not_exists(self):
        """Test updating activity for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        # Should not raise an exception
        update_batch_session_activity(fake_session_id)


class TestCreateBatchMetadata:
    """Test _create_batch_metadata function."""

    def test_create_batch_metadata(self, sample_targets, sample_input_obj):
        """Test creating batch metadata."""
        session_id = create_batch_session(
            targets=sample_targets,
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=5,
        )

        session = get_batch_session(session_id)
        assert session is not None
        current_batch = session['batches'][0]

        metadata = _create_batch_metadata(session, current_batch)

        assert metadata['batch_index'] == 1  # 1-based indexing
        assert metadata['total_batches'] == 3
        assert metadata['targets_in_batch'] == 5
        assert metadata['targets'] == current_batch


class TestBuildApiInput:
    """Test _build_api_input function."""

    def test_build_api_input_with_auditors(self, sample_targets, sample_input_obj):
        """Test building API input with auditors."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        current_batch = session['batches'][0]

        api_input = _build_api_input(session, current_batch)

        assert 'StartTime' in api_input
        assert 'EndTime' in api_input
        assert 'AuditTargets' in api_input
        assert 'Auditors' in api_input
        assert api_input['AuditTargets'] == current_batch
        assert api_input['Auditors'] == 'slo,operation_metric'
        assert isinstance(api_input['StartTime'], datetime)
        assert isinstance(api_input['EndTime'], datetime)

    def test_build_api_input_without_auditors(self, sample_targets):
        """Test building API input without auditors."""
        input_obj = {
            'StartTime': datetime.now(timezone.utc).timestamp(),
            'EndTime': datetime.now(timezone.utc).timestamp(),
        }

        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        current_batch = session['batches'][0]

        api_input = _build_api_input(session, current_batch)

        assert 'StartTime' in api_input
        assert 'EndTime' in api_input
        assert 'AuditTargets' in api_input
        assert 'Auditors' not in api_input


class TestUpdateSessionAfterBatch:
    """Test _update_session_after_batch function."""

    def test_update_session_after_batch_success(self, sample_targets, sample_input_obj):
        """Test updating session after successful batch processing."""
        session_id = create_batch_session(
            targets=sample_targets,
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=5,
        )

        session = get_batch_session(session_id)
        assert session is not None
        original_index = session['current_batch_index']

        batch_result = {
            'batch_index': 1,
            'total_batches': 3,
            'targets_in_batch': 5,
            'findings_count': 2,
            'findings': [{'finding': 'test'}],
            'status': 'success',
        }

        _update_session_after_batch(session, batch_result)

        assert session['current_batch_index'] == original_index + 1
        assert len(session['processed_batches']) == 1
        assert session['processed_batches'][0] == batch_result
        assert len(session['all_findings']) == 1
        assert session['status'] == 'in_progress'

    def test_update_session_after_batch_failure(self, sample_targets, sample_input_obj):
        """Test updating session after failed batch processing."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None

        batch_result = {
            'batch_index': 1,
            'total_batches': 1,
            'targets_in_batch': 3,
            'error': 'API error',
            'status': 'failed',
        }

        _update_session_after_batch(session, batch_result)

        assert session['current_batch_index'] == 1
        assert len(session['failed_batches']) == 1
        assert session['failed_batches'][0] == batch_result
        assert len(session['all_findings']) == 0
        assert session['status'] == 'completed'  # Single batch completed

    def test_update_session_after_batch_completion(self, sample_targets, sample_input_obj):
        """Test session status when all batches are processed."""
        session_id = create_batch_session(
            targets=sample_targets[:5],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=5,
        )

        session = get_batch_session(session_id)
        assert session is not None

        batch_result = {
            'batch_index': 1,
            'total_batches': 1,
            'targets_in_batch': 5,
            'findings_count': 0,
            'findings': [],
            'status': 'success',
        }

        _update_session_after_batch(session, batch_result)

        assert session['status'] == 'completed'


class TestProcessNextBatch:
    """Test process_next_batch function."""

    def test_process_next_batch_success(
        self, sample_targets, sample_input_obj, mock_appsignals_client
    ):
        """Test successful batch processing."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        result = process_next_batch(session_id, mock_appsignals_client)

        assert result['status'] == 'success'
        assert result['batch_index'] == 1
        assert result['total_batches'] == 1
        assert result['targets_in_batch'] == 3
        assert result['findings_count'] == 1
        assert len(result['findings']) == 1

        # Verify session was updated
        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 1
        assert session['status'] == 'completed'

    def test_process_next_batch_api_error(self, sample_targets, sample_input_obj):
        """Test batch processing with API error - batch index should NOT advance for retry."""
        mock_client = MagicMock()
        mock_client.list_audit_findings.side_effect = Exception('API error')

        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        result = process_next_batch(session_id, mock_client)

        assert result['status'] == 'failed'
        assert result['error'] == 'API error'
        assert result['batch_index'] == 1

        # Verify session was NOT updated (for retry capability)
        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 0  # Should NOT advance on failure
        assert len(session['failed_batches']) == 0  # Should NOT be added to failed_batches
        assert len(session['processed_batches']) == 0
        assert session['status'] == 'created'  # Should remain in original status

    def test_process_next_batch_session_not_found(self, mock_appsignals_client):
        """Test batch processing with non-existent session."""
        fake_session_id = str(uuid.uuid4())

        result = process_next_batch(fake_session_id, mock_appsignals_client)

        assert 'error' in result
        assert 'Session not found or expired' in result['error']

    def test_process_next_batch_no_more_batches(
        self, sample_targets, sample_input_obj, mock_appsignals_client
    ):
        """Test batch processing when no more batches remain."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        # Process the first (and only) batch
        process_next_batch(session_id, mock_appsignals_client)

        # Try to process again
        result = process_next_batch(session_id, mock_appsignals_client)

        assert 'error' in result
        assert 'No more batches to process' in result['error']
        assert result['status'] == 'completed'

    def test_process_next_batch_multiple_batches(
        self, sample_targets, sample_input_obj, mock_appsignals_client
    ):
        """Test processing multiple batches sequentially."""
        session_id = create_batch_session(
            targets=sample_targets[:10],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=3,
        )

        # Process first batch
        result1 = process_next_batch(session_id, mock_appsignals_client)
        assert result1['batch_index'] == 1
        assert result1['total_batches'] == 4  # 10 targets / 3 batch_size = 4 batches

        # Process second batch
        result2 = process_next_batch(session_id, mock_appsignals_client)
        assert result2['batch_index'] == 2
        assert result2['total_batches'] == 4

        # Verify session state
        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 2
        assert session['status'] == 'in_progress'

    def test_process_next_batch_retry_after_failure(self, sample_targets, sample_input_obj):
        """Test that failed batches can be retried by calling process_next_batch again."""
        # Mock client that fails first, then succeeds
        mock_client = MagicMock()
        mock_client.list_audit_findings.side_effect = [
            Exception('Network timeout'),  # First call fails
            {'AuditFindings': [{'FindingId': 'finding-1'}]},  # Second call succeeds
        ]

        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Retry Test',
        )

        # First attempt - should fail
        result1 = process_next_batch(session_id, mock_client)
        assert result1['status'] == 'failed'
        assert result1['error'] == 'Network timeout'
        assert result1['batch_index'] == 1

        # Verify session state unchanged (ready for retry)
        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 0  # Still at first batch
        assert session['status'] == 'created'  # Status unchanged
        assert len(session['failed_batches']) == 0  # No failed batches recorded
        assert len(session['processed_batches']) == 0

        # Second attempt - should succeed (retry same batch)
        result2 = process_next_batch(session_id, mock_client)
        assert result2['status'] == 'success'
        assert result2['batch_index'] == 1  # Same batch index
        assert result2['findings_count'] == 1

        # Verify session state updated after success
        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 1  # Now advanced
        assert session['status'] == 'completed'  # Single batch completed
        assert len(session['processed_batches']) == 1  # Success recorded
        assert len(session['failed_batches']) == 0  # No failures recorded

    def test_process_next_batch_multiple_retry_attempts(self, sample_targets, sample_input_obj):
        """Test multiple retry attempts for the same batch."""
        # Mock client that fails multiple times, then succeeds
        mock_client = MagicMock()
        mock_client.list_audit_findings.side_effect = [
            Exception('Connection timeout'),  # Attempt 1: fail
            Exception('Rate limit exceeded'),  # Attempt 2: fail
            Exception('Service unavailable'),  # Attempt 3: fail
            {'AuditFindings': []},  # Attempt 4: succeed
        ]

        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Multiple Retry Test',
        )

        # Attempt 1: Connection timeout
        result1 = process_next_batch(session_id, mock_client)
        assert result1['status'] == 'failed'
        assert result1['error'] == 'Connection timeout'
        assert result1['batch_index'] == 1

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 0  # No advancement

        # Attempt 2: Rate limit
        result2 = process_next_batch(session_id, mock_client)
        assert result2['status'] == 'failed'
        assert result2['error'] == 'Rate limit exceeded'
        assert result2['batch_index'] == 1  # Same batch

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 0  # Still no advancement

        # Attempt 3: Service unavailable
        result3 = process_next_batch(session_id, mock_client)
        assert result3['status'] == 'failed'
        assert result3['error'] == 'Service unavailable'
        assert result3['batch_index'] == 1  # Same batch

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 0  # Still no advancement

        # Attempt 4: Success
        result4 = process_next_batch(session_id, mock_client)
        assert result4['status'] == 'success'
        assert result4['batch_index'] == 1  # Same batch
        assert result4['findings_count'] == 0

        # Verify final session state
        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 1  # Finally advanced
        assert session['status'] == 'completed'
        assert len(session['processed_batches']) == 1
        assert len(session['failed_batches']) == 0  # No failures recorded in session

    def test_process_next_batch_retry_in_multi_batch_session(
        self, sample_targets, sample_input_obj
    ):
        """Test retry behavior in a multi-batch session."""
        # Mock client: batch 1 succeeds, batch 2 fails then succeeds, batch 3 succeeds
        mock_client = MagicMock()
        mock_client.list_audit_findings.side_effect = [
            {'AuditFindings': [{'FindingId': 'batch1-finding'}]},  # Batch 1: success
            Exception('Temporary failure'),  # Batch 2: fail
            {'AuditFindings': [{'FindingId': 'batch2-finding'}]},  # Batch 2 retry: success
            {'AuditFindings': []},  # Batch 3: success
        ]

        session_id = create_batch_session(
            targets=sample_targets[:9],  # 9 targets = 3 batches of 3
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Multi-batch Retry Test',
            batch_size=3,
        )

        # Process batch 1 (success)
        result1 = process_next_batch(session_id, mock_client)
        assert result1['status'] == 'success'
        assert result1['batch_index'] == 1
        assert result1['findings_count'] == 1

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 1  # Advanced to batch 2

        # Process batch 2 (failure)
        result2 = process_next_batch(session_id, mock_client)
        assert result2['status'] == 'failed'
        assert result2['error'] == 'Temporary failure'
        assert result2['batch_index'] == 2

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 1  # Still at batch 2 (no advancement)

        # Retry batch 2 (success)
        result3 = process_next_batch(session_id, mock_client)
        assert result3['status'] == 'success'
        assert result3['batch_index'] == 2  # Same batch index
        assert result3['findings_count'] == 1

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 2  # Now advanced to batch 3

        # Process batch 3 (success)
        result4 = process_next_batch(session_id, mock_client)
        assert result4['status'] == 'success'
        assert result4['batch_index'] == 3
        assert result4['findings_count'] == 0

        # Verify final session state
        session = get_batch_session(session_id)
        assert session is not None
        assert session['status'] == 'completed'
        assert len(session['processed_batches']) == 3  # All batches successful
        assert len(session['failed_batches']) == 0  # No failures recorded
        assert len(session['all_findings']) == 2  # Findings from batch 1 and 2


class TestFormatBatchResult:
    """Test format_batch_result function."""

    def test_format_batch_result_error(self, sample_targets, sample_input_obj):
        """Test formatting batch result with error."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        batch_result = {
            'batch_index': 1,
            'total_batches': 1,
            'targets_in_batch': 3,
            'error': 'API connection failed',
            'status': 'failed',
        }

        formatted = format_batch_result(batch_result, session)

        assert '❌ Batch 1/1 failed: API connection failed' == formatted

    def test_format_batch_result_healthy_with_continuation(self, sample_targets, sample_input_obj):
        """Test formatting healthy batch result with continuation instruction."""
        session_id = create_batch_session(
            targets=sample_targets[:10],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
            batch_size=5,
        )

        session = get_batch_session(session_id)
        assert session is not None
        batch_result = {
            'batch_index': 1,
            'total_batches': 2,
            'targets_in_batch': 5,
            'findings_count': 0,
            'findings': [],
            'status': 'success',
        }

        formatted = format_batch_result(batch_result, session)

        expected = (
            f"✅ Batch 1/2: 5 services healthy | Continue: continue_audit_batch('{session_id}')"
        )
        assert formatted == expected

    def test_format_batch_result_healthy_final_batch(self, sample_targets, sample_input_obj):
        """Test formatting healthy final batch result."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        batch_result = {
            'batch_index': 1,
            'total_batches': 1,
            'targets_in_batch': 3,
            'findings_count': 0,
            'findings': [],
            'status': 'success',
        }

        formatted = format_batch_result(batch_result, session)

        assert formatted == '✅ Batch 1/1: 3 services healthy'

    def test_format_batch_result_with_findings(self, sample_targets, sample_input_obj):
        """Test formatting batch result with findings."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        findings = [
            {
                'FindingId': 'finding-1',
                'Severity': 'CRITICAL',
                'Title': 'High error rate',
                'Description': 'Service experiencing errors',
            },
            {
                'FindingId': 'finding-2',
                'Severity': 'WARNING',
                'Title': 'Elevated latency',
                'Description': 'Response times are high',
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

        formatted = format_batch_result(batch_result, session)

        assert formatted.startswith('⚠️ Batch 1/1: 2 findings')
        assert '```' in formatted  # JSON formatting
        assert 'finding-1' in formatted
        assert 'CRITICAL' in formatted

    def test_format_batch_result_missing_findings_key(self, sample_targets, sample_input_obj):
        """Test formatting batch result when findings key is missing."""
        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner',
        )

        session = get_batch_session(session_id)
        assert session is not None
        batch_result = {
            'batch_index': 1,
            'total_batches': 1,
            'targets_in_batch': 3,
            'findings_count': 0,
            'status': 'success',
            # 'findings' key is missing
        }

        formatted = format_batch_result(batch_result, session)

        assert formatted == '✅ Batch 1/1: 3 services healthy'


class TestIntegration:
    """Integration tests for batch processing workflow."""

    def test_full_batch_processing_workflow(
        self, sample_targets, sample_input_obj, mock_appsignals_client
    ):
        """Test complete batch processing workflow."""
        # Create session with multiple batches
        session_id = create_batch_session(
            targets=sample_targets[:7],  # 7 targets
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Integration Test',
            batch_size=3,  # Will create 3 batches: [3, 3, 1]
        )

        session = get_batch_session(session_id)
        assert session is not None
        assert len(session['batches']) == 3
        assert session['status'] == 'created'

        # Process first batch
        result1 = process_next_batch(session_id, mock_appsignals_client)
        assert result1['status'] == 'success'
        assert result1['batch_index'] == 1

        session = get_batch_session(session_id)
        assert session is not None
        assert session['status'] == 'in_progress'
        assert len(session['processed_batches']) == 1

        # Process second batch
        result2 = process_next_batch(session_id, mock_appsignals_client)
        assert result2['status'] == 'success'
        assert result2['batch_index'] == 2

        # Process final batch
        result3 = process_next_batch(session_id, mock_appsignals_client)
        assert result3['status'] == 'success'
        assert result3['batch_index'] == 3
        assert result3['targets_in_batch'] == 1  # Final batch has 1 target

        session = get_batch_session(session_id)
        assert session is not None
        assert session['status'] == 'completed'
        assert len(session['processed_batches']) == 3
        assert len(session['all_findings']) == 3  # 1 finding per batch

        # Try to process again (should fail)
        result4 = process_next_batch(session_id, mock_appsignals_client)
        assert 'error' in result4
        assert 'No more batches to process' in result4['error']

    def test_batch_processing_with_mixed_results_and_retry(self, sample_targets, sample_input_obj):
        """Test batch processing with mixed success and failure results, including retry behavior."""
        # Mock client: batch 1 succeeds, batch 2 fails then succeeds on retry, batch 3 succeeds
        mock_client = MagicMock()
        mock_client.list_audit_findings.side_effect = [
            {'AuditFindings': [{'FindingId': 'finding-1'}]},  # Batch 1: success
            Exception('Network error'),  # Batch 2: failure
            {'AuditFindings': [{'FindingId': 'finding-2'}]},  # Batch 2 retry: success
            {'AuditFindings': []},  # Batch 3: success with no findings
        ]

        session_id = create_batch_session(
            targets=sample_targets[:9],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Mixed Results Test',
            batch_size=3,
        )

        # Process first batch (success)
        result1 = process_next_batch(session_id, mock_client)
        assert result1['status'] == 'success'
        assert result1['findings_count'] == 1

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 1  # Advanced to batch 2

        # Process second batch (failure - should NOT advance)
        result2 = process_next_batch(session_id, mock_client)
        assert result2['status'] == 'failed'
        assert result2['error'] == 'Network error'
        assert result2['batch_index'] == 2

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 1  # Should NOT advance on failure
        assert len(session['failed_batches']) == 0  # Should NOT be recorded as failed

        # Retry second batch (success - should advance)
        result3 = process_next_batch(session_id, mock_client)
        assert result3['status'] == 'success'
        assert result3['batch_index'] == 2  # Same batch index
        assert result3['findings_count'] == 1

        session = get_batch_session(session_id)
        assert session is not None
        assert session['current_batch_index'] == 2  # Now advanced to batch 3

        # Process third batch (success, no findings)
        result4 = process_next_batch(session_id, mock_client)
        assert result4['status'] == 'success'
        assert result4['batch_index'] == 3
        assert result4['findings_count'] == 0

        # Verify final session state
        session = get_batch_session(session_id)
        assert session is not None
        assert session['status'] == 'completed'
        assert len(session['processed_batches']) == 3  # All 3 batches successful (after retry)
        assert len(session['failed_batches']) == 0  # No failed batches recorded (retry succeeded)
        assert len(session['all_findings']) == 2  # Findings from batch 1 and 2

    @patch('awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger')
    def test_logging_during_batch_processing(self, mock_logger, sample_targets, sample_input_obj):
        """Test that appropriate logging occurs during batch processing."""
        mock_logger.reset_mock()

        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Logging Test',
        )

        # Verify session creation was logged (may also have cleanup logs)
        session_creation_calls = [
            call
            for call in mock_logger.info.call_args_list
            if f'Created batch session {session_id}' in str(call)
        ]
        assert len(session_creation_calls) == 1
        assert f'Created batch session {session_id} with 1 batches' in str(
            session_creation_calls[0]
        )


class TestCleanupExcessSessions:
    """Test _cleanup_excess_sessions function."""

    def setup_method(self):
        """Clear batch sessions before each test."""
        global _batch_sessions
        _batch_sessions.clear()

    def teardown_method(self):
        """Clear batch sessions after each test."""
        global _batch_sessions
        _batch_sessions.clear()

    def test_cleanup_excess_sessions_no_cleanup_needed(self):
        """Test cleanup when sessions are within limit."""
        global _batch_sessions

        # Create sessions within limit (MAX_BATCH_SESSIONS = 1)
        session_data = {
            'session_id': 'test-session-1',
            'created_at': '2024-01-01T10:00:00+00:00',
            'status': 'created',
        }
        _batch_sessions['test-session-1'] = session_data

        # Should not remove any sessions
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify no logging occurred (no cleanup needed)
            mock_logger.info.assert_not_called()

        # Verify session still exists
        assert len(_batch_sessions) == 1
        assert 'test-session-1' in _batch_sessions

    def test_cleanup_excess_sessions_at_limit(self):
        """Test cleanup when sessions are exactly at limit."""
        global _batch_sessions

        # Create exactly MAX_BATCH_SESSIONS (1) sessions
        session_data = {
            'session_id': 'test-session-1',
            'created_at': '2024-01-01T10:00:00+00:00',
            'status': 'created',
        }
        _batch_sessions['test-session-1'] = session_data

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify no logging occurred (at limit, no cleanup needed)
            mock_logger.info.assert_not_called()

        # Verify session still exists
        assert len(_batch_sessions) == 1
        assert 'test-session-1' in _batch_sessions

    def test_cleanup_excess_sessions_cleanup_needed(self):
        """Test cleanup when sessions exceed limit."""
        global _batch_sessions

        # Create sessions exceeding limit (MAX_BATCH_SESSIONS = 1)
        # Older session (should be removed)
        older_session = {
            'session_id': 'old-session',
            'created_at': '2024-01-01T09:00:00+00:00',
            'status': 'created',
        }
        # Newer session (should be kept)
        newer_session = {
            'session_id': 'new-session',
            'created_at': '2024-01-01T11:00:00+00:00',
            'status': 'created',
        }

        _batch_sessions['old-session'] = older_session
        _batch_sessions['new-session'] = newer_session

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify cleanup was logged
            mock_logger.info.assert_called_once_with('Cleaned up 1 excess batch sessions')

        # Verify only newer session remains
        assert len(_batch_sessions) == 1
        assert 'new-session' in _batch_sessions
        assert 'old-session' not in _batch_sessions

    def test_cleanup_excess_sessions_multiple_excess(self):
        """Test cleanup when multiple sessions exceed limit."""
        global _batch_sessions

        # Create multiple sessions exceeding limit (MAX_BATCH_SESSIONS = 1)
        sessions = [
            ('oldest-session', '2024-01-01T08:00:00+00:00'),
            ('old-session', '2024-01-01T09:00:00+00:00'),
            ('newer-session', '2024-01-01T10:00:00+00:00'),
            ('newest-session', '2024-01-01T11:00:00+00:00'),
        ]

        for session_id, created_at in sessions:
            _batch_sessions[session_id] = {
                'session_id': session_id,
                'created_at': created_at,
                'status': 'created',
            }

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify cleanup was logged (4 sessions - 1 limit = 3 excess)
            mock_logger.info.assert_called_once_with('Cleaned up 3 excess batch sessions')

        # Verify only newest session remains
        assert len(_batch_sessions) == 1
        assert 'newest-session' in _batch_sessions
        assert 'oldest-session' not in _batch_sessions
        assert 'old-session' not in _batch_sessions
        assert 'newer-session' not in _batch_sessions

    def test_cleanup_excess_sessions_missing_created_at(self):
        """Test cleanup when some sessions are missing created_at field."""
        global _batch_sessions

        # Create sessions with and without created_at
        session_with_time = {
            'session_id': 'session-with-time',
            'created_at': '2024-01-01T10:00:00+00:00',
            'status': 'created',
        }
        session_without_time = {
            'session_id': 'session-without-time',
            'status': 'created',
            # Missing 'created_at' field
        }

        _batch_sessions['session-with-time'] = session_with_time
        _batch_sessions['session-without-time'] = session_without_time

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify cleanup was logged (2 sessions - 1 limit = 1 excess)
            mock_logger.info.assert_called_once_with('Cleaned up 1 excess batch sessions')

        # Verify one session remains (the one with created_at should be kept as it sorts later)
        assert len(_batch_sessions) == 1
        # Session without created_at gets empty string and sorts first (gets removed)
        assert 'session-with-time' in _batch_sessions
        assert 'session-without-time' not in _batch_sessions

    def test_cleanup_excess_sessions_empty_created_at(self):
        """Test cleanup when sessions have empty created_at field."""
        global _batch_sessions

        # Create sessions with empty and valid created_at
        session_with_empty_time = {
            'session_id': 'session-empty-time',
            'created_at': '',
            'status': 'created',
        }
        session_with_time = {
            'session_id': 'session-with-time',
            'created_at': '2024-01-01T10:00:00+00:00',
            'status': 'created',
        }

        _batch_sessions['session-empty-time'] = session_with_empty_time
        _batch_sessions['session-with-time'] = session_with_time

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify cleanup was logged
            mock_logger.info.assert_called_once_with('Cleaned up 1 excess batch sessions')

        # Verify session with valid timestamp remains (empty string sorts first)
        assert len(_batch_sessions) == 1
        assert 'session-with-time' in _batch_sessions
        assert 'session-empty-time' not in _batch_sessions

    def test_cleanup_excess_sessions_same_timestamps(self):
        """Test cleanup when sessions have identical timestamps."""
        global _batch_sessions

        # Create sessions with identical timestamps
        same_time = '2024-01-01T10:00:00+00:00'
        session1 = {
            'session_id': 'session-1',
            'created_at': same_time,
            'status': 'created',
        }
        session2 = {
            'session_id': 'session-2',
            'created_at': same_time,
            'status': 'created',
        }

        _batch_sessions['session-1'] = session1
        _batch_sessions['session-2'] = session2

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify cleanup was logged
            mock_logger.info.assert_called_once_with('Cleaned up 1 excess batch sessions')

        # Verify one session remains (deterministic based on dict iteration order)
        assert len(_batch_sessions) == 1
        # One of the sessions should remain
        remaining_sessions = list(_batch_sessions.keys())
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0] in ['session-1', 'session-2']

    def test_cleanup_excess_sessions_empty_sessions_dict(self):
        """Test cleanup when sessions dictionary is empty."""
        global _batch_sessions

        # Ensure sessions dict is empty
        _batch_sessions.clear()

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify no logging occurred (no sessions to clean up)
            mock_logger.info.assert_not_called()

        # Verify sessions dict remains empty
        assert len(_batch_sessions) == 0

    def test_cleanup_excess_sessions_preserves_session_data(self):
        """Test that cleanup preserves all data in remaining sessions."""
        global _batch_sessions

        # Create sessions with rich data
        older_session = {
            'session_id': 'old-session',
            'created_at': '2024-01-01T09:00:00+00:00',
            'last_activity': '2024-01-01T09:30:00+00:00',
            'targets': [{'service': 'old-service'}],
            'batches': [['batch1'], ['batch2']],
            'current_batch_index': 1,
            'status': 'in_progress',
            'processed_batches': [{'batch': 'data'}],
            'all_findings': [{'finding': 'old'}],
        }
        newer_session = {
            'session_id': 'new-session',
            'created_at': '2024-01-01T11:00:00+00:00',
            'last_activity': '2024-01-01T11:30:00+00:00',
            'targets': [{'service': 'new-service'}],
            'batches': [['batch3'], ['batch4']],
            'current_batch_index': 0,
            'status': 'created',
            'processed_batches': [],
            'all_findings': [{'finding': 'new'}],
        }

        _batch_sessions['old-session'] = older_session
        _batch_sessions['new-session'] = newer_session

        _cleanup_excess_sessions()

        # Verify newer session remains with all data intact
        assert len(_batch_sessions) == 1
        assert 'new-session' in _batch_sessions

        remaining_session = _batch_sessions['new-session']
        assert remaining_session['session_id'] == 'new-session'
        assert remaining_session['created_at'] == '2024-01-01T11:00:00+00:00'
        assert remaining_session['last_activity'] == '2024-01-01T11:30:00+00:00'
        assert remaining_session['targets'] == [{'service': 'new-service'}]
        assert remaining_session['batches'] == [['batch3'], ['batch4']]
        assert remaining_session['current_batch_index'] == 0
        assert remaining_session['status'] == 'created'
        assert remaining_session['processed_batches'] == []
        assert remaining_session['all_findings'] == [{'finding': 'new'}]

    @patch('awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.MAX_BATCH_SESSIONS', 3)
    def test_cleanup_excess_sessions_different_limit(self):
        """Test cleanup with different MAX_BATCH_SESSIONS limit."""
        global _batch_sessions

        # Create 5 sessions when limit is 3
        sessions = [
            ('session-1', '2024-01-01T08:00:00+00:00'),
            ('session-2', '2024-01-01T09:00:00+00:00'),
            ('session-3', '2024-01-01T10:00:00+00:00'),
            ('session-4', '2024-01-01T11:00:00+00:00'),
            ('session-5', '2024-01-01T12:00:00+00:00'),
        ]

        for session_id, created_at in sessions:
            _batch_sessions[session_id] = {
                'session_id': session_id,
                'created_at': created_at,
                'status': 'created',
            }

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            _cleanup_excess_sessions()

            # Verify cleanup was logged (5 sessions - 3 limit = 2 excess)
            mock_logger.info.assert_called_once_with('Cleaned up 2 excess batch sessions')

        # Verify only 3 newest sessions remain
        assert len(_batch_sessions) == 3
        assert 'session-3' in _batch_sessions
        assert 'session-4' in _batch_sessions
        assert 'session-5' in _batch_sessions
        assert 'session-1' not in _batch_sessions
        assert 'session-2' not in _batch_sessions

    def test_cleanup_excess_sessions_integration_with_create_batch_session(
        self, sample_targets, sample_input_obj
    ):
        """Test that cleanup is called during session creation and works correctly."""
        global _batch_sessions

        # Clear sessions and create one session manually (to exceed limit when next is created)
        _batch_sessions.clear()
        existing_session = {
            'session_id': 'existing-session',
            'created_at': '2024-01-01T09:00:00+00:00',
            'status': 'created',
        }
        _batch_sessions['existing-session'] = existing_session

        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger'
        ) as mock_logger:
            # Create new session (should trigger cleanup)
            new_session_id = create_batch_session(
                targets=sample_targets[:3],
                input_obj=sample_input_obj,
                region='us-east-1',
                banner='Integration Test',
            )

            # Verify cleanup was logged (2 sessions - 1 limit = 1 excess)
            cleanup_calls = [
                call for call in mock_logger.info.call_args_list if 'Cleaned up' in str(call)
            ]
            assert len(cleanup_calls) == 1
            assert 'Cleaned up 1 excess batch sessions' in str(cleanup_calls[0])

        # Verify only the new session remains (it has a later timestamp)
        assert len(_batch_sessions) == 1
        assert new_session_id in _batch_sessions
        assert 'existing-session' not in _batch_sessions
