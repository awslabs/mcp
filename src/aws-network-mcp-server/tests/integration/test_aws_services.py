import pytest
from moto import mock_aws

class TestAwsServiceIntegration:
    """Integration tests using moto for AWS service mocking."""
    
    @mock_aws
    def test_vpc_tool_integration(self, mcp_test_client):
        """End-to-end test for VPC network details tool."""
        ec2 = boto3.client('ec2')
        vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
        
        result = mcp_test_client.execute_tool(
            'get_vpc_network_details',
            {'vpc_id': vpc['Vpc']['VpcId']}
        )
        
        assert result['VpcId'] == vpc['Vpc']['VpcId']
        assert 'Subnets' in result
        assert 'RouteTables' in result
        
    @mock_aws
    def test_error_handling_integration(self, mcp_test_client):
        """Test error handling with real AWS service responses."""
        with pytest.raises(exceptions.ResourceNotFoundError) as exc_info:
            mcp_test_client.execute_tool(
                'get_cloudwan_details',
                {'core_network_id': 'non-existent'}
            )
            
        assert 'could not be found' in str(exc_info.value)