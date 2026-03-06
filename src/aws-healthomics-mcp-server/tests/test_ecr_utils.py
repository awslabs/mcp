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

"""Property-based tests for ECR utility functions.

Feature: ecr-container-tools
"""

import json
from awslabs.aws_healthomics_mcp_server.consts import (
    ECR_REQUIRED_REGISTRY_ACTIONS,
    ECR_REQUIRED_REPOSITORY_ACTIONS,
    HEALTHOMICS_PRINCIPAL,
)
from awslabs.aws_healthomics_mcp_server.models.ecr import HealthOmicsAccessStatus
from awslabs.aws_healthomics_mcp_server.utils.ecr_utils import (
    check_repository_healthomics_access,
    evaluate_pull_through_cache_healthomics_usability,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from typing import Any, List, Optional


# =============================================================================
# Hypothesis Strategies for IAM Policy Documents
# =============================================================================

# Strategy for generating valid IAM policy effects
effect_strategy = st.sampled_from(['Allow', 'Deny', 'allow', 'ALLOW', 'deny', 'DENY'])

# Strategy for generating the HealthOmics principal in various formats
healthomics_principal_strategy = st.sampled_from(
    [
        HEALTHOMICS_PRINCIPAL,  # 'omics.amazonaws.com'
        {'Service': HEALTHOMICS_PRINCIPAL},
        {'Service': [HEALTHOMICS_PRINCIPAL]},
        {'Service': [HEALTHOMICS_PRINCIPAL, 'other.amazonaws.com']},
    ]
)

# Strategy for generating non-HealthOmics principals
non_healthomics_principal_strategy = st.sampled_from(
    [
        'ec2.amazonaws.com',
        'lambda.amazonaws.com',
        {'Service': 'ec2.amazonaws.com'},
        {'Service': ['ec2.amazonaws.com', 'lambda.amazonaws.com']},
        {'AWS': 'arn:aws:iam::123456789012:root'},
        {'AWS': ['arn:aws:iam::123456789012:root']},
    ]
)

# Strategy for generating wildcard principals
wildcard_principal_strategy = st.sampled_from(
    [
        '*',
        {'AWS': '*'},
    ]
)

# Strategy for generating the required ECR repository actions
required_actions_strategy = st.sampled_from(
    [
        ECR_REQUIRED_REPOSITORY_ACTIONS,  # ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer']
        ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
        ['ecr:batchgetimage', 'ecr:getdownloadurlforlayer'],  # lowercase
        ['ECR:BATCHGETIMAGE', 'ECR:GETDOWNLOADURLFORLAYER'],  # uppercase
    ]
)

# Strategy for generating wildcard actions that include required permissions
wildcard_actions_strategy = st.sampled_from(
    [
        ['ecr:*'],
        ['*'],
        'ecr:*',
        '*',
    ]
)

# Strategy for generating partial actions (missing one required action)
partial_actions_strategy = st.sampled_from(
    [
        ['ecr:BatchGetImage'],
        ['ecr:GetDownloadUrlForLayer'],
        'ecr:BatchGetImage',
        'ecr:GetDownloadUrlForLayer',
    ]
)

# Strategy for generating unrelated actions
unrelated_actions_strategy = st.sampled_from(
    [
        ['ecr:DescribeRepositories'],
        ['ecr:ListImages'],
        ['s3:GetObject'],
        ['ecr:PutImage', 'ecr:InitiateLayerUpload'],
    ]
)


@st.composite
def valid_healthomics_policy_strategy(draw) -> str:
    """Generate a valid IAM policy that grants HealthOmics the required permissions.

    This strategy generates policies where:
    - Effect is 'Allow'
    - Principal includes HealthOmics (omics.amazonaws.com)
    - Actions include both ecr:BatchGetImage and ecr:GetDownloadUrlForLayer
    """
    # Choose how to represent the principal
    principal = draw(healthomics_principal_strategy)

    # Choose how to represent the actions (exact or wildcard)
    use_wildcard = draw(st.booleans())
    if use_wildcard:
        actions = draw(wildcard_actions_strategy)
    else:
        actions = draw(required_actions_strategy)

    # Build the policy statement
    statement = {
        'Sid': draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=20)),
        'Effect': 'Allow',
        'Principal': principal,
        'Action': actions,
        'Resource': '*',
    }

    # Optionally add additional statements that don't affect the result
    additional_statements = []
    if draw(st.booleans()):
        # Add a Deny statement for a different principal
        additional_statements.append(
            {
                'Sid': 'DenyOther',
                'Effect': 'Deny',
                'Principal': draw(non_healthomics_principal_strategy),
                'Action': ['ecr:DeleteRepository'],
                'Resource': '*',
            }
        )

    policy = {
        'Version': '2012-10-17',
        'Statement': [statement] + additional_statements,
    }

    return json.dumps(policy)


