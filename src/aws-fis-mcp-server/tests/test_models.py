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

"""Tests for data models in the AWS FIS MCP server."""

import pytest
from awslabs.aws_fis_mcp_server.models import (
    Action,
    ExperimentActionsMode,
    ExperimentState,
    ExperimentTemplateRequest,
    LogConfiguration,
    ResourceExplorerViewRequest,
    StartExperimentRequest,
    StopCondition,
    Target,
)
from pydantic import ValidationError


class TestExperimentState:
    """Test cases for ExperimentState enum."""

    def test_experiment_state_values(self):
        """Test ExperimentState enum values."""
        assert ExperimentState.PENDING == 'pending'
        assert ExperimentState.INITIATING == 'initiating'
        assert ExperimentState.RUNNING == 'running'
        assert ExperimentState.COMPLETED == 'completed'
        assert ExperimentState.STOPPED == 'stopped'
        assert ExperimentState.FAILED == 'failed'


class TestExperimentActionsMode:
    """Test cases for ExperimentActionsMode enum."""

    def test_experiment_actions_mode_values(self):
        """Test ExperimentActionsMode enum values."""
        assert ExperimentActionsMode.RUN_ALL == 'run-all'


class TestStopCondition:
    """Test cases for StopCondition model."""

    def test_valid_stop_condition(self):
        """Test creating a valid StopCondition."""
        stop_condition = StopCondition(
            source='aws:cloudwatch:alarm',
            value='arn:aws:cloudwatch:us-east-1:123456789012:alarm:test-alarm',
        )
        assert stop_condition.source == 'aws:cloudwatch:alarm'
        assert stop_condition.value == 'arn:aws:cloudwatch:us-east-1:123456789012:alarm:test-alarm'

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            StopCondition()

        with pytest.raises(ValidationError):
            StopCondition(source='aws:cloudwatch:alarm')

        with pytest.raises(ValidationError):
            StopCondition(value='arn:aws:cloudwatch:us-east-1:123456789012:alarm:test-alarm')


class TestTarget:
    """Test cases for Target model."""

    def test_valid_target_minimal(self):
        """Test creating a valid Target with minimal fields."""
        target = Target(resource_type='aws:ec2:instance', selection_mode='ALL')
        assert target.resource_type == 'aws:ec2:instance'
        assert target.selection_mode == 'ALL'
        assert target.resource_arns is None
        assert target.resource_tags is None
        assert target.filters is None
        assert target.parameters is None

    def test_valid_target_with_arns(self):
        """Test creating a valid Target with resource ARNs."""
        arns = ['arn:aws:ec2:us-east-1:123456789012:instance/i-12345678901234567']
        target = Target(
            resource_type='aws:ec2:instance', selection_mode='COUNT(1)', resource_arns=arns
        )
        assert target.resource_type == 'aws:ec2:instance'
        assert target.selection_mode == 'COUNT(1)'
        assert target.resource_arns == arns

    def test_valid_target_with_tags(self):
        """Test creating a valid Target with resource tags."""
        tags = {'Environment': 'Test', 'Name': 'TestInstance'}
        target = Target(resource_type='aws:ec2:instance', selection_mode='ALL', resource_tags=tags)
        assert target.resource_type == 'aws:ec2:instance'
        assert target.selection_mode == 'ALL'
        assert target.resource_tags == tags

    def test_valid_target_with_filters(self):
        """Test creating a valid Target with filters."""
        filters = [{'Path': 'State.Name', 'Values': ['running']}]
        target = Target(resource_type='aws:ec2:instance', selection_mode='ALL', filters=filters)
        assert target.resource_type == 'aws:ec2:instance'
        assert target.selection_mode == 'ALL'
        assert target.filters == filters

    def test_valid_target_with_parameters(self):
        """Test creating a valid Target with parameters."""
        parameters = {'AvailabilityZone': 'us-east-1a'}
        target = Target(
            resource_type='aws:ec2:instance', selection_mode='ALL', parameters=parameters
        )
        assert target.resource_type == 'aws:ec2:instance'
        assert target.selection_mode == 'ALL'
        assert target.parameters == parameters

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            Target()

        with pytest.raises(ValidationError):
            Target(resource_type='aws:ec2:instance')

        with pytest.raises(ValidationError):
            Target(selection_mode='ALL')


