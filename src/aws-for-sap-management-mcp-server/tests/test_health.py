# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for SSM for SAP health summary and report tools."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def tools():
    """Create an SSMSAPHealthTools instance."""
    from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
        SSMSAPHealthTools,
    )

    return SSMSAPHealthTools()


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    return MagicMock()


def _make_ssm_sap_client(
    apps=None,
    app_detail=None,
    components=None,
    component_detail=None,
    config_check_ops=None,
    sub_check_results=None,
    rule_results=None,
    config_check_definitions=None,
):
    """Build a mock ssm-sap client with configurable responses."""
    mock = MagicMock()

    if apps is not None:
        mock.list_applications.return_value = {'Applications': apps}
    else:
        mock.list_applications.return_value = {'Applications': []}

    if app_detail is not None:
        mock.get_application.return_value = {'Application': app_detail}
    else:
        mock.get_application.return_value = {
            'Application': {
                'Id': 'test-app',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }

    if components is not None:
        mock.list_components.return_value = {'Components': components}
    else:
        mock.list_components.return_value = {'Components': []}

    if component_detail is not None:
        mock.get_component.return_value = {'Component': component_detail}
    else:
        mock.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [],
            }
        }

    if config_check_ops is not None:
        mock.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': config_check_ops,
        }
    else:
        mock.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': [],
        }

    if sub_check_results is not None:
        mock.list_sub_check_results.return_value = {'SubCheckResults': sub_check_results}
    else:
        mock.list_sub_check_results.return_value = {'SubCheckResults': []}

    if rule_results is not None:
        mock.list_sub_check_rule_results.return_value = {'RuleResults': rule_results}
    else:
        mock.list_sub_check_rule_results.return_value = {'RuleResults': []}

    if config_check_definitions is not None:
        mock.list_configuration_check_definitions.return_value = {
            'ConfigurationChecks': config_check_definitions,
        }
    else:
        mock.list_configuration_check_definitions.return_value = {
            'ConfigurationChecks': [{'Id': 'SAP_CHECK_01'}],
        }

    mock.start_configuration_checks.return_value = {
        'ConfigurationCheckOperations': [],
    }

    mock.get_configuration_check_operation.return_value = {
        'ConfigurationCheckOperation': {'Status': 'SUCCESS'},
    }

    return mock


class TestGetSapHealthSummary:
    """Tests for get_sap_health_summary tool (comprehensive overview)."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_single_healthy_app(self, mock_get_client, tools, ctx):
        """Test health summary for a single healthy application."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert result.application_count == 1
        assert result.healthy_count == 1
        assert result.unhealthy_count == 0
        assert len(result.applications) == 1
        assert result.applications[0].application_id == 'my-hana'
        assert result.applications[0].status == 'ACTIVATED'
        assert 'All 1 application(s) are running and healthy' in result.summary

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_no_applications_found(self, mock_get_client, tools, ctx):
        """Test health summary when no applications exist."""
        mock_sap = _make_ssm_sap_client(apps=[])
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert result.application_count == 0
        assert 'No SAP applications found' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_multiple_apps_mixed_status(self, mock_get_client, tools, ctx):
        """Test health summary with multiple apps in different states."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {
            'Applications': [{'Id': 'app-healthy'}, {'Id': 'app-failed'}]
        }
        mock_sap.get_application.side_effect = [
            {
                'Application': {
                    'Id': 'app-healthy',
                    'Type': 'HANA',
                    'Status': 'ACTIVATED',
                    'DiscoveryStatus': 'SUCCESS',
                }
            },
            {
                'Application': {
                    'Id': 'app-failed',
                    'Type': 'SAP_ABAP',
                    'Status': 'FAILED',
                    'DiscoveryStatus': 'REFRESH_FAILED',
                }
            },
        ]
        mock_sap.list_components.return_value = {'Components': []}
        mock_sap.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': []
        }
        mock_sap.list_configuration_check_definitions.return_value = {
            'ConfigurationChecks': [{'Id': 'SAP_CHECK_01'}]
        }
        mock_sap.start_configuration_checks.return_value = {'ConfigurationCheckOperations': []}
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert result.application_count == 2
        assert result.healthy_count == 1
        assert result.unhealthy_count == 1
        assert 'require attention' in result.summary

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_components(self, mock_get_client, tools, ctx):
        """Test health summary includes component details."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'HostName': 'host1', 'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert len(result.applications[0].components) == 1
        assert result.applications[0].components[0].component_id == 'hana-db-1'
        assert result.applications[0].components[0].component_type == 'HANA_NODE'
        assert 'i-abc123' in result.applications[0].components[0].ec2_instance_ids

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_config_checks(self, mock_get_client, tools, ctx):
        """Test health summary includes configuration check results."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'Id': 'op-1',
                    'EndTime': recent_time,
                    'RuleStatusCounts': {'Passed': 5, 'Failed': 0},
                },
            ],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert len(result.applications[0].config_checks) == 1
        assert result.applications[0].config_checks[0].check_id == 'SAP_CHECK_01'
        assert 'Passed: 5' in result.applications[0].config_checks[0].result
        assert result.applications[0].config_checks[0].triggered_by_summary is False

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_config_checks_include_subchecks_by_severity(self, mock_get_client, tools, ctx):
        """Test health summary includes subcheck details grouped by severity."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'Id': 'op-1',
                    'EndTime': recent_time,
                    'RuleStatusCounts': {'Passed': 3, 'Failed': 2, 'Warning': 1},
                },
            ],
            sub_check_results=[
                {
                    'Id': 'sc-1',
                    'Name': 'HA Config',
                    'Result': 'Failed',
                    'Description': 'HA not configured',
                },
                {
                    'Id': 'sc-2',
                    'Name': 'Backup Config',
                    'Result': 'Warning',
                    'Description': 'Backup interval too long',
                },
                {
                    'Id': 'sc-3',
                    'Name': 'Memory Config',
                    'Result': 'Passed',
                    'Description': 'Memory allocation OK',
                },
            ],
            rule_results=[
                {
                    'Id': 'rule-1',
                    'Description': 'Fencing check',
                    'Status': 'FAILED',
                    'Message': 'Fencing not configured',
                },
                {
                    'Id': 'rule-2',
                    'Description': 'Stonith enabled',
                    'Status': 'PASSED',
                    'Message': None,
                },
            ],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        check = result.applications[0].config_checks[0]
        assert len(check.subchecks) == 3

        # Verify subchecks have correct data
        failed_scs = [sc for sc in check.subchecks if sc.result == 'Failed']
        warning_scs = [sc for sc in check.subchecks if sc.result == 'Warning']
        passed_scs = [sc for sc in check.subchecks if sc.result == 'Passed']
        assert len(failed_scs) == 1
        assert failed_scs[0].name == 'HA Config'
        assert failed_scs[0].description == 'HA not configured'
        assert len(warning_scs) == 1
        assert warning_scs[0].name == 'Backup Config'
        assert len(passed_scs) == 1

        # Verify rule results are populated
        for sc in check.subchecks:
            assert len(sc.rule_results) == 2
            assert sc.rule_results[0].rule_id == 'rule-1'
            assert sc.rule_results[0].description == 'Fencing check'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_config_checks_no_subchecks_when_disabled(self, mock_get_client, tools, ctx):
        """Test health summary omits subchecks when include_subchecks=False."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'Id': 'op-1',
                    'EndTime': recent_time,
                    'RuleStatusCounts': {'Passed': 5},
                },
            ],
            sub_check_results=[
                {
                    'Id': 'sc-1',
                    'Name': 'HA Config',
                    'Result': 'Failed',
                    'Description': 'HA not configured',
                },
            ],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_subchecks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        check = result.applications[0].config_checks[0]
        assert len(check.subchecks) == 0

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_auto_triggers_config_checks_when_stale(self, mock_get_client, tools, ctx):
        """Test that config checks are auto-triggered when no recent results exist."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'Id': 'op-1',
                    'EndTime': old_time,
                    'RuleStatusCounts': {'Passed': 5},
                },
            ],
        )
        # Make start_configuration_checks return operations with IDs so polling is triggered
        mock_sap.start_configuration_checks.return_value = {
            'ConfigurationCheckOperations': [
                {
                    'Id': 'op-new-1',
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'IN_PROGRESS',
                },
            ],
        }
        mock_get_client.return_value = mock_sap

        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._wait_for_config_checks',
            new_callable=AsyncMock,
        ) as mock_wait:
            result = await tools.get_sap_health_summary(
                ctx,
                application_id='my-hana',
                include_log_backup_status=False,
                include_aws_backup_status=False,
                include_cloudwatch_metrics=False,
                auto_trigger_config_checks=True,
                config_check_max_age_hours=24,
            )

            assert result.status == 'success'
            mock_sap.start_configuration_checks.assert_called_once()
            mock_wait.assert_awaited_once()
            # After triggering and waiting, it re-fetches — so list_configuration_check_operations called twice
            assert mock_sap.list_configuration_check_operations.call_count == 2

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_auto_trigger_falls_back_to_previous_when_still_in_progress(
        self, mock_get_client, tools, ctx
    ):
        """Test that previous config check results are used when new checks are still in progress."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        previous_ops = [
            {
                'ConfigurationCheckId': 'SAP_CHECK_01',
                'Status': 'COMPLETED',
                'Id': 'op-old',
                'EndTime': old_time,
                'RuleStatusCounts': {'Passed': 5},
            },
        ]
        in_progress_ops = [
            {
                'ConfigurationCheckId': 'SAP_CHECK_01',
                'Status': 'INPROGRESS',
                'Id': 'op-new',
                'EndTime': datetime.now(timezone.utc),
                'RuleStatusCounts': {},
            },
        ]
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        # First call returns stale results, second call (after trigger) returns in-progress
        mock_sap.list_configuration_check_operations.side_effect = [
            {'ConfigurationCheckOperations': previous_ops},
            {'ConfigurationCheckOperations': in_progress_ops},
        ]
        mock_sap.start_configuration_checks.return_value = {
            'ConfigurationCheckOperations': [
                {'Id': 'op-new', 'ConfigurationCheckId': 'SAP_CHECK_01', 'Status': 'IN_PROGRESS'},
            ],
        }
        mock_get_client.return_value = mock_sap

        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._wait_for_config_checks',
            new_callable=AsyncMock,
        ):
            result = await tools.get_sap_health_summary(
                ctx,
                application_id='my-hana',
                include_log_backup_status=False,
                include_aws_backup_status=False,
                include_cloudwatch_metrics=False,
                auto_trigger_config_checks=True,
                config_check_max_age_hours=24,
            )

            assert result.status == 'success'
            app = result.applications[0]
            # Should fall back to previous COMPLETED results, not INPROGRESS
            assert len(app.config_checks) == 1
            assert app.config_checks[0].status == 'COMPLETED'
            assert 'Passed: 5' in app.config_checks[0].result

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_no_auto_trigger_when_recent(self, mock_get_client, tools, ctx):
        """Test that config checks are NOT auto-triggered when recent results exist."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'Id': 'op-1',
                    'EndTime': recent_time,
                    'RuleStatusCounts': {'Passed': 5},
                },
            ],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        mock_sap.start_configuration_checks.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_auto_trigger_disabled(self, mock_get_client, tools, ctx):
        """Test that auto-trigger can be disabled."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
            auto_trigger_config_checks=False,
        )

        assert result.status == 'success'
        mock_sap.start_configuration_checks.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_cloudwatch_metrics(self, mock_get_client, tools, ctx):
        """Test health summary includes CloudWatch metrics."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 45.2, 'Maximum': 78.5}]},
            {'Datapoints': [{'Maximum': 0}]},
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )

        assert result.status == 'success'
        metrics = result.applications[0].cloudwatch_metrics
        assert len(metrics) == 1
        assert metrics[0].instance_id == 'i-abc123'
        assert metrics[0].cpu_avg == 45.2
        assert metrics[0].cpu_max == 78.5
        assert metrics[0].status_check == 'OK'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_log_backup_status(self, mock_get_client, tools, ctx):
        """Test health summary includes log backup status."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2.1'}]
        }
        mock_paginator_empty = MagicMock()
        mock_paginator_empty.paginate.return_value = [{'Commands': []}]
        mock_ssm.get_paginator.return_value = mock_paginator_empty

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=True,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        lb = result.applications[0].log_backup_status
        assert len(lb) == 1
        assert lb[0].instance_id == 'i-abc123'
        assert lb[0].ssm_agent_status == 'Online'
        assert lb[0].agent_version == '3.2.1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_aws_backup_status(self, mock_get_client, tools, ctx):
        """Test health summary includes AWS Backup status."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        mock_backup.list_backup_plans.return_value = {
            'BackupPlansList': [{'BackupPlanName': 'SAP-Plan'}]
        }
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [{'State': 'COMPLETED', 'CompletionDate': '2026-03-18T10:00:00Z'}]
        }

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        bs = result.applications[0].backup_status
        assert len(bs) == 1
        assert bs[0].instance_id == 'i-abc123'
        assert bs[0].backup_status == 'COMPLETED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_client_creation_error(self, mock_get_client, tools, ctx):
        """Test health summary handles client creation errors."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        result = await tools.get_sap_health_summary(ctx, application_id='my-hana')

        assert result.status == 'error'
        assert 'Invalid credentials' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_app_retrieval_error(self, mock_get_client, tools, ctx):
        """Test health summary handles per-app errors gracefully."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'broken-app'}]}
        mock_sap.get_application.side_effect = Exception('Access denied')
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert result.application_count == 1
        assert result.applications[0].status == 'ERROR'
        assert 'Access denied' in result.applications[0].status_message

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_profile_and_region_passed_through(self, mock_get_client, tools, ctx):
        """Test that profile_name and region are passed to client factory."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_get_client.return_value = mock_sap

        await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            region='eu-west-1',
            profile_name='sap-prod',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        mock_get_client.assert_called_with(
            'ssm-sap', region_name='eu-west-1', profile_name='sap-prod'
        )

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_no_config_checks_when_disabled(self, mock_get_client, tools, ctx):
        """Test that config checks are skipped when disabled."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert len(result.applications[0].config_checks) == 0
        mock_sap.list_configuration_check_operations.assert_not_called()