@st.composite
def invalid_healthomics_policy_strategy(draw) -> str:
    """Generate an IAM policy that does NOT grant HealthOmics the required permissions.

    This strategy generates policies where at least one of these is true:
    - Effect is 'Deny'
    - Principal does not include HealthOmics
    - Actions do not include both required actions
    """
    # Choose the type of invalid policy
    invalid_type = draw(st.sampled_from(['wrong_effect', 'wrong_principal', 'wrong_actions']))

    if invalid_type == 'wrong_effect':
        # Deny effect with correct principal and actions
        statement = {
            'Sid': 'DenyHealthOmics',
            'Effect': 'Deny',
            'Principal': draw(healthomics_principal_strategy),
            'Action': draw(required_actions_strategy),
            'Resource': '*',
        }
    elif invalid_type == 'wrong_principal':
        # Allow effect with wrong principal
        statement = {
            'Sid': 'AllowOther',
            'Effect': 'Allow',
            'Principal': draw(non_healthomics_principal_strategy),
            'Action': draw(required_actions_strategy),
            'Resource': '*',
        }
    else:  # wrong_actions
        # Allow effect with correct principal but missing actions
        actions = draw(st.one_of(partial_actions_strategy, unrelated_actions_strategy))
        statement = {
            'Sid': 'PartialAccess',
            'Effect': 'Allow',
            'Principal': draw(healthomics_principal_strategy),
            'Action': actions,
            'Resource': '*',
        }

    policy = {
        'Version': '2012-10-17',
        'Statement': [statement],
    }

    return json.dumps(policy)


@st.composite
def policy_with_wildcard_principal_strategy(draw) -> str:
    """Generate an IAM policy with wildcard principal that grants required permissions."""
    principal = draw(wildcard_principal_strategy)

    # Choose how to represent the actions
    use_wildcard = draw(st.booleans())
    if use_wildcard:
        actions = draw(wildcard_actions_strategy)
    else:
        actions = draw(required_actions_strategy)

    statement = {
        'Sid': 'WildcardAccess',
        'Effect': 'Allow',
        'Principal': principal,
        'Action': actions,
        'Resource': '*',
    }

    policy = {
        'Version': '2012-10-17',
        'Statement': [statement],
    }

    return json.dumps(policy)


@st.composite
def multi_statement_policy_strategy(draw) -> str:
    """Generate a policy with multiple statements where HealthOmics access is granted.

    The policy may have multiple statements, but at least one grants HealthOmics
    the required permissions.
    """
    # Generate the valid HealthOmics statement
    valid_statement = {
        'Sid': 'HealthOmicsAccess',
        'Effect': 'Allow',
        'Principal': draw(healthomics_principal_strategy),
        'Action': draw(required_actions_strategy),
        'Resource': '*',
    }

    # Generate additional statements
    num_additional = draw(st.integers(min_value=0, max_value=3))
    additional_statements = []

    for i in range(num_additional):
        stmt_type = draw(st.sampled_from(['allow_other', 'deny_other', 'deny_healthomics_other']))

        if stmt_type == 'allow_other':
            additional_statements.append(
                {
                    'Sid': f'AllowOther{i}',
                    'Effect': 'Allow',
                    'Principal': draw(non_healthomics_principal_strategy),
                    'Action': ['ecr:DescribeRepositories'],
                    'Resource': '*',
                }
            )
        elif stmt_type == 'deny_other':
            additional_statements.append(
                {
                    'Sid': f'DenyOther{i}',
                    'Effect': 'Deny',
                    'Principal': draw(non_healthomics_principal_strategy),
                    'Action': ['ecr:DeleteRepository'],
                    'Resource': '*',
                }
            )
        else:
            # Deny HealthOmics for different actions (shouldn't affect required permissions)
            additional_statements.append(
                {
                    'Sid': f'DenyHealthOmicsOther{i}',
                    'Effect': 'Deny',
                    'Principal': draw(healthomics_principal_strategy),
                    'Action': ['ecr:DeleteRepository', 'ecr:PutImage'],
                    'Resource': '*',
                }
            )

    # Shuffle the statements
    all_statements = [valid_statement] + additional_statements
    shuffled = draw(st.permutations(all_statements))

    policy = {
        'Version': '2012-10-17',
        'Statement': list(shuffled),
    }

    return json.dumps(policy)


