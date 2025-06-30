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

"""Tests for EMREc2ClusterHandler."""

import pytest
from awslabs.dataprocessing_mcp_server.handlers.emr.emr_ec2_cluster_handler import EMREc2ClusterHandler
from awslabs.dataprocessing_mcp_server.models.emr_models import CreateClusterResponse, DescribeClusterResponse
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch('awslabs.dataprocessing_mcp_server.handlers.emr.emr_ec2_cluster_handler.AwsHelper') as mock:
        mock.create_boto3_client.return_value = MagicMock()
        mock.prepare_resource_tags.return_value = {'MCP:Managed': 'true', 'MCP:ResourceType': 'EMRCluster'}
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a mock EMREc2ClusterHandler instance for testing."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    return EMREc2ClusterHandler(mcp, allow_write=True, allow_sensitive_data_access=True)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return MagicMock(spec=Context)


@pytest.mark.asyncio
async def test_create_cluster_success(handler, mock_context):
    """Test successful creation of an EMR cluster."""
    handler.emr_client = MagicMock()
    handler.emr_client.run_job_flow.return_value = {
        "JobFlowId": "j-1234567890ABCDEF0",
        "ClusterArn": "arn:aws:elasticmapreduce:us-west-2:123456789012:cluster/j-1234567890ABCDEF0"
    }

    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-cluster",
        name="TestCluster",
        release_label="emr-7.9.0",
        instances={
            "InstanceGroups": [
                {
                    "Name": "Master",
                    "InstanceRole": "MASTER",
                    "InstanceType": "m5.xlarge",
                    "InstanceCount": 1
                },
                {
                    "Name": "Core",
                    "InstanceRole": "CORE",
                    "InstanceType": "m5.xlarge",
                    "InstanceCount": 2
                }
            ],
            "Ec2KeyName": "my-key-pair",
            "KeepJobFlowAliveWhenNoSteps": True
        },
        service_role="EMR_EC2_DefaultRole",
        job_flow_role="EMR_EC2_DefaultRole"
    )

    assert not response.isError
    assert response.cluster_id == "j-1234567890ABCDEF0"
    handler.emr_client.run_job_flow.assert_called_once()


@pytest.mark.asyncio
async def test_create_cluster_missing_name(handler, mock_context):
    """Test that creating a cluster fails when name is missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        name=None,
        operation="create-cluster",
        release_label="emr-7.9.0",
        instances={
            "InstanceGroups": [
                {
                    "Name": "Master",
                    "InstanceRole": "MASTER",
                    "InstanceType": "m5.xlarge",
                    "InstanceCount": 1
                }
            ]
        }
    )
    
    assert response.isError is True
    assert "name, release_label, and instances are required for create-cluster operation" in response.content[0].text


@pytest.mark.asyncio
async def test_create_cluster_missing_release_label(handler, mock_context):
    """Test that creating a cluster fails when release_label is missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        release_label=None,
        operation="create-cluster",
        name="TestCluster",
        instances={
            "InstanceGroups": [
                {
                    "Name": "Master",
                    "InstanceRole": "MASTER",
                    "InstanceType": "m5.xlarge",
                    "InstanceCount": 1
                }
            ]
        }
    )
    
    assert response.isError is True
    assert "name, release_label, and instances are required for create-cluster operation" in response.content[0].text


@pytest.mark.asyncio
async def test_create_cluster_missing_instances(handler, mock_context):
    """Test that creating a cluster fails when instances is missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        instances=None,
        operation="create-cluster",
        name="TestCluster",
        release_label="emr-7.9.0"
    )
    
    assert response.isError is True
    assert "name, release_label, and instances are required for create-cluster operation" in response.content[0].text


@pytest.mark.asyncio
async def test_create_cluster_error(handler, mock_context):
    """Test error handling during cluster creation."""
    handler.emr_client = MagicMock()
    handler.emr_client.run_job_flow.side_effect = Exception("Test exception")

    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-cluster",
        name="TestCluster",
        release_label="emr-7.9.0",
        instances={
            "InstanceGroups": [
                {
                    "Name": "Master",
                    "InstanceRole": "MASTER",
                    "InstanceType": "m5.xlarge",
                    "InstanceCount": 1
                }
            ]
        }
    )

    assert response.isError
    assert "Error in manage_aws_emr_clusters: Test exception" in response.content[0].text


@pytest.mark.asyncio
async def test_describe_cluster_success(handler, mock_context):
    """Test successful description of an EMR cluster."""
    handler.emr_client = MagicMock()
    handler.emr_client.describe_cluster.return_value = {
        "Cluster": {
            "Id": "j-1234567890ABCDEF0",
            "Name": "TestCluster",
            "Status": {"State": "RUNNING"}
        }
    }

    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="describe-cluster",
        cluster_id="j-1234567890ABCDEF0"
    )

    assert not response.isError
    assert response.cluster["Id"] == "j-1234567890ABCDEF0"
    assert response.cluster["Name"] == "TestCluster"
    handler.emr_client.describe_cluster.assert_called_once_with(ClusterId="j-1234567890ABCDEF0")


@pytest.mark.asyncio
async def test_describe_cluster_missing_id(handler, mock_context):
    """Test that describing a cluster fails when cluster_id is missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        cluster_id=None,
        operation="describe-cluster"
    )
    
    assert response.isError is True
    assert "cluster_id is required for describe-cluster operation" in response.content[0].text