class TestGenerateHealthReport:
    """Tests for generate_health_report tool (detailed Markdown report)."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_single_healthy_app(self, mock_get_client, tools, ctx):
        """Test health report for a single healthy application."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx,
            application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert result.application_count == 1
        assert 'my-hana' in result.report
        # Healthy apps don't show raw status codes — just the app name
        assert 'Application: `my-hana`' in result.report
        assert 'running and healthy' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_no_applications_found(self, mock_get_client, tools, ctx):
        """Test health report when no applications exist."""
        mock_sap = _make_ssm_sap_client(apps=[])
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert result.application_count == 0
        assert 'No SAP applications found' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_components(self, mock_get_client, tools, ctx):
        """Test health report includes component details."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'HostName': 'host1', 'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert 'i-abc123' in result.report
        assert 'HANA' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_config_checks(self, mock_get_client, tools, ctx):
        """Test health report includes configuration check results."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'RuleStatusCounts': {'Passed': 3},
                    'Id': 'op-1',
                },
                {
                    'ConfigurationCheckId': 'SAP_CHECK_02',
                    'Status': 'COMPLETED',
                    'RuleStatusCounts': {'Warning': 1},
                    'Id': 'op-2',
                },
            ],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx,
            application_id='my-hana',
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert 'EC2 Instance Type Selection' in result.report
        assert 'Storage Configuration' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_subchecks_and_rules(self, mock_get_client, tools, ctx):
        """Test health report includes subchecks and rule results."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'RuleStatusCounts': {'Passed': 3},
                    'Id': 'op-1',
                }
            ],
            sub_check_results=[
                {
                    'Id': 'sc-1',
                    'Name': 'SubCheck A',
                    'Result': 'PASS',
                    'Description': 'Checks something',
                }
            ],
            rule_results=[{'Id': 'rule-1', 'Description': 'Rule 1', 'Status': 'PASS'}],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx,
            application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert 'SubCheck A' in result.report
        assert 'Rule 1' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_cloudwatch_metrics(self, mock_get_client, tools, ctx):
        """Test health report includes CloudWatch metrics."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 45.2, 'Maximum': 78.5}]},
            {'Datapoints': [{'Maximum': 0}]},
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.generate_health_report(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )

        assert result.status == 'success'
        assert 'CloudWatch' in result.report
        assert 'i-abc123' in result.report
        assert '45.2' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_client_creation_error(self, mock_get_client, tools, ctx):
        """Test health report handles client creation errors."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        result = await tools.generate_health_report(ctx, application_id='my-hana')

        assert result.status == 'error'
        assert 'Invalid credentials' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_app_retrieval_error(self, mock_get_client, tools, ctx):
        """Test health report handles per-app errors gracefully."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'broken-app'}]}
        mock_sap.get_application.side_effect = Exception('Access denied')
        mock_sap.list_components.return_value = {'Components': []}
        mock_sap.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': []
        }
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert result.application_count == 1
        assert 'broken-app' in result.report
        assert 'Error' in result.report


class TestExtractEc2Ids:
    """Tests for _extract_ec2_ids helper function."""

    def test_extract_from_hosts_array(self):
        """Test extraction from standard Hosts array."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _extract_ec2_ids,
        )

        detail = {
            'Hosts': [
                {'EC2InstanceId': 'i-host1', 'HostName': 'host1'},
                {'EC2InstanceId': 'i-host2', 'HostName': 'host2'},
            ]
        }
        ids = _extract_ec2_ids(detail)
        assert ids == ['i-host1', 'i-host2']

    def test_extract_from_associated_host(self):
        """Test extraction from AssociatedHost (HANA_NODE components)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _extract_ec2_ids,
        )

        detail = {
            'Hosts': [],
            'AssociatedHost': {'Ec2InstanceId': 'i-assoc1'},
        }
        ids = _extract_ec2_ids(detail)
        assert ids == ['i-assoc1']

    def test_extract_from_primary_secondary_host(self):
        """Test extraction from PrimaryHost/SecondaryHost fallback."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _extract_ec2_ids,
        )

        detail = {
            'Hosts': [],
            'PrimaryHost': {'Ec2InstanceId': 'i-primary'},
            'SecondaryHost': {'Ec2InstanceId': 'i-secondary'},
        }
        ids = _extract_ec2_ids(detail)
        assert 'i-primary' in ids
        assert 'i-secondary' in ids

    def test_extract_primary_host_string(self):
        """Test extraction when PrimaryHost is a string instance ID."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _extract_ec2_ids,
        )

        detail = {
            'Hosts': [],
            'PrimaryHost': 'i-string-primary',
        }
        ids = _extract_ec2_ids(detail)
        assert ids == ['i-string-primary']

    def test_deduplication(self):
        """Test that duplicate IDs are deduplicated."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _extract_ec2_ids,
        )

        detail = {
            'Hosts': [{'EC2InstanceId': 'i-same'}],
            'AssociatedHost': {'Ec2InstanceId': 'i-same'},
        }
        ids = _extract_ec2_ids(detail)
        assert ids == ['i-same']

    def test_empty_detail(self):
        """Test with empty component detail."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _extract_ec2_ids,
        )

        ids = _extract_ec2_ids({})
        assert ids == []

    def test_instance_id_fallback(self):
        """Test InstanceId fallback when EC2InstanceId is missing."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _extract_ec2_ids,
        )

        detail = {
            'Hosts': [{'InstanceId': 'i-fallback'}],
        }
        ids = _extract_ec2_ids(detail)
        assert ids == ['i-fallback']


class TestAssociatedHostIntegration:
    """Tests for AssociatedHost EC2 extraction in health summary."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_hana_node_associated_host(self, mock_get_client, tools, ctx):
        """Test that HANA_NODE components with AssociatedHost get EC2 IDs extracted."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [],
                'AssociatedHost': {'Ec2InstanceId': 'i-node123', 'HostName': 'ip-10-0-1-1'},
            },
        )
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 30.0, 'Maximum': 50.0}]},
            {'Datapoints': [{'Maximum': 0}]},
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )

        assert result.status == 'success'
        comp = result.applications[0].components[0]
        assert 'i-node123' in comp.ec2_instance_ids
        # CloudWatch should have been queried for this instance
        metrics = result.applications[0].cloudwatch_metrics
        assert len(metrics) == 1
        assert metrics[0].instance_id == 'i-node123'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_component_with_hana_details(self, mock_get_client, tools, ctx):
        """Test that HANA component details (version, replication) are captured."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
                'HdbVersion': '2.00.070',
                'ReplicationMode': 'PRIMARY',
                'OperationMode': 'logreplay',
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        comp = result.applications[0].components[0]
        assert comp.hana_version == '2.00.070'
        assert comp.replication_mode == 'PRIMARY'
        assert comp.operation_mode == 'logreplay'


