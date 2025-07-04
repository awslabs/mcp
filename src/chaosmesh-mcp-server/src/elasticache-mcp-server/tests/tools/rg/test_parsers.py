"""Tests for parser functions."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg.parsers import (
    parse_shorthand_log_delivery,
    parse_shorthand_nodegroup,
)


class TestParseShorthandNodegroup:
    """Tests for parse_shorthand_nodegroup function."""

    def test_parse_basic_nodegroup(self):
        """Test parsing basic nodegroup configuration."""
        config = parse_shorthand_nodegroup('NodeGroupId=ng-1,Slots=0-8191,ReplicaCount=2')

        assert config['NodeGroupId'] == 'ng-1'
        assert config['Slots'] == '0-8191'
        assert config['ReplicaCount'] == 2

    def test_parse_full_nodegroup(self):
        """Test parsing nodegroup with all parameters."""
        config = parse_shorthand_nodegroup(
            'NodeGroupId=ng-1,Slots=0-8191,ReplicaCount=2,'
            'PrimaryAvailabilityZone=us-west-2a,'
            'ReplicaAvailabilityZones=us-west-2b,us-west-2c,'
            'PrimaryOutpostArn=arn:aws:outposts:1,'
            'ReplicaOutpostArns=arn:aws:outposts:2,arn:aws:outposts:3'
        )

        assert config['NodeGroupId'] == 'ng-1'
        assert config['Slots'] == '0-8191'
        assert config['ReplicaCount'] == 2
        assert config['PrimaryAvailabilityZone'] == 'us-west-2a'
        assert config['ReplicaAvailabilityZones'] == ['us-west-2b', 'us-west-2c']
        assert config['PrimaryOutpostArn'] == 'arn:aws:outposts:1'
        assert config['ReplicaOutpostArns'] == ['arn:aws:outposts:2', 'arn:aws:outposts:3']

    def test_empty_nodegroup(self):
        """Test parsing empty nodegroup configuration."""
        with pytest.raises(ValueError, match='Empty nodegroup configuration'):
            parse_shorthand_nodegroup('')

    def test_missing_required_field(self):
        """Test parsing nodegroup without required NodeGroupId."""
        with pytest.raises(ValueError, match='Missing required field: NodeGroupId'):
            parse_shorthand_nodegroup('Slots=0-8191,ReplicaCount=2')

    def test_invalid_format(self):
        """Test parsing nodegroup with invalid format."""
        with pytest.raises(ValueError, match='Invalid format'):
            parse_shorthand_nodegroup('NodeGroupId:ng-1')

    def test_empty_key_value(self):
        """Test parsing nodegroup with empty key or value."""
        with pytest.raises(ValueError, match='Empty key or value'):
            parse_shorthand_nodegroup('NodeGroupId=,Slots=0-8191')

    def test_invalid_parameter(self):
        """Test parsing nodegroup with invalid parameter."""
        with pytest.raises(ValueError, match='Invalid parameter'):
            parse_shorthand_nodegroup('NodeGroupId=ng-1,InvalidParam=value')

    def test_invalid_replica_count(self):
        """Test parsing nodegroup with invalid ReplicaCount."""
        with pytest.raises(ValueError, match='Invalid value for ReplicaCount'):
            parse_shorthand_nodegroup('NodeGroupId=ng-1,ReplicaCount=invalid')

    def test_nodegroup_with_whitespace(self):
        """Test parsing nodegroup with whitespace in the configuration."""
        config = parse_shorthand_nodegroup('NodeGroupId = ng-1, Slots = 0-8191, ReplicaCount = 2')
        assert config['NodeGroupId'] == 'ng-1'
        assert config['Slots'] == '0-8191'
        assert config['ReplicaCount'] == 2


class TestParseShorthandLogDelivery:
    """Tests for parse_shorthand_log_delivery function."""

    def test_parse_basic_log_delivery(self):
        """Test parsing basic log delivery configuration."""
        config = parse_shorthand_log_delivery(
            'LogType=slow-log,DestinationType=cloudwatch-logs,'
            "DestinationDetails={'CloudWatchLogsDetails':{'LogGroup':'/aws/elasticache/test'}},"
            'LogFormat=text,Enabled=true'
        )

        assert config['LogType'] == 'slow-log'
        assert config['DestinationType'] == 'cloudwatch-logs'
        assert config['DestinationDetails'] == {
            'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache/test'}
        }
        assert config['LogFormat'] == 'text'
        assert config['Enabled'] is True

    def test_parse_kinesis_log_delivery(self):
        """Test parsing log delivery with Kinesis configuration."""
        config = parse_shorthand_log_delivery(
            'LogType=engine-log,DestinationType=kinesis-firehose,'
            "DestinationDetails={'KinesisFirehoseDetails':{'DeliveryStream':'test-stream'}},"
            'LogFormat=json,Enabled=true'
        )

        assert config['LogType'] == 'engine-log'
        assert config['DestinationType'] == 'kinesis-firehose'
        assert config['DestinationDetails'] == {
            'KinesisFirehoseDetails': {'DeliveryStream': 'test-stream'}
        }
        assert config['LogFormat'] == 'json'
        assert config['Enabled'] is True

    def test_empty_log_delivery(self):
        """Test parsing empty log delivery configuration."""
        with pytest.raises(ValueError, match='Empty log delivery configuration'):
            parse_shorthand_log_delivery('')

    def test_missing_required_fields(self):
        """Test parsing log delivery without required fields."""
        with pytest.raises(ValueError, match='Missing required fields'):
            parse_shorthand_log_delivery('LogType=slow-log,DestinationType=cloudwatch-logs')

    def test_invalid_log_type(self):
        """Test parsing log delivery with invalid LogType."""
        with pytest.raises(ValueError, match='LogType must be either'):
            parse_shorthand_log_delivery(
                'LogType=invalid-log,DestinationType=cloudwatch-logs,'
                "DestinationDetails={'CloudWatchLogsDetails':{'LogGroup':'test'}},"
                'LogFormat=text,Enabled=true'
            )

    def test_invalid_destination_type(self):
        """Test parsing log delivery with invalid DestinationType."""
        with pytest.raises(ValueError, match='DestinationType must be either'):
            parse_shorthand_log_delivery(
                'LogType=slow-log,DestinationType=invalid-type,'
                "DestinationDetails={'CloudWatchLogsDetails':{'LogGroup':'test'}},"
                'LogFormat=text,Enabled=true'
            )

    def test_invalid_log_format(self):
        """Test parsing log delivery with invalid LogFormat."""
        with pytest.raises(ValueError, match='LogFormat must be either'):
            parse_shorthand_log_delivery(
                'LogType=slow-log,DestinationType=cloudwatch-logs,'
                "DestinationDetails={'CloudWatchLogsDetails':{'LogGroup':'test'}},"
                'LogFormat=invalid,Enabled=true'
            )

    def test_invalid_enabled(self):
        """Test parsing log delivery with invalid Enabled value."""
        config = parse_shorthand_log_delivery(
            'LogType=slow-log,DestinationType=cloudwatch-logs,'
            "DestinationDetails={'CloudWatchLogsDetails':{'LogGroup':'test'}},"
            'LogFormat=text,Enabled=invalid'
        )
        assert config['Enabled'] is False  # Non-'true' values are treated as False

    def test_invalid_destination_details_json(self):
        """Test parsing log delivery with invalid DestinationDetails JSON."""
        with pytest.raises(ValueError, match='Invalid value for DestinationDetails'):
            parse_shorthand_log_delivery(
                'LogType=slow-log,DestinationType=cloudwatch-logs,'
                'DestinationDetails=invalid-json,'
                'LogFormat=text,Enabled=true'
            )
