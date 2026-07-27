"""Tests targeting uncovered lines to push patch coverage above 92.40%."""

import pytest
from awslabs.amazon_translate_mcp_server import server
from awslabs.amazon_translate_mcp_server.models import (
    LanguagePair,
    TranslationJobStatus,
)
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# normalize_exception – ClientError branch (lines 300-302)
# ---------------------------------------------------------------------------
class TestNormalizeExceptionClientError:
    """Tests for the ClientError branch in normalize_exception."""

    def test_client_error_branch(self):
        """normalize_exception maps a raw ClientError to a structured response."""
        err = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'TranslateText',
        )
        result = server.normalize_exception(err)
        assert 'error' in result
        assert 'error_type' in result
        assert 'error_code' in result


# ---------------------------------------------------------------------------
# managed_batch_translation_workflow – not-initialized guard (line 973)
# ---------------------------------------------------------------------------
class TestManagedBatchWorkflowGuard:
    """Tests for managed_batch_translation_workflow not-initialized guard."""

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_not_initialized(self):
        """Return error when workflow_orchestrator is None."""
        with patch.object(server, 'workflow_orchestrator', None):
            ctx = MagicMock()
            result = await server.managed_batch_translation_workflow(
                ctx=ctx,
                input_s3_uri='s3://b/in/',
                output_s3_uri='s3://b/out/',
                data_access_role_arn='arn:aws:iam::123456789012:role/R',
                job_name='job',
                source_language='en',
                target_languages=['es'],
            )
        assert 'error' in result


# ---------------------------------------------------------------------------
# trigger_batch_translation – various not-initialized guards (1008-1051)
# and unsupported pair / missing terminology paths (1044, 1047, 1051, 1078)
# ---------------------------------------------------------------------------
class TestTriggerBatchTranslation:
    """Tests for trigger_batch_translation error paths."""

    @pytest.mark.asyncio
    async def test_batch_manager_not_initialized(self):
        """Return error when batch_manager is None."""
        with (
            patch.object(server, 'workflow_orchestrator', MagicMock()),
            patch.object(server, 'batch_manager', None),
        ):
            ctx = MagicMock()
            result = await server.trigger_batch_translation(
                ctx=ctx,
                input_s3_uri='s3://b/in/',
                output_s3_uri='s3://b/out/',
                data_access_role_arn='arn:aws:iam::123456789012:role/R',
                job_name='job',
                source_language='en',
                target_languages=['es'],
            )
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_language_operations_not_initialized(self):
        """Return error when language_operations is None."""
        with (
            patch.object(server, 'workflow_orchestrator', MagicMock()),
            patch.object(server, 'batch_manager', MagicMock()),
            patch.object(server, 'language_operations', None),
        ):
            ctx = MagicMock()
            result = await server.trigger_batch_translation(
                ctx=ctx,
                input_s3_uri='s3://b/in/',
                output_s3_uri='s3://b/out/',
                data_access_role_arn='arn:aws:iam::123456789012:role/R',
                job_name='job',
                source_language='en',
                target_languages=['es'],
            )
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_unsupported_language_pair(self):
        """Return error when target language pair is not supported."""
        mock_lang_ops = MagicMock()
        mock_lang_ops.list_language_pairs.return_value = [
            LanguagePair(
                source_language='en',
                target_language='fr',
                supported_formats=[],
                custom_terminology_supported=True,
            )
        ]
        with (
            patch.object(server, 'workflow_orchestrator', MagicMock()),
            patch.object(server, 'batch_manager', MagicMock()),
            patch.object(server, 'language_operations', mock_lang_ops),
        ):
            ctx = MagicMock()
            result = await server.trigger_batch_translation(
                ctx=ctx,
                input_s3_uri='s3://b/in/',
                output_s3_uri='s3://b/out/',
                data_access_role_arn='arn:aws:iam::123456789012:role/R',
                job_name='job',
                source_language='en',
                target_languages=['de'],  # not supported
            )
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_terminology_manager_not_initialized(self):
        """Return error when terminology_names provided but terminology_manager is None."""
        mock_lang_ops = MagicMock()
        mock_lang_ops.list_language_pairs.return_value = [
            LanguagePair(
                source_language='en',
                target_language='es',
                supported_formats=[],
                custom_terminology_supported=True,
            )
        ]
        with (
            patch.object(server, 'workflow_orchestrator', MagicMock()),
            patch.object(server, 'batch_manager', MagicMock()),
            patch.object(server, 'language_operations', mock_lang_ops),
            patch.object(server, 'terminology_manager', None),
        ):
            ctx = MagicMock()
            result = await server.trigger_batch_translation(
                ctx=ctx,
                input_s3_uri='s3://b/in/',
                output_s3_uri='s3://b/out/',
                data_access_role_arn='arn:aws:iam::123456789012:role/R',
                job_name='job',
                source_language='en',
                target_languages=['es'],
                terminology_names=['my-terms'],
            )
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_missing_terminology(self):
        """Return error when requested terminology does not exist."""
        mock_lang_ops = MagicMock()
        mock_lang_ops.list_language_pairs.return_value = [
            LanguagePair(
                source_language='en',
                target_language='es',
                supported_formats=[],
                custom_terminology_supported=True,
            )
        ]
        mock_term_mgr = MagicMock()
        mock_term = MagicMock()
        mock_term.name = 'other-terms'
        mock_term_mgr.list_terminologies.return_value = {'terminologies': [mock_term]}
        with (
            patch.object(server, 'workflow_orchestrator', MagicMock()),
            patch.object(server, 'batch_manager', MagicMock()),
            patch.object(server, 'language_operations', mock_lang_ops),
            patch.object(server, 'terminology_manager', mock_term_mgr),
        ):
            ctx = MagicMock()
            result = await server.trigger_batch_translation(
                ctx=ctx,
                input_s3_uri='s3://b/in/',
                output_s3_uri='s3://b/out/',
                data_access_role_arn='arn:aws:iam::123456789012:role/R',
                job_name='job',
                source_language='en',
                target_languages=['es'],
                terminology_names=['missing-terms'],
            )
        assert 'error' in result


