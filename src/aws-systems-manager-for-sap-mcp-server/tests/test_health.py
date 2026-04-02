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
    from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
        SSMSAPHealthTools,
    )

    return SSMSAPHealthTools()


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    return MagicMock()


def _make_ssm_sap_client(apps=None, app_detail=None, components=None, component_detail=None,
                          config_check_ops=None, sub_check_results=None, rule_results=None,
                          config_check_definitions=None):
    """Build a mock ssm-sap client with configurable responses."""
    mock = MagicMock()

    if apps is not None:
        mock.list_applications.return_value = {'Applications': apps}
    else:
        mock.list_applications.return_value = {'Applications': []}

    if app_detail is not None:
        mock.get_application.return_value = {'Application': app_detail}
    else:
        mock.get_application.return_value = {'Application': {
            'Id': 'test-app', 'Type': 'HANA', 'Status': 'ACTIVATED',
            'DiscoveryStatus': 'SUCCESS',
        }}

    if components is not None:
        mock.list_components.return_value = {'Components': components}
    else:
        mock.list_components.return_value = {'Components': []}

    if component_detail is not None:
        mock.get_component.return_value = {'Component': component_detail}
    else:
        mock.get_component.return_value = {'Component': {
            'ComponentType': 'HANA', 'Status': 'ACTIVATED', 'Sid': 'HDB', 'Hosts': [],
        }}

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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_single_healthy_app(self, mock_get_client, tools, ctx):
        """Test health summary for a single healthy application."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_multiple_apps_mixed_status(self, mock_get_client, tools, ctx):
        """Test health summary with multiple apps in different states."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {
            'Applications': [{'Id': 'app-healthy'}, {'Id': 'app-failed'}]
        }
        mock_sap.get_application.side_effect = [
            {'Application': {'Id': 'app-healthy', 'Type': 'HANA', 'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS'}},
            {'Application': {'Id': 'app-failed', 'Type': 'SAP_ABAP', 'Status': 'FAILED', 'DiscoveryStatus': 'REFRESH_FAILED'}},
        ]
        mock_sap.list_components.return_value = {'Components': []}
        mock_sap.list_configuration_check_operations.return_value = {'ConfigurationCheckOperations': []}
        mock_sap.list_configuration_check_definitions.return_value = {'ConfigurationChecks': [{'Id': 'SAP_CHECK_01'}]}
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_components(self, mock_get_client, tools, ctx):
        """Test health summary includes component details."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
                'Hosts': [{'HostName': 'host1', 'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_config_checks(self, mock_get_client, tools, ctx):
        """Test health summary includes configuration check results."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
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
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_config_checks_include_subchecks_by_severity(self, mock_get_client, tools, ctx):
        """Test health summary includes subcheck details grouped by severity."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
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
                {'Id': 'sc-1', 'Name': 'HA Config', 'Result': 'Failed', 'Description': 'HA not configured'},
                {'Id': 'sc-2', 'Name': 'Backup Config', 'Result': 'Warning', 'Description': 'Backup interval too long'},
                {'Id': 'sc-3', 'Name': 'Memory Config', 'Result': 'Passed', 'Description': 'Memory allocation OK'},
            ],
            rule_results=[
                {'Id': 'rule-1', 'Description': 'Fencing check', 'Status': 'FAILED', 'Message': 'Fencing not configured'},
                {'Id': 'rule-2', 'Description': 'Stonith enabled', 'Status': 'PASSED', 'Message': None},
            ],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_config_checks_no_subchecks_when_disabled(self, mock_get_client, tools, ctx):
        """Test health summary omits subchecks when include_subchecks=False."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
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
                {'Id': 'sc-1', 'Name': 'HA Config', 'Result': 'Failed', 'Description': 'HA not configured'},
            ],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
            include_subchecks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        check = result.applications[0].config_checks[0]
        assert len(check.subchecks) == 0

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_auto_triggers_config_checks_when_stale(self, mock_get_client, tools, ctx):
        """Test that config checks are auto-triggered when no recent results exist."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
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
                {'Id': 'op-new-1', 'ConfigurationCheckId': 'SAP_CHECK_01', 'Status': 'IN_PROGRESS'},
            ],
        }
        mock_get_client.return_value = mock_sap

        with patch(
            'awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools._wait_for_config_checks',
            new_callable=AsyncMock,
        ) as mock_wait:
            result = await tools.get_sap_health_summary(
                ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_auto_trigger_falls_back_to_previous_when_still_in_progress(self, mock_get_client, tools, ctx):
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
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
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
            'awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools._wait_for_config_checks',
            new_callable=AsyncMock,
        ):
            result = await tools.get_sap_health_summary(
                ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_no_auto_trigger_when_recent(self, mock_get_client, tools, ctx):
        """Test that config checks are NOT auto-triggered when recent results exist."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
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
            ctx, application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        mock_sap.start_configuration_checks.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_auto_trigger_disabled(self, mock_get_client, tools, ctx):
        """Test that auto-trigger can be disabled."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
            auto_trigger_config_checks=False,
        )

        assert result.status == 'success'
        mock_sap.start_configuration_checks.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_cloudwatch_metrics(self, mock_get_client, tools, ctx):
        """Test health summary includes CloudWatch metrics."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
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
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_log_backup_status(self, mock_get_client, tools, ctx):
        """Test health summary includes log backup status."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_ssm = MagicMock()
        mock_ssm.describe_instance_information.return_value = {
            'InstanceInformationList': [{'PingStatus': 'Online', 'AgentVersion': '3.2.1'}]
        }
        mock_paginator_empty = MagicMock()
        mock_paginator_empty.paginate.return_value = [{"Commands": []}]
        mock_ssm.get_paginator.return_value = mock_paginator_empty

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_aws_backup_status(self, mock_get_client, tools, ctx):
        """Test health summary includes AWS Backup status."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
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
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_client_creation_error(self, mock_get_client, tools, ctx):
        """Test health summary handles client creation errors."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        result = await tools.get_sap_health_summary(ctx, application_id='my-hana')

        assert result.status == 'error'
        assert 'Invalid credentials' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_profile_and_region_passed_through(self, mock_get_client, tools, ctx):
        """Test that profile_name and region are passed to client factory."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_get_client.return_value = mock_sap

        await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
            region='eu-west-1', profile_name='sap-prod',
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        mock_get_client.assert_called_with(
            'ssm-sap', region_name='eu-west-1', profile_name='sap-prod'
        )

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_no_config_checks_when_disabled(self, mock_get_client, tools, ctx):
        """Test that config checks are skipped when disabled."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_single_healthy_app(self, mock_get_client, tools, ctx):
        """Test health report for a single healthy application."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_components(self, mock_get_client, tools, ctx):
        """Test health report includes component details."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
                'Hosts': [{'HostName': 'host1', 'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx, application_id='my-hana',
            include_config_checks=False,
            include_log_backup_status=False,
            include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert 'i-abc123' in result.report
        assert 'HANA' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_config_checks(self, mock_get_client, tools, ctx):
        """Test health report includes configuration check results."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[
                {'ConfigurationCheckId': 'SAP_CHECK_01', 'Status': 'COMPLETED', 'RuleStatusCounts': {'Passed': 3}, 'Id': 'op-1'},
                {'ConfigurationCheckId': 'SAP_CHECK_02', 'Status': 'COMPLETED', 'RuleStatusCounts': {'Warning': 1}, 'Id': 'op-2'},
            ],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx, application_id='my-hana',
            include_subchecks=False, include_rule_results=False,
            include_log_backup_status=False, include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert 'EC2 Instance Type Selection' in result.report
        assert 'Storage Configuration' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_subchecks_and_rules(self, mock_get_client, tools, ctx):
        """Test health report includes subchecks and rule results."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            config_check_ops=[{
                'ConfigurationCheckId': 'SAP_CHECK_01', 'Status': 'COMPLETED',
                'RuleStatusCounts': {'Passed': 3}, 'Id': 'op-1',
            }],
            sub_check_results=[{
                'Id': 'sc-1', 'Name': 'SubCheck A', 'Result': 'PASS', 'Description': 'Checks something',
            }],
            rule_results=[{'Id': 'rule-1', 'Description': 'Rule 1', 'Status': 'PASS'}],
        )
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx, application_id='my-hana',
            include_log_backup_status=False, include_aws_backup_status=False,
            include_cloudwatch_metrics=False,
        )

        assert result.status == 'success'
        assert 'SubCheck A' in result.report
        assert 'Rule 1' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_with_cloudwatch_metrics(self, mock_get_client, tools, ctx):
        """Test health report includes CloudWatch metrics."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
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
            ctx, application_id='my-hana',
            include_config_checks=False, include_log_backup_status=False,
            include_aws_backup_status=False, include_cloudwatch_metrics=True,
        )

        assert result.status == 'success'
        assert 'CloudWatch' in result.report
        assert 'i-abc123' in result.report
        assert '45.2' in result.report

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_client_creation_error(self, mock_get_client, tools, ctx):
        """Test health report handles client creation errors."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        result = await tools.generate_health_report(ctx, application_id='my-hana')

        assert result.status == 'error'
        assert 'Invalid credentials' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_app_retrieval_error(self, mock_get_client, tools, ctx):
        """Test health report handles per-app errors gracefully."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {'Applications': [{'Id': 'broken-app'}]}
        mock_sap.get_application.side_effect = Exception('Access denied')
        mock_sap.list_components.return_value = {'Components': []}
        mock_sap.list_configuration_check_operations.return_value = {'ConfigurationCheckOperations': []}
        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx,
            include_log_backup_status=False, include_aws_backup_status=False,
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
            _extract_ec2_ids,
        )
        ids = _extract_ec2_ids({})
        assert ids == []

    def test_instance_id_fallback(self):
        """Test InstanceId fallback when EC2InstanceId is missing."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_hana_node_associated_host(self, mock_get_client, tools, ctx):
        """Test that HANA_NODE components with AssociatedHost get EC2 IDs extracted."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-node-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
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
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_component_with_hana_details(self, mock_get_client, tools, ctx):
        """Test that HANA component details (version, replication) are captured."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
                'HdbVersion': '2.00.070',
                'ReplicationMode': 'PRIMARY',
                'OperationMode': 'logreplay',
            },
        )
        mock_get_client.return_value = mock_sap

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_log_backup_with_command_history(self, mock_get_client, tools, ctx):
        """Test log backup status includes SSM command invocation results."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
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
            {'Commands': [{'CommandId': 'cmd-123', 'DocumentName': 'AWSSystemsManagerSAP-HanaLogBackupStatusCheck', 'InstanceIds': ['i-abc123']}]}
        ]
        mock_ssm.get_paginator.return_value = mock_paginator
        # Mock list_command_invocations with Details for PerformAction step
        mock_ssm.list_command_invocations.return_value = {
            'CommandInvocations': [{
                'Status': 'Success',
                'CommandPlugins': [
                    {'Name': 'InstallPackage', 'Status': 'Success', 'Output': 'installed'},
                    {'Name': 'InstallPackageAgain', 'Status': 'Success', 'Output': 'installed'},
                    {'Name': 'PerformAction', 'Status': 'Success', 'Output': 'pip output\n{"executionStatus": "Success", "data": {"is_log_backups_enabled": true}}'},
                ],
            }]
        }

        def client_router(service, **kwargs):
            if service == 'ssm':
                return mock_ssm
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_log_backup_no_command_history(self, mock_get_client, tools, ctx):
        """Test log backup status when no SSM command history exists."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
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
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_sap_hana_backup_type_query(self, mock_get_client, tools, ctx):
        """Test that backup queries SAP HANA on Amazon EC2 resource type."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        mock_backup.list_backup_jobs.return_value = {
            'BackupJobs': [{
                'State': 'COMPLETED',
                'CompletionDate': '2026-03-23T10:00:00Z',
                'ResourceArn': 'arn:aws:ssm-sap:us-east-1:123456789:my-hana/HANA/i-abc123',
            }]
        }

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_backup_fallback_to_ec2_arn(self, mock_get_client, tools, ctx):
        """Test backup falls back to EC2 ARN query when no SAP HANA jobs match."""
        mock_sap = _make_ssm_sap_client(
            app_detail={
                'Id': 'my-hana', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            },
            components=[{'ComponentId': 'hana-db-1'}],
            component_detail={
                'ComponentType': 'HANA_NODE', 'Status': 'ACTIVATED', 'Sid': 'HDB',
                'Hosts': [{'EC2InstanceId': 'i-abc123'}],
            },
        )
        mock_backup = MagicMock()
        # First call (SAP HANA type) returns no matching jobs
        # Second call (EC2 ARN fallback) returns a job
        mock_backup.list_backup_jobs.side_effect = [
            {'BackupJobs': []},  # SAP HANA type query - empty
            {'BackupJobs': [{'State': 'COMPLETED', 'CompletionDate': '2026-03-23T10:00:00Z'}]},  # EC2 ARN fallback
        ]

        def client_router(service, **kwargs):
            if service == 'backup':
                return mock_backup
            return mock_sap

        mock_get_client.side_effect = client_router

        result = await tools.get_sap_health_summary(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_cwagent_metrics_included(self, mock_get_client, tools, ctx):
        """Test that CWAgent metrics are collected alongside EC2 metrics."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {
            'Applications': [{'Id': 'my-hana'}]
        }
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {
            'Components': [{'ComponentId': 'HDB-00'}]
        }
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
        mem_dims = [{'Name': 'InstanceId', 'Value': 'i-abc123'}, {'Name': 'CustomComponentName', 'Value': 'HANA-HDB-00'}]
        disk_dims = [{'Name': 'InstanceId', 'Value': 'i-abc123'}, {'Name': 'CustomComponentName', 'Value': 'HANA-HDB-00'}, {'Name': 'path', 'Value': '/'}, {'Name': 'device', 'Value': 'xvda1'}, {'Name': 'fstype', 'Value': 'xfs'}]
        net_dims = [{'Name': 'InstanceId', 'Value': 'i-abc123'}, {'Name': 'interface', 'Value': 'eth0'}]
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
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_cwagent_metrics_unavailable(self, mock_get_client, tools, ctx):
        """Test graceful handling when CWAgent metrics are not available."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {
            'Applications': [{'Id': 'my-hana'}]
        }
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {
            'Components': [{'ComponentId': 'HDB-00'}]
        }
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
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_filesystem_usage_found(self, mock_get_client, tools, ctx):
        """Test filesystem usage data is collected from SSM command history."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {
            'Applications': [{'Id': 'my-hana'}]
        }
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {
            'Components': [{'ComponentId': 'HDB-00'}]
        }
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
            'Commands': [{
                'CommandId': 'cmd-fs123',
                'Parameters': {'commands': ['df -h /usr/sap']},
            }]
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
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_filesystem_usage_not_managed(self, mock_get_client, tools, ctx):
        """Test filesystem usage when instance is not managed by SSM."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {
            'Applications': [{'Id': 'my-hana'}]
        }
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {
            'Components': [{'ComponentId': 'HDB-00'}]
        }
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
            ctx, application_id='my-hana',
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
            _format_bytes,
        )
        assert _format_bytes(500) == '500 B'

    def test_kilobytes(self):
        """Test formatting of kilobyte values."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
            _format_bytes,
        )
        assert _format_bytes(2048) == '2.0 KB'

    def test_megabytes(self):
        """Test formatting of megabyte values."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
            _format_bytes,
        )
        assert _format_bytes(1048576) == '1.0 MB'

    def test_gigabytes(self):
        """Test formatting of gigabyte values."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools import (
            _format_bytes,
        )
        assert _format_bytes(1073741824) == '1.00 GB'


class TestListOperationsFallback:
    """Tests for list_operations fallback when OperationId is missing from config checks."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_report_config_checks_with_fallback(self, mock_get_client, tools, ctx):
        """Test that generate_health_report uses list_operations fallback."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {
            'Applications': [{'Id': 'my-hana'}]
        }
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {'Components': []}
        # Config check ops without OperationId
        mock_sap.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': [{
                'ConfigurationCheckId': 'CHECK_01',
                'Status': 'SUCCESS',
                'Result': 'PASS',
                'LastUpdatedTime': '2026-03-23T10:00:00Z',
                # No OperationId!
            }]
        }
        # list_operations fallback
        mock_sap.list_operations.return_value = {
            'Operations': [{
                'Type': 'CONFIGURATION_CHECK',
                'Id': 'op-fallback-123',
            }]
        }
        mock_sap.list_sub_check_results.return_value = {
            'SubCheckResults': [{
                'Name': 'SubCheck1',
                'Result': 'PASS',
                'Description': 'All good',
                'Id': 'sc-1',
            }]
        }
        mock_sap.list_sub_check_rule_results.return_value = {'RuleResults': []}

        mock_get_client.return_value = mock_sap

        result = await tools.generate_health_report(
            ctx, application_id='my-hana',
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
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_health.tools.get_aws_client')
    async def test_cluster_status_populated(self, mock_get_client, tools, ctx):
        """Test that cluster_status is extracted from Resilience.ClusterStatus."""
        mock_sap = MagicMock()
        mock_sap.list_applications.return_value = {
            'Applications': [{'Id': 'my-hana'}]
        }
        mock_sap.get_application.return_value = {
            'Application': {'Status': 'ACTIVATED', 'DiscoveryStatus': 'SUCCESS', 'Type': 'HANA'}
        }
        mock_sap.list_components.return_value = {
            'Components': [{'ComponentId': 'HDB-00-node1'}]
        }
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
            ctx, application_id='my-hana',
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