class TestAction:
    """Test cases for Action model."""

    def test_valid_action_minimal(self):
        """Test creating a valid Action with minimal fields."""
        action = Action(action_id='aws:ec2:stop-instances')
        assert action.action_id == 'aws:ec2:stop-instances'
        assert action.description is None
        assert action.parameters is None
        assert action.targets is None
        assert action.start_after is None

    def test_valid_action_with_all_fields(self):
        """Test creating a valid Action with all fields."""
        action = Action(
            action_id='aws:ec2:stop-instances',
            description='Stop EC2 instances',
            parameters={'durationSeconds': '300'},
            targets={'Instances': 'my-target'},
            start_after=['action-1', 'action-2'],
        )
        assert action.action_id == 'aws:ec2:stop-instances'
        assert action.description == 'Stop EC2 instances'
        assert action.parameters == {'durationSeconds': '300'}
        assert action.targets == {'Instances': 'my-target'}
        assert action.start_after == ['action-1', 'action-2']

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            Action()


class TestLogConfiguration:
    """Test cases for LogConfiguration model."""

    def test_valid_log_configuration_minimal(self):
        """Test creating a valid LogConfiguration with minimal fields."""
        log_config = LogConfiguration(log_schema_version=1)
        assert log_config.log_schema_version == 1
        assert log_config.cloud_watch_logs_configuration is None
        assert log_config.s3_configuration is None

    def test_valid_log_configuration_with_cloudwatch(self):
        """Test creating a valid LogConfiguration with CloudWatch configuration."""
        cloudwatch_config = {
            'LogGroupArn': 'arn:aws:logs:us-east-1:123456789012:log-group:test-group'
        }
        log_config = LogConfiguration(
            log_schema_version=1, cloud_watch_logs_configuration=cloudwatch_config
        )
        assert log_config.log_schema_version == 1
        assert log_config.cloud_watch_logs_configuration == cloudwatch_config
        assert log_config.s3_configuration is None

    def test_valid_log_configuration_with_s3(self):
        """Test creating a valid LogConfiguration with S3 configuration."""
        s3_config = {'BucketName': 'test-bucket', 'Prefix': 'logs/'}
        log_config = LogConfiguration(log_schema_version=1, s3_configuration=s3_config)
        assert log_config.log_schema_version == 1
        assert log_config.cloud_watch_logs_configuration is None
        assert log_config.s3_configuration == s3_config

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            LogConfiguration()


class TestExperimentTemplateRequest:
    """Test cases for ExperimentTemplateRequest model."""

    def test_valid_experiment_template_request_minimal(self):
        """Test creating a valid ExperimentTemplateRequest with minimal fields."""
        stop_condition = StopCondition(
            source='aws:cloudwatch:alarm',
            value='arn:aws:cloudwatch:us-east-1:123456789012:alarm:test-alarm',
        )
        target = Target(resource_type='aws:ec2:instance', selection_mode='ALL')
        action = Action(action_id='aws:ec2:stop-instances')

        request = ExperimentTemplateRequest(
            client_token='test-token',
            description='Test template',
            stop_conditions=[stop_condition],
            targets={'Instances': target},
            actions={'StopInstances': action},
            role_arn='arn:aws:iam::123456789012:role/FisRole',
        )

        assert request.client_token == 'test-token'
        assert request.description == 'Test template'
        assert len(request.stop_conditions) == 1
        assert request.stop_conditions[0].source == 'aws:cloudwatch:alarm'
        assert 'Instances' in request.targets
        assert 'StopInstances' in request.actions
        assert request.role_arn == 'arn:aws:iam::123456789012:role/FisRole'
        assert request.tags is None
        assert request.log_configuration is None
        assert request.experiment_options is None
        assert request.report_configuration is None

    def test_valid_experiment_template_request_with_all_fields(self):
        """Test creating a valid ExperimentTemplateRequest with all fields."""
        stop_condition = StopCondition(
            source='aws:cloudwatch:alarm',
            value='arn:aws:cloudwatch:us-east-1:123456789012:alarm:test-alarm',
        )
        target = Target(resource_type='aws:ec2:instance', selection_mode='ALL')
        action = Action(action_id='aws:ec2:stop-instances')
        log_config = LogConfiguration(log_schema_version=1)

        request = ExperimentTemplateRequest(
            client_token='test-token',
            description='Test template',
            tags={'Name': 'Test Template', 'Environment': 'Test'},
            stop_conditions=[stop_condition],
            targets={'Instances': target},
            actions={'StopInstances': action},
            role_arn='arn:aws:iam::123456789012:role/FisRole',
            log_configuration=log_config,
            experiment_options={'actionsMode': 'run-all'},
            report_configuration={
                's3Configuration': {'bucketName': 'test-bucket', 'prefix': 'reports/'}
            },
        )

        assert request.client_token == 'test-token'
        assert request.description == 'Test template'
        assert request.tags == {'Name': 'Test Template', 'Environment': 'Test'}
        assert len(request.stop_conditions) == 1
        assert 'Instances' in request.targets
        assert 'StopInstances' in request.actions
        assert request.role_arn == 'arn:aws:iam::123456789012:role/FisRole'
        assert request.log_configuration is not None
        assert request.log_configuration.log_schema_version == 1
        assert request.experiment_options == {'actionsMode': 'run-all'}
        assert request.report_configuration == {
            's3Configuration': {'bucketName': 'test-bucket', 'prefix': 'reports/'}
        }

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            ExperimentTemplateRequest()

        stop_condition = StopCondition(
            source='aws:cloudwatch:alarm',
            value='arn:aws:cloudwatch:us-east-1:123456789012:alarm:test-alarm',
        )
        target = Target(resource_type='aws:ec2:instance', selection_mode='ALL')
        action = Action(action_id='aws:ec2:stop-instances')

        # Missing client_token
        with pytest.raises(ValidationError):
            ExperimentTemplateRequest(
                description='Test template',
                stop_conditions=[stop_condition],
                targets={'Instances': target},
                actions={'StopInstances': action},
                role_arn='arn:aws:iam::123456789012:role/FisRole',
            )

        # Missing description
        with pytest.raises(ValidationError):
            ExperimentTemplateRequest(
                client_token='test-token',
                stop_conditions=[stop_condition],
                targets={'Instances': target},
                actions={'StopInstances': action},
                role_arn='arn:aws:iam::123456789012:role/FisRole',
            )