# =============================================================================
# Property 1: Permission Checking Correctness
# Feature: ecr-container-tools, Property 1: Permission Checking Correctness
# Validates: Requirements 1.2, 1.3
# =============================================================================


class TestPermissionCheckingCorrectness:
    """Property 1: Permission Checking Correctness.

    **Validates: Requirements 1.2, 1.3**

    *For any* ECR repository policy that contains the HealthOmics principal
    (`omics.amazonaws.com`) with both `ecr:BatchGetImage` and `ecr:GetDownloadUrlForLayer`
    actions, the repository SHALL be marked as `healthomics_accessible: accessible`.
    """

    @settings(max_examples=100)
    @given(policy_text=valid_healthomics_policy_strategy())
    def test_valid_policy_returns_accessible(self, policy_text: str):
        """Property 1.1: Valid HealthOmics policy returns ACCESSIBLE status.

        Feature: ecr-container-tools, Property 1: Permission Checking Correctness
        **Validates: Requirements 1.2, 1.3**

        When a repository policy grants HealthOmics principal both required actions
        (ecr:BatchGetImage and ecr:GetDownloadUrlForLayer), the function SHALL
        return HealthOmicsAccessStatus.ACCESSIBLE with no missing permissions.
        """
        status, missing_permissions = check_repository_healthomics_access(policy_text)

        assert status == HealthOmicsAccessStatus.ACCESSIBLE, (
            f'Expected ACCESSIBLE status for valid policy, got {status}. Policy: {policy_text}'
        )
        assert missing_permissions == [], (
            f'Expected no missing permissions, got {missing_permissions}. Policy: {policy_text}'
        )

    @settings(max_examples=100)
    @given(policy_text=invalid_healthomics_policy_strategy())
    def test_invalid_policy_returns_not_accessible(self, policy_text: str):
        """Property 1.2: Invalid HealthOmics policy returns NOT_ACCESSIBLE status.

        Feature: ecr-container-tools, Property 1: Permission Checking Correctness
        **Validates: Requirements 1.2, 1.3**

        When a repository policy does NOT grant HealthOmics principal both required
        actions, the function SHALL return HealthOmicsAccessStatus.NOT_ACCESSIBLE.
        """
        status, missing_permissions = check_repository_healthomics_access(policy_text)

        # Parse the policy to understand what type of invalid it is
        policy = json.loads(policy_text)
        statement = policy['Statement'][0]

        # If effect is Deny or principal doesn't match, should be NOT_ACCESSIBLE
        if statement['Effect'].lower() == 'deny':
            assert status == HealthOmicsAccessStatus.NOT_ACCESSIBLE, (
                f'Expected NOT_ACCESSIBLE for Deny effect, got {status}'
            )
        elif not _principal_matches_healthomics(statement.get('Principal')):
            assert status == HealthOmicsAccessStatus.NOT_ACCESSIBLE, (
                f'Expected NOT_ACCESSIBLE for non-HealthOmics principal, got {status}'
            )
        else:
            # Wrong actions case
            assert status == HealthOmicsAccessStatus.NOT_ACCESSIBLE, (
                f'Expected NOT_ACCESSIBLE for missing actions, got {status}'
            )
            assert len(missing_permissions) > 0, (
                'Expected missing permissions for partial actions policy'
            )

    @settings(max_examples=100)
    @given(policy_text=policy_with_wildcard_principal_strategy())
    def test_wildcard_principal_returns_accessible(self, policy_text: str):
        """Property 1.3: Wildcard principal with required actions returns ACCESSIBLE.

        Feature: ecr-container-tools, Property 1: Permission Checking Correctness
        **Validates: Requirements 1.2, 1.3**

        When a repository policy uses wildcard principal ('*') with both required
        actions, the function SHALL return HealthOmicsAccessStatus.ACCESSIBLE.
        """
        status, missing_permissions = check_repository_healthomics_access(policy_text)

        assert status == HealthOmicsAccessStatus.ACCESSIBLE, (
            f'Expected ACCESSIBLE for wildcard principal, got {status}. Policy: {policy_text}'
        )
        assert missing_permissions == [], (
            f'Expected no missing permissions for wildcard principal, got {missing_permissions}'
        )

    @settings(max_examples=100)
    @given(policy_text=multi_statement_policy_strategy())
    def test_multi_statement_policy_with_valid_statement_returns_accessible(
        self, policy_text: str
    ):
        """Property 1.4: Multi-statement policy with valid HealthOmics statement returns ACCESSIBLE.

        Feature: ecr-container-tools, Property 1: Permission Checking Correctness
        **Validates: Requirements 1.2, 1.3**

        When a repository policy contains multiple statements and at least one grants
        HealthOmics the required permissions, the function SHALL return ACCESSIBLE.
        """
        status, missing_permissions = check_repository_healthomics_access(policy_text)

        assert status == HealthOmicsAccessStatus.ACCESSIBLE, (
            f'Expected ACCESSIBLE for multi-statement policy with valid statement, got {status}. '
            f'Policy: {policy_text}'
        )
        assert missing_permissions == [], (
            f'Expected no missing permissions, got {missing_permissions}'
        )

    @settings(max_examples=100)
    @given(st.none())
    def test_none_policy_returns_unknown(self, policy_text: None):
        """Property 1.5: None policy returns UNKNOWN status.

        Feature: ecr-container-tools, Property 1: Permission Checking Correctness
        **Validates: Requirements 1.2, 1.3**

        When no repository policy exists (None), the function SHALL return
        HealthOmicsAccessStatus.UNKNOWN with no missing permissions.
        """
        status, missing_permissions = check_repository_healthomics_access(policy_text)

        assert status == HealthOmicsAccessStatus.UNKNOWN, (
            f'Expected UNKNOWN for None policy, got {status}'
        )
        assert missing_permissions == [], (
            f'Expected no missing permissions for None policy, got {missing_permissions}'
        )

    @settings(max_examples=100)
    @given(invalid_json=st.text(min_size=1, max_size=100).filter(lambda s: not _is_valid_json(s)))
    def test_invalid_json_returns_unknown(self, invalid_json: str):
        """Property 1.6: Invalid JSON policy returns UNKNOWN status.

        Feature: ecr-container-tools, Property 1: Permission Checking Correctness
        **Validates: Requirements 1.2, 1.3**

        When the policy text is not valid JSON, the function SHALL return
        HealthOmicsAccessStatus.UNKNOWN with no missing permissions.
        """
        status, missing_permissions = check_repository_healthomics_access(invalid_json)

        assert status == HealthOmicsAccessStatus.UNKNOWN, (
            f'Expected UNKNOWN for invalid JSON, got {status}'
        )
        assert missing_permissions == [], (
            f'Expected no missing permissions for invalid JSON, got {missing_permissions}'
        )

    @settings(max_examples=100)
    @given(
        actions=st.lists(
            st.sampled_from(
                [
                    'ecr:BatchGetImage',
                    'ecr:GetDownloadUrlForLayer',
                    'ecr:DescribeRepositories',
                    'ecr:ListImages',
                ]
            ),
            min_size=0,
            max_size=4,
            unique=True,
        )
    )
    def test_missing_permissions_are_correctly_identified(self, actions: List[str]):
        """Property 1.7: Missing permissions are correctly identified.

        Feature: ecr-container-tools, Property 1: Permission Checking Correctness
        **Validates: Requirements 1.2, 1.3**

        The function SHALL correctly identify which required permissions are missing
        from the policy.
        """
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'TestStatement',
                    'Effect': 'Allow',
                    'Principal': {'Service': HEALTHOMICS_PRINCIPAL},
                    'Action': actions if actions else ['ecr:DescribeRepositories'],
                    'Resource': '*',
                }
            ],
        }
        policy_text = json.dumps(policy)

        status, missing_permissions = check_repository_healthomics_access(policy_text)

        # Determine expected missing permissions
        actions_lower = {a.lower() for a in actions}
        expected_missing = []
        for required in ECR_REQUIRED_REPOSITORY_ACTIONS:
            if required.lower() not in actions_lower:
                expected_missing.append(required)

        if len(expected_missing) == 0:
            assert status == HealthOmicsAccessStatus.ACCESSIBLE
            assert missing_permissions == []
        else:
            assert status == HealthOmicsAccessStatus.NOT_ACCESSIBLE
            assert set(missing_permissions) == set(expected_missing), (
                f'Expected missing: {expected_missing}, got: {missing_permissions}'
            )


