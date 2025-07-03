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

"""Tests for the models module in the RDS Control Plane MCP Server."""

import json
from awslabs.rds_control_plane_mcp_server.common.models import (
    ClusterListModel,
    ClusterMember,
    ClusterModel,
    InstanceEndpoint,
    InstanceListModel,
    InstanceModel,
    InstanceStorage,
    VpcSecurityGroup,
)


def test_cluster_member_model():
    """Test the ClusterMember model."""
    member = ClusterMember(instance_id='test-instance', is_writer=True, status='available')

    member_dict = member.model_dump()
    assert member_dict['instance_id'] == 'test-instance'
    assert member_dict['is_writer'] is True
    assert member_dict['status'] == 'available'

    json_str = json.dumps(member_dict)
    parsed = json.loads(json_str)
    assert parsed['instance_id'] == 'test-instance'


def test_vpc_security_group_model():
    """Test the VpcSecurityGroup model."""
    sg = VpcSecurityGroup(id='sg-12345', status='active')

    sg_dict = sg.model_dump()
    assert sg_dict['id'] == 'sg-12345'
    assert sg_dict['status'] == 'active'


def test_cluster_model():
    """Test the ClusterModel model."""
    cluster = ClusterModel(
        cluster_id='test-cluster',
        engine='aurora-mysql',
        status='available',
        endpoint='cluster-endpoint.rds.aws.com',
        reader_endpoint='reader-endpoint.rds.aws.com',
        multi_az=True,
        backup_retention=7,
        preferred_backup_window='03:00-05:00',
        preferred_maintenance_window='sun:05:00-sun:06:00',
        members=[
            ClusterMember(instance_id='instance-1', is_writer=True, status='in-sync'),
            ClusterMember(instance_id='instance-2', is_writer=False, status='in-sync'),
        ],
        vpc_security_groups=[VpcSecurityGroup(id='sg-12345', status='active')],
        tags={'Environment': 'Test'},
        resource_uri='aws-rds://db-cluster/' + 'test-cluster',
    )

    cluster_dict = cluster.model_dump()
    assert cluster_dict['cluster_id'] == 'test-cluster'
    assert cluster_dict['engine'] == 'aurora-mysql'
    assert len(cluster_dict['members']) == 2
    assert cluster_dict['members'][0]['instance_id'] == 'instance-1'
    assert cluster_dict['vpc_security_groups'][0]['id'] == 'sg-12345'
    assert cluster_dict['tags'] == {'Environment': 'Test'}
    assert cluster_dict['resource_uri'] == 'aws-rds://db-cluster/' + 'test-cluster'

    json_str = json.dumps(cluster_dict)
    parsed = json.loads(json_str)
    assert parsed['cluster_id'] == 'test-cluster'
    assert len(parsed['members']) == 2


def test_cluster_model_with_defaults():
    """Test the ClusterModel model with default values."""
    cluster = ClusterModel(
        cluster_id='minimal-cluster',
        engine='aurora-postgresql',
        status='creating',
        multi_az=False,
        backup_retention=1,
    )

    cluster_dict = cluster.model_dump()
    assert cluster_dict['cluster_id'] == 'minimal-cluster'
    assert cluster_dict['members'] == []
    assert cluster_dict['vpc_security_groups'] == []
    assert cluster_dict['tags'] == {}
    assert cluster_dict['resource_uri'] is None


def test_instance_endpoint_model():
    """Test the InstanceEndpoint model."""
    endpoint = InstanceEndpoint(
        address='db.example.com', port=3306, hosted_zone_id='Z2R2ITUGPM61AM'
    )

    endpoint_dict = endpoint.model_dump()
    assert endpoint_dict['address'] == 'db.example.com'
    assert endpoint_dict['port'] == 3306
    assert endpoint_dict['hosted_zone_id'] == 'Z2R2ITUGPM61AM'

    minimal_endpoint = InstanceEndpoint(address='minimal.example.com')
    minimal_dict = minimal_endpoint.model_dump()
    assert minimal_dict['address'] == 'minimal.example.com'
    assert minimal_dict['port'] is None
    assert minimal_dict['hosted_zone_id'] is None


def test_instance_storage_model():
    """Test the InstanceStorage model."""
    storage = InstanceStorage(type='gp2', allocated=20, encrypted=True)

    storage_dict = storage.model_dump()
    assert storage_dict['type'] == 'gp2'
    assert storage_dict['allocated'] == 20
    assert storage_dict['encrypted'] is True

    minimal_storage = InstanceStorage(type='aurora')
    minimal_dict = minimal_storage.model_dump()
    assert minimal_dict['type'] == 'aurora'
    assert minimal_dict['allocated'] is None
    assert minimal_dict['encrypted'] is None