# ---------------------------------------------------------------------------
# monitor_batch_translation – not-initialized guards (1179, 1182)
# and timeout / FAILED / STOPPED paths (1221-1292)
# ---------------------------------------------------------------------------
class TestMonitorBatchTranslation:
    """Tests for monitor_batch_translation not-initialized and status paths."""

    @pytest.mark.asyncio
    async def test_batch_manager_not_initialized(self):
        """Return error when batch_manager is None."""
        with patch.object(server, 'batch_manager', None):
            ctx = MagicMock()
            result = await server.monitor_batch_translation(
                ctx=ctx, job_id='j1', output_s3_uri='s3://b/out/'
            )
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_not_initialized(self):
        """Return error when workflow_orchestrator is None during monitoring."""
        with (
            patch.object(server, 'batch_manager', MagicMock()),
            patch.object(server, 'workflow_orchestrator', None),
        ):
            ctx = MagicMock()
            result = await server.monitor_batch_translation(
                ctx=ctx, job_id='j1', output_s3_uri='s3://b/out/'
            )
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_job_completes_immediately(self):
        """Return COMPLETED status when job finishes on first poll."""
        mock_status = TranslationJobStatus(
            job_id='j1',
            job_name='job',
            status='COMPLETED',
            progress=100.0,
            created_at=datetime.now(),
            completed_at=datetime.now(),
        )
        mock_bm = MagicMock()
        mock_bm.get_translation_job.return_value = mock_status
        mock_wo = MagicMock()
        with (
            patch.object(server, 'batch_manager', mock_bm),
            patch.object(server, 'workflow_orchestrator', mock_wo),
        ):
            ctx = MagicMock()
            result = await server.monitor_batch_translation(
                ctx=ctx,
                job_id='j1',
                output_s3_uri='s3://b/out/',
                monitor_interval=1,
                max_monitoring_duration=60,
            )
        assert result['final_status'] == 'COMPLETED'

    @pytest.mark.asyncio
    async def test_job_failed_triggers_error_analysis(self):
        """Trigger error analysis when job reaches FAILED state."""
        mock_status = TranslationJobStatus(
            job_id='j1',
            job_name='job',
            status='FAILED',
            progress=0.0,
        )
        mock_bm = MagicMock()
        mock_bm.get_translation_job.return_value = mock_status
        mock_wo = MagicMock()
        mock_wo._analyze_job_errors = AsyncMock(
            return_value={'error_files_found': [], 'error_details': [], 'suggested_actions': []}
        )
        with (
            patch.object(server, 'batch_manager', mock_bm),
            patch.object(server, 'workflow_orchestrator', mock_wo),
        ):
            ctx = MagicMock()
            result = await server.monitor_batch_translation(
                ctx=ctx,
                job_id='j1',
                output_s3_uri='s3://b/out/',
                monitor_interval=1,
                max_monitoring_duration=60,
            )
        assert result['final_status'] == 'FAILED'
        mock_wo._analyze_job_errors.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitoring_timeout(self):
        """Stop monitoring and return IN_PROGRESS when max_monitoring_duration exceeded."""
        mock_status = TranslationJobStatus(
            job_id='j1',
            job_name='job',
            status='IN_PROGRESS',
            progress=50.0,
        )
        mock_bm = MagicMock()
        mock_bm.get_translation_job.return_value = mock_status
        mock_wo = MagicMock()
        with (
            patch.object(server, 'batch_manager', mock_bm),
            patch.object(server, 'workflow_orchestrator', mock_wo),
            patch('time.time', side_effect=[0, 0, 9999, 9999, 9999]),
        ):
            ctx = MagicMock()
            result = await server.monitor_batch_translation(
                ctx=ctx,
                job_id='j1',
                output_s3_uri='s3://b/out/',
                monitor_interval=1,
                max_monitoring_duration=1,
            )
        assert result['final_status'] == 'IN_PROGRESS'