class TestEnhancedLogBackup:
    """Tests for enhanced HANA log backup status with SSM command invocation."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_log_backup_with_command_history(self, mock_get_client, tools, ctx):
        """Test log backup status includes SSM command invocation results."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2.1'}]
        }
        # Mock paginator for list_commands
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'Commands': [
                    {
                        'CommandId': 'cmd-123',
                        'DocumentName': 'AWSSystemsManagerSAP-HanaLogBackupStatusCheck',
                        'InstanceIds': ['i-abc123'],
                    }
                ]
            }
        ]
        mock_ssm.get_paginator.return_value = mock_paginator
        # Mock list_command_invocations with Details for PerformAction step
        mock_ssm.list_command_invocations.return_value = {
            'CommandInvocations': [
                {
                    'Status': 'Success',
                    'CommandPlugins': [
                        {'Name': 'InstallPackage', 'Status': 'Success', 'Output': 'installed'},
                        {
                            'Name': 'InstallPackageAgain',
                            'Status': 'Success',
                            'Output': 'installed',
                        },
                        {
                            'Name': 'PerformAction',
                            'Status': 'Success',
                            'Output': 'pip output\n{"executionStatus": "Success", "data": {"is_log_backups_enabled": true}}',
                        },
                    ],
                }
            ]
        }

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=True,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        lb = result.applications[0].log_backup_status
        assert len(lb) == 1
        assert lb[0].ssm_agent_status == 'Online'
        assert lb[0].log_backup_status == 'Success'
        assert 'executionStatus' in lb[0].log_backup_details

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_log_backup_no_command_history(self, mock_get_client, tools, ctx):
        """Test log backup status when no SSM command history exists."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2.1'}]
        }
        mock_paginator_empty = MagicMock()
        mock_paginator_empty.paginate.return_value = [{'Commands': []}]
        mock_ssm.get_paginator.return_value = mock_paginator_empty

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=True,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        lb = result.applications[0].log_backup_status
        assert len(lb) == 1
        assert lb[0].ssm_agent_status == 'Online'
        assert lb[0].log_backup_status is None


class TestEnhancedBackup:
    """Tests for enhanced AWS Backup with SAP HANA resource type query."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_sap_hana_backup_type_query(self, mock_get_client, tools, ctx):
        """Test that backup queries SAP HANA on Amazon EC2 resource type."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [
                {
                    'State': 'COMPLETED',
                    'CompletionDate': '2026-03-23T10:00:00Z',
                    'ResourceArn': 'arn:aws:ssm-sap:us-east-1:123456789:my-hana/HANA/i-abc123',
                }
            ]
        }

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        bs = result.applications[0].backup_status
        assert len(bs) == 1
        assert bs[0].backup_status == 'COMPLETED'
        # Verify it queried with SAP HANA resource type
        mock_backup.list_backup_jobs.assert_called_with(
            ByResourceType='SAP HANA on Amazon EC2',
            MaxResults=50,
        )

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_backup_fallback_to_ec2_arn(self, mock_get_client, tools, ctx):
        """Test backup falls back to EC2 ARN query when no SAP HANA jobs match."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        # First call (SAP HANA type) returns no matching jobs
        # Second call (EC2 ARN fallback) returns a job
        mock_backup.list_backup_jobs.side_effect = [
            {'BackupJobs': []},  # SAP HANA type query - empty
            {
                'BackupJobs': [{'State': 'COMPLETED', 'CompletionDate': '2026-03-23T10:00:00Z'}]
            },  # EC2 ARN fallback
        ]

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        bs = result.applications[0].backup_status
        assert len(bs) == 1
        assert bs[0].backup_status == 'COMPLETED'


class TestCWAgentMetrics:
    """Tests for CWAgent metrics (memory, disk, network) in health summary."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_cwagent_metrics_included(self, mock_get_client, tools, ctx):
        """Test that CWAgent metrics are collected alongside EC2 metrics."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'my-hana'}]}
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {'Components': [{'ComponentId': 'HDB-00'}]}
        mock_sap.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'AssociatedHost': {'Ec2InstanceId': 'i-abc123'},
            }
        }

        mock_cw = MagicMock()
        # list_metrics calls for dimension discovery: mem, disk, net_recv, net_sent
        mem_dims = [
            {'Name': 'InstanceId', 'Value': 'i-abc123'},
            {'Name': 'CustomComponentName', 'Value': 'HANA-HDB-00'},
        ]
        disk_dims = [
            {'Name': 'InstanceId', 'Value': 'i-abc123'},
            {'Name': 'CustomComponentName', 'Value': 'HANA-HDB-00'},
            {'Name': 'path', 'Value': '/'},
            {'Name': 'device', 'Value': 'xvda1'},
            {'Name': 'fstype', 'Value': 'xfs'},
        ]
        net_dims = [
            {'Name': 'InstanceId', 'Value': 'i-abc123'},
            {'Name': 'interface', 'Value': 'eth0'},
        ]
        mock_cw.list_metrics.side_effect = [
            {'Metrics': [{'Dimensions': mem_dims}]},  # mem discover
            {'Metrics': [{'Dimensions': disk_dims}]},  # disk discover
            {'Metrics': [{'Dimensions': net_dims}]},  # net_recv discover
            {'Metrics': [{'Dimensions': net_dims}]},  # net_sent discover
        ]
        # get_metric_statistics calls: CPU, StatusCheck, mem, disk, net_recv, net_sent
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 45.2, 'Maximum': 78.1}]},  # CPU
            {'Datapoints': [{'Maximum': 0}]},  # StatusCheck
            {'Datapoints': [{'Average': 62.5}]},  # mem_used_percent
            {'Datapoints': [{'Average': 41.3}]},  # disk_used_percent
            {'Datapoints': [{'Sum': 1048576}]},  # net_bytes_recv
            {'Datapoints': [{'Sum': 524288}]},  # net_bytes_sent
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )

        assert result.status == 'success'
        cw = result.applications[0].cloudwatch_metrics
        assert len(cw) == 1
        assert cw[0].cpu_avg == 45.2
        assert cw[0].memory_used_pct == 62.5
        assert cw[0].disk_used_pct == 41.3
        assert cw[0].network_in == 1048576
        assert cw[0].network_out == 524288

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_cwagent_metrics_unavailable(self, mock_get_client, tools, ctx):
        """Test graceful handling when CWAgent metrics are not available."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'my-hana'}]}
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {'Components': [{'ComponentId': 'HDB-00'}]}
        mock_sap.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'AssociatedHost': {'Ec2InstanceId': 'i-abc123'},
            }
        }

        mock_cw = MagicMock()
        # list_metrics returns empty for all CWAgent metrics (not available)
        mock_cw.list_metrics.return_value = {'Metrics': []}
        # CPU and StatusCheck return data, CWAgent calls won't happen (no dims found)
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 10.0, 'Maximum': 20.0}]},  # CPU
            {'Datapoints': [{'Maximum': 0}]},  # StatusCheck
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )

        assert result.status == 'success'
        cw = result.applications[0].cloudwatch_metrics
        assert len(cw) == 1
        assert cw[0].cpu_avg == 10.0
        assert cw[0].memory_used_pct is None
        assert cw[0].disk_used_pct is None
        assert cw[0].network_in is None
        assert cw[0].network_out is None


class TestFilesystemUsage:
    """Tests for filesystem usage via SSM RunCommand."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_filesystem_usage_found(self, mock_get_client, tools, ctx):
        """Test filesystem usage data is collected from SSM command history."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'my-hana'}]}
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {'Components': [{'ComponentId': 'HDB-00'}]}
        mock_sap.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'AssociatedHost': {'Ec2InstanceId': 'i-abc123'},
            }
        }

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2.0'}]
        }
        # Paginator for log backup check (returns empty)
        mock_paginator_empty = MagicMock()
        mock_paginator_empty.paginate.return_value = [{'Commands': []}]
        mock_ssm.get_paginator.return_value = mock_paginator_empty
        # list_commands for filesystem fallback (not paginated)
        mock_ssm.list_commands.return_value = {
            'Commands': [
                {
                    'CommandId': 'cmd-fs123',
                    'Parameters': {'commands': ['df -h /usr/sap']},
                }
            ]
        }
        mock_ssm.get_command_invocation.return_value = {
            'Status': 'Success',
            'StandardOutputContent': 'Filesystem      Size  Used Avail Use% Mounted on\n/dev/xvdf       100G   45G   55G  45% /usr/sap',
        }

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=True,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        fs = result.applications[0].filesystem_usage
        assert len(fs) == 1
        assert fs[0].instance_id == 'i-abc123'
        assert fs[0].status == 'Success'
        assert '/usr/sap' in fs[0].filesystem_info

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_filesystem_usage_not_managed(self, mock_get_client, tools, ctx):
        """Test filesystem usage when instance is not managed by SSM."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'my-hana'}]}
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {'Components': [{'ComponentId': 'HDB-00'}]}
        mock_sap.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'AssociatedHost': {'Ec2InstanceId': 'i-abc123'},
            }
        }

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': []  # Not managed
        }

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=True,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        fs = result.applications[0].filesystem_usage
        assert len(fs) == 1
        assert fs[0].status == 'Not managed'
        assert fs[0].filesystem_info is None


class TestFormatBytes:
    """Tests for _format_bytes helper."""

    def test_bytes(self):
        """Test formatting of byte values."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _format_bytes,
        )

        assert _format_bytes(500) == '500 B'

    def test_kilobytes(self):
        """Test formatting of kilobyte values."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _format_bytes,
        )

        assert _format_bytes(2048) == '2.0 KB'

    def test_megabytes(self):
        """Test formatting of megabyte values."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _format_bytes,
        )

        assert _format_bytes(1048576) == '1.0 MB'

    def test_gigabytes(self):
        """Test formatting of gigabyte values."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _format_bytes,
        )

        assert _format_bytes(1073741824) == '1.00 GB'


class TestListOperationsFallback:
    """Tests for list_operations fallback when OperationId is missing from config checks."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_config_checks_with_fallback(self, mock_get_client, tools, ctx):
        """Test that generate_health_report uses list_operations fallback."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'my-hana'}]}
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {'Components': []}
        # Config check ops without OperationId
        mock_sap.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': [
                {
                    'ConfigurationCheckId': 'CHECK_01',
                    'Status': 'SUCCESS',
                    'Result': 'PASS',
                    'LastUpdatedTime': '2026-03-23T10:00:00Z',
                    # No OperationId!
                }
            ]
        }
        # list_operations fallback
        mock_sap.list_operations.return_value = {
            'Operations': [
                {
                    'Type': 'CONFIGURATION_CHECK',
                    'Id': 'op-fallback-123',
                }
            ]
        }
        mock_sap.list_sub_check_results.return_value = {
            'SubCheckResults': [
                {
                    'Name': 'SubCheck1',
                    'Result': 'PASS',
                    'Description': 'All good',
                    'Id': 'sc-1',
                }
            ]
        }
        mock_sap.list_sub_check_rule_results.return_value = {'RuleResults': []}

        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx,
            application_id='my-hana',
            include_config_checks=True,
            include_subchecks=True,
            include_rule_results=True,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert 'CHECK_01' in result.report
        assert 'SubCheck1' in result.report
        # Verify list_operations was called as fallback
        mock_sap.list_operations.assert_called_once()