# Write access restriction tests
@pytest.mark.asyncio
async def test_create_cluster_no_write_access(mock_aws_helper, mock_context):
    """Test that creating a cluster fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMREc2ClusterHandler(mcp, allow_write=False)
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-cluster",
        name="TestCluster",
        release_label="emr-7.9.0",
        instances={"InstanceGroups": []}
    )
    
    assert response.isError
    assert "Operation create-cluster is not allowed without write access" in response.content[0].text


@pytest.mark.asyncio
async def test_terminate_clusters_no_write_access(mock_aws_helper, mock_context):
    """Test that terminating clusters fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMREc2ClusterHandler(mcp, allow_write=False)
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="terminate-clusters",
        cluster_ids=["j-1234567890ABCDEF0"]
    )
    
    assert response.isError
    assert "Operation terminate-clusters is not allowed without write access" in response.content[0].text


# AWS permission and client error tests
@pytest.mark.asyncio
async def test_describe_cluster_aws_error(handler, mock_context):
    """Test AWS client error handling for describe cluster."""
    from botocore.exceptions import ClientError
    
    handler.emr_client = MagicMock()
    handler.emr_client.describe_cluster.side_effect = ClientError(
        {"Error": {"Code": "ClusterNotFound", "Message": "Cluster not found"}},
        "DescribeCluster"
    )
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="describe-cluster",
        cluster_id="j-nonexistent"
    )
    
    assert response.isError
    assert "Error in manage_aws_emr_clusters:" in response.content[0].text


@pytest.mark.asyncio
async def test_create_cluster_access_denied(handler, mock_context):
    """Test AWS access denied error during cluster creation."""
    from botocore.exceptions import ClientError
    
    handler.emr_client = MagicMock()
    handler.emr_client.run_job_flow.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "RunJobFlow"
    )
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-cluster",
        name="TestCluster",
        release_label="emr-7.9.0",
        instances={"InstanceGroups": []}
    )
    
    assert response.isError
    assert "Error in manage_aws_emr_clusters:" in response.content[0].text


# List clusters tests
@pytest.mark.asyncio
async def test_list_clusters_success(handler, mock_context):
    """Test successful listing of EMR clusters."""
    from awslabs.dataprocessing_mcp_server.models.emr_models import ListClustersResponse
    
    handler.emr_client = MagicMock()
    handler.emr_client.list_clusters.return_value = {
        "Clusters": [
            {"Id": "j-1234567890ABCDEF0", "Name": "Cluster1", "Status": {"State": "RUNNING"}},
            {"Id": "j-0987654321FEDCBA0", "Name": "Cluster2", "Status": {"State": "TERMINATED"}}
        ],
        "Marker": "next-page-token"
    }
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="list-clusters",
        cluster_states=["RUNNING", "TERMINATED"]
    )
    
    assert isinstance(response, ListClustersResponse)
    assert not response.isError
    assert response.count == 2
    assert response.marker == "next-page-token"
    # Verify the call was made and check the important parameter
    handler.emr_client.list_clusters.assert_called_once()
    call_args = handler.emr_client.list_clusters.call_args[1]
    assert call_args["ClusterStates"] == ["RUNNING", "TERMINATED"]


