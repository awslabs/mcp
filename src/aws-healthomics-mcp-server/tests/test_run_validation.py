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

"""Tests for pre-run validation tools."""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.run_validation import (
    evaluate_healthomics_trust,
    extract_s3_uris,
    parse_ecr_image_uri,
    validate_run_readiness,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


ACCOUNT_ID = '123456789012'
ROLE_ARN = f'arn:aws:iam::{ACCOUNT_ID}:role/OmicsServiceRole'
OUTPUT_URI = 's3://my-output-bucket/healthomics/'

TRUSTING_POLICY = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Principal': {'Service': 'omics.amazonaws.com'},
            'Action': 'sts:AssumeRole',
        }
    ],
}


def _client_error(code: str, operation: str = 'Op') -> ClientError:
    """Build a ClientError with the given error code."""
    return ClientError({'Error': {'Code': code, 'Message': f'{code} message'}}, operation)


def _mock_session(region: str = 'us-east-1', s3_client=None):
    """Build a mock boto3 session exposing a mock S3 client."""
    session = MagicMock()
    session.region_name = region
    session.client.return_value = s3_client if s3_client is not None else MagicMock()
    return session


def _find(checks, name):
    """Find a check result by name."""
    for check in checks:
        if check['name'] == name:
            return check
    return None


class TestParseEcrImageUri:
    """Tests for parse_ecr_image_uri."""

    def test_uri_with_tag(self):
        """A standard ECR URI with a tag is parsed into its parts."""
        parts = parse_ecr_image_uri(
            '123456789012.dkr.ecr.us-east-1.amazonaws.com/my-prefix/my-repo:1.0'
        )
        assert parts is not None
        assert parts['account'] == '123456789012'
        assert parts['region'] == 'us-east-1'
        assert parts['repository'] == 'my-prefix/my-repo'
        assert parts['tag'] == '1.0'

    def test_uri_without_tag_defaults_to_latest(self):
        """A URI with no tag or digest defaults to the latest tag."""
        parts = parse_ecr_image_uri('123456789012.dkr.ecr.us-west-2.amazonaws.com/repo')
        assert parts is not None
        assert parts['tag'] == 'latest'

    def test_uri_with_digest(self):
        """A digest-pinned URI exposes the digest rather than a tag."""
        digest = 'sha256:' + 'a' * 64
        parts = parse_ecr_image_uri(f'123456789012.dkr.ecr.eu-west-1.amazonaws.com/repo@{digest}')
        assert parts is not None
        assert parts['digest'] == digest
        assert 'tag' not in parts

    def test_public_registry_uri_rejected(self):
        """A non-ECR URI is not parsed."""
        assert parse_ecr_image_uri('quay.io/biocontainers/bwa:0.7.17') is None
        assert parse_ecr_image_uri('ubuntu:20.04') is None
        assert parse_ecr_image_uri('public.ecr.aws/ubuntu/ubuntu:20.04') is None


