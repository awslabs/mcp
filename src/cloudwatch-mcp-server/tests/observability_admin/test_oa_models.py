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

"""Tests for Observability Admin models."""

from awslabs.cloudwatch_mcp_server.observability_admin.models import (
    DestinationConfiguration,
    GetTelemetryRuleResponse,
    ListResourceTelemetryResponse,
    TelemetryConfiguration,
    TelemetryEvaluationStatusResponse,
    TelemetryRuleDetail,
    TelemetryRuleSummary,
)


class TestTelemetryEvaluationStatusResponse:
    """Tests for TelemetryEvaluationStatusResponse model."""

    def test_basic_creation(self):
        """Test test_basic_creation."""
        resp = TelemetryEvaluationStatusResponse(status='RUNNING')
        assert resp.status == 'RUNNING'
        assert resp.failure_reason is None

    def test_with_failure_reason(self):
        """Test test_with_failure_reason."""
        resp = TelemetryEvaluationStatusResponse(
            status='FAILED_START', failure_reason='Insufficient permissions'
        )
        assert resp.status == 'FAILED_START'
        assert resp.failure_reason == 'Insufficient permissions'


class TestTelemetryConfiguration:
    """Tests for TelemetryConfiguration model."""

    def test_basic_creation(self):
        """Test test_basic_creation."""
        config = TelemetryConfiguration(
            account_identifier='123456789012',
            resource_type='AWS::EC2::Instance',
            resource_identifier='i-0e979d278b040f856',
            telemetry_configuration_state={'Logs': 'Enabled', 'Metrics': 'Disabled'},
        )
        assert config.account_identifier == '123456789012'
        assert config.resource_type == 'AWS::EC2::Instance'
        assert config.telemetry_configuration_state['Logs'] == 'Enabled'
        assert config.resource_tags == {}
        assert config.last_update_timestamp is None
        assert config.telemetry_source_type is None

    def test_with_all_fields(self):
        """Test test_with_all_fields."""
        config = TelemetryConfiguration(
            account_identifier='123456789012',
            resource_type='AWS::EC2::VPC',
            resource_identifier='vpc-abc123',
            telemetry_configuration_state={'Logs': 'Enabled'},
            resource_tags={'Environment': 'Production'},
            last_update_timestamp=1700000000,
            telemetry_source_type='VPC_FLOW_LOGS',
        )
        assert config.resource_tags == {'Environment': 'Production'}
        assert config.last_update_timestamp == 1700000000
        assert config.telemetry_source_type == 'VPC_FLOW_LOGS'


class TestListResourceTelemetryResponse:
    """Tests for ListResourceTelemetryResponse model."""

    def test_empty_response(self):
        """Test test_empty_response."""
        resp = ListResourceTelemetryResponse()
        assert resp.telemetry_configurations == []
        assert resp.has_more_results is False
        assert resp.message is None

    def test_with_configurations(self):
        """Test test_with_configurations."""
        config = TelemetryConfiguration(
            account_identifier='123456789012',
            resource_type='AWS::Lambda::Function',
            resource_identifier='my-function',
            telemetry_configuration_state={'Traces': 'Enabled'},
        )
        resp = ListResourceTelemetryResponse(
            telemetry_configurations=[config],
            has_more_results=True,
            message='Showing 1 resources (more available)',
        )
        assert len(resp.telemetry_configurations) == 1
        assert resp.has_more_results is True


class TestTelemetryRuleSummary:
    """Tests for TelemetryRuleSummary model."""

    def test_basic_creation(self):
        """Test test_basic_creation."""
        summary = TelemetryRuleSummary(
            rule_name='vpc-flow-logs-rule',
            rule_arn='arn:aws:observabilityadmin:us-east-1:123456789012:rule/vpc-flow-logs-rule',
            resource_type='AWS::EC2::VPC',
            telemetry_type='Logs',
        )
        assert summary.rule_name == 'vpc-flow-logs-rule'
        assert summary.telemetry_source_types == []
        assert summary.created_timestamp is None

    def test_with_source_types(self):
        """Test test_with_source_types."""
        summary = TelemetryRuleSummary(
            rule_name='eks-rule',
            rule_arn='arn:aws:observabilityadmin:us-east-1:123456789012:rule/eks-rule',
            resource_type='AWS::EKS::Cluster',
            telemetry_type='Logs',
            telemetry_source_types=['EKS_AUDIT_LOGS', 'EKS_CONTROL_PLANE_LOGS'],
            created_timestamp=1700000000,
        )
        assert len(summary.telemetry_source_types) == 2