def test_instance_model():
    """Test the InstanceModel model."""
    instance = InstanceModel(
        instance_id='test-instance',
        status='available',
        engine='mysql',
        engine_version='8.0',
        instance_class='db.t3.medium',
        availability_zone='us-east-1a',
        multi_az=False,
        publicly_accessible=True,
        endpoint=InstanceEndpoint(
            address='test-instance.abc123.us-east-1.rds.amazonaws.com',
            port=3306,
            hosted_zone_id='Z2R2ITUGPM61AM',
        ),
        storage=InstanceStorage(type='gp2', allocated=20, encrypted=True),
        db_cluster='test-cluster',
        vpc_security_groups=[VpcSecurityGroup(id='sg-12345', status='active')],
        tags={'Environment': 'Development'},
        resource_uri='aws-rds://db-instance/test-instance',
    )

    instance_dict = instance.model_dump()
    assert instance_dict['instance_id'] == 'test-instance'
    assert instance_dict['engine'] == 'mysql'
    assert instance_dict['engine_version'] == '8.0'
    assert instance_dict['instance_class'] == 'db.t3.medium'
    assert instance_dict['db_cluster'] == 'test-cluster'
    assert (
        instance_dict['endpoint']['address'] == 'test-instance.abc123.us-east-1.rds.amazonaws.com'
    )
    assert instance_dict['storage']['type'] == 'gp2'
    assert instance_dict['storage']['allocated'] == 20

    json_str = json.dumps(instance_dict)
    parsed = json.loads(json_str)
    assert parsed['instance_id'] == 'test-instance'
    assert parsed['endpoint']['port'] == 3306


def test_instance_model_with_defaults():
    """Test the InstanceModel model with default values."""
    instance = InstanceModel(
        instance_id='minimal-instance',
        status='creating',
        engine='postgres',
        instance_class='db.t3.micro',
        multi_az=False,
        publicly_accessible=False,
    )

    instance_dict = instance.model_dump()
    assert instance_dict['instance_id'] == 'minimal-instance'
    assert instance_dict['engine'] == 'postgres'
    assert instance_dict['engine_version'] is None
    assert instance_dict['db_cluster'] is None
    assert isinstance(instance_dict['endpoint'], dict)
    assert isinstance(instance_dict['storage'], dict)
    assert instance_dict['vpc_security_groups'] == []
    assert instance_dict['tags'] == {}
    assert instance_dict['resource_uri'] is None


def test_instance_list_model():
    """Test the InstanceListModel model."""
    instance1 = InstanceModel(
        instance_id='instance-1',
        status='available',
        engine='mysql',
        instance_class='db.t3.medium',
        multi_az=False,
        publicly_accessible=True,
    )
    instance2 = InstanceModel(
        instance_id='instance-2',
        status='available',
        engine='postgres',
        instance_class='db.t3.large',
        multi_az=True,
        publicly_accessible=False,
    )

    instance_list = InstanceListModel(
        instances=[instance1, instance2], count=2, resource_uri='aws-rds://db-instance'
    )

    list_dict = instance_list.model_dump()
    assert len(list_dict['instances']) == 2
    assert list_dict['count'] == 2
    assert list_dict['resource_uri'] == 'aws-rds://db-instance'
    assert list_dict['instances'][0]['instance_id'] == 'instance-1'
    assert list_dict['instances'][1]['instance_id'] == 'instance-2'

    empty_list = InstanceListModel(instances=[], count=0, resource_uri='aws-rds://db-instance')
    empty_dict = empty_list.model_dump()
    assert empty_dict['instances'] == []
    assert empty_dict['count'] == 0


def test_cluster_list_model():
    """Test the ClusterListModel model."""
    cluster1 = ClusterModel(
        cluster_id='cluster-1',
        engine='aurora-mysql',
        status='available',
        multi_az=True,
        backup_retention=7,
    )
    cluster2 = ClusterModel(
        cluster_id='cluster-2',
        engine='aurora-postgresql',
        status='available',
        multi_az=False,
        backup_retention=5,
    )

    cluster_list = ClusterListModel(
        clusters=[cluster1, cluster2], count=2, resource_uri='aws-rds://db-cluster'
    )

    list_dict = cluster_list.model_dump()
    assert len(list_dict['clusters']) == 2
    assert list_dict['count'] == 2
    assert list_dict['resource_uri'] == 'aws-rds://db-cluster'
    assert list_dict['clusters'][0]['cluster_id'] == 'cluster-1'
    assert list_dict['clusters'][1]['cluster_id'] == 'cluster-2'
