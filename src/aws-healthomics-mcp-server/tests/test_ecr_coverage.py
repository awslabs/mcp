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

"""Additional tests for ECR tools and utils to improve coverage.

These tests target specific uncovered code paths identified by coverage analysis.
"""

import botocore
import botocore.exceptions
import json
import pytest
from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
    _check_pull_through_cache_healthomics_usability,
    _is_pull_through_cache_repository,
    check_container_availability,
    create_container_registry_map,
    list_ecr_repositories,
    validate_healthomics_ecr_config,
)
from awslabs.aws_healthomics_mcp_server.utils.ecr_utils import (
    _check_actions_allowed,
    _check_principal_match,
    _normalize_actions,
    _parse_policy_document,
    check_registry_policy_healthomics_access,
    check_repository_template_healthomics_access,
    initiate_pull_through_cache,
)
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Tests for ecr_utils.py - Utility Functions
# =============================================================================


class TestNormalizeActions:
    """Tests for _normalize_actions utility function."""

    def test_normalize_actions_with_none(self):
        """Test that None returns empty set."""
        result = _normalize_actions(None)
        assert result == set()

    def test_normalize_actions_with_string(self):
        """Test that a single string is normalized to lowercase set."""
        result = _normalize_actions('ECR:BatchGetImage')
        assert result == {'ecr:batchgetimage'}

    def test_normalize_actions_with_list(self):
        """Test that a list of strings is normalized to lowercase set."""
        result = _normalize_actions(['ECR:BatchGetImage', 'ECR:GetDownloadUrlForLayer'])
        assert result == {'ecr:batchgetimage', 'ecr:getdownloadurlforlayer'}

    def test_normalize_actions_with_mixed_list(self):
        """Test that non-string items in list are filtered out."""
        result = _normalize_actions(['ECR:BatchGetImage', 123, None, 'ECR:GetDownloadUrlForLayer'])
        assert result == {'ecr:batchgetimage', 'ecr:getdownloadurlforlayer'}

    def test_normalize_actions_with_invalid_type(self):
        """Test that invalid types return empty set."""
        result = _normalize_actions(12345)
        assert result == set()

    def test_normalize_actions_with_dict(self):
        """Test that dict returns empty set."""
        result = _normalize_actions({'action': 'ecr:BatchGetImage'})
        assert result == set()


class TestCheckPrincipalMatch:
    """Tests for _check_principal_match utility function."""

    def test_principal_match_with_none(self):
        """Test that None principal returns False."""
        result = _check_principal_match(None, 'omics.amazonaws.com')
        assert result is False

    def test_principal_match_with_wildcard(self):
        """Test that wildcard principal matches any target."""
        result = _check_principal_match('*', 'omics.amazonaws.com')
        assert result is True

    def test_principal_match_with_string_match(self):
        """Test that string principal matches when equal."""
        result = _check_principal_match('omics.amazonaws.com', 'omics.amazonaws.com')
        assert result is True

    def test_principal_match_with_string_no_match(self):
        """Test that string principal doesn't match when different."""
        result = _check_principal_match('other.amazonaws.com', 'omics.amazonaws.com')
        assert result is False

    def test_principal_match_with_service_dict_string(self):
        """Test that Service dict with string matches."""
        principal = {'Service': 'omics.amazonaws.com'}
        result = _check_principal_match(principal, 'omics.amazonaws.com')
        assert result is True

    def test_principal_match_with_service_dict_list(self):
        """Test that Service dict with list matches."""
        principal = {'Service': ['omics.amazonaws.com', 'other.amazonaws.com']}
        result = _check_principal_match(principal, 'omics.amazonaws.com')
        assert result is True

    def test_principal_match_with_aws_dict_string(self):
        """Test that AWS dict with string matches."""
        principal = {'AWS': 'omics.amazonaws.com'}
        result = _check_principal_match(principal, 'omics.amazonaws.com')
        assert result is True

    def test_principal_match_with_aws_dict_wildcard(self):
        """Test that AWS dict with wildcard matches."""
        principal = {'AWS': '*'}
        result = _check_principal_match(principal, 'omics.amazonaws.com')
        assert result is True

    def test_principal_match_with_aws_dict_list(self):
        """Test that AWS dict with list matches."""
        principal = {'AWS': ['arn:aws:iam::123456789012:root', 'omics.amazonaws.com']}
        result = _check_principal_match(principal, 'omics.amazonaws.com')
        assert result is True

    def test_principal_match_with_aws_dict_list_wildcard(self):
        """Test that AWS dict with list containing wildcard matches."""
        principal = {'AWS': ['arn:aws:iam::123456789012:root', '*']}
        result = _check_principal_match(principal, 'omics.amazonaws.com')
        assert result is True

    def test_principal_match_with_empty_dict(self):
        """Test that empty dict returns False."""
        result = _check_principal_match({}, 'omics.amazonaws.com')
        assert result is False


