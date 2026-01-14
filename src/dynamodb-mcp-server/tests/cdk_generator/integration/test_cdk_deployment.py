"""Integration tests for CDK deployment."""

import boto3
import pytest
import subprocess
from awslabs.dynamodb_mcp_server.cdk_generator import CdkGenerator
from botocore.exceptions import NoCredentialsError, PartialCredentialsError


STACK_NAME = 'CdkStack'


@pytest.mark.integration
class TestCdkDeployment:
    """Tests for deploying generated CDK apps to AWS."""

    @pytest.fixture
    def aws_session(self):
        """Create boto3 session from environment, skip if credentials unavailable."""
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials is None:
                pytest.skip('AWS credentials not available')
            return session
        except (NoCredentialsError, PartialCredentialsError):
            pytest.skip('AWS credentials not available')

    @pytest.mark.live
    def test_cdk_deployment_to_aws(self, complex_json_file, aws_session):
        """Test deploying generated CDK app to AWS and verify table configuration.

        This test uses the complex_json_data fixture which defines:
        - UserTable: user_id (B) HASH, created_at (N) RANGE, EmailIndex GSI with KEYS_ONLY, TTL enabled
        - OrderTable: customer_id (S) HASH, order_id (N) RANGE, StatusIndex GSI with multi-keys and INCLUDE
          StatusIndex has 2 HASH keys (status, region) and 2 RANGE keys (created_date, priority)
        """
        cfn_client = aws_session.client('cloudformation')
        dynamodb_client = aws_session.client('dynamodb')

        generator = CdkGenerator()
        generator.generate(complex_json_file)

        cdk_dir = complex_json_file.parent / 'cdk'

        try:
            # Install dependencies
            install_result = subprocess.run(
                ['npm', 'install'],
                cwd=cdk_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if install_result.returncode != 0:
                pytest.skip(f'npm install failed: {install_result.stderr}')

            # Deploy stack
            deploy_result = subprocess.run(
                ['npx', 'cdk', 'deploy', '--require-approval=never'],
                cwd=cdk_dir,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if deploy_result.returncode != 0:
                pytest.fail(
                    f'CDK deployment failed. stderr: {deploy_result.stderr}\n'
                    f'stdout: {deploy_result.stdout}\n'
                    f'Resources preserved for inspection'
                )

            # Get deployed table names from CloudFormation stack
            paginator = cfn_client.get_paginator('list_stack_resources')
            table_names = []
            for page in paginator.paginate(StackName=STACK_NAME):
                for resource in page['StackResourceSummaries']:
                    if resource['ResourceType'] in [
                        'AWS::DynamoDB::Table',
                        'AWS::DynamoDB::GlobalTable',
                    ]:
                        table_names.append(resource['PhysicalResourceId'])

            assert len(table_names) == 2, f'Expected 2 tables, got {len(table_names)}'

            # Find UserTable and OrderTable (names may have stack prefix/suffix)
            user_table_name = next((t for t in table_names if 'UserTable' in t), None)
            order_table_name = next((t for t in table_names if 'OrderTable' in t), None)

            assert user_table_name is not None, 'UserTable not found in deployed resources'
            assert order_table_name is not None, 'OrderTable not found in deployed resources'

            # Verify UserTable configuration
            user_table = dynamodb_client.describe_table(TableName=user_table_name)['Table']
            assert len(user_table['KeySchema']) == 2
            assert user_table['KeySchema'][0]['AttributeName'] == 'user_id'
            assert user_table['KeySchema'][0]['KeyType'] == 'HASH'
            assert user_table['KeySchema'][1]['AttributeName'] == 'created_at'
            assert user_table['KeySchema'][1]['KeyType'] == 'RANGE'

            user_attrs = {
                ad['AttributeName']: ad['AttributeType']
                for ad in user_table['AttributeDefinitions']
            }
            assert user_attrs['user_id'] == 'B'
            assert user_attrs['created_at'] == 'N'
            assert user_attrs['email'] == 'S'

            # Verify UserTable EmailIndex GSI with KEYS_ONLY projection
            assert 'GlobalSecondaryIndexes' in user_table
            user_gsis = user_table['GlobalSecondaryIndexes']
            assert len(user_gsis) == 1
            assert user_gsis[0]['IndexName'] == 'EmailIndex'
            assert len(user_gsis[0]['KeySchema']) == 1
            assert user_gsis[0]['KeySchema'][0]['AttributeName'] == 'email'
            assert user_gsis[0]['KeySchema'][0]['KeyType'] == 'HASH'
            assert user_gsis[0]['Projection']['ProjectionType'] == 'KEYS_ONLY'

            # Verify OrderTable configuration
            order_table = dynamodb_client.describe_table(TableName=order_table_name)['Table']
            assert len(order_table['KeySchema']) == 2
            assert order_table['KeySchema'][0]['AttributeName'] == 'customer_id'
            assert order_table['KeySchema'][0]['KeyType'] == 'HASH'
            assert order_table['KeySchema'][1]['AttributeName'] == 'order_id'
            assert order_table['KeySchema'][1]['KeyType'] == 'RANGE'

            order_attrs = {
                ad['AttributeName']: ad['AttributeType']
                for ad in order_table['AttributeDefinitions']
            }
            assert order_attrs['customer_id'] == 'S'
            assert order_attrs['order_id'] == 'N'
            assert order_attrs['status'] == 'S'
            assert order_attrs['region'] == 'S'
            assert order_attrs['created_date'] == 'S'
            assert order_attrs['priority'] == 'N'

            # Verify OrderTable StatusIndex GSI with INCLUDE projection and multi-keys
            assert 'GlobalSecondaryIndexes' in order_table
            order_gsis = order_table['GlobalSecondaryIndexes']
            assert len(order_gsis) == 1
            assert order_gsis[0]['IndexName'] == 'StatusIndex'
            assert len(order_gsis[0]['KeySchema']) == 4  # 2 HASH + 2 RANGE keys

            # Verify partition keys (HASH)
            hash_keys = [k for k in order_gsis[0]['KeySchema'] if k['KeyType'] == 'HASH']
            assert len(hash_keys) == 2
            hash_key_names = {k['AttributeName'] for k in hash_keys}
            assert hash_key_names == {'status', 'region'}

            # Verify sort keys (RANGE)
            range_keys = [k for k in order_gsis[0]['KeySchema'] if k['KeyType'] == 'RANGE']
            assert len(range_keys) == 2
            range_key_names = {k['AttributeName'] for k in range_keys}
            assert range_key_names == {'created_date', 'priority'}

            # Verify projection
            assert order_gsis[0]['Projection']['ProjectionType'] == 'INCLUDE'
            assert set(order_gsis[0]['Projection']['NonKeyAttributes']) == {
                'total_amount',
                'customer_name',
            }

            # Verify billing mode
            assert user_table['BillingModeSummary']['BillingMode'] == 'PAY_PER_REQUEST'
            assert order_table['BillingModeSummary']['BillingMode'] == 'PAY_PER_REQUEST'

            # Verify UserTable TTL configuration
            user_ttl = dynamodb_client.describe_time_to_live(TableName=user_table_name)
            assert 'TimeToLiveDescription' in user_ttl
            assert user_ttl['TimeToLiveDescription']['AttributeName'] == 'ttl'
            assert user_ttl['TimeToLiveDescription']['TimeToLiveStatus'] in ['ENABLING', 'ENABLED']

            # Verify OrderTable does not have TTL configured
            order_ttl = dynamodb_client.describe_time_to_live(TableName=order_table_name)
            assert 'TimeToLiveDescription' in order_ttl
            ttl_status = order_ttl['TimeToLiveDescription'].get('TimeToLiveStatus', 'DISABLED')
            assert ttl_status in ['DISABLED', 'DISABLING']

            # Clean up on success
            cleanup_result = subprocess.run(
                ['npx', 'cdk', 'destroy', '--force'],
                cwd=cdk_dir,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if cleanup_result.returncode != 0:
                pytest.warns(UserWarning, f'CDK cleanup failed: {cleanup_result.stderr}')

        except subprocess.TimeoutExpired:
            pytest.skip('CDK deployment timed out')
        except FileNotFoundError:
            pytest.skip('npx or npm not found')