class TestDestinationConfiguration:
    """Tests for DestinationConfiguration model."""

    def test_basic_creation(self):
        """Test test_basic_creation."""
        dest = DestinationConfiguration()
        assert dest.destination_type is None
        assert dest.destination_pattern is None
        assert dest.retention_in_days is None

    def test_with_all_fields(self):
        """Test test_with_all_fields."""
        dest = DestinationConfiguration(
            destination_type='cloud-watch-logs',
            destination_pattern='/aws/telemetry/<resourceId>',
            retention_in_days=30,
            vpc_flow_log_parameters={'TrafficType': 'ALL', 'MaxAggregationInterval': 60},
            cloudtrail_parameters={'AdvancedEventSelectors': []},
            elb_load_balancer_logging_parameters={'OutputFormat': 'json'},
            waf_logging_parameters={'LogType': 'WAF_LOGS'},
            log_delivery_parameters={'LogTypes': ['APPLICATION_LOGS']},
        )
        assert dest.destination_type == 'cloud-watch-logs'
        assert dest.retention_in_days == 30
        assert dest.vpc_flow_log_parameters is not None
        assert dest.vpc_flow_log_parameters['TrafficType'] == 'ALL'
        assert dest.log_delivery_parameters is not None
        assert dest.log_delivery_parameters['LogTypes'] == ['APPLICATION_LOGS']


class TestTelemetryRuleDetail:
    """Tests for TelemetryRuleDetail model."""

    def test_basic_creation(self):
        """Test test_basic_creation."""
        detail = TelemetryRuleDetail(
            resource_type='AWS::EC2::VPC',
            telemetry_type='Logs',
        )
        assert detail.resource_type == 'AWS::EC2::VPC'
        assert detail.telemetry_source_types == []
        assert detail.destination_configuration is None
        assert detail.scope is None
        assert detail.selection_criteria is None

    def test_with_vpc_flow_log_params(self):
        """Test test_with_vpc_flow_log_params."""
        detail = TelemetryRuleDetail(
            resource_type='AWS::EC2::VPC',
            telemetry_type='Logs',
            telemetry_source_types=['VPC_FLOW_LOGS'],
            destination_configuration=DestinationConfiguration(
                destination_type='cloud-watch-logs',
                vpc_flow_log_parameters={'TrafficType': 'ALL', 'MaxAggregationInterval': 60},
            ),
            scope='ACCOUNT',
            selection_criteria='ALL',
        )
        assert detail.destination_configuration is not None
        assert detail.destination_configuration.vpc_flow_log_parameters is not None
        assert detail.destination_configuration.vpc_flow_log_parameters['TrafficType'] == 'ALL'
        assert detail.destination_configuration.destination_type == 'cloud-watch-logs'
        assert detail.scope == 'ACCOUNT'


class TestGetTelemetryRuleResponse:
    """Tests for GetTelemetryRuleResponse model."""

    def test_basic_creation(self):
        """Test test_basic_creation."""
        resp = GetTelemetryRuleResponse(
            rule_name='test-rule',
            rule_arn='arn:aws:observabilityadmin:us-east-1:123456789012:rule/test-rule',
        )
        assert resp.rule_name == 'test-rule'
        assert resp.telemetry_rule is None

    def test_with_full_rule(self):
        """Test test_with_full_rule."""
        resp = GetTelemetryRuleResponse(
            rule_name='test-rule',
            rule_arn='arn:aws:observabilityadmin:us-east-1:123456789012:rule/test-rule',
            created_timestamp=1700000000,
            last_update_timestamp=1700001000,
            telemetry_rule=TelemetryRuleDetail(
                resource_type='AWS::EC2::VPC',
                telemetry_type='Logs',
                scope='ORGANIZATION',
                selection_criteria='ALL',
            ),
        )
        assert resp.telemetry_rule is not None
        assert resp.telemetry_rule.scope == 'ORGANIZATION'
