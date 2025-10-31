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
# ruff: noqa: D101, D102, D103
"""Tests for the models module."""

from awslabs.sagemaker_hyperpod_mcp_server.models import (
    AlarmDetails,
    BatchDeleteClusterNodesError,
    BatchDeleteClusterNodesResponse,
    CapacitySizeConfig,
    ClusterEbsVolumeConfig,
    ClusterInstancePlacement,
    ClusterInstanceStatusDetails,
    ClusterInstanceStorageConfig,
    ClusterLifeCycleConfig,
    ClusterNodeDetails,
    ClusterNodeSummary,
    ClusterSummary,
    DeploymentConfiguration,
    DeployStackResponse,
    DescribeClusterNodeResponse,
    DescribeStackResponse,
    ListClusterNodesResponse,
    ListClustersResponse,
    RollingDeploymentPolicy,
    UpdateClusterSoftwareInstanceGroupSpecification,
    UpdateClusterSoftwareResponse,
    VpcConfig,
)
from mcp.types import TextContent


class TestClusterSummary:
    """Tests for the ClusterSummary model."""

    def test_create_cluster_summary(self):
        """Test creating a ClusterSummary instance."""
        cluster_summary = ClusterSummary(
            cluster_name='test-cluster',
            cluster_arn='arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
            cluster_status='InService',
            creation_time='2023-01-01T00:00:00Z',
            training_plan_arns=[
                'arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan'
            ],
        )

        assert cluster_summary.cluster_name == 'test-cluster'
        assert (
            cluster_summary.cluster_arn
            == 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster'
        )
        assert cluster_summary.cluster_status == 'InService'
        assert cluster_summary.creation_time == '2023-01-01T00:00:00Z'
        assert cluster_summary.training_plan_arns == [
            'arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan'
        ]

    def test_create_cluster_summary_without_optional_fields(self):
        """Test creating a ClusterSummary instance without optional fields."""
        cluster_summary = ClusterSummary(
            cluster_name='test-cluster',
            cluster_arn='arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
            cluster_status='InService',
            creation_time='2023-01-01T00:00:00Z',
        )

        assert cluster_summary.cluster_name == 'test-cluster'
        assert (
            cluster_summary.cluster_arn
            == 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster'
        )
        assert cluster_summary.cluster_status == 'InService'
        assert cluster_summary.creation_time == '2023-01-01T00:00:00Z'
        assert cluster_summary.training_plan_arns is None


class TestClusterInstanceStatusDetails:
    """Tests for the ClusterInstanceStatusDetails model."""

    def test_create_cluster_instance_status_details(self):
        """Test creating a ClusterInstanceStatusDetails instance."""
        status_details = ClusterInstanceStatusDetails(
            status='Running',
            message='Instance is running normally',
        )

        assert status_details.status == 'Running'
        assert status_details.message == 'Instance is running normally'

    def test_create_cluster_instance_status_details_without_optional_fields(self):
        """Test creating a ClusterInstanceStatusDetails instance without optional fields."""
        status_details = ClusterInstanceStatusDetails(
            status='Running',
        )

        assert status_details.status == 'Running'
        assert status_details.message is None


class TestClusterNodeSummary:
    """Tests for the ClusterNodeSummary model."""

    def test_create_cluster_node_summary(self):
        """Test creating a ClusterNodeSummary instance."""
        instance_status = ClusterInstanceStatusDetails(
            status='Running',
            message='Instance is running normally',
        )

        node_summary = ClusterNodeSummary(
            instance_group_name='test-group',
            instance_id='i-1234567890abcdef0',
            instance_status=instance_status,
            instance_type='ml.p4d.24xlarge',
            launch_time='2023-01-01T00:00:00Z',
            last_software_update_time='2023-01-02T00:00:00Z',
        )

        assert node_summary.instance_group_name == 'test-group'
        assert node_summary.instance_id == 'i-1234567890abcdef0'
        assert node_summary.instance_status == instance_status
        assert node_summary.instance_type == 'ml.p4d.24xlarge'
        assert node_summary.launch_time == '2023-01-01T00:00:00Z'
        assert node_summary.last_software_update_time == '2023-01-02T00:00:00Z'

    def test_create_cluster_node_summary_without_optional_fields(self):
        """Test creating a ClusterNodeSummary instance without optional fields."""
        instance_status = ClusterInstanceStatusDetails(
            status='Running',
        )

        node_summary = ClusterNodeSummary(
            instance_group_name='test-group',
            instance_id='i-1234567890abcdef0',
            instance_status=instance_status,
            instance_type='ml.p4d.24xlarge',
            launch_time='2023-01-01T00:00:00Z',
        )

        assert node_summary.instance_group_name == 'test-group'
        assert node_summary.instance_id == 'i-1234567890abcdef0'
        assert node_summary.instance_status == instance_status
        assert node_summary.instance_type == 'ml.p4d.24xlarge'
        assert node_summary.launch_time == '2023-01-01T00:00:00Z'
        assert node_summary.last_software_update_time is None