# Terminate clusters tests
@pytest.mark.asyncio
async def test_terminate_clusters_success(handler, mock_context):
    """Test successful termination of MCP-managed clusters."""
    from awslabs.dataprocessing_mcp_server.models.emr_models import TerminateClustersResponse
    
    handler.emr_client = MagicMock()
    handler.emr_client.describe_cluster.return_value = {
        "Cluster": {
            "Tags": [
                {"Key": "ManagedBy", "Value": "DataprocessingMcpServer"},
                {"Key": "ResourceType", "Value": "EMRCluster"}
            ]
        }
    }
    handler.emr_client.terminate_job_flows.return_value = {}
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="terminate-clusters",
        cluster_ids=["j-1234567890ABCDEF0"]
    )
    
    assert isinstance(response, TerminateClustersResponse)
    assert not response.isError
    assert response.cluster_ids == ["j-1234567890ABCDEF0"]
    handler.emr_client.terminate_job_flows.assert_called_once_with(JobFlowIds=["j-1234567890ABCDEF0"])


@pytest.mark.asyncio
async def test_terminate_clusters_unmanaged(handler, mock_context):
    """Test that terminating unmanaged clusters fails."""
    handler.emr_client = MagicMock()
    handler.emr_client.describe_cluster.return_value = {
        "Cluster": {"Tags": [{"Key": "Other", "Value": "tag"}]}
    }
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="terminate-clusters",
        cluster_ids=["j-1234567890ABCDEF0"]
    )
    
    assert response.isError
    assert "Cannot terminate clusters" in response.content[0].text
    assert "not managed by the MCP server" in response.content[0].text


@pytest.mark.asyncio
async def test_terminate_clusters_missing_ids(handler, mock_context):
    """Test that terminating clusters fails when cluster_ids is missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="terminate-clusters",
        cluster_ids=None
    )
    
    assert response.isError
    assert "cluster_ids is required for terminate-clusters operation" in response.content[0].text


# Modify cluster tests
@pytest.mark.asyncio
async def test_modify_cluster_success(handler, mock_context):
    """Test successful modification of cluster step concurrency."""
    from awslabs.dataprocessing_mcp_server.models.emr_models import ModifyClusterResponse
    
    handler.emr_client = MagicMock()
    handler.emr_client.modify_cluster.return_value = {"StepConcurrencyLevel": 5}
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster",
        cluster_id="j-1234567890ABCDEF0",
        step_concurrency_level=5
    )
    
    assert isinstance(response, ModifyClusterResponse)
    assert not response.isError
    assert response.cluster_id == "j-1234567890ABCDEF0"
    assert response.step_concurrency_level == 5


@pytest.mark.asyncio
async def test_modify_cluster_missing_params(handler, mock_context):
    """Test that modifying cluster fails when required parameters are missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster",
        cluster_id=None
    )
    
    assert response.isError
    assert "cluster_id is required for modify-cluster operation" in response.content[0].text


# Modify cluster attributes tests
@pytest.mark.asyncio
async def test_modify_cluster_attributes_success(handler, mock_context):
    """Test successful modification of cluster attributes."""
    from awslabs.dataprocessing_mcp_server.models.emr_models import ModifyClusterAttributesResponse
    
    handler.emr_client = MagicMock()
    handler.emr_client.set_termination_protection.return_value = {}
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster-attributes",
        cluster_id="j-1234567890ABCDEF0",
        termination_protected=True
    )
    
    assert isinstance(response, ModifyClusterAttributesResponse)
    assert not response.isError
    assert response.cluster_id == "j-1234567890ABCDEF0"


@pytest.mark.asyncio
async def test_modify_cluster_attributes_missing_params(handler, mock_context):
    """Test that modifying cluster attributes fails when no attributes are provided."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster-attributes",
        cluster_id="j-1234567890ABCDEF0",
        auto_terminate=None,
        termination_protected=None
    )
    
    assert response.isError
    assert "At least one of auto_terminate or termination_protected must be provided" in response.content[0].text


# Security configuration tests
@pytest.mark.asyncio
async def test_create_security_configuration_success(handler, mock_context):
    """Test successful creation of security configuration."""
    from awslabs.dataprocessing_mcp_server.models.emr_models import CreateSecurityConfigurationResponse
    import datetime
    
    handler.emr_client = MagicMock()
    handler.emr_client.create_security_configuration.return_value = {
        "Name": "test-config",
        "CreationDateTime": datetime.datetime(2023, 1, 1)
    }
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-security-configuration",
        security_configuration_name="test-config",
        security_configuration_json={"EncryptionConfiguration": {}}
    )
    
    assert isinstance(response, CreateSecurityConfigurationResponse)
    assert not response.isError
    assert response.name == "test-config"


@pytest.mark.asyncio
async def test_create_security_configuration_missing_params(handler, mock_context):
    """Test that creating security configuration fails when parameters are missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-security-configuration",
        security_configuration_name=None
    )
    
    assert response.isError
    assert "security_configuration_name and security_configuration_json are required" in response.content[0].text