class TestCheckActionsAllowed:
    """Tests for _check_actions_allowed utility function."""

    def test_exact_match_allowed(self):
        """Test that exact action match is allowed."""
        statement_actions = {'ecr:batchgetimage', 'ecr:getdownloadurlforlayer'}
        required_actions = ['ecr:BatchGetImage']
        allowed, missing = _check_actions_allowed(statement_actions, required_actions)
        assert allowed is True
        assert missing == []

    def test_service_wildcard_allowed(self):
        """Test that service-level wildcard allows all actions."""
        statement_actions = {'ecr:*'}
        required_actions = ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer']
        allowed, missing = _check_actions_allowed(statement_actions, required_actions)
        assert allowed is True
        assert missing == []

    def test_global_wildcard_allowed(self):
        """Test that global wildcard allows all actions."""
        statement_actions = {'*'}
        required_actions = ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer']
        allowed, missing = _check_actions_allowed(statement_actions, required_actions)
        assert allowed is True
        assert missing == []

    def test_missing_actions_returned(self):
        """Test that missing actions are correctly identified."""
        statement_actions = {'ecr:batchgetimage'}
        required_actions = ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer']
        allowed, missing = _check_actions_allowed(statement_actions, required_actions)
        assert allowed is False
        assert missing == ['ecr:GetDownloadUrlForLayer']

    def test_wildcards_disabled(self):
        """Test that wildcards can be disabled."""
        statement_actions = {'ecr:*'}
        required_actions = ['ecr:BatchGetImage']
        allowed, missing = _check_actions_allowed(
            statement_actions, required_actions, allow_wildcards=False
        )
        assert allowed is False
        assert missing == ['ecr:BatchGetImage']


class TestParsePolicyDocument:
    """Tests for _parse_policy_document utility function."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON policy."""
        policy_text = '{"Version": "2012-10-17", "Statement": []}'
        result = _parse_policy_document(policy_text)
        assert result == {'Version': '2012-10-17', 'Statement': []}

    def test_parse_none_returns_none(self):
        """Test that None input returns None."""
        result = _parse_policy_document(None)
        assert result is None

    def test_parse_invalid_json_returns_none(self):
        """Test that invalid JSON returns None."""
        result = _parse_policy_document('not valid json')
        assert result is None


class TestCheckRegistryPolicyHealthOmicsAccess:
    """Tests for check_registry_policy_healthomics_access function."""

    def test_no_policy_returns_not_granted(self):
        """Test that None policy returns not granted with all missing actions."""
        granted, missing = check_registry_policy_healthomics_access(None)
        assert granted is False
        assert len(missing) > 0

    def test_invalid_json_returns_not_granted(self):
        """Test that invalid JSON returns not granted."""
        granted, missing = check_registry_policy_healthomics_access('invalid json')
        assert granted is False
        assert len(missing) > 0

    def test_valid_policy_with_healthomics_access(self):
        """Test that valid policy with HealthOmics access returns granted."""
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                }
            ],
        }
        granted, missing = check_registry_policy_healthomics_access(json.dumps(policy))
        assert granted is True
        assert missing == []

    def test_policy_with_deny_effect_ignored(self):
        """Test that Deny statements are ignored."""
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Deny',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                }
            ],
        }
        granted, missing = check_registry_policy_healthomics_access(json.dumps(policy))
        assert granted is False

    def test_policy_with_wrong_principal_ignored(self):
        """Test that statements with wrong principal are ignored."""
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'other.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                }
            ],
        }
        granted, missing = check_registry_policy_healthomics_access(json.dumps(policy))
        assert granted is False

    def test_policy_with_single_statement_dict(self):
        """Test that single statement as dict (not list) is handled."""
        policy = {
            'Version': '2012-10-17',
            'Statement': {
                'Effect': 'Allow',
                'Principal': {'Service': 'omics.amazonaws.com'},
                'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
            },
        }
        granted, missing = check_registry_policy_healthomics_access(json.dumps(policy))
        assert granted is True


class TestCheckRepositoryTemplateHealthOmicsAccess:
    """Tests for check_repository_template_healthomics_access function."""

    def test_no_template_returns_not_exists(self):
        """Test that None template returns template doesn't exist."""
        exists, granted, missing = check_repository_template_healthomics_access(None)
        assert exists is False
        assert granted is False
        assert len(missing) > 0

    def test_invalid_json_returns_exists_but_not_granted(self):
        """Test that invalid JSON returns exists but not granted."""
        exists, granted, missing = check_repository_template_healthomics_access('invalid json')
        assert exists is True
        assert granted is False
        assert len(missing) > 0

    def test_valid_template_with_healthomics_access(self):
        """Test that valid template with HealthOmics access returns granted."""
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                }
            ],
        }
        exists, granted, missing = check_repository_template_healthomics_access(json.dumps(policy))
        assert exists is True
        assert granted is True
        assert missing == []

    def test_template_with_single_statement_dict(self):
        """Test that single statement as dict is handled."""
        policy = {
            'Version': '2012-10-17',
            'Statement': {
                'Effect': 'Allow',
                'Principal': {'Service': 'omics.amazonaws.com'},
                'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
            },
        }
        exists, granted, missing = check_repository_template_healthomics_access(json.dumps(policy))
        assert exists is True
        assert granted is True