# =============================================================================
# Helper Functions
# =============================================================================


def _is_valid_json(s: str) -> bool:
    """Check if a string is valid JSON."""
    try:
        json.loads(s)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def _principal_matches_healthomics(principal: Any) -> bool:
    """Check if a principal matches the HealthOmics principal."""
    if principal is None:
        return False
    if principal == '*':
        return True
    if isinstance(principal, str):
        return principal == HEALTHOMICS_PRINCIPAL
    if isinstance(principal, dict):
        service = principal.get('Service')
        if service is not None:
            if isinstance(service, str):
                return service == HEALTHOMICS_PRINCIPAL
            if isinstance(service, list):
                return HEALTHOMICS_PRINCIPAL in service
        aws = principal.get('AWS')
        if aws is not None:
            if isinstance(aws, str):
                return aws == '*'
            if isinstance(aws, list):
                return '*' in aws
    return False


# =============================================================================
# Hypothesis Strategies for Registry Policies (Property 4)
# =============================================================================

# Strategy for generating the required ECR registry actions
registry_required_actions_strategy = st.sampled_from(
    [
        ECR_REQUIRED_REGISTRY_ACTIONS,  # ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage']
        ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
        ['ecr:createrepository', 'ecr:batchimportupstreamimage'],  # lowercase
        ['ECR:CREATEREPOSITORY', 'ECR:BATCHIMPORTUPSTREAMIMAGE'],  # uppercase
    ]
)