class TestClusterStatusExtraction:
    """Tests for cluster_status extraction in _get_app_summary."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_cluster_status_populated(self, mock_get_client, tools, ctx):
        """Test that cluster_status is extracted from Resilience.ClusterStatus."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'my-hana'}]}
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {'Components': [{'ComponentId': 'HDB-00-node1'}]}
        mock_sap.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'AssociatedHost': {'Ec2InstanceId': 'i-abc123'},
                'HdbVersion': '2.00.073.00',
                'Resilience': {
                    'HsrReplicationMode': 'sync',
                    'HsrOperationMode': 'logreplay',
                    'ClusterStatus': 'ONLINE',
                },
            }
        }

        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        comp = result.applications[0].components[0]
        assert comp.cluster_status == 'ONLINE'
        assert comp.replication_mode == 'sync'
        assert comp.operation_mode == 'logreplay'
        assert comp.hana_version == '2.00.073.00'


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_emoji_known_status(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _emoji

        assert _emoji('ACTIVATED') == '🟢'
        assert _emoji('FAILED') == '🔴'
        assert _emoji('UNKNOWN') == '⚪'

    def test_emoji_unknown_status(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _emoji

        assert _emoji('NONEXISTENT') == '⚪'

    def test_get_all_app_ids_pagination(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _get_all_app_ids

        mock_client = MagicMock()
        mock_client.list_applications.side_effect = [
            {'Applications': [{'Id': 'a1'}], 'NextToken': 'tok'},
            {'Applications': [{'Id': 'a2'}]},
        ]
        ids = _get_all_app_ids(mock_client)
        assert ids == ['a1', 'a2']

    def test_discover_cwagent_dimensions_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _discover_cwagent_dimensions,
        )

        mock_cw = MagicMock()
        mock_cw.list_metrics.side_effect = Exception('fail')
        result = _discover_cwagent_dimensions(mock_cw, 'mem_used_percent', 'i-123')
        assert result is None

    def test_discover_cwagent_dimensions_empty(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _discover_cwagent_dimensions,
        )

        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {'Metrics': []}
        result = _discover_cwagent_dimensions(mock_cw, 'mem_used_percent', 'i-123')
        assert result is None

    def test_discover_cwagent_disk_dimensions(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _discover_cwagent_disk_dimensions,
        )

        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {
            'Metrics': [
                {
                    'Dimensions': [
                        {'Name': 'InstanceId', 'Value': 'i-1'},
                        {'Name': 'path', 'Value': '/'},
                    ]
                },
                {
                    'Dimensions': [
                        {'Name': 'InstanceId', 'Value': 'i-1'},
                        {'Name': 'path', 'Value': '/hana/data'},
                    ]
                },
                {
                    'Dimensions': [
                        {'Name': 'InstanceId', 'Value': 'i-1'},
                        {'Name': 'path', 'Value': '/tmp'},
                    ]
                },
            ]
        }
        result = _discover_cwagent_disk_dimensions(mock_cw, 'i-1')
        assert len(result) == 2  # / and /hana/data match, /tmp does not

    def test_discover_cwagent_disk_dimensions_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _discover_cwagent_disk_dimensions,
        )

        mock_cw = MagicMock()
        mock_cw.list_metrics.side_effect = Exception('fail')
        result = _discover_cwagent_disk_dimensions(mock_cw, 'i-1')
        assert result == []

    def test_has_recent_config_checks_empty(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _has_recent_config_checks,
        )

        assert _has_recent_config_checks([]) is False

    def test_has_recent_config_checks_recent(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _has_recent_config_checks,
        )

        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        assert _has_recent_config_checks([{'EndTime': recent}]) is True

    def test_has_recent_config_checks_old(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _has_recent_config_checks,
        )

        old = datetime.now(timezone.utc) - timedelta(hours=48)
        assert _has_recent_config_checks([{'EndTime': old}]) is False

    def test_has_recent_config_checks_string_timestamp(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _has_recent_config_checks,
        )

        assert _has_recent_config_checks([{'EndTime': '2020-01-01'}]) is False

    def test_has_recent_config_checks_naive_datetime(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _has_recent_config_checks,
        )

        recent = datetime.now() - timedelta(hours=1)  # naive datetime
        assert _has_recent_config_checks([{'EndTime': recent}]) is True

    def test_trigger_config_checks_success(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _trigger_config_checks,
        )

        mock_client = MagicMock()
        mock_client.list_configuration_check_definitions.return_value = {
            'ConfigurationChecks': [{'Id': 'CHECK_01'}, {'Id': 'CHECK_02'}]
        }
        mock_client.start_configuration_checks.return_value = {
            'ConfigurationCheckOperations': [{'OperationId': 'op-1'}]
        }
        result = _trigger_config_checks(mock_client, 'app-1')
        assert len(result) == 1

    def test_trigger_config_checks_no_definitions(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _trigger_config_checks,
        )

        mock_client = MagicMock()
        mock_client.list_configuration_check_definitions.return_value = {'ConfigurationChecks': []}
        result = _trigger_config_checks(mock_client, 'app-1')
        assert result == []

    def test_trigger_config_checks_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _trigger_config_checks,
        )

        mock_client = MagicMock()
        mock_client.list_configuration_check_definitions.side_effect = Exception('fail')
        result = _trigger_config_checks(mock_client, 'app-1')
        assert result == []


class TestWaitForConfigChecks:
    """Tests for _wait_for_config_checks."""

    @pytest.mark.asyncio
    async def test_wait_all_complete(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _wait_for_config_checks,
        )

        mock_client = MagicMock()
        mock_client.get_configuration_check_operation.return_value = {
            'ConfigurationCheckOperation': {'Status': 'SUCCESS'}
        }
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.asyncio.sleep',
            new_callable=AsyncMock,
        ):
            await _wait_for_config_checks(
                mock_client, [{'OperationId': 'op-1'}], poll_interval_seconds=1, max_wait_seconds=5
            )

    @pytest.mark.asyncio
    async def test_wait_empty_operations(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _wait_for_config_checks,
        )

        mock_client = MagicMock()
        await _wait_for_config_checks(mock_client, [], poll_interval_seconds=1, max_wait_seconds=5)

    @pytest.mark.asyncio
    async def test_wait_timeout(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _wait_for_config_checks,
        )

        mock_client = MagicMock()
        mock_client.get_configuration_check_operation.return_value = {
            'ConfigurationCheckOperation': {'Status': 'IN_PROGRESS'}
        }
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.asyncio.sleep',
            new_callable=AsyncMock,
        ):
            await _wait_for_config_checks(
                mock_client, [{'OperationId': 'op-1'}], poll_interval_seconds=1, max_wait_seconds=2
            )

    @pytest.mark.asyncio
    async def test_wait_poll_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _wait_for_config_checks,
        )

        mock_client = MagicMock()
        mock_client.get_configuration_check_operation.side_effect = Exception('fail')
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.asyncio.sleep',
            new_callable=AsyncMock,
        ):
            await _wait_for_config_checks(
                mock_client, [{'OperationId': 'op-1'}], poll_interval_seconds=1, max_wait_seconds=2
            )


class TestRunSsmCommand:
    """Tests for _run_ssm_command async function."""

    @pytest.mark.asyncio
    async def test_success(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _run_ssm_command

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-1'}}
        mock_ssm.get_command_invocation.return_value = {
            'Status': 'Success',
            'StandardOutputContent': 'output data',
        }
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.asyncio.sleep',
            new_callable=AsyncMock,
        ):
            result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h', timeout_seconds=6)
        assert result == 'output data'

    @pytest.mark.asyncio
    async def test_command_failed(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _run_ssm_command

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-1'}}
        mock_ssm.get_command_invocation.return_value = {'Status': 'Failed'}
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.asyncio.sleep',
            new_callable=AsyncMock,
        ):
            result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h', timeout_seconds=6)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_command_id(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _run_ssm_command

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {}}
        result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h')
        assert result is None

    @pytest.mark.asyncio
    async def test_send_command_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _run_ssm_command

        mock_ssm = MagicMock()
        mock_ssm.send_command.side_effect = Exception('fail')
        result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h')
        assert result is None

    @pytest.mark.asyncio
    async def test_invocation_does_not_exist(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _run_ssm_command

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-1'}}
        exc_class = type('InvocationDoesNotExist', (Exception,), {})
        mock_ssm.exceptions = MagicMock()
        mock_ssm.exceptions.InvocationDoesNotExist = exc_class
        mock_ssm.get_command_invocation.side_effect = exc_class('not yet')
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.asyncio.sleep',
            new_callable=AsyncMock,
        ):
            result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h', timeout_seconds=3)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_invocation_other_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import _run_ssm_command

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-1'}}
        mock_ssm.exceptions = MagicMock()
        mock_ssm.exceptions.InvocationDoesNotExist = type(
            'InvocationDoesNotExist', (Exception,), {}
        )
        mock_ssm.get_command_invocation.side_effect = Exception('other error')
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.asyncio.sleep',
            new_callable=AsyncMock,
        ):
            result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h', timeout_seconds=6)
        assert result is None


class TestRunSsmCommandSync:
    """Tests for _run_ssm_command async function."""

    async def test_success(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _run_ssm_command,
        )

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-1'}}
        mock_ssm.get_command_invocation.return_value = {
            'Status': 'Success',
            'StandardOutputContent': 'output',
        }
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h', timeout_seconds=6)
        assert result == 'output'

    async def test_failed(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _run_ssm_command,
        )

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-1'}}
        mock_ssm.get_command_invocation.return_value = {'Status': 'Failed'}
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h', timeout_seconds=6)
        assert result is None

    async def test_no_command_id(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _run_ssm_command,
        )

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {}}
        result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h')
        assert result is None

    async def test_send_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _run_ssm_command,
        )

        mock_ssm = MagicMock()
        mock_ssm.send_command.side_effect = Exception('fail')
        result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h')
        assert result is None

    async def test_poll_exception_continues(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _run_ssm_command,
        )

        mock_ssm = MagicMock()
        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-1'}}
        mock_ssm.get_command_invocation.side_effect = Exception('poll fail')
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await _run_ssm_command(mock_ssm, 'i-123', 'df -h', timeout_seconds=3)
        assert result is None


class TestBuildOverallSummary:
    """Tests for _build_overall_summary."""

    def test_all_healthy(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _build_overall_summary,
        )

        result = _build_overall_summary(2, {'ACTIVATED': 2}, {'SUCCESS': 2})
        assert 'All 2 application(s) are running and healthy' in result

    def test_mixed_status(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _build_overall_summary,
        )

        result = _build_overall_summary(
            3, {'ACTIVATED': 1, 'FAILED': 1, 'STOPPED': 1}, {'SUCCESS': 2, 'ERROR': 1}
        )
        assert 'require attention' in result
        assert 'failed' in result
        assert 'stopped' in result

    def test_zero_apps(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _build_overall_summary,
        )

        result = _build_overall_summary(0, {}, {})
        assert 'Overall Summary' in result