class TestInitiatePullThroughCache:
    """Tests for initiate_pull_through_cache function."""

    def test_successful_pull_through(self):
        """Test successful pull-through cache initiation."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [
                {
                    'imageId': {
                        'imageDigest': 'sha256:abc123',
                        'imageTag': 'latest',
                    }
                }
            ],
            'failures': [],
        }

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_tag='latest'
        )

        assert success is True
        assert 'successfully' in message.lower()
        assert details is not None
        assert details['imageDigest'] == 'sha256:abc123'

    def test_pull_through_with_digest(self):
        """Test pull-through cache with digest instead of tag."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [
                {
                    'imageId': {
                        'imageDigest': 'sha256:abc123',
                    }
                }
            ],
            'failures': [],
        }

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_digest='sha256:abc123'
        )

        assert success is True
        mock_client.batch_get_image.assert_called_once()
        call_args = mock_client.batch_get_image.call_args
        assert call_args[1]['imageIds'] == [{'imageDigest': 'sha256:abc123'}]

    def test_pull_through_image_not_found_failure(self):
        """Test pull-through when image not found in upstream."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [],
            'failures': [
                {
                    'failureCode': 'ImageNotFound',
                    'failureReason': 'Image does not exist in upstream registry',
                }
            ],
        }

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/nonexistent', image_tag='latest'
        )

        assert success is False
        assert 'not found' in message.lower()
        assert details is None

    def test_pull_through_repository_not_found_failure(self):
        """Test pull-through when repository not found."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [],
            'failures': [
                {
                    'failureCode': 'RepositoryNotFound',
                    'failureReason': 'Repository does not exist',
                }
            ],
        }

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/nonexistent/repo', image_tag='latest'
        )

        assert success is False
        assert 'not found' in message.lower()
        assert details is None

    def test_pull_through_other_failure(self):
        """Test pull-through with other failure code."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [],
            'failures': [
                {
                    'failureCode': 'UnknownError',
                    'failureReason': 'Something went wrong',
                }
            ],
        }

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_tag='latest'
        )

        assert success is False
        assert 'failed' in message.lower()
        assert details is None

    def test_pull_through_no_images_no_failures(self):
        """Test pull-through when response has no images and no failures."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [],
            'failures': [],
        }

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_tag='latest'
        )

        assert success is False
        assert 'no images' in message.lower()
        assert details is None

    def test_pull_through_repository_not_found_exception(self):
        """Test pull-through when RepositoryNotFoundException is raised."""
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'RepositoryNotFoundException',
                'Message': 'Repository does not exist',
            }
        }
        mock_client.batch_get_image.side_effect = botocore.exceptions.ClientError(
            error_response, 'BatchGetImage'
        )

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_tag='latest'
        )

        assert success is False
        assert 'does not exist' in message.lower()
        assert details is None

    def test_pull_through_image_not_found_exception(self):
        """Test pull-through when ImageNotFoundException is raised."""
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'ImageNotFoundException',
                'Message': 'Image not found',
            }
        }
        mock_client.batch_get_image.side_effect = botocore.exceptions.ClientError(
            error_response, 'BatchGetImage'
        )

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_tag='latest'
        )

        assert success is False
        assert 'not found' in message.lower()
        assert details is None

    def test_pull_through_access_denied_exception(self):
        """Test pull-through when AccessDeniedException is raised."""
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied',
            }
        }
        mock_client.batch_get_image.side_effect = botocore.exceptions.ClientError(
            error_response, 'BatchGetImage'
        )

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_tag='latest'
        )

        assert success is False
        assert 'access denied' in message.lower()
        assert details is None

    def test_pull_through_other_client_error(self):
        """Test pull-through when other ClientError is raised."""
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'InternalServerError',
                'Message': 'Internal error',
            }
        }
        mock_client.batch_get_image.side_effect = botocore.exceptions.ClientError(
            error_response, 'BatchGetImage'
        )

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_tag='latest'
        )

        assert success is False
        assert 'failed' in message.lower()
        assert details is None

    def test_pull_through_unexpected_exception(self):
        """Test pull-through when unexpected exception is raised."""
        mock_client = MagicMock()
        mock_client.batch_get_image.side_effect = Exception('Unexpected error')

        success, message, details = initiate_pull_through_cache(
            mock_client, 'docker-hub/library/ubuntu', image_tag='latest'
        )

        assert success is False
        assert 'unexpected' in message.lower()
        assert details is None

    def test_pull_through_default_tag(self):
        """Test pull-through uses 'latest' as default tag."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [{'imageId': {'imageDigest': 'sha256:abc', 'imageTag': 'latest'}}],
            'failures': [],
        }

        initiate_pull_through_cache(mock_client, 'docker-hub/library/ubuntu')

        call_args = mock_client.batch_get_image.call_args
        assert call_args[1]['imageIds'] == [{'imageTag': 'latest'}]


# =============================================================================
# Tests for ecr_tools.py - Private Functions
# =============================================================================


class TestIsPullThroughCacheRepository:
    """Additional tests for _is_pull_through_cache_repository function."""

    def test_other_client_error_fallback(self):
        """Test fallback to default prefixes on non-AccessDenied ClientError."""
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'InternalServerError',
                'Message': 'Internal error',
            }
        }
        mock_client.describe_pull_through_cache_rules.side_effect = (
            botocore.exceptions.ClientError(error_response, 'DescribePullThroughCacheRules')
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            # Should fall back to default prefix check
            result = _is_pull_through_cache_repository('docker-hub/library/ubuntu')

        assert result is True

    def test_unexpected_exception_fallback(self):
        """Test fallback to default prefixes on unexpected exception."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.side_effect = Exception('Unexpected')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _is_pull_through_cache_repository('docker-hub/library/ubuntu')

        assert result is True

    def test_pagination_handling(self):
        """Test that pagination is handled correctly."""
        mock_client = MagicMock()
        # First page returns nextToken, second page doesn't
        mock_client.describe_pull_through_cache_rules.side_effect = [
            {
                'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}],
                'nextToken': 'token123',
            },
            {
                'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'quay'}],
            },
        ]

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _is_pull_through_cache_repository('quay/myimage')

        assert result is True
        assert mock_client.describe_pull_through_cache_rules.call_count == 2