class TestListClustersResponse:
    """Tests for the ListClustersResponse model."""

    def test_create_list_clusters_response(self):
        """Test creating a ListClustersResponse instance."""
        cluster_summary = ClusterSummary(
            cluster_name='test-cluster',
            cluster_arn='arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
            cluster_status='InService',
            creation_time='2023-01-01T00:00:00Z',
        )

        response = ListClustersResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully listed clusters')],
            clusters=[cluster_summary],
            next_token='next-token',
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully listed clusters'
        assert len(response.clusters) == 1
        assert response.clusters[0] == cluster_summary
        assert response.next_token == 'next-token'

    def test_create_list_clusters_response_without_optional_fields(self):
        """Test creating a ListClustersResponse instance without optional fields."""
        cluster_summary = ClusterSummary(
            cluster_name='test-cluster',
            cluster_arn='arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
            cluster_status='InService',
            creation_time='2023-01-01T00:00:00Z',
        )

        response = ListClustersResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully listed clusters')],
            clusters=[cluster_summary],
            next_token=None,
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully listed clusters'
        assert len(response.clusters) == 1
        assert response.clusters[0] == cluster_summary
        assert response.next_token is None


class TestListClusterNodesResponse:
    """Tests for the ListClusterNodesResponse model."""

    def test_create_list_cluster_nodes_response(self):
        """Test creating a ListClusterNodesResponse instance."""
        instance_status = ClusterInstanceStatusDetails(
            status='Running',
        )

        node_summary = ClusterNodeSummary(
            instance_group_name='test-group',
            instance_id='i-1234567890abcdef0',
            instance_status=instance_status,
            instance_type='ml.p4d.24xlarge',
            launch_time='2023-01-01T00:00:00Z',
        )

        response = ListClusterNodesResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully listed cluster nodes')],
            nodes=[node_summary],
            next_token='next-token',
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully listed cluster nodes'
        assert len(response.nodes) == 1
        assert response.nodes[0] == node_summary
        assert response.next_token == 'next-token'

    def test_create_list_cluster_nodes_response_without_optional_fields(self):
        """Test creating a ListClusterNodesResponse instance without optional fields."""
        instance_status = ClusterInstanceStatusDetails(
            status='Running',
        )

        node_summary = ClusterNodeSummary(
            instance_group_name='test-group',
            instance_id='i-1234567890abcdef0',
            instance_status=instance_status,
            instance_type='ml.p4d.24xlarge',
            launch_time='2023-01-01T00:00:00Z',
        )

        response = ListClusterNodesResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully listed cluster nodes')],
            nodes=[node_summary],
            next_token=None,
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully listed cluster nodes'
        assert len(response.nodes) == 1
        assert response.nodes[0] == node_summary
        assert response.next_token is None


class TestClusterEbsVolumeConfig:
    """Tests for the ClusterEbsVolumeConfig model."""

    def test_create_cluster_ebs_volume_config(self):
        """Test creating a ClusterEbsVolumeConfig instance."""
        ebs_volume_config = ClusterEbsVolumeConfig(
            volume_size_in_gb=100,
        )

        assert ebs_volume_config.volume_size_in_gb == 100

    def test_create_cluster_ebs_volume_config_without_optional_fields(self):
        """Test creating a ClusterEbsVolumeConfig instance without optional fields."""
        ebs_volume_config = ClusterEbsVolumeConfig()

        assert ebs_volume_config.volume_size_in_gb is None


class TestClusterInstanceStorageConfig:
    """Tests for the ClusterInstanceStorageConfig model."""

    def test_create_cluster_instance_storage_config(self):
        """Test creating a ClusterInstanceStorageConfig instance."""
        ebs_volume_config = ClusterEbsVolumeConfig(
            volume_size_in_gb=100,
        )

        storage_config = ClusterInstanceStorageConfig(
            ebs_volume_config=ebs_volume_config,
        )

        assert storage_config.ebs_volume_config == ebs_volume_config

    def test_create_cluster_instance_storage_config_without_optional_fields(self):
        """Test creating a ClusterInstanceStorageConfig instance without optional fields."""
        storage_config = ClusterInstanceStorageConfig()

        assert storage_config.ebs_volume_config is None