# ---------------------------------------------------------------------------
# analyze_batch_translation_errors – not-initialized + no-results + patterns
# (1266-1292, 1320-1366)
# ---------------------------------------------------------------------------
class TestAnalyzeBatchTranslationErrors:
    """Tests for analyze_batch_translation_errors paths."""

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_not_initialized(self):
        """Return error when workflow_orchestrator is None."""
        with patch.object(server, 'workflow_orchestrator', None):
            ctx = MagicMock()
            result = await server.analyze_batch_translation_errors(
                ctx=ctx, job_id='j1', output_s3_uri='s3://b/out/'
            )
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_no_error_analysis_returned(self):
        """Return no-details message when _analyze_job_errors returns None."""
        mock_wo = MagicMock()
        mock_wo._analyze_job_errors = AsyncMock(return_value=None)
        with patch.object(server, 'workflow_orchestrator', mock_wo):
            ctx = MagicMock()
            result = await server.analyze_batch_translation_errors(
                ctx=ctx, job_id='j1', output_s3_uri='s3://b/out/'
            )
        assert result['job_id'] == 'j1'
        assert 'No error details' in result['error']

    @pytest.mark.asyncio
    async def test_error_patterns_utf8_and_format(self):
        """Detect UTF-8 and format error patterns from error_details."""
        error_analysis = {
            'error_files_found': ['file1.json'],
            'error_details': [
                {
                    'error_data': {
                        'sourceLanguageCode': 'en',
                        'targetLanguageCode': 'es',
                        'details': [
                            {
                                'auxiliaryData': {
                                    'error': {
                                        'errorMessage': 'Invalid utf-8 encoding and bad format'
                                    }
                                }
                            }
                        ],
                    }
                }
            ],
            'suggested_actions': ['Fix encoding'],
        }
        mock_wo = MagicMock()
        mock_wo._analyze_job_errors = AsyncMock(return_value=error_analysis)
        with patch.object(server, 'workflow_orchestrator', mock_wo):
            ctx = MagicMock()
            result = await server.analyze_batch_translation_errors(
                ctx=ctx, job_id='j1', output_s3_uri='s3://b/out/'
            )
        assert 'UTF-8 Encoding Error' in result['error_summary']['error_patterns']
        assert 'Unsupported Format' in result['error_summary']['error_patterns']
        assert 'en->es' in result['error_summary']['affected_languages']