class TestCheckPullThroughCacheHealthOmicsUsability:
    """Tests for _check_pull_through_cache_healthomics_usability function."""

    def test_no_matching_rule(self):
        """Test when no matching PTC rule exists."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'other-prefix'}]
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is False
        assert result['healthomics_usable'] is False

    def test_matching_rule_with_full_permissions(self):
        """Test when matching rule exists with full HealthOmics permissions."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {'ecrRepositoryPrefix': 'docker-hub', 'upstreamRegistryUrl': 'https://docker.io'}
            ]
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                        }
                    ],
                }
            )
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'repositoryPolicy': json.dumps(
                        {
                            'Version': '2012-10-17',
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'omics.amazonaws.com'},
                                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                                }
                            ],
                        }
                    )
                }
            ]
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True
        assert result['healthomics_usable'] is True

    def test_registry_policy_not_found(self):
        """Test when registry policy doesn't exist."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }
        error_response = {
            'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRegistryPolicy'
        )
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': []
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True
        assert result['healthomics_usable'] is False

    def test_registry_policy_other_error(self):
        """Test when registry policy fetch fails with other error."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }
        error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'Error'}}
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRegistryPolicy'
        )
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': []
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True

    def test_template_not_found(self):
        """Test when repository creation template doesn't exist."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }
        mock_client.get_registry_policy.return_value = {'policyText': '{}'}
        error_response = {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}}
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(error_response, 'DescribeRepositoryCreationTemplates')
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True
        assert result['healthomics_usable'] is False

    def test_template_other_error(self):
        """Test when template fetch fails with other error."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }
        mock_client.get_registry_policy.return_value = {'policyText': '{}'}
        error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'Error'}}
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(error_response, 'DescribeRepositoryCreationTemplates')
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True

    def test_unexpected_exception(self):
        """Test when unexpected exception occurs."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.side_effect = Exception('Unexpected')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is False
        assert result['healthomics_usable'] is False

    def test_pagination_handling(self):
        """Test that pagination is handled when fetching PTC rules."""
        mock_client = MagicMock()
        mock_client.describe_pull_through_cache_rules.side_effect = [
            {'pullThroughCacheRules': [], 'nextToken': 'token1'},
            {'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]},
        ]
        mock_client.get_registry_policy.return_value = {'policyText': '{}'}
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': []
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True
        assert mock_client.describe_pull_through_cache_rules.call_count == 2


# =============================================================================
# Tests for check_container_availability - Pull-Through Initiation
# =============================================================================


class TestCheckContainerAvailabilityPullThroughInitiation:
    """Tests for check_container_availability with initiate_pull_through=True."""

    @pytest.mark.asyncio
    async def test_initiate_pull_through_on_repo_not_found_success(self):
        """Test successful pull-through initiation when repository not found."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        # First call raises RepositoryNotFoundException
        error_response = {'Error': {'Code': 'RepositoryNotFoundException', 'Message': 'Not found'}}
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        # PTC rules exist
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }

        # Registry policy and template grant HealthOmics access
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                        }
                    ]
                }
            )
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'repositoryPolicy': json.dumps(
                        {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'omics.amazonaws.com'},
                                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                                }
                            ]
                        }
                    )
                }
            ]
        }

        # batch_get_image succeeds
        mock_client.batch_get_image.return_value = {
            'images': [{'imageId': {'imageDigest': 'sha256:abc', 'imageTag': 'latest'}}],
            'failures': [],
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                image_digest=None,
                initiate_pull_through=True,
            )

        assert result['available'] is True
        assert result['pull_through_initiated'] is True

    @pytest.mark.asyncio
    async def test_initiate_pull_through_on_repo_not_found_not_usable(self):
        """Test pull-through not initiated when PTC not usable by HealthOmics."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        error_response = {'Error': {'Code': 'RepositoryNotFoundException', 'Message': 'Not found'}}
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        # PTC rules exist but no permissions
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }
        error_response2 = {
            'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            error_response2, 'GetRegistryPolicy'
        )
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': []
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                image_digest=None,
                initiate_pull_through=True,
            )

        assert result['available'] is False
        assert result['pull_through_initiated'] is False
        assert 'not usable' in result['pull_through_initiation_message'].lower()

    @pytest.mark.asyncio
    async def test_initiate_pull_through_on_image_not_found_success(self):
        """Test successful pull-through initiation when image not found."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        error_response = {'Error': {'Code': 'ImageNotFoundException', 'Message': 'Not found'}}
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                        }
                    ]
                }
            )
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'repositoryPolicy': json.dumps(
                        {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'omics.amazonaws.com'},
                                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                                }
                            ]
                        }
                    )
                }
            ]
        }
        mock_client.batch_get_image.return_value = {
            'images': [{'imageId': {'imageDigest': 'sha256:abc', 'imageTag': 'latest'}}],
            'failures': [],
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                image_digest=None,
                initiate_pull_through=True,
            )

        assert result['available'] is True
        assert result['pull_through_initiated'] is True

    @pytest.mark.asyncio
    async def test_initiate_pull_through_failure(self):
        """Test when pull-through initiation fails."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        error_response = {'Error': {'Code': 'ImageNotFoundException', 'Message': 'Not found'}}
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                        }
                    ]
                }
            )
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'repositoryPolicy': json.dumps(
                        {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'omics.amazonaws.com'},
                                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                                }
                            ]
                        }
                    )
                }
            ]
        }
        # batch_get_image fails
        mock_client.batch_get_image.return_value = {
            'images': [],
            'failures': [{'failureCode': 'ImageNotFound', 'failureReason': 'Not in upstream'}],
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                image_digest=None,
                initiate_pull_through=True,
            )

        assert result['available'] is False
        assert result['pull_through_initiated'] is False

    @pytest.mark.asyncio
    async def test_no_initiate_when_not_ptc(self):
        """Test that pull-through is not initiated for non-PTC repositories."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        error_response = {'Error': {'Code': 'RepositoryNotFoundException', 'Message': 'Not found'}}
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        # No PTC rules match
        mock_client.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-private-repo',
                image_tag='latest',
                image_digest=None,
                initiate_pull_through=True,
            )

        assert result['available'] is False
        assert result['is_pull_through_cache'] is False
        # batch_get_image should not be called
        mock_client.batch_get_image.assert_not_called()