class TestEvaluateHealthOmicsTrust:
    """Tests for evaluate_healthomics_trust."""

    REGION = 'us-east-1'
    ACCOUNT = '123456789012'

    def _eval(self, policy):
        return evaluate_healthomics_trust(policy, region=self.REGION, account_id=self.ACCOUNT)

    def test_passes_with_no_conditions(self):
        """A statement naming the omics principal without conditions passes."""
        status, detail = self._eval(TRUSTING_POLICY)
        assert status == 'pass'
        assert 'without conditions' in detail

    def test_passes_when_service_is_a_list(self):
        """The omics principal is found inside a list of services."""
        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': ['ec2.amazonaws.com', 'omics.amazonaws.com']},
                }
            ]
        }
        assert self._eval(policy)[0] == 'pass'

    def test_passes_when_source_arn_matches_run_region(self):
        """A SourceArn condition scoped to this region permits the run."""
        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Condition': {
                        'StringEquals': {'aws:SourceAccount': ACCOUNT_ID},
                        'ArnLike': {
                            'aws:SourceArn': f'arn:aws:omics:us-east-1:{ACCOUNT_ID}:run/*'
                        },
                    },
                }
            ]
        }
        status, detail = self._eval(policy)
        assert status == 'pass'
        assert 'permit a run' in detail

    def test_fails_when_source_arn_restricts_another_region(self):
        """A role scoped to another region cannot be assumed for this run.

        Observed against the service: the principal is present, so a check that only
        looks for it reports pass, and StartRun still rejects the role with
        'IAM role is invalid or inaccessible'.
        """
        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Condition': {
                        'StringEquals': {'aws:SourceAccount': ACCOUNT_ID},
                        'ArnLike': {
                            'aws:SourceArn': f'arn:aws:omics:ap-northeast-2:{ACCOUNT_ID}:run/*'
                        },
                    },
                }
            ]
        }
        status, detail = self._eval(policy)
        assert status == 'fail'
        assert 'ap-northeast-2' in detail
        assert 'us-east-1' in detail
        assert 'IAM role is invalid or inaccessible' in detail

    def test_passes_when_source_arn_region_is_wildcarded(self):
        """A wildcard region in SourceArn does not exclude any region."""
        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Condition': {
                        'ArnLike': {'aws:SourceArn': f'arn:aws:omics:*:{ACCOUNT_ID}:run/*'}
                    },
                }
            ]
        }
        assert self._eval(policy)[0] == 'pass'

    def test_fails_when_source_account_is_another_account(self):
        """A SourceAccount condition naming another account excludes this run."""
        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Condition': {'StringEquals': {'aws:SourceAccount': '999999999999'}},
                }
            ]
        }
        status, detail = self._eval(policy)
        assert status == 'fail'
        assert '999999999999' in detail

    def test_warns_on_conditions_it_cannot_evaluate(self):
        """An unrecognized condition key warns rather than silently passing."""
        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Condition': {'StringEquals': {'sts:ExternalId': 'secret'}},
                }
            ]
        }
        status, detail = self._eval(policy)
        assert status == 'warn'
        assert 'does not evaluate' in detail
        assert 'sts:ExternalId' in detail

    def test_passes_when_a_later_statement_permits(self):
        """A restricted statement does not mask a permissive one."""
        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Condition': {
                        'ArnLike': {'aws:SourceArn': f'arn:aws:omics:eu-west-1:{ACCOUNT_ID}:run/*'}
                    },
                },
                {'Effect': 'Allow', 'Principal': {'Service': 'omics.amazonaws.com'}},
            ]
        }
        assert self._eval(policy)[0] == 'pass'

    def test_fails_for_other_principal(self):
        """A policy that does not name the omics principal fails."""
        policy = {
            'Statement': [{'Effect': 'Allow', 'Principal': {'Service': 'ec2.amazonaws.com'}}]
        }
        status, detail = self._eval(policy)
        assert status == 'fail'
        assert 'does not allow' in detail

    def test_fails_for_deny_statement(self):
        """A Deny statement naming the omics principal does not grant access."""
        policy = {
            'Statement': [{'Effect': 'Deny', 'Principal': {'Service': 'omics.amazonaws.com'}}]
        }
        assert self._eval(policy)[0] == 'fail'

    def test_accepts_json_string_policy(self):
        """A policy supplied as a JSON string is decoded before evaluation."""
        import json

        assert self._eval(json.dumps(TRUSTING_POLICY))[0] == 'pass'

    def test_fails_on_malformed_input(self):
        """Malformed policies fail rather than raising."""
        assert self._eval('not json')[0] == 'fail'
        assert self._eval(None)[0] == 'fail'


class TestExtractS3Uris:
    """Tests for extract_s3_uris."""

    def test_flat_parameters(self):
        """S3 URIs in top-level string values are found."""
        params = {'reads': 's3://bucket/reads.fq', 'sample': 'NA12878'}
        assert extract_s3_uris(params) == ['s3://bucket/reads.fq']

    def test_nested_struct_and_array(self):
        """S3 URIs inside nested Structs and Arrays are found."""
        params = {
            'meta': {'ref': 's3://bucket/ref.fa'},
            'fastqs': ['s3://bucket/a.fq', 's3://bucket/b.fq'],
            'count': 3,
        }
        assert extract_s3_uris(params) == [
            's3://bucket/a.fq',
            's3://bucket/b.fq',
            's3://bucket/ref.fa',
        ]

    def test_deduplicates(self):
        """A URI repeated across parameters is reported once."""
        params = {'a': 's3://bucket/x.bam', 'b': 's3://bucket/x.bam'}
        assert extract_s3_uris(params) == ['s3://bucket/x.bam']

    def test_no_s3_uris(self):
        """Parameters with no S3 URIs produce an empty list."""
        assert extract_s3_uris({'name': 'World', 'n': 1}) == []