# Invalid operation test
@pytest.mark.asyncio
async def test_invalid_operation(handler, mock_context):
    """Test handling of invalid operation."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="invalid-operation"
    )
    
    assert response.isError
    assert "Invalid operation: invalid-operation" in response.content[0].text


# Test with optional parameters
@pytest.mark.asyncio
async def test_create_cluster_with_optional_params(handler, mock_context):
    """Test creating cluster with optional parameters."""
    handler.emr_client = MagicMock()
    handler.emr_client.run_job_flow.return_value = {"JobFlowId": "j-1234567890ABCDEF0"}
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-cluster",
        name="TestCluster",
        release_label="emr-7.9.0",
        instances={"InstanceGroups": []},
        applications=[{"Name": "Spark"}, {"Name": "Hadoop"}],
        log_uri="s3://my-bucket/logs/",
        visible_to_all_users=False,
        bootstrap_actions=[{"Name": "setup", "ScriptBootstrapAction": {"Path": "s3://bucket/script.sh"}}]
    )
    
    assert not response.isError
    # Verify that optional parameters were passed to the AWS call
    call_args = handler.emr_client.run_job_flow.call_args[1]
    assert call_args["Applications"] == [{"Name": "Spark"}, {"Name": "Hadoop"}]
    assert call_args["LogUri"] == "s3://my-bucket/logs/"
    assert call_args["VisibleToAllUsers"] is False

# Additional test cases for better coverage

# Test _create_error_response method for different operations
@pytest.mark.asyncio
async def test_create_error_response_coverage(handler, mock_context):
    """Test _create_error_response for different operation types."""
    # Test modify-cluster-attributes error response
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster-attributes",
        cluster_id=None
    )
    assert response.isError
    assert "cluster_id is required" in response.content[0].text

# Test modify cluster with missing step_concurrency_level
@pytest.mark.asyncio
async def test_modify_cluster_missing_step_concurrency(handler, mock_context):
    """Test modify cluster fails when step_concurrency_level is missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster",
        cluster_id="j-1234567890ABCDEF0",
        step_concurrency_level=None
    )
    
    assert response.isError
    assert "step_concurrency_level is required for modify-cluster operation" in response.content[0].text

# Test modify cluster attributes with both parameters
@pytest.mark.asyncio
async def test_modify_cluster_attributes_both_params(handler, mock_context):
    """Test modifying cluster attributes with both auto_terminate and termination_protected."""
    handler.emr_client = MagicMock()
    handler.emr_client.set_termination_protection.return_value = {}
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster-attributes",
        cluster_id="j-1234567890ABCDEF0",
        auto_terminate=True,
        termination_protected=False
    )
    
    assert not response.isError
    # Should be called twice - once for auto_terminate, once for termination_protected
    assert handler.emr_client.set_termination_protection.call_count == 2

# Test terminate clusters with exception during describe
@pytest.mark.asyncio
async def test_terminate_clusters_describe_exception(handler, mock_context):
    """Test terminate clusters when describe_cluster raises exception."""
    handler.emr_client = MagicMock()
    handler.emr_client.describe_cluster.side_effect = Exception("Cluster not found")
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="terminate-clusters",
        cluster_ids=["j-nonexistent"]
    )
    
    assert response.isError
    assert "Cannot terminate clusters" in response.content[0].text

# Test list clusters with all optional parameters
@pytest.mark.asyncio
async def test_list_clusters_with_all_params(handler, mock_context):
    """Test list clusters with all optional parameters."""
    handler.emr_client = MagicMock()
    handler.emr_client.list_clusters.return_value = {
        "Clusters": [],
        "Marker": None
    }
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="list-clusters",
        cluster_states=["RUNNING"],
        created_after="2023-01-01",
        created_before="2023-12-31",
        marker="test-marker"
    )
    
    assert not response.isError
    call_args = handler.emr_client.list_clusters.call_args[1]
    assert call_args["ClusterStates"] == ["RUNNING"]
    assert call_args["CreatedAfter"] == "2023-01-01"
    assert call_args["CreatedBefore"] == "2023-12-31"
    assert call_args["Marker"] == "test-marker"