class TestCheckContainerAvailabilityEdgeCases:
    """Additional edge case tests for check_container_availability."""

    @pytest.mark.asyncio
    async def test_empty_image_details_response(self):
        """Test when describe_images returns empty imageDetails."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_images.return_value = {'imageDetails': []}
        mock_client.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
                initiate_pull_through=False,
            )

        assert result['available'] is False
        assert 'not found' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_botocore_error_handling(self):
        """Test BotoCoreError handling."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_images.side_effect = botocore.exceptions.BotoCoreError()
        mock_client.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
                initiate_pull_through=False,
            )

        assert 'error' in result
        assert 'Error' in result['error']

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self):
        """Test unexpected exception handling."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_images.side_effect = Exception('Unexpected error')
        mock_client.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
                initiate_pull_through=False,
            )

        assert 'error' in result
        assert 'Error' in result['error']


# =============================================================================
# Tests for list_ecr_repositories - Edge Cases
# =============================================================================


class TestListECRRepositoriesEdgeCases:
    """Additional edge case tests for list_ecr_repositories."""

    @pytest.mark.asyncio
    async def test_unexpected_exception(self):
        """Test unexpected exception handling."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_repositories.side_effect = Exception('Unexpected error')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        assert 'error' in result
        assert 'Error' in result['error']


# =============================================================================
# Tests for validate_healthomics_ecr_config - Additional Scenarios
# =============================================================================


