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

"""ECR utility functions for permission checking and HealthOmics integration."""

import json
from awslabs.aws_healthomics_mcp_server.consts import (
    ECR_REQUIRED_REGISTRY_ACTIONS,
    ECR_REQUIRED_REPOSITORY_ACTIONS,
    HEALTHOMICS_PRINCIPAL,
)
from awslabs.aws_healthomics_mcp_server.models.ecr import HealthOmicsAccessStatus
from loguru import logger
from typing import Any, Dict, List, Optional, Set, Tuple


def _normalize_actions(actions: Any) -> Set[str]:
    """Normalize IAM policy actions to a set of lowercase strings.

    Args:
        actions: Actions from IAM policy (can be string, list, or None)

    Returns:
        Set of normalized action strings
    """
    if actions is None:
        return set()
    if isinstance(actions, str):
        return {actions.lower()}
    if isinstance(actions, list):
        return {action.lower() for action in actions if isinstance(action, str)}
    return set()


def _check_principal_match(principal: Any, target_principal: str) -> bool:
    """Check if a principal in an IAM policy matches the target principal.

    Args:
        principal: Principal from IAM policy statement (can be string, dict, or '*')
        target_principal: The principal to match (e.g., 'omics.amazonaws.com')

    Returns:
        True if the principal matches, False otherwise
    """
    if principal is None:
        return False

    # Handle wildcard principal
    if principal == '*':
        return True

    # Handle string principal
    if isinstance(principal, str):
        return principal == target_principal

    # Handle dict principal (e.g., {'Service': 'omics.amazonaws.com'})
    if isinstance(principal, dict):
        # Check Service principal
        service = principal.get('Service')
        if service is not None:
            if isinstance(service, str):
                return service == target_principal
            if isinstance(service, list):
                return target_principal in service

        # Check AWS principal (for cross-account access)
        aws = principal.get('AWS')
        if aws is not None:
            if isinstance(aws, str):
                return aws == target_principal or aws == '*'
            if isinstance(aws, list):
                return target_principal in aws or '*' in aws

    return False


def _check_actions_allowed(
    statement_actions: Set[str], required_actions: List[str], allow_wildcards: bool = True
) -> Tuple[bool, List[str]]:
    """Check if required actions are allowed by statement actions.

    Args:
        statement_actions: Set of actions from the policy statement (normalized to lowercase)
        required_actions: List of required actions to check
        allow_wildcards: Whether to allow wildcard actions (e.g., 'ecr:*')

    Returns:
        Tuple of (all_allowed, missing_actions)
    """
    missing_actions = []

    for required_action in required_actions:
        required_lower = required_action.lower()
        action_allowed = False

        # Check for exact match
        if required_lower in statement_actions:
            action_allowed = True
        # Check for wildcard match (e.g., 'ecr:*' allows all ecr actions)
        elif allow_wildcards:
            # Check for service-level wildcard (e.g., 'ecr:*')
            service_prefix = required_lower.split(':')[0] + ':*'
            if service_prefix in statement_actions:
                action_allowed = True
            # Check for global wildcard
            elif '*' in statement_actions:
                action_allowed = True

        if not action_allowed:
            missing_actions.append(required_action)

    return len(missing_actions) == 0, missing_actions