class TestCheckAppHealth:
    """Tests for _check_app_health report generation."""

    async def test_healthy_app_report(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {'Components': []}
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': []
        }
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            None,
            'app-1',
            include_config_checks=False,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert status == 'ACTIVATED'
        assert disc == 'SUCCESS'
        assert 'app-1' in report

    async def test_unhealthy_app_report(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'FAILED',
                'DiscoveryStatus': 'REFRESH_FAILED',
                'StatusMessage': 'Something broke',
            }
        }
        mock_client.list_components.return_value = {'Components': []}
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': []
        }
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            None,
            'app-1',
            include_config_checks=False,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert status == 'FAILED'
        assert 'Something broke' in report

    async def test_app_retrieval_error(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.side_effect = Exception('Access denied')
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            None,
            'app-1',
            include_config_checks=False,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert status == 'ERROR'
        assert 'Access denied' in report

    async def test_with_hana_node_components(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {
            'Components': [
                {'ComponentId': 'HDB-HDB00-primary'},
                {'ComponentId': 'HDB-HDB00-secondary'},
            ]
        }
        mock_client.get_component.side_effect = [
            {
                'Component': {
                    'ComponentType': 'HANA_NODE',
                    'Status': 'ACTIVATED',
                    'Sid': 'HDB',
                    'Hosts': [{'EC2InstanceId': 'i-1'}],
                    'HdbVersion': '2.00.070',
                    'Resilience': {
                        'HsrReplicationMode': 'PRIMARY',
                        'HsrOperationMode': 'PRIMARY',
                        'ClusterStatus': 'ONLINE',
                    },
                }
            },
            {
                'Component': {
                    'ComponentType': 'HANA_NODE',
                    'Status': 'ACTIVATED',
                    'Sid': 'HDB',
                    'Hosts': [{'EC2InstanceId': 'i-2'}],
                    'Resilience': {
                        'HsrReplicationMode': 'sync',
                        'HsrOperationMode': 'logreplay',
                        'ClusterStatus': 'ONLINE',
                    },
                }
            },
        ]
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            None,
            'app-1',
            include_config_checks=False,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert 'Primary' in report
        assert 'Secondary' in report
        assert 'i-1' in report
        assert 'i-2' in report

    async def test_with_parent_component_skipped(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {
            'Components': [{'ComponentId': 'HDB-parent'}, {'ComponentId': 'HDB-node1'}]
        }
        mock_client.get_component.side_effect = [
            {
                'Component': {
                    'ComponentType': 'HANA',
                    'Status': 'ACTIVATED',
                    'Sid': 'HDB',
                    'Hosts': [],
                    'HdbVersion': '2.00.070',
                    'Databases': ['SYSTEMDB', 'HDB'],
                }
            },
            {
                'Component': {
                    'ComponentType': 'HANA_NODE',
                    'Status': 'ACTIVATED',
                    'Sid': 'HDB',
                    'Hosts': [{'EC2InstanceId': 'i-1'}],
                }
            },
        ]
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            None,
            'app-1',
            include_config_checks=False,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert '2.00.070' in report
        assert 'SYSTEMDB' in report

    async def test_component_error(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {'Components': [{'ComponentId': 'comp-1'}]}
        mock_client.get_component.side_effect = Exception('Component error')
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            None,
            'app-1',
            include_config_checks=False,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert 'comp-1' in report

    async def test_abap_components(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'SAP_ABAP',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {
            'Components': [{'ComponentId': 'ASCS-01'}, {'ComponentId': 'APP-01'}]
        }
        mock_client.get_component.side_effect = [
            {
                'Component': {
                    'ComponentType': 'ASCS',
                    'Status': 'ACTIVATED',
                    'Sid': 'S4H',
                    'Hosts': [{'EC2InstanceId': 'i-1'}],
                }
            },
            {
                'Component': {
                    'ComponentType': 'APP',
                    'Status': 'ACTIVATED',
                    'Sid': 'S4H',
                    'Hosts': [{'EC2InstanceId': 'i-2'}],
                }
            },
        ]
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            None,
            'app-1',
            include_config_checks=False,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert 'SAP Components' in report
        assert 'ASCS' in report


class TestAppendConfigChecks:
    """Tests for _append_config_checks."""

    def test_no_check_ops(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_config_checks,
        )

        mock_client = MagicMock()
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': []
        }
        lines = []
        _append_config_checks(mock_client, 'app-1', lines, True, True)
        assert any('No configuration check results' in l for l in lines)

    def test_with_subchecks_and_rules(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_config_checks,
        )

        mock_client = MagicMock()
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': [
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'SUCCESS',
                    'RuleStatusCounts': {'Passed': 3, 'Failed': 1},
                    'Id': 'op-1',
                }
            ]
        }
        mock_client.list_sub_check_results.return_value = {
            'SubCheckResults': [
                {'Id': 'sc-1', 'Name': 'SubA', 'Result': 'FAIL', 'Description': 'Desc'}
            ]
        }
        mock_client.list_sub_check_rule_results.return_value = {
            'RuleResults': [
                {
                    'Id': 'r1',
                    'Description': 'Rule1',
                    'Status': 'FAILED',
                    'Message': 'Fix this',
                    'Metadata': {'ActualValue': '10', 'ExpectedValue': '20'},
                },
                {
                    'Id': 'r2',
                    'Description': 'Rule2',
                    'Status': 'WARNING',
                    'Message': 'Check this',
                    'Metadata': {},
                },
            ]
        }
        lines = []
        findings = []
        _append_config_checks(mock_client, 'app-1', lines, True, True, findings=findings)
        assert any('EC2 Instance Type Selection' in l for l in lines)
        assert any('Rule1' in l for l in lines)
        assert len(findings) == 2

    def test_exception_handling(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_config_checks,
        )

        mock_client = MagicMock()
        mock_client.list_configuration_check_operations.side_effect = Exception('fail')
        lines = []
        _append_config_checks(mock_client, 'app-1', lines, True, True)
        assert any('Could not retrieve' in l for l in lines)

    def test_fallback_to_list_operations(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_config_checks,
        )

        mock_client = MagicMock()
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': [
                {
                    'ConfigurationCheckId': 'SAP_CHECK_02',
                    'Status': 'SUCCESS',
                    'RuleStatusCounts': {'Passed': 5},
                    # No Id or OperationId
                }
            ]
        }
        mock_client.list_operations.return_value = {
            'Operations': [{'Type': 'CONFIGURATION_CHECK', 'Id': 'op-fallback'}]
        }
        mock_client.list_sub_check_results.return_value = {
            'SubCheckResults': [
                {'Id': 'sc-1', 'Name': 'Sub1', 'Result': 'PASS', 'Description': 'OK'}
            ]
        }
        mock_client.list_sub_check_rule_results.return_value = {'RuleResults': []}
        lines = []
        _append_config_checks(mock_client, 'app-1', lines, True, True)
        assert any('Storage Configuration' in l for l in lines)
        mock_client.list_operations.assert_called_once()


class TestAppendLogBackupStatus:
    """Tests for _append_log_backup_status."""

    def test_no_instances(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        lines = []
        _append_log_backup_status(MagicMock(), 'app-1', [], lines)
        assert any('No EC2 instances' in l for l in lines)

    def test_online_with_backup_history(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'Commands': [{'CommandId': 'cmd-1', 'InstanceIds': ['i-1']}]}
        ]
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_ssm.list_command_invocations.return_value = {
            'CommandInvocations': [
                {
                    'Status': 'Success',
                    'CommandPlugins': [
                        {
                            'Name': 'PerformAction',
                            'Status': 'Success',
                            'Output': '{"executionStatus": "Success"}',
                        },
                    ],
                }
            ]
        }
        lines = []
        findings = []
        _append_log_backup_status(mock_ssm, 'app-1', ['i-1'], lines, findings=findings)
        assert any('Online' in l for l in lines)
        assert any('executionStatus' in l for l in lines)

    def test_online_no_history(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Commands': []}]
        mock_ssm.get_paginator.return_value = mock_paginator
        lines = []
        findings = []
        _append_log_backup_status(mock_ssm, 'app-1', ['i-1'], lines, findings=findings)
        assert any('No check history' in l for l in lines)
        assert len(findings) == 1

    def test_not_managed(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {'InstanceInformationList': []}
        lines = []
        _append_log_backup_status(mock_ssm, 'app-1', ['i-1'], lines)
        assert any('Not managed' in l for l in lines)

    def test_describe_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.side_effect = Exception('fail')
        lines = []
        _append_log_backup_status(mock_ssm, 'app-1', ['i-1'], lines)
        assert any('Unable to query' in l for l in lines)

    def test_failed_backup_check(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'Commands': [{'CommandId': 'cmd-1', 'InstanceIds': ['i-1']}]}
        ]
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_ssm.list_command_invocations.return_value = {
            'CommandInvocations': [
                {
                    'Status': 'Failed',
                    'CommandPlugins': [
                        {'Name': 'PerformAction', 'Status': 'Failed', 'Output': 'error'},
                    ],
                }
            ]
        }
        lines = []
        findings = []
        _append_log_backup_status(mock_ssm, 'app-1', ['i-1'], lines, findings=findings)
        assert any('🔴' in l for l in lines)
        assert len(findings) == 1


class TestAppendAwsBackupStatus:
    """Tests for _append_aws_backup_status."""

    def test_no_instances(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        lines = []
        _append_aws_backup_status(MagicMock(), 'app-1', [], lines)
        assert any('No EC2 instances' in l for l in lines)

    def test_sap_hana_jobs_found(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [
                {
                    'State': 'COMPLETED',
                    'CompletionDate': '2026-01-01',
                    'ResourceArn': 'arn:aws:ssm-sap:us-east-1:123:app-1/HANA',
                    'BackupType': 'CONTINUOUS',
                }
            ]
        }
        lines = []
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines)
        assert any('COMPLETED' in l for l in lines)

    def test_sap_hana_failed_job_with_describe(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [
                {
                    'State': 'FAILED',
                    'CreationDate': '2026-01-01',
                    'ResourceArn': 'arn:aws:ssm-sap:us-east-1:123:app-1/HANA',
                    'BackupJobId': 'job-1',
                }
            ]
        }
        mock_backup.describe_backup_job.return_value = {'StatusMessage': 'Disk full'}
        lines = []
        findings = []
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines, findings=findings)
        assert any('FAILED' in l for l in lines)
        assert any('Disk full' in l for l in lines)
        assert len(findings) == 1

    def test_fallback_to_ec2_arn(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.side_effect = [
            {'BackupJobs': []},  # SAP HANA query empty
            {'BackupJobs': [{'State': 'COMPLETED', 'CompletionDate': '2026-01-01'}]},
        ]
        lines = []
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines)
        assert any('COMPLETED' in l for l in lines)

    def test_fallback_no_backups(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.side_effect = [
            {'BackupJobs': []},  # SAP HANA query empty
            {'BackupJobs': []},  # EC2 ARN query empty
        ]
        lines = []
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines)
        assert any('No backups found' in l for l in lines)

    def test_fallback_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.side_effect = [
            Exception('SAP query fail'),
            {'BackupJobs': [{'State': 'COMPLETED', 'CompletionDate': '2026-01-01'}]},
        ]
        lines = []
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines)
        assert any('COMPLETED' in l for l in lines)

    def test_ec2_fallback_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.side_effect = [
            Exception('SAP query fail'),
            Exception('EC2 query fail'),
        ]
        lines = []
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines)
        assert any('Error' in l for l in lines)

    def test_outer_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.side_effect = Exception('total fail')
        lines = []
        # The outer try/except should catch this
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines)