# Strategy for generating partial registry actions (missing one required action)
partial_registry_actions_strategy = st.sampled_from(
    [
        ['ecr:CreateRepository'],
        ['ecr:BatchImportUpstreamImage'],
        'ecr:CreateRepository',
        'ecr:BatchImportUpstreamImage',
    ]
)


@st.composite
def valid_registry_policy_strategy(draw) -> str:
    """Generate a valid registry permissions policy that grants HealthOmics required permissions.

    This strategy generates policies where:
    - Effect is 'Allow'
    - Principal includes HealthOmics (omics.amazonaws.com)
    - Actions include both ecr:CreateRepository and ecr:BatchImportUpstreamImage
    """
    principal = draw(healthomics_principal_strategy)

    # Choose how to represent the actions (exact or wildcard)
    use_wildcard = draw(st.booleans())
    if use_wildcard:
        actions = draw(wildcard_actions_strategy)
    else:
        actions = draw(registry_required_actions_strategy)

    statement = {
        'Sid': draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=20)),
        'Effect': 'Allow',
        'Principal': principal,
        'Action': actions,
        'Resource': '*',
    }

    policy = {
        'Version': '2012-10-17',
        'Statement': [statement],
    }

    return json.dumps(policy)


@st.composite
def invalid_registry_policy_strategy(draw) -> str:
    """Generate a registry policy that does NOT grant HealthOmics required permissions.

    This strategy generates policies where at least one of these is true:
    - Effect is 'Deny'
    - Principal does not include HealthOmics
    - Actions do not include both required registry actions
    """
    invalid_type = draw(st.sampled_from(['wrong_effect', 'wrong_principal', 'wrong_actions']))

    if invalid_type == 'wrong_effect':
        statement = {
            'Sid': 'DenyHealthOmics',
            'Effect': 'Deny',
            'Principal': draw(healthomics_principal_strategy),
            'Action': draw(registry_required_actions_strategy),
            'Resource': '*',
        }
    elif invalid_type == 'wrong_principal':
        statement = {
            'Sid': 'AllowOther',
            'Effect': 'Allow',
            'Principal': draw(non_healthomics_principal_strategy),
            'Action': draw(registry_required_actions_strategy),
            'Resource': '*',
        }
    else:  # wrong_actions
        actions = draw(partial_registry_actions_strategy)
        statement = {
            'Sid': 'PartialAccess',
            'Effect': 'Allow',
            'Principal': draw(healthomics_principal_strategy),
            'Action': actions,
            'Resource': '*',
        }

    policy = {
        'Version': '2012-10-17',
        'Statement': [statement],
    }

    return json.dumps(policy)


@st.composite
def valid_template_policy_strategy(draw) -> str:
    """Generate a valid repository creation template policy for HealthOmics.

    This strategy generates policies where:
    - Effect is 'Allow'
    - Principal includes HealthOmics (omics.amazonaws.com)
    - Actions include both ecr:BatchGetImage and ecr:GetDownloadUrlForLayer
    """
    principal = draw(healthomics_principal_strategy)

    # Choose how to represent the actions (exact or wildcard)
    use_wildcard = draw(st.booleans())
    if use_wildcard:
        actions = draw(wildcard_actions_strategy)
    else:
        actions = draw(required_actions_strategy)

    statement = {
        'Sid': draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=20)),
        'Effect': 'Allow',
        'Principal': principal,
        'Action': actions,
        'Resource': '*',
    }

    policy = {
        'Version': '2012-10-17',
        'Statement': [statement],
    }

    return json.dumps(policy)


