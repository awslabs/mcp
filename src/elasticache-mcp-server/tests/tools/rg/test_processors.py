"""Tests for processor functions."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg import (
    process_log_delivery_configurations,
    process_nodegroup_configuration,
)


class TestProcessLogDeliveryConfigurations:
    """Tests for process_log_delivery_configurations function."""

    def test_process_shorthand_log_delivery(self):
        """Test processing shorthand log delivery configuration."""
        shorthand = (
            'LogType=slow-log,DestinationType=cloudwatch-logs,'
            "DestinationDetails={'CloudWatchLogsDetails':{'LogGroup':'/aws/elasticache/test'}},"
            'LogFormat=text,Enabled=true'
        )

        configs = process_log_delivery_configurations(shorthand)

        assert len(configs) == 1
        assert configs[0]['LogType'] == 'slow-log'
        assert configs[0]['DestinationType'] == 'cloudwatch-logs'
        assert configs[0]['DestinationDetails'] == {
            'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache/test'}
        }
        assert configs[0]['LogFormat'] == 'text'
        assert configs[0]['Enabled'] is True

    def test_process_multiple_shorthand_log_delivery(self):
        """Test processing multiple shorthand log delivery configurations."""
        shorthand = (
            'LogType=slow-log,DestinationType=cloudwatch-logs,'
            "DestinationDetails={'CloudWatchLogsDetails':{'LogGroup':'/aws/elasticache/slow'}},"
            'LogFormat=text,Enabled=true '
            'LogType=engine-log,DestinationType=kinesis-firehose,'
            "DestinationDetails={'KinesisFirehoseDetails':{'DeliveryStream':'test-stream'}},"
            'LogFormat=json,Enabled=true'
        )

        configs = process_log_delivery_configurations(shorthand)

        assert len(configs) == 2
        # First config
        assert configs[0]['LogType'] == 'slow-log'
        assert configs[0]['DestinationType'] == 'cloudwatch-logs'
        assert configs[0]['DestinationDetails'] == {
            'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache/slow'}
        }
        assert configs[0]['LogFormat'] == 'text'
        assert configs[0]['Enabled'] is True
        # Second config
        assert configs[1]['LogType'] == 'engine-log'
        assert configs[1]['DestinationType'] == 'kinesis-firehose'
        assert configs[1]['DestinationDetails'] == {
            'KinesisFirehoseDetails': {'DeliveryStream': 'test-stream'}
        }
        assert configs[1]['LogFormat'] == 'json'
        assert configs[1]['Enabled'] is True

    def test_process_json_log_delivery(self):
        """Test processing JSON log delivery configuration."""
        json_config = [
            {
                'LogType': 'slow-log',
                'DestinationType': 'cloudwatch-logs',
                'DestinationDetails': {
                    'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache/test'}
                },
                'LogFormat': 'text',
                'Enabled': True,
            }
        ]

        configs = process_log_delivery_configurations(json_config)

        assert len(configs) == 1
        assert configs[0] == json_config[0]

    def test_process_invalid_json_log_delivery(self):
        """Test processing invalid JSON log delivery configuration."""
        with pytest.raises(
            ValueError, match='Each log delivery configuration must be a dictionary'
        ):
            process_log_delivery_configurations([123])  # type: ignore

    def test_process_invalid_shorthand_log_delivery(self):
        """Test processing invalid shorthand log delivery configuration."""
        with pytest.raises(ValueError, match='Invalid log delivery shorthand syntax'):
            process_log_delivery_configurations('InvalidConfig')

    def test_process_invalid_log_delivery_type(self):
        """Test processing log delivery configuration with invalid type."""
        with pytest.raises(
            ValueError, match='must be a list of dictionaries or a shorthand string'
        ):
            process_log_delivery_configurations(123)  # type: ignore

    def test_process_empty_list_log_delivery(self):
        """Test processing an empty list of log delivery configurations."""
        configs = process_log_delivery_configurations([])
        assert configs == []


class TestProcessNodegroupConfiguration:
    """Tests for process_nodegroup_configuration function."""

    def test_process_shorthand_nodegroup(self):
        """Test processing shorthand nodegroup configuration."""
        shorthand = 'NodeGroupId=ng-1,Slots=0-8191,ReplicaCount=2'

        configs = process_nodegroup_configuration(shorthand)

        assert len(configs) == 1
        assert configs[0]['NodeGroupId'] == 'ng-1'
        assert configs[0]['Slots'] == '0-8191'
        assert configs[0]['ReplicaCount'] == 2

    def test_process_multiple_shorthand_nodegroups(self):
        """Test processing multiple shorthand nodegroup configurations."""
        shorthand = (
            'NodeGroupId=ng-1,Slots=0-8191,ReplicaCount=2 '
            'NodeGroupId=ng-2,Slots=8192-16383,ReplicaCount=2'
        )

        configs = process_nodegroup_configuration(shorthand)

        assert len(configs) == 2
        # First config
        assert configs[0]['NodeGroupId'] == 'ng-1'
        assert configs[0]['Slots'] == '0-8191'
        assert configs[0]['ReplicaCount'] == 2
        # Second config
        assert configs[1]['NodeGroupId'] == 'ng-2'
        assert configs[1]['Slots'] == '8192-16383'
        assert configs[1]['ReplicaCount'] == 2

    def test_process_json_nodegroup(self):
        """Test processing JSON nodegroup configuration."""
        json_config = [
            {
                'NodeGroupId': 'ng-1',
                'Slots': '0-8191',
                'ReplicaCount': 2,
                'PrimaryAvailabilityZone': 'us-west-2a',
                'ReplicaAvailabilityZones': ['us-west-2b', 'us-west-2c'],
            }
        ]

        configs = process_nodegroup_configuration(json_config)

        assert len(configs) == 1
        assert configs[0]['NodeGroupId'] == 'ng-1'
        assert configs[0]['Slots'] == '0-8191'
        assert configs[0]['ReplicaCount'] == 2
        assert configs[0]['PrimaryAvailabilityZone'] == 'us-west-2a'
        assert configs[0]['ReplicaAvailabilityZones'] == ['us-west-2b', 'us-west-2c']

    def test_process_json_nodegroup_with_string_lists(self):
        """Test processing JSON nodegroup with comma-separated strings."""
        json_config = [
            {'NodeGroupId': 'ng-1', 'ReplicaAvailabilityZones': 'us-west-2b,us-west-2c'}
        ]

        configs = process_nodegroup_configuration(json_config)

        assert len(configs) == 1
        assert configs[0]['ReplicaAvailabilityZones'] == ['us-west-2b', 'us-west-2c']

    def test_process_invalid_json_nodegroup(self):
        """Test processing invalid JSON nodegroup configuration."""
        with pytest.raises(ValueError, match='Each node group configuration must be a dictionary'):
            process_nodegroup_configuration([123])  # type: ignore

    def test_process_invalid_shorthand_nodegroup(self):
        """Test processing invalid shorthand nodegroup configuration."""
        with pytest.raises(ValueError, match='Invalid nodegroup shorthand syntax'):
            process_nodegroup_configuration('InvalidConfig')

    def test_process_invalid_nodegroup_type(self):
        """Test processing nodegroup configuration with invalid type."""
        with pytest.raises(
            ValueError, match='must be a list of dictionaries or a shorthand string'
        ):
            process_nodegroup_configuration(123)  # type: ignore

    def test_process_json_nodegroup_missing_required(self):
        """Test processing JSON nodegroup without required NodeGroupId."""
        with pytest.raises(ValueError, match='Missing required field: NodeGroupId'):
            process_nodegroup_configuration([{'Slots': '0-8191'}])

    def test_process_json_nodegroup_invalid_replica_count(self):
        """Test processing JSON nodegroup with invalid ReplicaCount."""
        with pytest.raises(ValueError, match='ReplicaCount must be an integer'):
            process_nodegroup_configuration([{'NodeGroupId': 'ng-1', 'ReplicaCount': 'invalid'}])

    def test_process_json_nodegroup_invalid_zones(self):
        """Test processing JSON nodegroup with invalid ReplicaAvailabilityZones."""
        with pytest.raises(ValueError, match='must be a string or list of strings'):
            process_nodegroup_configuration(
                [{'NodeGroupId': 'ng-1', 'ReplicaAvailabilityZones': 123}]
            )

    def test_process_nodegroup_all_fields(self):
        """Test processing a nodegroup configuration with all fields."""
        config = {
            'NodeGroupId': 'ng-1',
            'Slots': '0-8191',
            'ReplicaCount': 2,
            'PrimaryAvailabilityZone': 'us-west-2a',
            'ReplicaAvailabilityZones': ['us-west-2b', 'us-west-2c'],
            'PrimaryOutpostArn': 'arn:aws:outposts:us-west-2:123456789012:outpost/op-1234567890abcdef0',
            'ReplicaOutpostArns': [
                'arn:aws:outposts:us-west-2:123456789012:outpost/op-0987654321fedcba0'
            ],
        }
        configs = process_nodegroup_configuration([config])
        assert len(configs) == 1
        assert configs[0] == config

    def test_process_empty_list_nodegroup(self):
        """Test processing an empty list of nodegroup configurations."""
        configs = process_nodegroup_configuration([])
        assert configs == []

    def test_process_nodegroup_minimal_fields(self):
        """Test processing a nodegroup configuration with only required fields."""
        minimal_config = {
            'NodeGroupId': 'ng-1',
        }
        configs = process_nodegroup_configuration([minimal_config])
        assert len(configs) == 1
        assert configs[0]['NodeGroupId'] == 'ng-1'
        assert 'Slots' not in configs[0]
        assert 'ReplicaCount' not in configs[0]