# ---------------------------------------------------------------------------
# list_active_workflows / get_workflow_status – not-initialized + None status
# (1400, 1409-1411, 1435-1436)
# ---------------------------------------------------------------------------
class TestWorkflowManagementTools:
    """Tests for list_active_workflows and get_workflow_status tools."""

    @pytest.mark.asyncio
    async def test_list_active_workflows_not_initialized(self):
        """Return error when workflow_orchestrator is None."""
        with patch.object(server, 'workflow_orchestrator', None):
            ctx = MagicMock()
            result = await server.list_active_workflows(ctx=ctx)
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_list_active_workflows_success(self):
        """Return workflow list when orchestrator is initialized."""
        mock_wo = MagicMock()
        mock_wo.list_active_workflows.return_value = [{'id': 'wf1'}]
        with patch.object(server, 'workflow_orchestrator', mock_wo):
            ctx = MagicMock()
            result = await server.list_active_workflows(ctx=ctx)
        assert result['total_count'] == 1

    @pytest.mark.asyncio
    async def test_get_workflow_status_not_initialized(self):
        """Return error when workflow_orchestrator is None."""
        with patch.object(server, 'workflow_orchestrator', None):
            ctx = MagicMock()
            result = await server.get_workflow_status(ctx=ctx, workflow_id='wf1')
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_get_workflow_status_not_found(self):
        """Return WorkflowNotFound error when workflow ID does not exist."""
        mock_wo = MagicMock()
        mock_wo.get_workflow_status.return_value = None
        with patch.object(server, 'workflow_orchestrator', mock_wo):
            ctx = MagicMock()
            result = await server.get_workflow_status(ctx=ctx, workflow_id='wf-missing')
        assert result['error_type'] == 'WorkflowNotFound'

    @pytest.mark.asyncio
    async def test_get_workflow_status_found(self):
        """Return workflow status dict when workflow exists."""
        mock_wo = MagicMock()
        mock_wo.get_workflow_status.return_value = {'status': 'running', 'step': 'translate'}
        with patch.object(server, 'workflow_orchestrator', mock_wo):
            ctx = MagicMock()
            result = await server.get_workflow_status(ctx=ctx, workflow_id='wf1')
        assert result['status'] == 'running'


# ---------------------------------------------------------------------------
# health_check – degraded / unhealthy paths (1463-1490)
# ---------------------------------------------------------------------------
class TestHealthCheck:
    """Tests for health_check degraded and unhealthy paths."""

    def test_health_check_all_healthy(self):
        """Return healthy when all services and credentials are valid."""
        mock_aws = MagicMock()
        mock_aws.validate_credentials.return_value = True
        with (
            patch.object(server, 'aws_client_manager', mock_aws),
            patch.object(server, 'translation_service', MagicMock()),
            patch.object(server, 'batch_manager', MagicMock()),
            patch.object(server, 'terminology_manager', MagicMock()),
            patch.object(server, 'language_operations', MagicMock()),
            patch.object(server, 'workflow_orchestrator', MagicMock()),
        ):
            result = server.health_check()
        assert result['status'] == 'healthy'

    def test_health_check_aws_client_not_initialized(self):
        """Return unhealthy when aws_client_manager is None."""
        with patch.object(server, 'aws_client_manager', None):
            result = server.health_check()
        assert result['status'] == 'unhealthy'
        assert result['components']['aws_client'] == 'not_initialized'

    def test_health_check_aws_credentials_fail(self):
        """Return degraded when credential validation raises an exception."""
        mock_aws = MagicMock()
        mock_aws.validate_credentials.side_effect = Exception('creds invalid')
        with (
            patch.object(server, 'aws_client_manager', mock_aws),
            patch.object(server, 'translation_service', MagicMock()),
            patch.object(server, 'batch_manager', MagicMock()),
            patch.object(server, 'terminology_manager', MagicMock()),
            patch.object(server, 'language_operations', MagicMock()),
            patch.object(server, 'workflow_orchestrator', MagicMock()),
        ):
            result = server.health_check()
        assert result['status'] == 'degraded'

    def test_health_check_translation_service_not_initialized(self):
        """Return unhealthy when translation_service is None."""
        mock_aws = MagicMock()
        mock_aws.validate_credentials.return_value = True
        with (
            patch.object(server, 'aws_client_manager', mock_aws),
            patch.object(server, 'translation_service', None),
        ):
            result = server.health_check()
        assert result['status'] == 'unhealthy'

    def test_health_check_sub_service_not_initialized(self):
        """Return degraded when a non-critical service is None."""
        mock_aws = MagicMock()
        mock_aws.validate_credentials.return_value = True
        with (
            patch.object(server, 'aws_client_manager', mock_aws),
            patch.object(server, 'translation_service', MagicMock()),
            patch.object(server, 'batch_manager', None),
            patch.object(server, 'terminology_manager', MagicMock()),
            patch.object(server, 'language_operations', MagicMock()),
            patch.object(server, 'workflow_orchestrator', MagicMock()),
        ):
            result = server.health_check()
        assert result['status'] == 'degraded'
        assert result['components']['batch_manager'] == 'not_initialized'