class TestValidateRunReadiness:
    """Tests for the validate_run_readiness tool."""

    @pytest.mark.asyncio
    async def test_all_checks_pass(self):
        """A correctly configured run reports ready with no failures."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {'Role': {'AssumeRolePolicyDocument': TRUSTING_POLICY}}
        iam.simulate_principal_policy.return_value = {
            'EvaluationResults': [{'EvalDecision': 'allowed'}]
        }

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': None}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(s3_client=s3),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
            )

        assert result['ready'] is True
        assert _find(result['checks'], 'workflow_active')['status'] == 'pass'
        assert _find(result['checks'], 'role_trust_policy')['status'] == 'pass'
        assert _find(result['checks'], 'output_bucket_region')['status'] == 'pass'
        assert _find(result['checks'], 'role_s3_write')['status'] == 'pass'

    @pytest.mark.asyncio
    async def test_bucket_region_mismatch_fails(self):
        """An output bucket in another region is reported as a failure."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {'Role': {'AssumeRolePolicyDocument': TRUSTING_POLICY}}
        iam.simulate_principal_policy.return_value = {
            'EvaluationResults': [{'EvalDecision': 'allowed'}]
        }

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': 'ap-northeast-2'}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(region='us-east-1', s3_client=s3),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
            )

        assert result['ready'] is False
        region_check = _find(result['checks'], 'output_bucket_region')
        assert region_check['status'] == 'fail'
        assert 'ap-northeast-2' in region_check['detail']
        assert 'us-east-1' in region_check['detail']

    @pytest.mark.asyncio
    async def test_missing_trust_policy_fails(self):
        """A role that does not trust HealthOmics is reported as a failure."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {
            'Role': {
                'AssumeRolePolicyDocument': {
                    'Statement': [
                        {'Effect': 'Allow', 'Principal': {'Service': 'ec2.amazonaws.com'}}
                    ]
                }
            }
        }
        iam.simulate_principal_policy.return_value = {
            'EvaluationResults': [{'EvalDecision': 'allowed'}]
        }

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': None}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(s3_client=s3),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
            )

        assert result['ready'] is False
        assert _find(result['checks'], 'role_trust_policy')['status'] == 'fail'

    @pytest.mark.asyncio
    async def test_region_restricted_role_fails_even_when_writable(self):
        """A role scoped to another region fails on the trust check alone.

        Verified against the service: such a role names the omics principal, so a
        check that only looks for the principal reports pass, while StartRun rejects
        the role with 'IAM role is invalid or inaccessible'. Every other check here
        passes, so the trust check has to be what fails.
        """
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {
            'Role': {
                'AssumeRolePolicyDocument': {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Condition': {
                                'StringEquals': {'aws:SourceAccount': ACCOUNT_ID},
                                'ArnLike': {
                                    'aws:SourceArn': (
                                        f'arn:aws:omics:ap-northeast-2:{ACCOUNT_ID}:run/*'
                                    )
                                },
                            },
                        }
                    ]
                }
            }
        }
        iam.simulate_principal_policy.return_value = {
            'EvaluationResults': [{'EvalDecision': 'allowed'}]
        }

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': None}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(region='us-east-1', s3_client=s3),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
            )

        assert result['ready'] is False
        trust = _find(result['checks'], 'role_trust_policy')
        assert trust['status'] == 'fail'
        assert 'ap-northeast-2' in trust['detail']
        # Everything else is fine, so the trust check is the only failure
        assert [c['name'] for c in result['checks'] if c['status'] == 'fail'] == [
            'role_trust_policy'
        ]

    @pytest.mark.asyncio
    async def test_simulate_permission_denied_warns(self):
        """Missing iam:SimulatePrincipalPolicy warns rather than fails."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {'Role': {'AssumeRolePolicyDocument': TRUSTING_POLICY}}
        iam.simulate_principal_policy.side_effect = _client_error('AccessDenied')

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': None}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(s3_client=s3),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
            )

        write_check = _find(result['checks'], 'role_s3_write')
        assert write_check['status'] == 'warn'
        # A warning alone must not block the run
        assert result['ready'] is True

    @pytest.mark.asyncio
    async def test_non_active_workflow_fails(self):
        """A workflow that is not ACTIVE is reported as a failure."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {
            'status': 'FAILED',
            'statusMessage': 'Invalid zip file',
        }

        iam = MagicMock()
        iam.get_role.return_value = {'Role': {'AssumeRolePolicyDocument': TRUSTING_POLICY}}
        iam.simulate_principal_policy.return_value = {
            'EvaluationResults': [{'EvalDecision': 'allowed'}]
        }

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': None}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(s3_client=s3),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
            )

        assert result['ready'] is False
        workflow_check = _find(result['checks'], 'workflow_active')
        assert workflow_check['status'] == 'fail'
        assert 'Invalid zip file' in workflow_check['detail']

    @pytest.mark.asyncio
    async def test_missing_input_object_fails(self):
        """An input S3 object that does not exist is reported as a failure."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {'Role': {'AssumeRolePolicyDocument': TRUSTING_POLICY}}
        iam.simulate_principal_policy.return_value = {
            'EvaluationResults': [{'EvalDecision': 'allowed'}]
        }

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': None}
        s3.head_object.side_effect = _client_error('404')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(s3_client=s3),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
                parameters={'reads': 's3://bucket/missing.fq'},
            )

        assert result['ready'] is False
        input_check = _find(result['checks'], 'input:s3://bucket/missing.fq')
        assert input_check['status'] == 'fail'
        assert 'not found' in input_check['detail'].lower()

    @pytest.mark.asyncio
    async def test_container_check_reuses_ecr_tool(self):
        """Container checks delegate to check_container_availability."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {'Role': {'AssumeRolePolicyDocument': TRUSTING_POLICY}}
        iam.simulate_principal_policy.return_value = {
            'EvaluationResults': [{'EvalDecision': 'allowed'}]
        }

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': None}

        image = '123456789012.dkr.ecr.us-east-1.amazonaws.com/ecr-public/ubuntu/ubuntu:20.04'

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(s3_client=s3),
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.check_container_availability',
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_check.return_value = {
                'available': True,
                'healthomics_accessible': 'accessible',
                'message': 'Image available',
            }
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
                container_images=[image],
            )

        mock_check.assert_awaited_once()
        assert mock_check.await_args.kwargs['repository_name'] == 'ecr-public/ubuntu/ubuntu'
        assert mock_check.await_args.kwargs['image_tag'] == '20.04'
        assert _find(result['checks'], f'container:{image}')['status'] == 'pass'
        assert result['ready'] is True

    @pytest.mark.asyncio
    async def test_public_container_uri_fails(self):
        """A public registry image URI is reported as a failure."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {'Role': {'AssumeRolePolicyDocument': TRUSTING_POLICY}}
        iam.simulate_principal_policy.return_value = {
            'EvaluationResults': [{'EvalDecision': 'allowed'}]
        }

        s3 = MagicMock()
        s3.head_bucket.return_value = {}
        s3.get_bucket_location.return_value = {'LocationConstraint': None}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(s3_client=s3),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
                container_images=['quay.io/biocontainers/bwa:0.7.17'],
            )

        assert result['ready'] is False
        check = _find(result['checks'], 'container:quay.io/biocontainers/bwa:0.7.17')
        assert check['status'] == 'fail'
        assert 'ECR' in check['detail']

    @pytest.mark.asyncio
    async def test_invalid_output_uri_fails(self):
        """An output URI that is not an S3 URI is reported as a failure."""
        ctx = AsyncMock()

        omics = MagicMock()
        omics.get_workflow.return_value = {'status': 'ACTIVE'}

        iam = MagicMock()
        iam.get_role.return_value = {'Role': {'AssumeRolePolicyDocument': TRUSTING_POLICY}}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_omics_client',
                return_value=omics,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_iam_client',
                return_value=iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
                return_value=_mock_session(),
            ),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri='/local/path/outputs',
            )

        assert result['ready'] is False
        assert _find(result['checks'], 'output_uri_format')['status'] == 'fail'

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_error_dict(self):
        """An unexpected exception is surfaced through handle_tool_error."""
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_validation.get_aws_session',
            side_effect=RuntimeError('boom'),
        ):
            result = await validate_run_readiness(
                ctx,
                workflow_id='1234567',
                role_arn=ROLE_ARN,
                output_uri=OUTPUT_URI,
            )

        assert 'error' in result
        assert 'boom' in result['error']
        ctx.error.assert_called_once()