class TestAppendCloudwatchMetrics:
    """Tests for _append_cloudwatch_metrics."""

    def test_no_instances(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_cloudwatch_metrics,
        )

        lines = []
        _append_cloudwatch_metrics(MagicMock(), [], lines)
        assert any('No EC2 instances' in l for l in lines)

    def test_with_all_metrics(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_cloudwatch_metrics,
        )

        mock_cw = MagicMock()
        mem_dims = [{'Name': 'InstanceId', 'Value': 'i-1'}]
        disk_dims = [
            {'Name': 'InstanceId', 'Value': 'i-1'},
            {'Name': 'path', 'Value': '/'},
            {'Name': 'device', 'Value': 'xvda'},
        ]
        net_dims = [{'Name': 'InstanceId', 'Value': 'i-1'}, {'Name': 'interface', 'Value': 'eth0'}]
        mock_cw.list_metrics.side_effect = [
            {'Metrics': [{'Dimensions': mem_dims}]},
            {'Metrics': [{'Dimensions': disk_dims}]},
            {'Metrics': [{'Dimensions': net_dims}]},
            {'Metrics': [{'Dimensions': net_dims}]},
            {'Metrics': [{'Dimensions': disk_dims}]},  # disk detail
        ]
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 45.0, 'Maximum': 80.0}]},  # CPU
            {'Datapoints': [{'Maximum': 0}]},  # StatusCheck
            {'Datapoints': [{'Average': 92.0}]},  # mem (>90 = critical)
            {'Datapoints': [{'Average': 55.0}]},  # disk
            {'Datapoints': [{'Sum': 1024}]},  # net_recv
            {'Datapoints': [{'Sum': 512}]},  # net_sent
            {'Datapoints': [{'Average': 55.0}]},  # disk detail
        ]
        lines = []
        findings = []
        _append_cloudwatch_metrics(mock_cw, ['i-1'], lines, findings=findings)
        assert any('45.0' in l for l in lines)
        assert any('Network I/O' in l for l in lines)
        # Memory >90 should generate a finding
        assert any('Memory usage critical' in f.get('rule', '') for f in findings)

    def test_status_check_failed(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_cloudwatch_metrics,
        )

        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {'Metrics': []}
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 10.0, 'Maximum': 20.0}]},  # CPU
            {'Datapoints': [{'Maximum': 1}]},  # StatusCheck FAILED
        ]
        lines = []
        findings = []
        _append_cloudwatch_metrics(mock_cw, ['i-1'], lines, findings=findings)
        assert any('FAILED' in l for l in lines)
        assert any('status check failed' in f.get('rule', '') for f in findings)

    def test_no_datapoints(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_cloudwatch_metrics,
        )

        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {'Metrics': []}
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': []},  # CPU no data
            {'Datapoints': []},  # StatusCheck no data
        ]
        lines = []
        _append_cloudwatch_metrics(mock_cw, ['i-1'], lines)
        assert any('No data' in l for l in lines)

    def test_cpu_exception(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_cloudwatch_metrics,
        )

        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {'Metrics': []}
        mock_cw.get_metric_statistics.side_effect = [
            Exception('CPU fail'),
            Exception('Status fail'),
        ]
        lines = []
        _append_cloudwatch_metrics(mock_cw, ['i-1'], lines)
        assert any('Error' in l for l in lines)


class TestAppendFilesystemUsage:
    """Tests for _append_filesystem_usage."""

    async def test_no_instances(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_filesystem_usage,
        )

        lines = []
        await _append_filesystem_usage(MagicMock(), [], lines)
        assert any('No EC2 instances' in l for l in lines)

    async def test_with_ssm_command_output(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_filesystem_usage,
        )

        mock_ssm = MagicMock()
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._run_ssm_command',
            new_callable=AsyncMock,
            return_value='Filesystem  Size  Used Avail Use% Mounted on\n/dev/xvda   50G   40G   10G  85% /\n/dev/xvdb  100G   96G    4G  96% /hana/data',
        ):
            lines = []
            findings = []
            await _append_filesystem_usage(mock_ssm, ['i-1'], lines, findings=findings)
            assert any('/hana/data' in l for l in lines)
            # 96% should be critical, 85% should be warning
            assert any('critically full' in f.get('rule', '') for f in findings)
            assert any('high usage' in f.get('rule', '') for f in findings)

    async def test_fallback_to_command_history(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_filesystem_usage,
        )

        mock_ssm = MagicMock()
        mock_ssm.list_commands.return_value = {
            'Commands': [{'CommandId': 'cmd-1', 'Parameters': {'commands': ['df -h /']}}]
        }
        mock_ssm.get_command_invocation.return_value = {
            'Status': 'Success',
            'StandardOutputContent': 'Filesystem  Size\n/dev/xvda   50G   40G   10G  70% /',
        }
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._run_ssm_command',
            new_callable=AsyncMock,
            return_value=None,
        ):
            lines = []
            await _append_filesystem_usage(mock_ssm, ['i-1'], lines)
            assert any('50G' in l for l in lines)

    async def test_no_data_available(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_filesystem_usage,
        )

        mock_ssm = MagicMock()
        mock_ssm.list_commands.return_value = {'Commands': []}
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._run_ssm_command',
            new_callable=AsyncMock,
            return_value=None,
        ):
            lines = []
            await _append_filesystem_usage(mock_ssm, ['i-1'], lines)
            assert any('No filesystem usage data' in l for l in lines)

    async def test_exception_handling(self):
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_filesystem_usage,
        )

        mock_ssm = MagicMock()
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._run_ssm_command',
            new_callable=AsyncMock,
            side_effect=Exception('fail'),
        ):
            mock_ssm.list_commands.side_effect = Exception('fail')
            lines = []
            await _append_filesystem_usage(mock_ssm, ['i-1'], lines)
            assert any('No filesystem usage data' in l for l in lines)


class TestGetAppSummaryEdgeCases:
    """Tests for _get_app_summary edge cases."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_component_list_error(self, mock_get_client, tools, ctx):
        """Test _get_app_summary when list_components fails."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_sap.list_components.side_effect = Exception('Component list error')
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert result.applications[0].component_count == 0

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_component_detail_error(self, mock_get_client, tools, ctx):
        """Test _get_app_summary when get_component fails for one component."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'comp-1'}],
        )
        mock_sap.get_component.side_effect = Exception('Component detail error')
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert result.applications[0].components[0].status == 'ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_parent_hana_component_skipped(self, mock_get_client, tools, ctx):
        """Test that parent HANA component type is skipped in summary."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-parent'}, {'ComponentId': 'hana-node'}],
        )
        mock_sap.get_component.side_effect = [
            {
                'Component': {
                    'ComponentType': 'HANA',
                    'Status': 'ACTIVATED',
                    'Sid': 'HDB',
                    'Hosts': [],
                    'Databases': [{'DatabaseId': 'SYSTEMDB'}],
                }
            },
            {
                'Component': {
                    'ComponentType': 'HANA_NODE',
                    'Status': 'ACTIVATED',
                    'Sid': 'HDB',
                    'Hosts': [{'EC2InstanceId': 'i-1'}],
                }
            },
        ]
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        # Only HANA_NODE should be in components, not the parent HANA
        assert len(result.applications[0].components) == 1
        assert result.applications[0].components[0].component_type == 'HANA_NODE'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_hana_node_with_resilience(self, mock_get_client, tools, ctx):
        """Test HANA_NODE with Resilience dict for replication info."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
                'HdbVersion': '2.00.070',
                'Resilience': {
                    'HsrReplicationMode': 'sync',
                    'HsrOperationMode': 'logreplay',
                    'ClusterStatus': 'ONLINE',
                },
                'Databases': [{'DatabaseId': 'SYSTEMDB'}, {'DatabaseId': 'HDB'}],
            },
        )
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        comp = result.applications[0].components[0]
        assert comp.replication_mode == 'sync'
        assert comp.operation_mode == 'logreplay'
        assert comp.cluster_status == 'ONLINE'
        assert comp.databases == ['SYSTEMDB', 'HDB']

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_config_check_exception(self, mock_get_client, tools, ctx):
        """Test _get_app_summary when config check operations fail."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_sap.list_configuration_check_operations.side_effect = Exception('Config check error')
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_config_checks=True,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert len(result.applications[0].config_checks) == 0

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_status_check_no_data(self, mock_get_client, tools, ctx):
        """Test CloudWatch status check with no datapoints."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {'Metrics': []}
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': []},  # CPU no data
            {'Datapoints': []},  # StatusCheck no data
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )
        assert result.applications[0].cloudwatch_metrics[0].status_check == 'No data'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_status_check_error(self, mock_get_client, tools, ctx):
        """Test CloudWatch status check with exception."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {'Metrics': []}
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 10.0, 'Maximum': 20.0}]},  # CPU
            Exception('StatusCheck error'),  # StatusCheck fails
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )
        assert result.applications[0].cloudwatch_metrics[0].status_check == 'Error'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_app_with_status_message(self, mock_get_client, tools, ctx):
        """Test app with StatusMessage field."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'FAILED',
                'DiscoveryStatus': 'REFRESH_FAILED',
                'StatusMessage': 'Something went wrong',
            },
        )
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert result.applications[0].status_message == 'Something went wrong'


class TestReportWithLogBackup:
    """Tests for generate_health_report with log backup status."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_with_log_backup(self, mock_get_client, tools, ctx):
        """Test report includes log backup section."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Commands': []}]
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_ssm.list_commands.return_value = {'Commands': []}

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._run_ssm_command',
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await tools.generate_health_report(
                ctx,
                application_id='app-1',
                include_config_checks=False,
                include_log_backup_status=True,
                include_aws_backup_status=False,
                include_cloudwatch_metrics=False,
            )
        assert result.status == 'success'
        assert 'Log Backup' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_with_backup(self, mock_get_client, tools, ctx):
        """Test report includes AWS Backup section."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [
                {
                    'State': 'COMPLETED',
                    'CompletionDate': '2026-01-01',
                    'ResourceArn': 'arn:app-1/HANA',
                    'BackupType': 'FULL',
                }
            ]
        }

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router
        result = await tools.generate_health_report(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert 'Backup' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_with_cloudwatch(self, mock_get_client, tools, ctx):
        """Test report includes CloudWatch section."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {'Metrics': []}
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 30.0, 'Maximum': 50.0}]},
            {'Datapoints': [{'Maximum': 0}]},
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router
        result = await tools.generate_health_report(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )
        assert result.status == 'success'
        assert 'CloudWatch' in result.report


class TestGetAppSummarySubchecks:
    """Tests for subcheck/rule result paths in _get_app_summary."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_subcheck_rule_results_exception(self, mock_get_client, tools, ctx):
        """Test that rule result exceptions are handled gracefully."""
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'Id': 'op-1',
                    'EndTime': recent,
                }
            ],
            sub_check_results=[
                {'Id': 'sc-1', 'Name': 'Sub1', 'Result': 'FAIL', 'Description': 'Desc'}
            ],
        )
        mock_sap.list_sub_check_rule_results.side_effect = Exception('Rule results error')
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_subchecks=True,
            include_rule_results=True,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert len(result.applications[0].config_checks[0].subchecks) == 1
        assert result.applications[0].config_checks[0].subchecks[0].rule_results == []

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_subcheck_list_exception(self, mock_get_client, tools, ctx):
        """Test that subcheck list exceptions are handled gracefully."""
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {
                    'ConfigurationCheckId': 'SAP_CHECK_01',
                    'Status': 'COMPLETED',
                    'Id': 'op-1',
                    'EndTime': recent,
                }
            ],
        )
        mock_sap.list_sub_check_results.side_effect = Exception('Subcheck error')
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_subchecks=True,
            include_rule_results=True,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert result.applications[0].config_checks[0].subchecks == []

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_config_check_no_operation_id_fallback(self, mock_get_client, tools, ctx):
        """Test fallback to list_operations when no operation ID."""
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {'ConfigurationCheckId': 'SAP_CHECK_01', 'Status': 'COMPLETED', 'EndTime': recent}
            ],
            sub_check_results=[{'Id': 'sc-1', 'Name': 'Sub1', 'Result': 'PASS'}],
        )
        mock_sap.list_operations = MagicMock(
            return_value={'Operations': [{'Type': 'CONFIGURATION_CHECK', 'Id': 'op-fallback'}]}
        )
        mock_get_client.return_value = mock_sap
        result = await tools.get_sap_health_summary(
            ctx,
            application_id='app-1',
            include_subchecks=True,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert len(result.applications[0].config_checks[0].subchecks) == 1
        mock_sap.list_operations.assert_called_once()


class TestReportLogBackupDetails:
    """Tests for log backup details in report."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_log_backup_with_invocation_details(self, mock_get_client, tools, ctx):
        """Test report log backup with invocation details."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'Commands': [{'CommandId': 'cmd-1', 'InstanceIds': ['i-1']}]}
        ]
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_ssm.list_command_invocations.return_value = {
            'CommandInvocations': [
                {
                    'Status': 'Failed',
                    'CommandPlugins': [
                        {'Name': 'PerformAction', 'Status': 'Failed', 'Output': 'error output'}
                    ],
                }
            ]
        }
        mock_ssm.list_commands.return_value = {'Commands': []}

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._run_ssm_command',
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await tools.generate_health_report(
                ctx,
                application_id='app-1',
                include_config_checks=False,
                include_log_backup_status=True,
                include_aws_backup_status=False,
                include_cloudwatch_metrics=False,
            )
        assert result.status == 'success'
        assert 'Log Backup' in result.report