@st.composite
def invalid_template_policy_strategy(draw) -> str:
    """Generate a template policy that does NOT grant HealthOmics required permissions.

    This strategy generates policies where at least one of these is true:
    - Effect is 'Deny'
    - Principal does not include HealthOmics
    - Actions do not include both required repository actions
    """
    invalid_type = draw(st.sampled_from(['wrong_effect', 'wrong_principal', 'wrong_actions']))

    if invalid_type == 'wrong_effect':
        statement = {
            'Sid': 'DenyHealthOmics',
            'Effect': 'Deny',
            'Principal': draw(healthomics_principal_strategy),
            'Action': draw(required_actions_strategy),
            'Resource': '*',
        }
    elif invalid_type == 'wrong_principal':
        statement = {
            'Sid': 'AllowOther',
            'Effect': 'Allow',
            'Principal': draw(non_healthomics_principal_strategy),
            'Action': draw(required_actions_strategy),
            'Resource': '*',
        }
    else:  # wrong_actions
        actions = draw(partial_actions_strategy)
        statement = {
            'Sid': 'PartialAccess',
            'Effect': 'Allow',
            'Principal': draw(healthomics_principal_strategy),
            'Action': actions,
            'Resource': '*',
        }

    policy = {
        'Version': '2012-10-17',
        'Statement': [statement],
    }

    return json.dumps(policy)


# Strategy for generating ECR repository prefixes
ecr_prefix_strategy = st.one_of(
    st.sampled_from(['docker-hub', 'quay', 'ecr-public', 'custom-prefix']),
    st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',  # pragma: allowlist secret
        min_size=1,
        max_size=20,  # pragma: allowlist secret
    ),  # pragma: allowlist secret
    st.none(),
)


# =============================================================================
# Property 4: HealthOmics Usability Evaluation
# Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
# Validates: Requirements 3.3, 3.4, 3.5
# =============================================================================