class TestClusterLifeCycleConfig:
    """Tests for the ClusterLifeCycleConfig model."""

    def test_create_cluster_life_cycle_config(self):
        """Test creating a ClusterLifeCycleConfig instance."""
        life_cycle_config = ClusterLifeCycleConfig(
            on_create="echo 'Hello, World!'",
            source_s3_uri='s3://bucket/path/to/script.sh',
        )

        assert life_cycle_config.on_create == "echo 'Hello, World!'"
        assert life_cycle_config.source_s3_uri == 's3://bucket/path/to/script.sh'


class TestVpcConfig:
    """Tests for the VpcConfig model."""

    def test_create_vpc_config(self):
        """Test creating a VpcConfig instance."""
        vpc_config = VpcConfig(
            security_group_ids=['sg-1234567890abcdef0'],
            subnets=['subnet-1234567890abcdef0'],
        )

        assert vpc_config.security_group_ids == ['sg-1234567890abcdef0']
        assert vpc_config.subnets == ['subnet-1234567890abcdef0']

    def test_create_vpc_config_without_optional_fields(self):
        """Test creating a VpcConfig instance without optional fields."""
        vpc_config = VpcConfig()

        assert vpc_config.security_group_ids is None
        assert vpc_config.subnets is None


class TestClusterInstancePlacement:
    """Tests for the ClusterInstancePlacement model."""

    def test_create_cluster_instance_placement(self):
        """Test creating a ClusterInstancePlacement instance."""
        placement = ClusterInstancePlacement(
            availability_zone='us-west-2a',
            availability_zone_id='usw2-az1',
        )

        assert placement.availability_zone == 'us-west-2a'
        assert placement.availability_zone_id == 'usw2-az1'

    def test_create_cluster_instance_placement_without_optional_fields(self):
        """Test creating a ClusterInstancePlacement instance without optional fields."""
        placement = ClusterInstancePlacement()

        assert placement.availability_zone is None
        assert placement.availability_zone_id is None


class TestAlarmDetails:
    """Tests for the AlarmDetails model."""

    def test_create_alarm_details(self):
        """Test creating an AlarmDetails instance."""
        alarm_details = AlarmDetails(
            alarm_name='test-alarm',
        )

        assert alarm_details.alarm_name == 'test-alarm'


class TestCapacitySizeConfig:
    """Tests for the CapacitySizeConfig model."""

    def test_create_capacity_size_config(self):
        """Test creating a CapacitySizeConfig instance."""
        capacity_size_config = CapacitySizeConfig(
            type='INSTANCE_COUNT',
            value=5,
        )

        assert capacity_size_config.type == 'INSTANCE_COUNT'
        assert capacity_size_config.value == 5


class TestRollingDeploymentPolicy:
    """Tests for the RollingDeploymentPolicy model."""

    def test_create_rolling_deployment_policy(self):
        """Test creating a RollingDeploymentPolicy instance."""
        maximum_batch_size = CapacitySizeConfig(
            type='INSTANCE_COUNT',
            value=5,
        )

        rollback_maximum_batch_size = CapacitySizeConfig(
            type='CAPACITY_PERCENTAGE',
            value=20,
        )

        policy = RollingDeploymentPolicy(
            maximum_batch_size=maximum_batch_size,
            rollback_maximum_batch_size=rollback_maximum_batch_size,
        )

        assert policy.maximum_batch_size == maximum_batch_size
        assert policy.rollback_maximum_batch_size == rollback_maximum_batch_size

    def test_create_rolling_deployment_policy_without_optional_fields(self):
        """Test creating a RollingDeploymentPolicy instance without optional fields."""
        maximum_batch_size = CapacitySizeConfig(
            type='INSTANCE_COUNT',
            value=5,
        )

        policy = RollingDeploymentPolicy(
            maximum_batch_size=maximum_batch_size,
        )

        assert policy.maximum_batch_size == maximum_batch_size
        assert policy.rollback_maximum_batch_size is None