class TestReportBackupDetails:
    """Tests for backup details in report."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_backup_failed_with_details(self, mock_get_client, tools, ctx):
        """Test report backup with failed job details."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [
                {
                    'State': 'FAILED',
                    'CreationDate': '2026-01-01',
                    'ResourceArn': 'arn:app-1/HANA',
                    'BackupJobId': 'job-1',
                    'StatusMessage': 'Disk full',
                }
            ]
        }

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router
        result = await tools.generate_health_report(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert 'FAILED' in result.report
        assert 'Disk full' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_backup_ec2_fallback(self, mock_get_client, tools, ctx):
        """Test report backup with EC2 ARN fallback."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.side_effect = [
            {'BackupJobs': []},  # SAP HANA query empty
            {'BackupJobs': [{'State': 'COMPLETED', 'CompletionDate': '2026-01-01'}]},
        ]

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router
        result = await tools.generate_health_report(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )
        assert result.status == 'success'
        assert 'COMPLETED' in result.report


class TestReportFilesystemUsage:
    """Tests for filesystem usage in report."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_filesystem_with_data(self, mock_get_client, tools, ctx):
        """Test report filesystem usage with data."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Commands': []}]
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_ssm.list_commands.return_value = {'Commands': []}

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router
        with (
            patch(
                'awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools._run_ssm_command',
                new_callable=AsyncMock,
                return_value='Filesystem  Size  Used Avail Use% Mounted on\n/dev/xvda   50G   40G   10G  80% /',
            ),
        ):
            result = await tools.generate_health_report(
                ctx,
                application_id='app-1',
                include_config_checks=False,
                include_log_backup_status=True,
                include_aws_backup_status=False,
                include_cloudwatch_metrics=False,
            )
        assert result.status == 'success'
        assert 'Filesystem' in result.report


class TestReportCloudwatchDetails:
    """Tests for CloudWatch details in report."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_cloudwatch_with_cwagent(self, mock_get_client, tools, ctx):
        """Test report CloudWatch with CWAgent metrics."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            },
        )
        mock_cw = MagicMock()
        mem_dims = [{'Name': 'InstanceId', 'Value': 'i-1'}]
        disk_dims = [
            {'Name': 'InstanceId', 'Value': 'i-1'},
            {'Name': 'path', 'Value': '/'},
            {'Name': 'device', 'Value': 'xvda'},
        ]
        net_dims = [{'Name': 'InstanceId', 'Value': 'i-1'}, {'Name': 'interface', 'Value': 'eth0'}]
        mock_cw.list_metrics.side_effect = [
            {'Metrics': [{'Dimensions': mem_dims}]},
            {'Metrics': [{'Dimensions': disk_dims}]},
            {'Metrics': [{'Dimensions': net_dims}]},
            {'Metrics': [{'Dimensions': net_dims}]},
            {'Metrics': [{'Dimensions': disk_dims}]},
        ]
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 45.0, 'Maximum': 80.0}]},
            {'Datapoints': [{'Maximum': 0}]},
            {'Datapoints': [{'Average': 62.5}]},
            {'Datapoints': [{'Average': 41.3}]},
            {'Datapoints': [{'Sum': 1024}]},
            {'Datapoints': [{'Sum': 512}]},
            {'Datapoints': [{'Average': 41.3}]},
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router
        result = await tools.generate_health_report(
            ctx,
            application_id='app-1',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )
        assert result.status == 'success'
        assert 'CloudWatch' in result.report
        assert 'Memory' in result.report or '62.5' in result.report
        assert 'Network' in result.report


class TestGetAppSummaryBackupEdgeCases:
    """Tests for _get_app_summary backup edge cases."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_sap_hana_backup_failed_with_describe(self, mock_get_client, tools, ctx):
        """Test backup with FAILED status triggers describe_backup_job (lines 807-819)."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [
                {
                    'State': 'FAILED',
                    'CreationDate': '2026-03-23T10:00:00Z',
                    'ResourceArn': 'arn:aws:ssm-sap:us-east-1:123:my-hana/HANA',
                    'BackupJobId': 'job-fail-1',
                }
            ]
        }
        mock_backup.describe_backup_job.return_value = {'StatusMessage': 'Disk space insufficient'}

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        bs = result.applications[0].backup_status
        assert len(bs) == 1
        assert 'FAILED' in bs[0].backup_status
        assert bs[0].failure_reason == 'Disk space insufficient'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_backup_sap_query_exception_fallback(self, mock_get_client, tools, ctx):
        """Test backup when SAP HANA query raises exception, falls back to EC2 ARN (lines 842-856)."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        # First call (SAP HANA type) raises exception
        # Second call (EC2 ARN fallback) succeeds
        mock_backup.list_backup_jobs.side_effect = [
            Exception('SAP HANA query failed'),
            {'BackupJobs': [{'State': 'COMPLETED', 'CompletionDate': '2026-03-23'}]},
        ]

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        bs = result.applications[0].backup_status
        assert len(bs) == 1
        assert bs[0].backup_status == 'COMPLETED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_backup_ec2_fallback_failed_with_describe(self, mock_get_client, tools, ctx):
        """Test EC2 ARN fallback with FAILED job and describe_backup_job (lines 863-901)."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        # SAP HANA query returns no matching jobs -> fallback to EC2 ARN
        mock_backup.list_backup_jobs.side_effect = [
            {'BackupJobs': []},  # SAP HANA type - no matching app_id
            {
                'BackupJobs': [
                    {
                        'State': 'FAILED',
                        'CompletionDate': '2026-03-23',
                        'BackupJobId': 'job-ec2-fail',
                    }
                ]
            },
        ]
        mock_backup.describe_backup_job.return_value = {
            'StatusMessage': 'EC2 backup failed reason'
        }

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        bs = result.applications[0].backup_status
        assert len(bs) == 1
        assert bs[0].failure_reason == 'EC2 backup failed reason'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_backup_exception_fallback_ec2_failed(self, mock_get_client, tools, ctx):
        """Test backup outer exception fallback with FAILED EC2 job (lines 933-952)."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        # First call raises exception (outer except catches it)
        # Second call in the except fallback returns EXPIRED job
        mock_backup.list_backup_jobs.side_effect = [
            Exception('Outer exception'),
            {
                'BackupJobs': [
                    {
                        'State': 'EXPIRED',
                        'CompletionDate': '2026-03-20',
                        'BackupJobId': 'job-expired',
                        'StatusMessage': 'Retention expired',
                    }
                ]
            },
        ]

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        bs = result.applications[0].backup_status
        assert len(bs) == 1
        assert 'EXPIRED' in bs[0].backup_status
        assert bs[0].failure_reason == 'Retention expired'


class TestGetAppSummaryLogBackupEdgeCases:
    """Tests for _get_app_summary log backup edge cases."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_log_backup_invocation_detail_exception(self, mock_get_client, tools, ctx):
        """Test log backup when list_command_invocations raises (lines 757-762)."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2.1'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'Commands': [{'CommandId': 'cmd-123', 'InstanceIds': ['i-abc123']}]}
        ]
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_ssm.list_command_invocations.side_effect = Exception('Invocation error')

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=True,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        lb = result.applications[0].log_backup_status
        assert len(lb) == 1
        assert lb[0].ssm_agent_status == 'Online'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_log_backup_paginator_exception(self, mock_get_client, tools, ctx):
        """Test log backup when paginator raises exception (lines 715-716)."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2.1'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = Exception('Paginator error')
        mock_ssm.get_paginator.return_value = mock_paginator

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=True,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        lb = result.applications[0].log_backup_status
        assert len(lb) == 1
        assert lb[0].ssm_agent_status == 'Online'


class TestGetAppSummaryCWAgentExceptions:
    """Tests for CWAgent metric exception paths in _get_app_summary."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_cwagent_mem_exception(self, mock_get_client, tools, ctx):
        """Test CWAgent memory metric exception (lines 590-591)."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_cw = MagicMock()
        # CPU and StatusCheck succeed
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 10.0, 'Maximum': 20.0}]},  # CPU
            {'Datapoints': [{'Maximum': 0}]},  # StatusCheck
            Exception('mem metric fail'),  # mem_used_percent
        ]
        # list_metrics returns dims for mem but get_metric_statistics fails
        mem_dims = [{'Name': 'InstanceId', 'Value': 'i-abc123'}]
        mock_cw.list_metrics.side_effect = [
            {'Metrics': [{'Dimensions': mem_dims}]},  # mem discover
            {'Metrics': []},  # disk discover
            {'Metrics': []},  # net_recv discover
            {'Metrics': []},  # net_sent discover
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )

        assert result.status == 'success'
        cw = result.applications[0].cloudwatch_metrics
        assert len(cw) == 1
        assert cw[0].memory_used_pct is None

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_cwagent_disk_exception(self, mock_get_client, tools, ctx):
        """Test CWAgent disk metric exception (lines 651-652)."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_cw = MagicMock()
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 10.0, 'Maximum': 20.0}]},  # CPU
            {'Datapoints': [{'Maximum': 0}]},  # StatusCheck
        ]
        mock_cw.list_metrics.side_effect = [
            {'Metrics': []},  # mem discover
            Exception('disk discover fail'),  # disk discover raises
            {'Metrics': []},  # net_recv discover
            {'Metrics': []},  # net_sent discover
        ]

        def client_router(service, **kwargs):
            if service == 'cloudwatch':
                return mock_cw
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx,
            application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )

        assert result.status == 'success'
        cw = result.applications[0].cloudwatch_metrics
        assert cw[0].disk_used_pct is None