class TestStartExperimentRequest:
    """Test cases for StartExperimentRequest model."""

    def test_valid_start_experiment_request_minimal(self):
        """Test creating a valid StartExperimentRequest with minimal fields."""
        request = StartExperimentRequest(id='template-1')
        assert request.id == 'template-1'
        assert request.tags is None
        assert request.action == ExperimentActionsMode.RUN_ALL
        assert request.max_timeout_seconds == 3600
        assert request.initial_poll_interval == 5
        assert request.max_poll_interval == 60

    def test_valid_start_experiment_request_with_all_fields(self):
        """Test creating a valid StartExperimentRequest with all fields."""
        request = StartExperimentRequest(
            id='template-1',
            tags={'Environment': 'Test', 'Project': 'Coverage'},
            action=ExperimentActionsMode.RUN_ALL,
            max_timeout_seconds=1800,
            initial_poll_interval=10,
            max_poll_interval=30,
        )
        assert request.id == 'template-1'
        assert request.tags == {'Environment': 'Test', 'Project': 'Coverage'}
        assert request.action == ExperimentActionsMode.RUN_ALL
        assert request.max_timeout_seconds == 1800
        assert request.initial_poll_interval == 10
        assert request.max_poll_interval == 30

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            StartExperimentRequest()


class TestResourceExplorerViewRequest:
    """Test cases for ResourceExplorerViewRequest model."""

    def test_valid_resource_explorer_view_request_minimal(self):
        """Test creating a valid ResourceExplorerViewRequest with minimal fields."""
        request = ResourceExplorerViewRequest(query='service:ec2', view_name='test-view')
        assert request.query == 'service:ec2'
        assert request.view_name == 'test-view'
        assert request.tags is None
        assert request.scope is None
        assert request.client_token is None

    def test_valid_resource_explorer_view_request_with_all_fields(self):
        """Test creating a valid ResourceExplorerViewRequest with all fields."""
        request = ResourceExplorerViewRequest(
            query='service:ec2',
            view_name='test-view',
            tags={'Name': 'Test View', 'Environment': 'Test'},
            scope='arn:aws:iam::123456789012:root',
            client_token='test-token-123',
        )
        assert request.query == 'service:ec2'
        assert request.view_name == 'test-view'
        assert request.tags == {'Name': 'Test View', 'Environment': 'Test'}
        assert request.scope == 'arn:aws:iam::123456789012:root'
        assert request.client_token == 'test-token-123'

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            ResourceExplorerViewRequest()

        with pytest.raises(ValidationError):
            ResourceExplorerViewRequest(query='service:ec2')

        with pytest.raises(ValidationError):
            ResourceExplorerViewRequest(view_name='test-view')