class TestDeploymentConfiguration:
    """Tests for the DeploymentConfiguration model."""

    def test_create_deployment_configuration(self):
        """Test creating a DeploymentConfiguration instance."""
        alarm_details = AlarmDetails(
            alarm_name='test-alarm',
        )

        maximum_batch_size = CapacitySizeConfig(
            type='INSTANCE_COUNT',
            value=5,
        )

        rolling_update_policy = RollingDeploymentPolicy(
            maximum_batch_size=maximum_batch_size,
        )

        deployment_config = DeploymentConfiguration(
            auto_rollback_configuration=[alarm_details],
            rolling_update_policy=rolling_update_policy,
            wait_interval_in_seconds=60,
        )

        assert deployment_config.auto_rollback_configuration == [alarm_details]
        assert deployment_config.rolling_update_policy == rolling_update_policy
        assert deployment_config.wait_interval_in_seconds == 60

    def test_create_deployment_configuration_without_optional_fields(self):
        """Test creating a DeploymentConfiguration instance without optional fields."""
        deployment_config = DeploymentConfiguration()

        assert deployment_config.auto_rollback_configuration is None
        assert deployment_config.rolling_update_policy is None
        assert deployment_config.wait_interval_in_seconds is None


class TestUpdateClusterSoftwareInstanceGroupSpecification:
    """Tests for the UpdateClusterSoftwareInstanceGroupSpecification model."""

    def test_create_update_cluster_software_instance_group_specification(self):
        """Test creating an UpdateClusterSoftwareInstanceGroupSpecification instance."""
        spec = UpdateClusterSoftwareInstanceGroupSpecification(
            instance_group_name='test-group',
        )

        assert spec.instance_group_name == 'test-group'


class TestClusterNodeDetails:
    """Tests for the ClusterNodeDetails model."""

    def test_create_cluster_node_details(self):
        """Test creating a ClusterNodeDetails instance."""
        instance_status = ClusterInstanceStatusDetails(
            status='Running',
            message='Instance is running normally',
        )

        ebs_volume_config = ClusterEbsVolumeConfig(
            volume_size_in_gb=100,
        )

        storage_config = ClusterInstanceStorageConfig(
            ebs_volume_config=ebs_volume_config,
        )

        life_cycle_config = ClusterLifeCycleConfig(
            on_create="echo 'Hello, World!'",
            source_s3_uri='s3://bucket/path/to/script.sh',
        )

        vpc_config = VpcConfig(
            security_group_ids=['sg-1234567890abcdef0'],
            subnets=['subnet-1234567890abcdef0'],
        )

        placement = ClusterInstancePlacement(
            availability_zone='us-west-2a',
            availability_zone_id='usw2-az1',
        )

        node_details = ClusterNodeDetails(
            instance_group_name='test-group',
            instance_id='i-1234567890abcdef0',
            instance_status=instance_status,
            instance_storage_configs=[storage_config],
            instance_type='ml.p4d.24xlarge',
            last_software_update_time='2023-01-02T00:00:00Z',
            launch_time='2023-01-01T00:00:00Z',
            life_cycle_config=life_cycle_config,
            override_vpc_config=vpc_config,
            placement=placement,
            private_dns_hostname='ip-10-0-0-1.us-west-2.compute.internal',
            private_primary_ip='10.0.0.1',
            private_primary_ipv6='2001:db8::1',
            threads_per_core=2,
        )

        assert node_details.instance_group_name == 'test-group'
        assert node_details.instance_id == 'i-1234567890abcdef0'
        assert node_details.instance_status == instance_status
        assert node_details.instance_storage_configs == [storage_config]
        assert node_details.instance_type == 'ml.p4d.24xlarge'
        assert node_details.last_software_update_time == '2023-01-02T00:00:00Z'
        assert node_details.launch_time == '2023-01-01T00:00:00Z'
        assert node_details.life_cycle_config == life_cycle_config
        assert node_details.override_vpc_config == vpc_config
        assert node_details.placement == placement
        assert node_details.private_dns_hostname == 'ip-10-0-0-1.us-west-2.compute.internal'
        assert node_details.private_primary_ip == '10.0.0.1'
        assert node_details.private_primary_ipv6 == '2001:db8::1'
        assert node_details.threads_per_core == 2

    def test_create_cluster_node_details_without_optional_fields(self):
        """Test creating a ClusterNodeDetails instance without optional fields."""
        instance_status = ClusterInstanceStatusDetails(
            status='Running',
        )

        node_details = ClusterNodeDetails(
            instance_group_name='test-group',
            instance_id='i-1234567890abcdef0',
            instance_status=instance_status,
            instance_type='ml.p4d.24xlarge',
        )

        assert node_details.instance_group_name == 'test-group'
        assert node_details.instance_id == 'i-1234567890abcdef0'
        assert node_details.instance_status == instance_status
        assert node_details.instance_type == 'ml.p4d.24xlarge'
        assert node_details.instance_storage_configs is None
        assert node_details.last_software_update_time is None
        assert node_details.launch_time is None
        assert node_details.life_cycle_config is None
        assert node_details.override_vpc_config is None
        assert node_details.placement is None
        assert node_details.private_dns_hostname is None
        assert node_details.private_primary_ip is None
        assert node_details.private_primary_ipv6 is None
        assert node_details.threads_per_core is None