class TestAppendLogBackupStatusEdgeCases:
    """Additional tests for _append_log_backup_status edge cases."""

    def test_invocation_detail_exception(self):
        """Test log backup when list_command_invocations raises (lines 1492-1533)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'Commands': [{'CommandId': 'cmd-1', 'InstanceIds': ['i-1']}]}
        ]
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_ssm.list_command_invocations.side_effect = Exception('Invocation error')
        lines = []
        _append_log_backup_status(mock_ssm, 'app-1', ['i-1'], lines)
        assert any('Unable to query invocation' in l for l in lines)

    def test_paginator_exception(self):
        """Test log backup when paginator raises (lines 1405-1408)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = Exception('Paginator error')
        mock_ssm.get_paginator.return_value = mock_paginator
        lines = []
        _append_log_backup_status(mock_ssm, 'app-1', ['i-1'], lines)
        assert any('Unable to query' in l for l in lines)

    def test_outer_exception(self):
        """Test log backup outer exception (lines 1343-1344)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_log_backup_status,
        )

        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.side_effect = Exception('Total failure')
        lines = []
        _append_log_backup_status(mock_ssm, 'app-1', ['i-1'], lines)
        # Should still produce output without crashing
        assert any('Unable to query' in l for l in lines)


class TestAppendAwsBackupStatusEdgeCases:
    """Additional tests for _append_aws_backup_status edge cases."""

    def test_sap_hana_failed_job_no_status_message(self):
        """Test SAP HANA FAILED job without StatusMessage triggers describe (lines 1600-1641)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [
                {
                    'State': 'FAILED',
                    'CreationDate': '2026-01-01',
                    'ResourceArn': 'arn:aws:ssm-sap:us-east-1:123:app-1/HANA',
                    'BackupJobId': 'job-1',
                }
            ]
        }
        mock_backup.describe_backup_job.return_value = {'StatusMessage': 'Detailed failure reason'}
        lines = []
        findings = []
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines, findings=findings)
        assert any('FAILED' in l for l in lines)
        assert any('Detailed failure reason' in l for l in lines)
        assert len(findings) == 1

    def test_ec2_fallback_failed_job_with_describe(self):
        """Test EC2 fallback FAILED job triggers describe (lines 1679-1681)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_aws_backup_status,
        )

        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.side_effect = [
            {'BackupJobs': []},  # SAP HANA empty
            {
                'BackupJobs': [
                    {
                        'State': 'ABORTED',
                        'CompletionDate': '2026-01-01',
                        'BackupJobId': 'job-abort',
                    }
                ]
            },
        ]
        mock_backup.describe_backup_job.return_value = {'StatusMessage': 'User aborted'}
        lines = []
        findings = []
        _append_aws_backup_status(mock_backup, 'app-1', ['i-1'], lines, findings=findings)
        assert any('ABORTED' in l for l in lines)
        assert any('User aborted' in l for l in lines)
        assert len(findings) == 1


class TestAppendCloudwatchMetricsEdgeCases:
    """Additional tests for _append_cloudwatch_metrics edge cases."""

    def test_memory_warning_threshold(self):
        """Test memory between 80-90% generates warning (lines 1849-1857)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_cloudwatch_metrics,
        )

        mock_cw = MagicMock()
        mem_dims = [{'Name': 'InstanceId', 'Value': 'i-1'}]
        mock_cw.list_metrics.side_effect = [
            {'Metrics': [{'Dimensions': mem_dims}]},  # mem discover
            {'Metrics': []},  # disk discover
            {'Metrics': []},  # net_recv discover
            {'Metrics': []},  # net_sent discover
        ]
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 50.0, 'Maximum': 60.0}]},  # CPU
            {'Datapoints': [{'Maximum': 0}]},  # StatusCheck
            {'Datapoints': [{'Average': 85.0}]},  # mem (80-90 = warning)
        ]
        lines = []
        findings = []
        _append_cloudwatch_metrics(mock_cw, ['i-1'], lines, findings=findings)
        assert any('Memory usage high' in f.get('rule', '') for f in findings)

    def test_disk_detail_table(self):
        """Test disk detail table with multiple paths (lines 1881-1900)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _append_cloudwatch_metrics,
        )

        mock_cw = MagicMock()
        disk_dims_root = [
            {'Name': 'InstanceId', 'Value': 'i-1'},
            {'Name': 'path', 'Value': '/'},
            {'Name': 'device', 'Value': 'xvda1'},
        ]
        disk_dims_hana = [
            {'Name': 'InstanceId', 'Value': 'i-1'},
            {'Name': 'path', 'Value': '/hana/data'},
            {'Name': 'device', 'Value': 'xvdb'},
        ]
        # list_metrics calls in order:
        # 1. mem discover (empty)
        # 2. disk discover for summary
        # 3. disk discover for detail table
        # 4. net_recv discover (empty)
        # 5. net_sent discover (empty)
        mock_cw.list_metrics.side_effect = [
            {'Metrics': []},  # 1. mem
            {
                'Metrics': [{'Dimensions': disk_dims_root}, {'Dimensions': disk_dims_hana}]
            },  # 2. disk summary
            {
                'Metrics': [{'Dimensions': disk_dims_root}, {'Dimensions': disk_dims_hana}]
            },  # 3. disk detail
            {'Metrics': []},  # 4. net_recv
            {'Metrics': []},  # 5. net_sent
        ]
        # get_metric_statistics calls:
        # 1. CPU
        # 2. StatusCheck
        # 3. disk root summary
        # 4. disk detail root
        # 5. disk detail hana
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 30.0, 'Maximum': 40.0}]},  # CPU
            {'Datapoints': [{'Maximum': 0}]},  # StatusCheck
            {'Datapoints': [{'Average': 45.0}]},  # disk root summary
            {'Datapoints': [{'Average': 45.0}]},  # disk detail root
            {'Datapoints': [{'Average': 70.0}]},  # disk detail hana
        ]
        lines = []
        _append_cloudwatch_metrics(mock_cw, ['i-1'], lines)
        assert any('Disk Usage by Path' in l for l in lines)
        assert any('/hana/data' in l for l in lines)


class TestCheckAppHealthReportEdgeCases:
    """Additional tests for _check_app_health report generation edge cases."""

    async def test_report_with_config_checks_and_findings(self):
        """Test report with config checks that produce findings (lines 1178-1180, 1231, 1249)."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {'Components': []}
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': [
                {
                    'ConfigurationCheckId': 'SAP_CHECK_03',
                    'Status': 'SUCCESS',
                    'RuleStatusCounts': {'Passed': 2, 'Failed': 1, 'Warning': 1},
                    'Id': 'op-1',
                }
            ]
        }
        mock_client.list_sub_check_results.return_value = {
            'SubCheckResults': [
                {
                    'Id': 'sc-1',
                    'Name': 'Pacemaker Config',
                    'Result': 'FAIL',
                    'Description': 'Pacemaker not configured',
                }
            ]
        }
        mock_client.list_sub_check_rule_results.return_value = {
            'RuleResults': [
                {
                    'Id': 'r1',
                    'Description': 'STONITH timeout',
                    'Status': 'FAILED',
                    'Message': 'Timeout too low',
                    'Metadata': {'ActualValue': '150', 'ExpectedValue': '600'},
                },
                {
                    'Id': 'r2',
                    'Description': 'Fencing enabled',
                    'Status': 'WARNING',
                    'Message': 'Check fencing config',
                    'Metadata': {},
                },
            ]
        }
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            None,
            'app-1',
            include_config_checks=True,
            include_subchecks=True,
            include_rule_results=True,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )
        assert 'Pacemaker HA Configuration' in report
        assert 'STONITH timeout' in report
        assert 'Recommended Actions' in report
        assert 'Failures' in report
        assert 'Warnings' in report

    async def test_report_with_log_backup_and_backup(self):
        """Test report with log backup and AWS backup sections."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {'Components': [{'ComponentId': 'node-1'}]}
        mock_client.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            }
        }
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': []
        }
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2'}]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Commands': []}]
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_ssm.list_commands.return_value = {'Commands': []}
        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [
                {
                    'State': 'COMPLETED',
                    'CompletionDate': '2026-03-23',
                    'ResourceArn': 'arn:aws:ssm-sap:us-east-1:123:app-1/HANA',
                    'BackupType': 'CONTINUOUS',
                }
            ]
        }
        report, status, disc = await _check_app_health(
            mock_client,
            mock_ssm,
            mock_backup,
            None,
            'app-1',
            include_config_checks=True,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=True,
            include_aws_backup_status=True,
            include_cloudwatch_metrics=False,
        )
        assert 'Log Backup' in report
        assert 'AWS Backup' in report
        assert 'COMPLETED' in report

    async def test_report_with_cloudwatch_metrics(self):
        """Test report with CloudWatch metrics section."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.tools import (
            _check_app_health,
        )

        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {'Components': [{'ComponentId': 'node-1'}]}
        mock_client.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA_NODE',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-1'}],
            }
        }
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': []
        }
        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {'Metrics': []}
        mock_cw.get_metric_statistics.side_effect = [
            {'Datapoints': [{'Average': 50.0, 'Maximum': 70.0}]},  # CPU
            {'Datapoints': [{'Maximum': 0}]},  # StatusCheck
        ]
        report, status, disc = await _check_app_health(
            mock_client,
            None,
            None,
            mock_cw,
            'app-1',
            include_config_checks=False,
            include_subchecks=False,
            include_rule_results=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=True,
        )
        assert 'CloudWatch' in report
        assert '50.0' in report