class TestValidateHealthOmicsECRConfigAdditional:
    """Additional tests for validate_healthomics_ecr_config."""

    @pytest.mark.asyncio
    async def test_registry_policy_missing_actions(self):
        """Test validation when registry policy is missing some actions."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [{'ecrRepositoryPrefix': 'docker-hub'}]
        }
        # Policy exists but missing BatchImportUpstreamImage
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository'],  # Missing BatchImportUpstreamImage
                        }
                    ]
                }
            )
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'repositoryPolicy': json.dumps(
                        {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'omics.amazonaws.com'},
                                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                                }
                            ]
                        }
                    )
                }
            ]
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        assert result['valid'] is False
        assert any('registry_policy' in issue['component'] for issue in result['issues'])

    @pytest.mark.asyncio
    async def test_template_without_policy(self):
        """Test validation when template exists but has no policy."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {'ecrRepositoryPrefix': 'docker-hub', 'upstreamRegistryUrl': 'https://docker.io'}
            ]
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                        }
                    ]
                }
            )
        }
        # Template exists but has no repositoryPolicy
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [{'prefix': 'docker-hub'}]  # No repositoryPolicy
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        assert result['valid'] is False

    @pytest.mark.asyncio
    async def test_template_missing_permissions(self):
        """Test validation when template policy is missing permissions."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {'ecrRepositoryPrefix': 'docker-hub', 'upstreamRegistryUrl': 'https://docker.io'}
            ]
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                        }
                    ]
                }
            )
        }
        # Template policy missing GetDownloadUrlForLayer
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'repositoryPolicy': json.dumps(
                        {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'omics.amazonaws.com'},
                                    'Action': [
                                        'ecr:BatchGetImage'
                                    ],  # Missing GetDownloadUrlForLayer
                                }
                            ]
                        }
                    )
                }
            ]
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        assert result['valid'] is False
        assert any('repository_template' in issue['component'] for issue in result['issues'])

    @pytest.mark.asyncio
    async def test_unexpected_exception(self):
        """Test unexpected exception handling."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_pull_through_cache_rules.side_effect = Exception('Unexpected')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        assert 'error' in result
        assert 'Error' in result['error']


# =============================================================================
# Tests for create_container_registry_map
# =============================================================================


class TestCreateContainerRegistryMap:
    """Tests for create_container_registry_map function."""

    @pytest.mark.asyncio
    async def test_successful_map_creation_with_discovered_caches(self):
        """Test successful map creation with discovered PTC rules."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        # Mock PTC rules discovery
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'https://registry-1.docker.io',
                }
            ]
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                        }
                    ]
                }
            )
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'repositoryPolicy': json.dumps(
                        {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'omics.amazonaws.com'},
                                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                                }
                            ]
                        }
                    )
                }
            ]
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id=None,
                ecr_region=None,
                include_pull_through_caches=True,
                additional_registry_mappings=None,
                image_mappings=None,
                output_format='json',
            )

        assert result['success'] is True
        assert result['account_id'] == '123456789012'
        assert result['region'] == 'us-east-1'
        assert result['discovered_healthomics_usable_caches'] == 1
        assert 'registryMappings' in result['container_registry_map']

    @pytest.mark.asyncio
    async def test_map_creation_with_explicit_account_and_region(self):
        """Test map creation with explicit account ID and region."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id='987654321098',
                ecr_region='eu-west-1',
                include_pull_through_caches=True,
                additional_registry_mappings=None,
                image_mappings=None,
                output_format='json',
            )

        assert result['success'] is True
        assert result['account_id'] == '987654321098'
        assert result['region'] == 'eu-west-1'

    @pytest.mark.asyncio
    async def test_map_creation_without_ptc_discovery(self):
        """Test map creation with include_pull_through_caches=False."""
        mock_ctx = AsyncMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id=None,
                ecr_region=None,
                include_pull_through_caches=False,
                additional_registry_mappings=[
                    {
                        'upstreamRegistryUrl': 'https://custom.registry.io',
                        'ecrRepositoryPrefix': 'custom',
                    }
                ],
                image_mappings=None,
                output_format='json',
            )

        assert result['success'] is True
        assert result['discovered_healthomics_usable_caches'] == 0
        assert 'registryMappings' in result['container_registry_map']
        assert len(result['container_registry_map']['registryMappings']) == 1

    @pytest.mark.asyncio
    async def test_map_creation_with_image_mappings(self):
        """Test map creation with image mappings."""
        mock_ctx = AsyncMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id=None,
                ecr_region=None,
                include_pull_through_caches=False,
                additional_registry_mappings=None,
                image_mappings=[
                    {
                        'sourceImage': 'ubuntu:latest',
                        'destinationImage': '123456789012.dkr.ecr.us-east-1.amazonaws.com/ubuntu:latest',
                    }
                ],
                output_format='json',
            )

        assert result['success'] is True
        assert 'imageMappings' in result['container_registry_map']
        assert len(result['container_registry_map']['imageMappings']) == 1

    @pytest.mark.asyncio
    async def test_map_creation_with_invalid_registry_mapping(self):
        """Test that invalid registry mappings are skipped."""
        mock_ctx = AsyncMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id=None,
                ecr_region=None,
                include_pull_through_caches=False,
                additional_registry_mappings=[
                    {'upstreamRegistryUrl': 'https://valid.io', 'ecrRepositoryPrefix': 'valid'},
                    {'upstreamRegistryUrl': 'https://invalid.io'},  # Missing ecrRepositoryPrefix
                    {'ecrRepositoryPrefix': 'also-invalid'},  # Missing upstreamRegistryUrl
                ],
                image_mappings=None,
                output_format='json',
            )

        assert result['success'] is True
        # Only the valid mapping should be included
        assert len(result['container_registry_map']['registryMappings']) == 1

    @pytest.mark.asyncio
    async def test_map_creation_with_invalid_image_mapping(self):
        """Test that invalid image mappings are skipped."""
        mock_ctx = AsyncMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id=None,
                ecr_region=None,
                include_pull_through_caches=False,
                additional_registry_mappings=None,
                image_mappings=[
                    {'sourceImage': 'valid:latest', 'destinationImage': 'dest:latest'},
                    {'sourceImage': 'invalid:latest'},  # Missing destinationImage
                    {'destinationImage': 'also-invalid:latest'},  # Missing sourceImage
                ],
                output_format='json',
            )

        assert result['success'] is True
        assert len(result['container_registry_map']['imageMappings']) == 1

    @pytest.mark.asyncio
    async def test_map_creation_account_id_error(self):
        """Test error handling when account ID cannot be retrieved."""
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
            side_effect=Exception('Failed to get account ID'),
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id=None,
                ecr_region=None,
                include_pull_through_caches=False,
                additional_registry_mappings=None,
                image_mappings=None,
                output_format='json',
            )

        assert result['success'] is False
        assert 'Failed to get AWS account ID' in result['message']

    @pytest.mark.asyncio
    async def test_map_creation_ptc_discovery_error(self):
        """Test graceful handling when PTC discovery fails."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_pull_through_cache_rules.side_effect = Exception('Discovery failed')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id=None,
                ecr_region=None,
                include_pull_through_caches=True,
                additional_registry_mappings=None,
                image_mappings=None,
                output_format='json',
            )

        # Should still succeed but with 0 discovered caches
        assert result['success'] is True
        assert result['discovered_healthomics_usable_caches'] == 0

    @pytest.mark.asyncio
    async def test_map_creation_merge_additional_mappings(self):
        """Test that additional mappings are merged with discovered ones."""
        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'https://registry-1.docker.io',
                }
            ]
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                        }
                    ]
                }
            )
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'repositoryPolicy': json.dumps(
                        {
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'omics.amazonaws.com'},
                                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                                }
                            ]
                        }
                    )
                }
            ]
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await create_container_registry_map(
                ctx=mock_ctx,
                ecr_account_id=None,
                ecr_region=None,
                include_pull_through_caches=True,
                additional_registry_mappings=[
                    {
                        'upstreamRegistryUrl': 'https://quay.io',
                        'ecrRepositoryPrefix': 'quay',
                    },
                    # Override discovered docker-hub mapping
                    {
                        'upstreamRegistryUrl': 'https://registry-1.docker.io',
                        'ecrRepositoryPrefix': 'custom-docker-hub',
                    },
                ],
                image_mappings=None,
                output_format='json',
            )

        assert result['success'] is True
        mappings = result['container_registry_map']['registryMappings']
        # Should have quay and custom-docker-hub (overriding discovered docker-hub)
        assert len(mappings) == 2
        prefixes = [m['ecrRepositoryPrefix'] for m in mappings]
        assert 'quay' in prefixes
        assert 'custom-docker-hub' in prefixes


# =============================================================================
# Additional Tests for Remaining Uncovered Lines
# =============================================================================


class TestListPullThroughCacheRulesEdgeCases:
    """Additional edge case tests for list_pull_through_cache_rules."""

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self):
        """Test unexpected exception handling."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            list_pull_through_cache_rules,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.describe_pull_through_cache_rules.side_effect = Exception('Unexpected error')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        assert 'error' in result
        assert 'Error' in result['error']