class TestDescribeClusterNodeResponse:
    """Tests for the DescribeClusterNodeResponse model."""

    def test_create_describe_cluster_node_response(self):
        """Test creating a DescribeClusterNodeResponse instance."""
        instance_status = ClusterInstanceStatusDetails(
            status='Running',
        )

        node_details = ClusterNodeDetails(
            instance_group_name='test-group',
            instance_id='i-1234567890abcdef0',
            instance_status=instance_status,
            instance_type='ml.p4d.24xlarge',
        )

        response = DescribeClusterNodeResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully described cluster node')],
            node_details=node_details,
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully described cluster node'
        assert response.node_details == node_details

    def test_create_describe_cluster_node_response_without_optional_fields(self):
        """Test creating a DescribeClusterNodeResponse instance without optional fields."""
        response = DescribeClusterNodeResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully described cluster node')],
            node_details=None,
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully described cluster node'
        assert response.node_details is None


class TestUpdateClusterSoftwareResponse:
    """Tests for the UpdateClusterSoftwareResponse model."""

    def test_create_update_cluster_software_response(self):
        """Test creating an UpdateClusterSoftwareResponse instance."""
        response = UpdateClusterSoftwareResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully updated cluster software')],
            cluster_arn='arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully updated cluster software'
        assert (
            response.cluster_arn == 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster'
        )


class TestBatchDeleteClusterNodesError:
    """Tests for the BatchDeleteClusterNodesError model."""

    def test_create_batch_delete_cluster_nodes_error(self):
        """Test creating a BatchDeleteClusterNodesError instance."""
        error = BatchDeleteClusterNodesError(
            code='ValidationException',
            message='Node not found',
            node_id='i-1234567890abcdef0',
        )

        assert error.code == 'ValidationException'
        assert error.message == 'Node not found'
        assert error.node_id == 'i-1234567890abcdef0'


class TestBatchDeleteClusterNodesResponse:
    """Tests for the BatchDeleteClusterNodesResponse model."""

    def test_create_batch_delete_cluster_nodes_response(self):
        """Test creating a BatchDeleteClusterNodesResponse instance."""
        error = BatchDeleteClusterNodesError(
            code='ValidationException',
            message='Node not found',
            node_id='i-1234567890abcdef0',
        )

        response = BatchDeleteClusterNodesResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully deleted cluster nodes')],
            cluster_name='test-cluster',
            successful=['i-0987654321fedcba0'],
            failed=[error],
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully deleted cluster nodes'
        assert response.cluster_name == 'test-cluster'
        assert response.successful == ['i-0987654321fedcba0']
        assert response.failed == [error]

    def test_create_batch_delete_cluster_nodes_response_without_optional_fields(self):
        """Test creating a BatchDeleteClusterNodesResponse instance without optional fields."""
        response = BatchDeleteClusterNodesResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully deleted cluster nodes')],
            cluster_name='test-cluster',
            successful=['i-0987654321fedcba0'],
            failed=None,
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully deleted cluster nodes'
        assert response.cluster_name == 'test-cluster'
        assert response.successful == ['i-0987654321fedcba0']
        assert response.failed is None


class TestDeployStackResponse:
    """Tests for the DeployStackResponse model."""

    def test_create_deploy_stack_response(self):
        """Test creating a DeployStackResponse instance."""
        response = DeployStackResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully deployed stack')],
            stack_name='test-stack',
            stack_arn='arn:aws:cloudformation:us-west-2:123456789012:stack/test-stack/1234567890abcdef',
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully deployed stack'
        assert response.stack_name == 'test-stack'
        assert (
            response.stack_arn
            == 'arn:aws:cloudformation:us-west-2:123456789012:stack/test-stack/1234567890abcdef'
        )


class TestDescribeStackResponse:
    """Tests for the DescribeStackResponse model."""

    def test_create_describe_stack_response(self):
        """Test creating a DescribeStackResponse instance."""
        response = DescribeStackResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully described stack')],
            stack_name='test-stack',
            stack_id='arn:aws:cloudformation:us-west-2:123456789012:stack/test-stack/1234567890abcdef',
            creation_time='2023-01-01T00:00:00Z',
            stack_status='CREATE_COMPLETE',
            outputs={
                'ClusterName': 'test-cluster',
                'ClusterArn': 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
            },
        )

        assert response.isError is False
        assert len(response.content) == 1