# Test delete security configuration
@pytest.mark.asyncio
async def test_delete_security_configuration_success(handler, mock_context):
    """Test successful deletion of security configuration."""
    from awslabs.dataprocessing_mcp_server.models.emr_models import DeleteSecurityConfigurationResponse
    
    handler.emr_client = MagicMock()
    handler.emr_client.delete_security_configuration.return_value = {}
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="delete-security-configuration",
        security_configuration_name="test-config"
    )
    
    assert isinstance(response, DeleteSecurityConfigurationResponse)
    assert not response.isError
    assert response.name == "test-config"

@pytest.mark.asyncio
async def test_delete_security_configuration_missing_name(handler, mock_context):
    """Test delete security configuration fails when name is missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="delete-security-configuration",
        security_configuration_name=None
    )
    
    assert response.isError
    assert "security_configuration_name is required" in response.content[0].text

# Test describe security configuration
@pytest.mark.asyncio
async def test_describe_security_configuration_success(handler, mock_context):
    """Test successful description of security configuration."""
    from awslabs.dataprocessing_mcp_server.models.emr_models import DescribeSecurityConfigurationResponse
    import datetime
    
    handler.emr_client = MagicMock()
    handler.emr_client.describe_security_configuration.return_value = {
        "Name": "test-config",
        "SecurityConfiguration": '{"EncryptionConfiguration": {}}',
        "CreationDateTime": datetime.datetime(2023, 1, 1)
    }
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="describe-security-configuration",
        security_configuration_name="test-config"
    )
    
    assert isinstance(response, DescribeSecurityConfigurationResponse)
    assert not response.isError
    assert response.name == "test-config"
    assert response.security_configuration == '{"EncryptionConfiguration": {}}'

@pytest.mark.asyncio
async def test_describe_security_configuration_missing_name(handler, mock_context):
    """Test describe security configuration fails when name is missing."""
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="describe-security-configuration",
        security_configuration_name=None
    )
    
    assert response.isError
    assert "security_configuration_name is required" in response.content[0].text

# Test list security configurations
@pytest.mark.asyncio
async def test_list_security_configurations_success(handler, mock_context):
    """Test successful listing of security configurations."""
    from awslabs.dataprocessing_mcp_server.models.emr_models import ListSecurityConfigurationsResponse
    
    handler.emr_client = MagicMock()
    handler.emr_client.list_security_configurations.return_value = {
        "SecurityConfigurations": [
            {"Name": "config1", "CreationDateTime": "2023-01-01"},
            {"Name": "config2", "CreationDateTime": "2023-01-02"}
        ],
        "Marker": "next-token"
    }
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="list-security-configurations",
        marker="test-marker"
    )
    
    assert isinstance(response, ListSecurityConfigurationsResponse)
    assert not response.isError
    assert response.count == 2
    assert response.marker == "next-token"

# Test create cluster with all optional parameters
@pytest.mark.asyncio
async def test_create_cluster_all_optional_params(handler, mock_context):
    """Test creating cluster with all optional parameters."""
    handler.emr_client = MagicMock()
    handler.emr_client.run_job_flow.return_value = {"JobFlowId": "j-1234567890ABCDEF0"}
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-cluster",
        name="TestCluster",
        release_label="emr-7.9.0",
        instances={"InstanceGroups": []},
        log_encryption_kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        steps=[{"Name": "test-step"}],
        configurations=[{"Classification": "spark"}],
        service_role="EMR_DefaultRole",
        job_flow_role="EMR_EC2_DefaultRole",
        security_configuration="test-security-config",
        auto_scaling_role="EMR_AutoScaling_DefaultRole",
        scale_down_behavior="TERMINATE_AT_TASK_COMPLETION",
        custom_ami_id="ami-12345678",
        ebs_root_volume_size=20,
        ebs_root_volume_iops=3000,
        ebs_root_volume_throughput=125,
        repo_upgrade_on_boot="SECURITY",
        kerberos_attributes={"Realm": "EC2.INTERNAL"},
        unhealthy_node_replacement=True,
        os_release_label="2.0.20220606.1",
        placement_groups=[{"InstanceRole": "MASTER", "PlacementStrategy": "SPREAD"}]
    )
    
    assert not response.isError
    call_args = handler.emr_client.run_job_flow.call_args[1]
    assert call_args["LogEncryptionKmsKeyId"] == "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    assert call_args["Steps"] == [{"Name": "test-step"}]
    assert call_args["Configurations"] == [{"Classification": "spark"}]
    assert call_args["ServiceRole"] == "EMR_DefaultRole"
    assert call_args["JobFlowRole"] == "EMR_EC2_DefaultRole"
    assert call_args["SecurityConfiguration"] == "test-security-config"
    assert call_args["AutoScalingRole"] == "EMR_AutoScaling_DefaultRole"
    assert call_args["ScaleDownBehavior"] == "TERMINATE_AT_TASK_COMPLETION"
    assert call_args["CustomAmiId"] == "ami-12345678"
    assert call_args["EbsRootVolumeSize"] == 20
    assert call_args["EbsRootVolumeIops"] == 3000
    assert call_args["EbsRootVolumeThroughput"] == 125
    assert call_args["RepoUpgradeOnBoot"] == "SECURITY"
    assert call_args["KerberosAttributes"] == {"Realm": "EC2.INTERNAL"}
    assert call_args["UnhealthyNodeReplacement"] is True
    assert call_args["OSReleaseLabel"] == "2.0.20220606.1"
    assert call_args["PlacementGroups"] == [{"InstanceRole": "MASTER", "PlacementStrategy": "SPREAD"}]

# Test create security configuration with string CreationDateTime
@pytest.mark.asyncio
async def test_create_security_configuration_string_datetime(handler, mock_context):
    """Test create security configuration with string CreationDateTime."""
    handler.emr_client = MagicMock()
    handler.emr_client.create_security_configuration.return_value = {
        "Name": "test-config",
        "CreationDateTime": "2023-01-01T00:00:00Z"  # String instead of datetime object
    }
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-security-configuration",
        security_configuration_name="test-config",
        security_configuration_json={"EncryptionConfiguration": {}}
    )
    
    assert not response.isError
    assert response.creation_date_time == "2023-01-01T00:00:00Z"

# Test describe security configuration with string CreationDateTime
@pytest.mark.asyncio
async def test_describe_security_configuration_string_datetime(handler, mock_context):
    """Test describe security configuration with string CreationDateTime."""
    handler.emr_client = MagicMock()
    handler.emr_client.describe_security_configuration.return_value = {
        "Name": "test-config",
        "SecurityConfiguration": "{}",
        "CreationDateTime": "2023-01-01T00:00:00Z"  # String instead of datetime object
    }
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="describe-security-configuration",
        security_configuration_name="test-config"
    )
    
    assert not response.isError
    assert response.creation_date_time == "2023-01-01T00:00:00Z"

# Test write access restrictions for all write operations
@pytest.mark.asyncio
async def test_modify_cluster_no_write_access(mock_aws_helper, mock_context):
    """Test that modifying cluster fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMREc2ClusterHandler(mcp, allow_write=False)
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster",
        cluster_id="j-1234567890ABCDEF0",
        step_concurrency_level=5
    )
    
    assert response.isError
    assert "Operation modify-cluster is not allowed without write access" in response.content[0].text

