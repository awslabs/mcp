"""Tests for batch processing utilities."""

import pytest
import uuid
from awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils import (
    _build_api_input,
    _create_batch_metadata,
    _update_session_after_batch,
    cleanup_batch_sessions,
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
        """Test batch processing with API error."""
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

        # Verify session was updated
        session = get_batch_session(session_id)
        assert session is not None
        assert len(session['failed_batches']) == 1

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


class TestCleanupBatchSessions:
    """Test cleanup_batch_sessions function."""

    def test_cleanup_batch_sessions(self, sample_targets, sample_input_obj):
        """Test cleaning up all batch sessions."""
        # Create multiple sessions
        session_id1 = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner 1',
        )

        session_id2 = create_batch_session(
            targets=sample_targets[:5],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Test Banner 2',
        )

        # Verify sessions exist
        assert get_batch_session(session_id1) is not None
        assert get_batch_session(session_id2) is not None

        # Clean up all sessions
        cleanup_batch_sessions()

        # Verify sessions are gone
        assert get_batch_session(session_id1) is None
        assert get_batch_session(session_id2) is None

    def test_cleanup_batch_sessions_empty(self):
        """Test cleaning up when no sessions exist."""
        # Should not raise an exception
        cleanup_batch_sessions()


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

    def test_batch_processing_with_mixed_results(self, sample_targets, sample_input_obj):
        """Test batch processing with mixed success and failure results."""
        # Mock client that fails on second call
        mock_client = MagicMock()
        mock_client.list_audit_findings.side_effect = [
            {'AuditFindings': [{'FindingId': 'finding-1'}]},  # Success
            Exception('Network error'),  # Failure
            {'AuditFindings': []},  # Success with no findings
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

        # Process second batch (failure)
        result2 = process_next_batch(session_id, mock_client)
        assert result2['status'] == 'failed'
        assert result2['error'] == 'Network error'

        # Process third batch (success, no findings)
        result3 = process_next_batch(session_id, mock_client)
        assert result3['status'] == 'success'
        assert result3['findings_count'] == 0

        # Verify final session state
        session = get_batch_session(session_id)
        assert session is not None
        assert session['status'] == 'completed'
        assert len(session['processed_batches']) == 2  # 2 successful batches
        assert len(session['failed_batches']) == 1  # 1 failed batch
        assert len(session['all_findings']) == 1  # Only findings from successful batches

    @patch('awslabs.cloudwatch_appsignals_mcp_server.batch_processing_utils.logger')
    def test_logging_during_batch_processing(self, mock_logger, sample_targets, sample_input_obj):
        """Test that appropriate logging occurs during batch processing."""
        # Clean up any existing sessions first
        cleanup_batch_sessions()
        mock_logger.reset_mock()

        session_id = create_batch_session(
            targets=sample_targets[:3],
            input_obj=sample_input_obj,
            region='us-east-1',
            banner='Logging Test',
        )

        # Verify session creation was logged
        mock_logger.info.assert_called_with(f'Created batch session {session_id} with 1 batches')

        # Clean up and verify cleanup was logged
        cleanup_batch_sessions()
        mock_logger.info.assert_called_with('Cleaned up all 1 batch sessions')