class TestHealthOmicsUsabilityEvaluation:
    """Property 4: HealthOmics Usability Evaluation.

    **Validates: Requirements 3.3, 3.4, 3.5**

    *For any* pull-through cache rule, the `healthomics_usable` field SHALL be True
    if and only if:
    1. The registry permissions policy grants HealthOmics `ecr:CreateRepository`
       and `ecr:BatchImportUpstreamImage` for the prefix
    2. A repository creation template exists for the prefix
    3. The repository creation template grants HealthOmics `ecr:BatchGetImage`
       and `ecr:GetDownloadUrlForLayer`
    """

    @settings(max_examples=100)
    @given(
        registry_policy=valid_registry_policy_strategy(),
        template_policy=valid_template_policy_strategy(),
        prefix=ecr_prefix_strategy,
    )
    def test_all_conditions_met_returns_usable(
        self, registry_policy: str, template_policy: str, prefix: Optional[str]
    ):
        """Property 4.1: All conditions met returns healthomics_usable=True.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        When registry policy grants required permissions AND template exists AND
        template grants required permissions, healthomics_usable SHALL be True.
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=registry_policy,
            template_policy_text=template_policy,
            ecr_repository_prefix=prefix,
        )

        assert result['healthomics_usable'] is True, (
            f'Expected healthomics_usable=True when all conditions met. Result: {result}'
        )
        assert result['registry_permission_granted'] is True
        assert result['repository_template_exists'] is True
        assert result['repository_template_permission_granted'] is True
        assert result['missing_registry_permissions'] == []
        assert result['missing_template_permissions'] == []

    @settings(max_examples=100)
    @given(
        registry_policy=invalid_registry_policy_strategy(),
        template_policy=valid_template_policy_strategy(),
        prefix=ecr_prefix_strategy,
    )
    def test_invalid_registry_policy_returns_not_usable(
        self, registry_policy: str, template_policy: str, prefix: Optional[str]
    ):
        """Property 4.2: Invalid registry policy returns healthomics_usable=False.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        When registry policy does NOT grant required permissions, healthomics_usable
        SHALL be False even if template is valid.
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=registry_policy,
            template_policy_text=template_policy,
            ecr_repository_prefix=prefix,
        )

        assert result['healthomics_usable'] is False, (
            f'Expected healthomics_usable=False when registry policy is invalid. Result: {result}'
        )
        assert result['registry_permission_granted'] is False

    @settings(max_examples=100)
    @given(
        registry_policy=valid_registry_policy_strategy(),
        template_policy=invalid_template_policy_strategy(),
        prefix=ecr_prefix_strategy,
    )
    def test_invalid_template_policy_returns_not_usable(
        self, registry_policy: str, template_policy: str, prefix: Optional[str]
    ):
        """Property 4.3: Invalid template policy returns healthomics_usable=False.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        When template policy does NOT grant required permissions, healthomics_usable
        SHALL be False even if registry policy is valid.
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=registry_policy,
            template_policy_text=template_policy,
            ecr_repository_prefix=prefix,
        )

        assert result['healthomics_usable'] is False, (
            f'Expected healthomics_usable=False when template policy is invalid. Result: {result}'
        )
        assert result['registry_permission_granted'] is True
        assert result['repository_template_exists'] is True
        assert result['repository_template_permission_granted'] is False

    @settings(max_examples=100)
    @given(
        registry_policy=valid_registry_policy_strategy(),
        prefix=ecr_prefix_strategy,
    )
    def test_no_template_returns_not_usable(self, registry_policy: str, prefix: Optional[str]):
        """Property 4.4: No template (None) returns healthomics_usable=False.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        When no repository creation template exists (None), healthomics_usable
        SHALL be False even if registry policy is valid.
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=registry_policy,
            template_policy_text=None,
            ecr_repository_prefix=prefix,
        )

        assert result['healthomics_usable'] is False, (
            f'Expected healthomics_usable=False when template is None. Result: {result}'
        )
        assert result['registry_permission_granted'] is True
        assert result['repository_template_exists'] is False
        assert result['repository_template_permission_granted'] is False

    @settings(max_examples=100)
    @given(
        template_policy=valid_template_policy_strategy(),
        prefix=ecr_prefix_strategy,
    )
    def test_no_registry_policy_returns_not_usable(
        self, template_policy: str, prefix: Optional[str]
    ):
        """Property 4.5: No registry policy (None) returns healthomics_usable=False.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        When no registry permissions policy exists (None), healthomics_usable
        SHALL be False even if template is valid.
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=None,
            template_policy_text=template_policy,
            ecr_repository_prefix=prefix,
        )

        assert result['healthomics_usable'] is False, (
            f'Expected healthomics_usable=False when registry policy is None. Result: {result}'
        )
        assert result['registry_permission_granted'] is False
        assert result['missing_registry_permissions'] == list(ECR_REQUIRED_REGISTRY_ACTIONS)

    @settings(max_examples=100)
    @given(prefix=ecr_prefix_strategy)
    def test_both_policies_none_returns_not_usable(self, prefix: Optional[str]):
        """Property 4.6: Both policies None returns healthomics_usable=False.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        When both registry policy and template policy are None, healthomics_usable
        SHALL be False.
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=None,
            template_policy_text=None,
            ecr_repository_prefix=prefix,
        )

        assert result['healthomics_usable'] is False, (
            f'Expected healthomics_usable=False when both policies are None. Result: {result}'
        )
        assert result['registry_permission_granted'] is False
        assert result['repository_template_exists'] is False
        assert result['repository_template_permission_granted'] is False

    @settings(max_examples=100)
    @given(
        invalid_registry=invalid_registry_policy_strategy(),
        invalid_template=invalid_template_policy_strategy(),
        prefix=ecr_prefix_strategy,
    )
    def test_both_policies_invalid_returns_not_usable(
        self, invalid_registry: str, invalid_template: str, prefix: Optional[str]
    ):
        """Property 4.7: Both policies invalid returns healthomics_usable=False.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        When both registry policy and template policy are invalid, healthomics_usable
        SHALL be False.
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=invalid_registry,
            template_policy_text=invalid_template,
            ecr_repository_prefix=prefix,
        )

        assert result['healthomics_usable'] is False, (
            f'Expected healthomics_usable=False when both policies are invalid. Result: {result}'
        )

    @settings(max_examples=100)
    @given(
        registry_has_create=st.booleans(),
        registry_has_import=st.booleans(),
        template_has_batch_get=st.booleans(),
        template_has_download=st.booleans(),
        prefix=ecr_prefix_strategy,
    )
    def test_usability_iff_all_permissions_present(
        self,
        registry_has_create: bool,
        registry_has_import: bool,
        template_has_batch_get: bool,
        template_has_download: bool,
        prefix: Optional[str],
    ):
        """Property 4.8: healthomics_usable is True IFF all permissions are present.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        The healthomics_usable field SHALL be True if and only if all four required
        permissions are granted across both policies.
        """
        # Build registry policy with selected actions
        registry_actions = []
        if registry_has_create:
            registry_actions.append('ecr:CreateRepository')
        if registry_has_import:
            registry_actions.append('ecr:BatchImportUpstreamImage')
        if not registry_actions:
            registry_actions.append('ecr:DescribeRepositories')  # Placeholder

        registry_policy = json.dumps(
            {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Sid': 'RegistryAccess',
                        'Effect': 'Allow',
                        'Principal': {'Service': HEALTHOMICS_PRINCIPAL},
                        'Action': registry_actions,
                        'Resource': '*',
                    }
                ],
            }
        )

        # Build template policy with selected actions
        template_actions = []
        if template_has_batch_get:
            template_actions.append('ecr:BatchGetImage')
        if template_has_download:
            template_actions.append('ecr:GetDownloadUrlForLayer')
        if not template_actions:
            template_actions.append('ecr:DescribeRepositories')  # Placeholder

        template_policy = json.dumps(
            {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Sid': 'TemplateAccess',
                        'Effect': 'Allow',
                        'Principal': {'Service': HEALTHOMICS_PRINCIPAL},
                        'Action': template_actions,
                        'Resource': '*',
                    }
                ],
            }
        )

        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=registry_policy,
            template_policy_text=template_policy,
            ecr_repository_prefix=prefix,
        )

        # Expected: usable only if ALL four permissions are present
        expected_usable = (
            registry_has_create
            and registry_has_import
            and template_has_batch_get
            and template_has_download
        )

        assert result['healthomics_usable'] == expected_usable, (
            f'Expected healthomics_usable={expected_usable} for permissions: '
            f'registry_create={registry_has_create}, registry_import={registry_has_import}, '
            f'template_batch_get={template_has_batch_get}, template_download={template_has_download}. '
            f'Got: {result["healthomics_usable"]}'
        )

        # Verify individual permission flags
        expected_registry_granted = registry_has_create and registry_has_import
        assert result['registry_permission_granted'] == expected_registry_granted

        expected_template_granted = template_has_batch_get and template_has_download
        assert result['repository_template_permission_granted'] == expected_template_granted

    @settings(max_examples=100)
    @given(
        registry_policy=valid_registry_policy_strategy(),
        template_policy=valid_template_policy_strategy(),
    )
    def test_result_contains_all_required_fields(self, registry_policy: str, template_policy: str):
        """Property 4.9: Result contains all required fields.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        The result dictionary SHALL always contain all required fields regardless
        of input values.
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=registry_policy,
            template_policy_text=template_policy,
            ecr_repository_prefix=None,
        )

        required_fields = [
            'healthomics_usable',
            'registry_permission_granted',
            'repository_template_exists',
            'repository_template_permission_granted',
            'missing_registry_permissions',
            'missing_template_permissions',
        ]

        for field in required_fields:
            assert field in result, f'Missing required field: {field}'

        # Verify types
        assert isinstance(result['healthomics_usable'], bool)
        assert isinstance(result['registry_permission_granted'], bool)
        assert isinstance(result['repository_template_exists'], bool)
        assert isinstance(result['repository_template_permission_granted'], bool)
        assert isinstance(result['missing_registry_permissions'], list)
        assert isinstance(result['missing_template_permissions'], list)

    @settings(max_examples=100)
    @given(
        registry_policy=st.one_of(valid_registry_policy_strategy(), st.none()),
        template_policy=st.one_of(valid_template_policy_strategy(), st.none()),
        prefix=ecr_prefix_strategy,
    )
    def test_usability_logical_conjunction(
        self, registry_policy: Optional[str], template_policy: Optional[str], prefix: Optional[str]
    ):
        """Property 4.10: healthomics_usable equals logical AND of all conditions.

        Feature: ecr-container-tools, Property 4: HealthOmics Usability Evaluation
        **Validates: Requirements 3.3, 3.4, 3.5**

        The healthomics_usable field SHALL equal the logical conjunction (AND) of:
        - registry_permission_granted
        - repository_template_exists
        - repository_template_permission_granted
        """
        result = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=registry_policy,
            template_policy_text=template_policy,
            ecr_repository_prefix=prefix,
        )

        expected_usable = (
            result['registry_permission_granted']
            and result['repository_template_exists']
            and result['repository_template_permission_granted']
        )

        assert result['healthomics_usable'] == expected_usable, (
            f'healthomics_usable should equal AND of all conditions. '
            f'registry_granted={result["registry_permission_granted"]}, '
            f'template_exists={result["repository_template_exists"]}, '
            f'template_granted={result["repository_template_permission_granted"]}, '
            f'expected_usable={expected_usable}, '
            f'actual_usable={result["healthomics_usable"]}'
        )