class TestGrantHealthOmicsRepositoryAccessEdgeCases:
    """Additional edge case tests for grant_healthomics_repository_access."""

    @pytest.mark.asyncio
    async def test_policy_with_single_statement_dict(self):
        """Test handling when existing policy has Statement as dict instead of list."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            grant_healthomics_repository_access,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        # Existing policy with Statement as dict (not list)
        existing_policy = {
            'Version': '2012-10-17',
            'Statement': {
                'Sid': 'ExistingStatement',
                'Effect': 'Allow',
                'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                'Action': ['ecr:GetDownloadUrlForLayer'],
            },
        }
        mock_client.get_repository_policy.return_value = {
            'policyText': json.dumps(existing_policy)
        }
        mock_client.set_repository_policy.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='my-repo',
            )

        assert result['success'] is True
        assert result['policy_updated'] is True

    @pytest.mark.asyncio
    async def test_policy_with_healthomics_service_in_list(self):
        """Test handling when existing policy has HealthOmics in Service list."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            grant_healthomics_repository_access,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        # Existing policy with HealthOmics in Service list
        existing_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'ExistingHealthOmics',
                    'Effect': 'Allow',
                    'Principal': {'Service': ['omics.amazonaws.com', 'other.amazonaws.com']},
                    'Action': ['ecr:GetDownloadUrlForLayer'],
                }
            ],
        }
        mock_client.get_repository_policy.return_value = {
            'policyText': json.dumps(existing_policy)
        }
        mock_client.set_repository_policy.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='my-repo',
            )

        assert result['success'] is True
        # The existing HealthOmics statement should be replaced
        assert result['policy_updated'] is True

    @pytest.mark.asyncio
    async def test_policy_with_healthomics_as_string_principal(self):
        """Test handling when existing policy has HealthOmics as string principal."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            grant_healthomics_repository_access,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        # Existing policy with HealthOmics as string principal
        existing_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'ExistingHealthOmics',
                    'Effect': 'Allow',
                    'Principal': 'omics.amazonaws.com',
                    'Action': ['ecr:GetDownloadUrlForLayer'],
                }
            ],
        }
        mock_client.get_repository_policy.return_value = {
            'policyText': json.dumps(existing_policy)
        }
        mock_client.set_repository_policy.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='my-repo',
            )

        assert result['success'] is True
        assert result['policy_updated'] is True

    @pytest.mark.asyncio
    async def test_verify_policy_update_fails(self):
        """Test handling when policy verification fails after update."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            grant_healthomics_repository_access,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        # No existing policy
        error_response = {
            'Error': {'Code': 'RepositoryPolicyNotFoundException', 'Message': 'Not found'}
        }
        mock_client.get_repository_policy.side_effect = [
            botocore.exceptions.ClientError(error_response, 'GetRepositoryPolicy'),
            Exception('Verification failed'),  # Second call for verification
        ]
        mock_client.set_repository_policy.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='my-repo',
            )

        # Should still succeed since set_repository_policy didn't raise
        assert result['success'] is True
        assert result['policy_created'] is True

    @pytest.mark.asyncio
    async def test_other_client_error_on_get_policy(self):
        """Test handling of other ClientError when getting policy."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            grant_healthomics_repository_access,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'Error'}}
        mock_client.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRepositoryPolicy'
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                await grant_healthomics_repository_access(
                    ctx=mock_ctx,
                    repository_name='my-repo',
                )

    @pytest.mark.asyncio
    async def test_other_client_error_on_set_policy(self):
        """Test handling of other ClientError when setting policy."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            grant_healthomics_repository_access,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        # No existing policy
        error_response = {
            'Error': {'Code': 'RepositoryPolicyNotFoundException', 'Message': 'Not found'}
        }
        mock_client.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRepositoryPolicy'
        )

        # Set policy fails with other error
        set_error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'Error'}}
        mock_client.set_repository_policy.side_effect = botocore.exceptions.ClientError(
            set_error_response, 'SetRepositoryPolicy'
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                await grant_healthomics_repository_access(
                    ctx=mock_ctx,
                    repository_name='my-repo',
                )


class TestCreatePullThroughCacheEdgeCases:
    """Additional edge case tests for create_pull_through_cache_for_healthomics."""

    @pytest.mark.asyncio
    async def test_template_update_fails_but_has_policy(self):
        """Test when template update fails but existing template has policy."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            create_pull_through_cache_for_healthomics,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        # PTC rule creation succeeds
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'https://quay.io',
            'createdAt': datetime.now(timezone.utc),
        }

        # Registry policy update succeeds
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Template creation fails because it exists
        mock_client.create_repository_creation_template.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateAlreadyExistsException', 'Message': 'Exists'}},
                'CreateRepositoryCreationTemplate',
            )
        )
        # Update also fails
        mock_client.update_repository_creation_template.side_effect = Exception('Update failed')
        # But describe shows it has a policy
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'prefix': 'quay',
                    'repositoryPolicy': json.dumps({'Statement': []}),
                }
            ]
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        assert result['success'] is True
        assert result['repository_template_created'] is True

    @pytest.mark.asyncio
    async def test_template_update_fails_no_policy(self):
        """Test when template update fails and existing template has no policy."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            create_pull_through_cache_for_healthomics,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'https://quay.io',
            'createdAt': datetime.now(timezone.utc),
        }

        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        mock_client.create_repository_creation_template.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateAlreadyExistsException', 'Message': 'Exists'}},
                'CreateRepositoryCreationTemplate',
            )
        )
        mock_client.update_repository_creation_template.side_effect = Exception('Update failed')
        # Describe shows no policy
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [{'prefix': 'quay'}]  # No repositoryPolicy
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        assert result['success'] is True
        assert result['repository_template_created'] is False

    @pytest.mark.asyncio
    async def test_template_describe_fails_after_update_failure(self):
        """Test when template describe fails after update failure."""
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            create_pull_through_cache_for_healthomics,
        )

        mock_client = MagicMock()
        mock_ctx = AsyncMock()

        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'https://quay.io',
            'createdAt': datetime.now(timezone.utc),
        }

        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        mock_client.create_repository_creation_template.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateAlreadyExistsException', 'Message': 'Exists'}},
                'CreateRepositoryCreationTemplate',
            )
        )
        mock_client.update_repository_creation_template.side_effect = Exception('Update failed')
        mock_client.describe_repository_creation_templates.side_effect = Exception(
            'Describe failed'
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        assert result['success'] is True
        assert result['repository_template_created'] is False