@pytest.mark.asyncio
async def test_modify_cluster_attributes_no_write_access(mock_aws_helper, mock_context):
    """Test that modifying cluster attributes fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMREc2ClusterHandler(mcp, allow_write=False)
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="modify-cluster-attributes",
        cluster_id="j-1234567890ABCDEF0",
        termination_protected=True
    )
    
    assert response.isError
    assert "Operation modify-cluster-attributes is not allowed without write access" in response.content[0].text

@pytest.mark.asyncio
async def test_create_security_configuration_no_write_access(mock_aws_helper, mock_context):
    """Test that creating security configuration fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMREc2ClusterHandler(mcp, allow_write=False)
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="create-security-configuration",
        security_configuration_name="test-config",
        security_configuration_json={}
    )
    
    assert response.isError
    assert "Operation create-security-configuration is not allowed without write access" in response.content[0].text

@pytest.mark.asyncio
async def test_delete_security_configuration_no_write_access(mock_aws_helper, mock_context):
    """Test that deleting security configuration fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMREc2ClusterHandler(mcp, allow_write=False)
    
    response = await handler.manage_aws_emr_clusters(
        mock_context,
        operation="delete-security-configuration",
        security_configuration_name="test-config"
    )
    
    assert response.isError
    assert "Operation delete-security-configuration is not allowed without write access" in response.content[0].text