def _parse_policy_document(policy_text: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse a policy document from JSON string.

    Args:
        policy_text: JSON string of the policy document

    Returns:
        Parsed policy document as dict, or None if parsing fails
    """
    if policy_text is None:
        return None

    try:
        return json.loads(policy_text)
    except json.JSONDecodeError as e:
        logger.warning(f'Failed to parse policy document: {e}')
        return None


def check_repository_healthomics_access(
    policy_text: Optional[str],
) -> Tuple[HealthOmicsAccessStatus, List[str]]:
    """Check if a repository policy grants HealthOmics the required permissions.

    Parses the repository policy and checks if the HealthOmics principal
    (omics.amazonaws.com) has the required permissions:
    - ecr:BatchGetImage
    - ecr:GetDownloadUrlForLayer

    Args:
        policy_text: JSON string of the repository policy, or None if no policy exists

    Returns:
        Tuple of (access_status, missing_permissions):
        - access_status: HealthOmicsAccessStatus indicating accessibility
        - missing_permissions: List of missing permission actions
    """
    # No policy means unknown access (policy might be inherited or not set)
    if policy_text is None:
        return HealthOmicsAccessStatus.UNKNOWN, []

    policy = _parse_policy_document(policy_text)
    if policy is None:
        return HealthOmicsAccessStatus.UNKNOWN, []

    statements = policy.get('Statement', [])
    if not isinstance(statements, list):
        statements = [statements]

    # Track which required actions are granted
    granted_actions: Set[str] = set()

    for statement in statements:
        if not isinstance(statement, dict):
            continue

        # Only consider Allow statements
        effect = statement.get('Effect', '').lower()
        if effect != 'allow':
            continue

        # Check if principal matches HealthOmics
        principal = statement.get('Principal')
        if not _check_principal_match(principal, HEALTHOMICS_PRINCIPAL):
            continue

        # Get actions from this statement
        actions = statement.get('Action')
        statement_actions = _normalize_actions(actions)

        # Check which required actions are granted by this statement
        for required_action in ECR_REQUIRED_REPOSITORY_ACTIONS:
            required_lower = required_action.lower()
            if required_lower in statement_actions:
                granted_actions.add(required_action)
            # Check for wildcards
            elif 'ecr:*' in statement_actions or '*' in statement_actions:
                granted_actions.add(required_action)

    # Determine missing actions
    missing_actions = [
        action for action in ECR_REQUIRED_REPOSITORY_ACTIONS if action not in granted_actions
    ]

    if len(missing_actions) == 0:
        return HealthOmicsAccessStatus.ACCESSIBLE, []
    else:
        return HealthOmicsAccessStatus.NOT_ACCESSIBLE, missing_actions


def check_registry_policy_healthomics_access(
    policy_text: Optional[str],
    ecr_repository_prefix: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """Check if the registry permissions policy grants HealthOmics the required permissions.

    Parses the registry permissions policy and checks if the HealthOmics principal
    (omics.amazonaws.com) has the required permissions for pull-through cache:
    - ecr:CreateRepository
    - ecr:BatchImportUpstreamImage

    Args:
        policy_text: JSON string of the registry permissions policy, or None if no policy exists
        ecr_repository_prefix: Optional prefix to check for resource restrictions

    Returns:
        Tuple of (permission_granted, missing_permissions):
        - permission_granted: True if all required permissions are granted
        - missing_permissions: List of missing permission actions
    """
    # No policy means no permissions granted
    if policy_text is None:
        return False, list(ECR_REQUIRED_REGISTRY_ACTIONS)

    policy = _parse_policy_document(policy_text)
    if policy is None:
        return False, list(ECR_REQUIRED_REGISTRY_ACTIONS)

    statements = policy.get('Statement', [])
    if not isinstance(statements, list):
        statements = [statements]

    # Track which required actions are granted
    granted_actions: Set[str] = set()

    for statement in statements:
        if not isinstance(statement, dict):
            continue

        # Only consider Allow statements
        effect = statement.get('Effect', '').lower()
        if effect != 'allow':
            continue

        # Check if principal matches HealthOmics
        principal = statement.get('Principal')
        if not _check_principal_match(principal, HEALTHOMICS_PRINCIPAL):
            continue

        # Get actions from this statement
        actions = statement.get('Action')
        statement_actions = _normalize_actions(actions)

        # Check which required actions are granted by this statement
        for required_action in ECR_REQUIRED_REGISTRY_ACTIONS:
            required_lower = required_action.lower()
            if required_lower in statement_actions:
                granted_actions.add(required_action)
            # Check for wildcards
            elif 'ecr:*' in statement_actions or '*' in statement_actions:
                granted_actions.add(required_action)

    # Determine missing actions
    missing_actions = [
        action for action in ECR_REQUIRED_REGISTRY_ACTIONS if action not in granted_actions
    ]

    return len(missing_actions) == 0, missing_actions


def check_repository_template_healthomics_access(
    template_policy_text: Optional[str],
) -> Tuple[bool, bool, List[str]]:
    """Check if a repository creation template grants HealthOmics the required permissions.

    Parses the repository creation template's applied policy and checks if it grants
    the HealthOmics principal (omics.amazonaws.com) the required permissions:
    - ecr:BatchGetImage
    - ecr:GetDownloadUrlForLayer

    Args:
        template_policy_text: JSON string of the template's repository policy,
                              or None if no template/policy exists

    Returns:
        Tuple of (template_exists, permission_granted, missing_permissions):
        - template_exists: True if a template policy was provided
        - permission_granted: True if all required permissions are granted
        - missing_permissions: List of missing permission actions
    """
    # No template policy means template doesn't exist or has no policy
    if template_policy_text is None:
        return False, False, list(ECR_REQUIRED_REPOSITORY_ACTIONS)

    policy = _parse_policy_document(template_policy_text)
    if policy is None:
        return True, False, list(ECR_REQUIRED_REPOSITORY_ACTIONS)

    statements = policy.get('Statement', [])
    if not isinstance(statements, list):
        statements = [statements]

    # Track which required actions are granted
    granted_actions: Set[str] = set()

    for statement in statements:
        if not isinstance(statement, dict):
            continue

        # Only consider Allow statements
        effect = statement.get('Effect', '').lower()
        if effect != 'allow':
            continue

        # Check if principal matches HealthOmics
        principal = statement.get('Principal')
        if not _check_principal_match(principal, HEALTHOMICS_PRINCIPAL):
            continue

        # Get actions from this statement
        actions = statement.get('Action')
        statement_actions = _normalize_actions(actions)

        # Check which required actions are granted by this statement
        for required_action in ECR_REQUIRED_REPOSITORY_ACTIONS:
            required_lower = required_action.lower()
            if required_lower in statement_actions:
                granted_actions.add(required_action)
            # Check for wildcards
            elif 'ecr:*' in statement_actions or '*' in statement_actions:
                granted_actions.add(required_action)

    # Determine missing actions
    missing_actions = [
        action for action in ECR_REQUIRED_REPOSITORY_ACTIONS if action not in granted_actions
    ]

    return True, len(missing_actions) == 0, missing_actions


def get_pull_through_cache_rule_for_repository(
    repository_name: str,
    ptc_rules: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Get the pull-through cache rule that matches a repository name.

    Args:
        repository_name: The ECR repository name to check
        ptc_rules: List of pull-through cache rules from describe_pull_through_cache_rules

    Returns:
        The matching pull-through cache rule dict, or None if no match
    """
    for rule in ptc_rules:
        prefix = rule.get('ecrRepositoryPrefix', '')
        if prefix and repository_name.startswith(f'{prefix}/'):
            return rule
    return None


def evaluate_pull_through_cache_healthomics_usability(
    registry_policy_text: Optional[str],
    template_policy_text: Optional[str],
    ecr_repository_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate if a pull-through cache is usable by HealthOmics.

    Combines checks for registry permissions policy and repository creation template
    to determine overall HealthOmics usability for a pull-through cache rule.

    A pull-through cache is usable by HealthOmics if and only if:
    1. The registry permissions policy grants HealthOmics ecr:CreateRepository
       and ecr:BatchImportUpstreamImage for the prefix
    2. A repository creation template exists for the prefix
    3. The repository creation template grants HealthOmics ecr:BatchGetImage
       and ecr:GetDownloadUrlForLayer

    Args:
        registry_policy_text: JSON string of the registry permissions policy
        template_policy_text: JSON string of the template's repository policy
        ecr_repository_prefix: The ECR repository prefix for the pull-through cache

    Returns:
        Dict containing:
        - healthomics_usable: True if all conditions are met
        - registry_permission_granted: True if registry policy grants required permissions
        - repository_template_exists: True if a template exists
        - repository_template_permission_granted: True if template grants required permissions
        - missing_registry_permissions: List of missing registry permissions
        - missing_template_permissions: List of missing template permissions
    """
    # Check registry permissions
    registry_granted, missing_registry = check_registry_policy_healthomics_access(
        registry_policy_text, ecr_repository_prefix
    )

    # Check template permissions
    template_exists, template_granted, missing_template = (
        check_repository_template_healthomics_access(template_policy_text)
    )

    # HealthOmics usability requires all three conditions
    healthomics_usable = registry_granted and template_exists and template_granted

    return {
        'healthomics_usable': healthomics_usable,
        'registry_permission_granted': registry_granted,
        'repository_template_exists': template_exists,
        'repository_template_permission_granted': template_granted,
        'missing_registry_permissions': missing_registry,
        'missing_template_permissions': missing_template,
    }


def initiate_pull_through_cache(
    ecr_client: Any,
    repository_name: str,
    image_tag: Optional[str] = None,
    image_digest: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Initiate a pull-through cache by calling batch_get_image.

    When an image is not found in a pull-through cache repository, calling
    batch_get_image will trigger ECR to pull the image from the upstream
    registry. This is useful for pre-caching images before HealthOmics
    workflow execution.

    Args:
        ecr_client: boto3 ECR client
        repository_name: The ECR repository name (e.g., "docker-hub/library/ubuntu")
        image_tag: Image tag to pull (e.g., "latest")
        image_digest: Image digest to pull (e.g., "sha256:...")

    Returns:
        Tuple of (success, message, image_details):
        - success: True if the pull-through was initiated successfully
        - message: Human-readable status message
        - image_details: Image details if available after pull-through
    """
    import botocore.exceptions

    # Build image identifier
    image_ids: List[Dict[str, str]] = []
    if image_digest:
        image_ids.append({'imageDigest': image_digest})
    else:
        image_ids.append({'imageTag': image_tag or 'latest'})

    try:
        # batch_get_image triggers the pull-through cache mechanism
        response = ecr_client.batch_get_image(
            repositoryName=repository_name,
            imageIds=image_ids,
            acceptedMediaTypes=[
                'application/vnd.docker.distribution.manifest.v2+json',
                'application/vnd.oci.image.manifest.v1+json',
            ],
        )

        # Check if we got images back
        images = response.get('images', [])
        failures = response.get('failures', [])

        if images:
            # Pull-through succeeded - image is now cached
            image = images[0]
            image_id = image.get('imageId', {})
            digest = image_id.get('imageDigest', '')
            tag = image_id.get('imageTag', image_tag)

            return (
                True,
                f'Pull-through cache initiated successfully. Image {repository_name}:{tag or digest} is now cached.',
                {
                    'imageDigest': digest,
                    'imageTag': tag,
                    'repositoryName': repository_name,
                },
            )

        if failures:
            # Check failure reasons
            failure = failures[0]
            failure_code = failure.get('failureCode', '')
            failure_reason = failure.get('failureReason', '')

            if failure_code == 'ImageNotFound':
                return (
                    False,
                    f'Image not found in upstream registry: {failure_reason}',
                    None,
                )
            elif failure_code == 'RepositoryNotFound':
                return (
                    False,
                    f'Repository not found: {failure_reason}',
                    None,
                )
            else:
                return (
                    False,
                    f'Pull-through cache failed: {failure_code} - {failure_reason}',
                    None,
                )

        return (
            False,
            'Pull-through cache returned no images and no failures',
            None,
        )

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'RepositoryNotFoundException':
            # Repository doesn't exist yet - this is expected for first pull
            # The pull-through cache should create it, but we need permissions
            return (
                False,
                f'Repository does not exist yet. Pull-through cache may create it on first access: {error_message}',
                None,
            )
        elif error_code == 'ImageNotFoundException':
            return (
                False,
                f'Image not found in upstream registry: {error_message}',
                None,
            )
        elif error_code == 'AccessDeniedException':
            return (
                False,
                f'Access denied. Ensure IAM permissions include ecr:BatchGetImage: {error_message}',
                None,
            )
        else:
            logger.warning(f'Pull-through cache initiation failed: {error_code} - {error_message}')
            return (
                False,
                f'Pull-through cache initiation failed: {error_message}',
                None,
            )

    except Exception as e:
        logger.warning(f'Unexpected error initiating pull-through cache: {str(e)}')
        return (
            False,
            f'Unexpected error initiating pull-through cache: {str(e)}',
            None,
        )
