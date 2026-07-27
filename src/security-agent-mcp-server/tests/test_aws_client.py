# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for aws_client.py using boto3 SDK."""

import pytest
from awslabs.security_agent_mcp_server.aws_client import SecurityAgentClient
from unittest.mock import MagicMock, patch


class TestSecurityAgentClient:
    """Tests for SecurityAgentClient."""

    def test_init_default_region(self):
        """Default region is us-east-1."""
        client = SecurityAgentClient()
        assert client.region == 'us-east-1'

    def test_init_custom_region(self):
        """Region passed at construction is preserved."""
        client = SecurityAgentClient(region='us-west-2')
        assert client.region == 'us-west-2'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_list_agent_spaces(self, mock_boto3):
        """list_agent_spaces returns the agentSpaceSummaries list."""
        mock_client = MagicMock()
        mock_client.list_agent_spaces.return_value = {
            'agentSpaceSummaries': [{'agentSpaceId': 'as-1', 'name': 'test'}]
        }
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.list_agent_spaces()
        assert len(result) == 1
        assert result[0]['agentSpaceId'] == 'as-1'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_get_agent_space(self, mock_boto3):
        """get_agent_space returns the first agent space from the batch response."""
        mock_client = MagicMock()
        mock_client.batch_get_agent_spaces.return_value = {
            'agentSpaces': [{'agentSpaceId': 'as-1', 'name': 'test'}]
        }
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.get_agent_space('as-1')
        assert result['name'] == 'test'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_get_agent_space_empty(self, mock_boto3):
        """Empty agentSpaces response yields {}."""
        mock_client = MagicMock()
        mock_client.batch_get_agent_spaces.return_value = {'agentSpaces': []}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.get_agent_space('as-nonexistent')
        assert result == {}

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_code_review(self, mock_boto3):
        """create_code_review returns codeReviewId from boto3 response."""
        mock_client = MagicMock()
        mock_client.create_code_review.return_value = {'codeReviewId': 'cr-123'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.create_code_review(
            agent_space_id='as-1',
            title='test',
            service_role='arn:role',
            s3_url='s3://bucket/key.zip',
        )
        assert result['codeReviewId'] == 'cr-123'
        mock_client.create_code_review.assert_called_once()

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_start_code_review_job(self, mock_boto3):
        """start_code_review_job returns codeReviewJobId."""
        mock_client = MagicMock()
        mock_client.start_code_review_job.return_value = {'codeReviewJobId': 'cj-456'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.start_code_review_job('as-1', 'cr-123')
        assert result['codeReviewJobId'] == 'cj-456'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_list_findings_pagination(self, mock_boto3):
        """list_findings follows nextToken pagination and concatenates pages."""
        mock_client = MagicMock()
        mock_client.list_findings.side_effect = [
            {'findingsSummaries': [{'findingId': 'f-1'}], 'nextToken': 'tok'},
            {'findingsSummaries': [{'findingId': 'f-2'}]},
        ]
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.list_findings('as-1', 'cj-456')
        assert len(result['findingsSummaries']) == 2

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_batch_get_findings(self, mock_boto3):
        """batch_get_findings passes findings through unchanged."""
        mock_client = MagicMock()
        mock_client.batch_get_findings.return_value = {
            'findings': [{'findingId': 'f-1', 'name': 'SQL Injection'}]
        }
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.batch_get_findings('as-1', ['f-1'])
        assert result['findings'][0]['name'] == 'SQL Injection'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_call_generic(self, mock_boto3):
        """call() dispatches PascalCase op names to snake_case boto3 methods."""
        mock_client = MagicMock()
        mock_client.meta.service_model.operation_names = ['ListPentests']
        mock_client.list_pentests.return_value = {'pentests': []}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.call('ListPentests', {'agentSpaceId': 'as-1'})
        assert result == {'pentests': []}

    def test_call_invalid_operation(self):
        """Operation names that don't match the regex raise ValueError."""
        client = SecurityAgentClient()
        with pytest.raises(ValueError, match='Invalid operation'):
            client.call('../evil', {})

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_call_unknown_operation_rejected(self, mock_boto3):
        """Operations not in the SDK are rejected."""
        mock_client = MagicMock()
        mock_client.meta.service_model.operation_names = ['ListPentests']
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        with pytest.raises(ValueError, match='Unknown SecurityAgent operation'):
            client.call('SomeMissingOperation', {})

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_get_caller_identity(self, mock_boto3):
        """get_caller_identity returns the STS Account field."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_boto3.Session.return_value.client.return_value = mock_sts

        client = SecurityAgentClient()
        result = client.get_caller_identity()
        assert result['Account'] == '123456789012'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_agent_space_no_resources(self, mock_boto3):
        """create_agent_space without role/bucket omits awsResources from kwargs."""
        mock_client = MagicMock()
        mock_client.create_agent_space.return_value = {'agentSpaceId': 'as-1'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.create_agent_space(name='test')
        assert result['agentSpaceId'] == 'as-1'
        kwargs = mock_client.create_agent_space.call_args.kwargs
        assert kwargs == {'name': 'test'}

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_agent_space_with_role_and_bucket(self, mock_boto3):
        """Role and bucket land on awsResources.iamRoles / s3Buckets."""
        mock_client = MagicMock()
        mock_client.create_agent_space.return_value = {'agentSpaceId': 'as-1'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        client.create_agent_space(
            name='test', service_role='arn:aws:iam::1:role/r', s3_bucket='bkt'
        )
        kwargs = mock_client.create_agent_space.call_args.kwargs
        assert kwargs['awsResources']['iamRoles'] == ['arn:aws:iam::1:role/r']
        assert kwargs['awsResources']['s3Buckets'] == ['bkt']

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_update_agent_space_with_resources(self, mock_boto3):
        """update_agent_space forwards the full awsResources dict unchanged."""
        mock_client = MagicMock()
        mock_client.update_agent_space.return_value = {'agentSpaceId': 'as-1'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        client.update_agent_space(
            'as-1', 'name', {'iamRoles': ['arn:role-a'], 's3Buckets': ['bkt']}
        )
        kwargs = mock_client.update_agent_space.call_args.kwargs
        assert kwargs['agentSpaceId'] == 'as-1'
        assert kwargs['awsResources']['iamRoles'] == ['arn:role-a']
        assert kwargs['awsResources']['s3Buckets'] == ['bkt']

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_update_agent_space_no_resources(self, mock_boto3):
        """When no resources provided, awsResources is omitted."""
        mock_client = MagicMock()
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        client.update_agent_space('as-1', 'name')
        kwargs = mock_client.update_agent_space.call_args.kwargs
        assert 'awsResources' not in kwargs

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_batch_get_code_review_jobs(self, mock_boto3):
        """batch_get_code_review_jobs returns codeReviewJobs from boto3."""
        mock_client = MagicMock()
        mock_client.batch_get_code_review_jobs.return_value = {
            'codeReviewJobs': [{'codeReviewJobId': 'cj-1', 'status': 'IN_PROGRESS'}]
        }
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.batch_get_code_review_jobs('as-1', ['cj-1'])
        assert result['codeReviewJobs'][0]['status'] == 'IN_PROGRESS'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_stop_code_review_job(self, mock_boto3):
        """stop_code_review_job calls the underlying boto3 method with correct kwargs."""
        mock_client = MagicMock()
        mock_client.stop_code_review_job.return_value = {}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        client.stop_code_review_job('as-1', 'cj-1')
        mock_client.stop_code_review_job.assert_called_once_with(
            agentSpaceId='as-1', codeReviewJobId='cj-1'
        )

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_s3_bucket_us_east_1(self, mock_boto3):
        """us-east-1 must NOT include LocationConstraint."""
        mock_s3 = MagicMock()
        mock_boto3.Session.return_value.client.return_value = mock_s3

        client = SecurityAgentClient(region='us-east-1')
        result = client.create_s3_bucket('my-bucket')

        assert result == 'my-bucket'
        create_kwargs = mock_s3.create_bucket.call_args.kwargs
        assert create_kwargs == {'Bucket': 'my-bucket'}
        mock_s3.put_public_access_block.assert_called_once()
        mock_s3.put_bucket_lifecycle_configuration.assert_called_once()
        # Verify lifecycle has 30-day expiration
        lc = mock_s3.put_bucket_lifecycle_configuration.call_args.kwargs['LifecycleConfiguration']
        assert lc['Rules'][0]['Expiration']['Days'] == 30

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_s3_bucket_applies_encryption_and_tls_policy(self, mock_boto3):
        """Bucket creation must explicitly configure SSE-S3 and a TLS-only deny policy."""
        import json as _json

        mock_s3 = MagicMock()
        mock_boto3.Session.return_value.client.return_value = mock_s3

        client = SecurityAgentClient(region='us-east-1')
        client.create_s3_bucket('my-bucket')

        # Encryption: SSE-S3 (AES256) with bucket key.
        mock_s3.put_bucket_encryption.assert_called_once()
        enc_kwargs = mock_s3.put_bucket_encryption.call_args.kwargs
        assert enc_kwargs['Bucket'] == 'my-bucket'
        rule = enc_kwargs['ServerSideEncryptionConfiguration']['Rules'][0]
        assert rule['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] == 'AES256'
        assert rule['BucketKeyEnabled'] is True

        # TLS-only deny policy.
        mock_s3.put_bucket_policy.assert_called_once()
        pol_kwargs = mock_s3.put_bucket_policy.call_args.kwargs
        assert pol_kwargs['Bucket'] == 'my-bucket'
        policy = _json.loads(pol_kwargs['Policy'])
        stmt = policy['Statement'][0]
        assert stmt['Effect'] == 'Deny'
        assert stmt['Principal'] == '*'
        assert stmt['Condition']['Bool']['aws:SecureTransport'] == 'false'
        # Resource covers both bucket and objects.
        assert 'arn:aws:s3:::my-bucket' in stmt['Resource']
        assert 'arn:aws:s3:::my-bucket/*' in stmt['Resource']

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_s3_bucket_other_region(self, mock_boto3):
        """Non us-east-1 must include LocationConstraint."""
        mock_s3 = MagicMock()
        mock_boto3.Session.return_value.client.return_value = mock_s3

        client = SecurityAgentClient(region='us-west-2')
        client.create_s3_bucket('my-bucket')

        create_kwargs = mock_s3.create_bucket.call_args.kwargs
        assert create_kwargs['CreateBucketConfiguration'] == {'LocationConstraint': 'us-west-2'}

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_service_role_new(self, mock_boto3):
        """Creates the role with confused-deputy-safe trust policy."""
        import json as _json

        mock_iam = MagicMock()
        mock_boto3.Session.return_value.client.return_value = mock_iam

        client = SecurityAgentClient(region='us-east-1')
        arn = client.create_service_role('SecurityAgentScanRole', '123', '')

        assert arn == 'arn:aws:iam::123:role/SecurityAgentScanRole'
        mock_iam.create_role.assert_called_once()
        mock_iam.put_role_policy.assert_called_once()
        trust = _json.loads(mock_iam.create_role.call_args.kwargs['AssumeRolePolicyDocument'])
        stmt = trust['Statement'][0]
        assert stmt['Principal']['Service'] == 'securityagent.amazonaws.com'
        assert stmt['Condition']['StringEquals']['aws:SourceAccount'] == '123'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_service_role_already_exists(self, mock_boto3):
        """When role already exists, falls through to update_assume_role_policy."""
        mock_iam = MagicMock()

        # Build the EntityAlreadyExistsException class on the mock client
        class _AlreadyExists(Exception):
            """AlreadyExists."""

            pass

        mock_iam.exceptions.EntityAlreadyExistsException = _AlreadyExists
        mock_iam.create_role.side_effect = _AlreadyExists()
        mock_boto3.Session.return_value.client.return_value = mock_iam

        client = SecurityAgentClient(region='us-east-1')
        arn = client.create_service_role('SecurityAgentScanRole', '123', '')

        assert arn == 'arn:aws:iam::123:role/SecurityAgentScanRole'
        mock_iam.update_assume_role_policy.assert_called_once()
        mock_iam.put_role_policy.assert_called_once()

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_upload_to_s3(self, mock_boto3):
        """upload_to_s3 returns the s3:// URL and calls boto3.upload_file."""
        mock_s3 = MagicMock()
        mock_boto3.Session.return_value.client.return_value = mock_s3

        client = SecurityAgentClient()
        url = client.upload_to_s3('bkt', 'k.zip', '/tmp/source.zip')

        assert url == 's3://bkt/k.zip'
        mock_s3.upload_file.assert_called_once_with('/tmp/source.zip', 'bkt', 'k.zip')


class TestDiffScanAndThreatModel:
    """Tests for diff scan and threat model operations using standard SDK."""

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_start_code_review_job_with_diff_success(self, mock_boto3):
        """Diff scan job calls start_code_review_job with diffSource."""
        mock_client = MagicMock()
        mock_client.start_code_review_job.return_value = {'codeReviewJobId': 'cj-diff'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.start_code_review_job_with_diff('as-1', 'cr-1', 's3://b/k')
        assert result == {'codeReviewJobId': 'cj-diff'}
        mock_client.start_code_review_job.assert_called_once_with(
            agentSpaceId='as-1', codeReviewId='cr-1', diffSource={'s3Uri': 's3://b/k'}
        )

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_threat_model_with_scope_docs(self, mock_boto3):
        """create_threat_model includes scopeDocs when provided."""
        mock_client = MagicMock()
        mock_client.create_threat_model.return_value = {'threatModelId': 'tm-1'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.create_threat_model(
            agent_space_id='as-1',
            title='t',
            service_role='arn:role',
            assets={'sourceCode': []},
            scope_docs=[{'s3Location': 's3://b/spec.md'}],
        )
        assert result == {'threatModelId': 'tm-1'}
        kwargs = mock_client.create_threat_model.call_args.kwargs
        assert kwargs['scopeDocs'] == [{'s3Location': 's3://b/spec.md'}]

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_threat_model_without_scope_docs(self, mock_boto3):
        """create_threat_model omits scopeDocs when not provided."""
        mock_client = MagicMock()
        mock_client.create_threat_model.return_value = {'threatModelId': 'tm-2'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        client.create_threat_model(
            agent_space_id='as-1', title='t', service_role='arn:role', assets={}
        )
        kwargs = mock_client.create_threat_model.call_args.kwargs
        assert 'scopeDocs' not in kwargs

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_start_threat_model_job(self, mock_boto3):
        """start_threat_model_job calls the SDK method."""
        mock_client = MagicMock()
        mock_client.start_threat_model_job.return_value = {'threatModelJobId': 'tj-1'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.start_threat_model_job('as-1', 'tm-1')
        assert result == {'threatModelJobId': 'tj-1'}
        mock_client.start_threat_model_job.assert_called_once_with(
            agentSpaceId='as-1', threatModelId='tm-1'
        )

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_batch_get_threat_model_jobs(self, mock_boto3):
        """batch_get_threat_model_jobs calls the SDK method."""
        mock_client = MagicMock()
        mock_client.batch_get_threat_model_jobs.return_value = {'threatModelJobs': []}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.batch_get_threat_model_jobs('as-1', ['tj-1', 'tj-2'])
        assert result == {'threatModelJobs': []}
        mock_client.batch_get_threat_model_jobs.assert_called_once_with(
            agentSpaceId='as-1', threatModelJobIds=['tj-1', 'tj-2']
        )

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_list_threats_pagination(self, mock_boto3):
        """list_threats follows nextToken until exhausted and concatenates."""
        mock_client = MagicMock()
        mock_client.list_threats.side_effect = [
            {'threats': [{'threatId': 't-1'}], 'nextToken': 'tok'},
            {'threats': [{'threatId': 't-2'}]},
        ]
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.list_threats('as-1', 'tj-1')
        assert len(result['threats']) == 2
        assert mock_client.list_threats.call_count == 2

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_batch_get_threats(self, mock_boto3):
        """batch_get_threats calls the SDK method."""
        mock_client = MagicMock()
        mock_client.batch_get_threats.return_value = {'threats': [{'threatId': 't-1'}]}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.batch_get_threats('as-1', ['t-1'])
        assert result == {'threats': [{'threatId': 't-1'}]}
        mock_client.batch_get_threats.assert_called_once_with(
            agentSpaceId='as-1', threatIds=['t-1']
        )
