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

"""ECR container tools for the AWS HealthOmics MCP server."""

import botocore
import botocore.exceptions
import json
from awslabs.aws_healthomics_mcp_server.consts import (
    DEFAULT_ECR_PREFIXES,
    ECR_REQUIRED_REGISTRY_ACTIONS,
    ECR_REQUIRED_REPOSITORY_ACTIONS,
    HEALTHOMICS_PRINCIPAL,
)
from awslabs.aws_healthomics_mcp_server.models.ecr import (
    UPSTREAM_REGISTRY_URLS,
    ContainerAvailabilityResponse,
    ContainerImage,
    ECRRepository,
    ECRRepositoryListResponse,
    HealthOmicsAccessStatus,
    PullThroughCacheListResponse,
    PullThroughCacheRule,
    UpstreamRegistry,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_ecr_client,
)
from awslabs.aws_healthomics_mcp_server.utils.ecr_utils import (
    check_repository_healthomics_access,
    evaluate_pull_through_cache_healthomics_usability,
    get_pull_through_cache_rule_for_repository,
    initiate_pull_through_cache,
)
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional


async def list_ecr_repositories(
    ctx: Context,
    max_results: int = Field(
        100,
        description='Maximum number of results to return',
        ge=1,
        le=1000,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Pagination token from a previous response',
    ),
    filter_healthomics_accessible: bool = Field(
        False,
        description='Only return repositories accessible by HealthOmics',
    ),
) -> Dict[str, Any]:
    """List ECR repositories with HealthOmics accessibility status.

    Lists all ECR repositories in the current region and checks each repository's
    policy to determine if HealthOmics has the required permissions to pull images.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of results to return (default: 100, max: 1000)
        next_token: Pagination token from a previous response
        filter_healthomics_accessible: If True, only return repositories that are
            accessible by HealthOmics

    Returns:
        Dictionary containing:
        - repositories: List of ECR repositories with accessibility status
        - next_token: Pagination token if more results are available
        - total_count: Total number of repositories returned
    """
    client = get_ecr_client()

    # Build parameters for describe_repositories API
    params: Dict[str, Any] = {'maxResults': max_results}
    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.describe_repositories(**params)

        # Process each repository
        repositories: List[ECRRepository] = []
        for repo in response.get('repositories', []):
            repository_name = repo.get('repositoryName', '')
            repository_arn = repo.get('repositoryArn', '')
            repository_uri = repo.get('repositoryUri', '')
            created_at = repo.get('createdAt')

            # Check HealthOmics accessibility by getting the repository policy
            healthomics_accessible = HealthOmicsAccessStatus.UNKNOWN
            missing_permissions: List[str] = []

            try:
                policy_response = client.get_repository_policy(repositoryName=repository_name)
                policy_text = policy_response.get('policyText')
                healthomics_accessible, missing_permissions = check_repository_healthomics_access(
                    policy_text
                )
            except botocore.exceptions.ClientError as policy_error:
                error_code = policy_error.response.get('Error', {}).get('Code', '')
                if error_code == 'RepositoryPolicyNotFoundException':
                    # No policy means HealthOmics cannot access the repository
                    healthomics_accessible = HealthOmicsAccessStatus.NOT_ACCESSIBLE
                    missing_permissions = list(ECR_REQUIRED_REPOSITORY_ACTIONS)
                    logger.debug(
                        f'Repository {repository_name} has no policy, '
                        'marking as not accessible by HealthOmics'
                    )
                else:
                    # Other errors - mark as unknown
                    logger.warning(
                        f'Failed to get policy for repository {repository_name}: '
                        f'{error_code} - {policy_error.response.get("Error", {}).get("Message", "")}'
                    )
                    healthomics_accessible = HealthOmicsAccessStatus.UNKNOWN
                await ctx.error(f'Failed to get repository policy: {policy_error}')

            # Apply filter if requested
            if filter_healthomics_accessible:
                if healthomics_accessible != HealthOmicsAccessStatus.ACCESSIBLE:
                    continue

            # Create ECRRepository model
            ecr_repo = ECRRepository(
                repository_name=repository_name,
                repository_arn=repository_arn,
                repository_uri=repository_uri,
                created_at=created_at,
                healthomics_accessible=healthomics_accessible,
                missing_permissions=missing_permissions,
            )
            repositories.append(ecr_repo)

        # Build response
        response_next_token = response.get('nextToken')
        result = ECRRepositoryListResponse(
            repositories=repositories,
            next_token=response_next_token,
            total_count=len(repositories),
        )

        return result.model_dump()

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'AccessDeniedException':
            required_actions = ['ecr:DescribeRepositories', 'ecr:GetRepositoryPolicy']
            logger.error(f'Access denied to ECR: {error_message}')
            await ctx.error(
                f'Access denied to ECR. Ensure IAM permissions include: {required_actions}'
            )
            raise
        else:
            logger.error(f'ECR API error: {error_code} - {error_message}')
            await ctx.error(f'ECR error: {error_message}')
            raise

    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error accessing ECR: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise

    except Exception as e:
        error_message = f'Unexpected error listing ECR repositories: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


def _is_pull_through_cache_repository(repository_name: str) -> bool:
    """Check if a repository has a pull-through cache rule configured.

    Queries ECR to check if any pull-through cache rule's prefix matches
    the repository name. This is more accurate than just checking default
    prefixes since users can configure custom prefixes.

    Args:
        repository_name: The ECR repository name to check

    Returns:
        True if a pull-through cache rule exists for this repository, False otherwise
    """
    client = get_ecr_client()

    try:
        # Get all pull-through cache rules
        ptc_rules = []
        next_token = None

        while True:
            params: Dict[str, Any] = {'maxResults': 100}
            if next_token:
                params['nextToken'] = next_token

            response = client.describe_pull_through_cache_rules(**params)
            ptc_rules.extend(response.get('pullThroughCacheRules', []))
            next_token = response.get('nextToken')

            if not next_token:
                break

        # Check if repository name matches any pull-through cache prefix
        for rule in ptc_rules:
            prefix = rule.get('ecrRepositoryPrefix', '')
            if prefix and repository_name.startswith(f'{prefix}/'):
                return True

        return False

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'AccessDeniedException':
            # Fall back to checking default prefixes if we can't query rules
            logger.warning(
                'Access denied to describe pull-through cache rules, '
                'falling back to default prefix check'
            )
            for prefix in DEFAULT_ECR_PREFIXES.values():
                if repository_name.startswith(f'{prefix}/'):
                    return True
            return False
        else:
            logger.warning(f'Error checking pull-through cache rules: {e}')
            # Fall back to default prefix check on other errors
            for prefix in DEFAULT_ECR_PREFIXES.values():
                if repository_name.startswith(f'{prefix}/'):
                    return True
            return False

    except Exception as e:
        logger.warning(f'Unexpected error checking pull-through cache rules: {e}')
        # Fall back to default prefix check
        for prefix in DEFAULT_ECR_PREFIXES.values():
            if repository_name.startswith(f'{prefix}/'):
                return True
        return False


def _check_pull_through_cache_healthomics_usability(
    repository_name: str,
) -> Dict[str, Any]:
    """Check if a pull-through cache repository is usable by HealthOmics.

    Evaluates whether the pull-through cache configuration allows HealthOmics
    to use the cached images. This includes checking:
    1. Registry permissions policy grants HealthOmics required permissions
    2. Repository creation template exists and grants HealthOmics access

    Args:
        repository_name: The ECR repository name to check

    Returns:
        Dictionary containing:
        - is_ptc: Whether this is a pull-through cache repository
        - healthomics_usable: Whether HealthOmics can use this pull-through cache
        - ptc_rule: The matching pull-through cache rule (if any)
        - usability_details: Detailed usability information
    """
    client = get_ecr_client()

    result: Dict[str, Any] = {
        'is_ptc': False,
        'healthomics_usable': False,
        'ptc_rule': None,
        'usability_details': None,
    }

    try:
        # Get all pull-through cache rules
        ptc_rules = []
        next_token = None

        while True:
            params: Dict[str, Any] = {'maxResults': 100}
            if next_token:
                params['nextToken'] = next_token

            response = client.describe_pull_through_cache_rules(**params)
            ptc_rules.extend(response.get('pullThroughCacheRules', []))
            next_token = response.get('nextToken')

            if not next_token:
                break

        # Find matching rule
        matching_rule = get_pull_through_cache_rule_for_repository(repository_name, ptc_rules)
        if not matching_rule:
            return result

        result['is_ptc'] = True
        result['ptc_rule'] = matching_rule
        ecr_repository_prefix = matching_rule.get('ecrRepositoryPrefix', '')

        # Get registry permissions policy
        registry_policy_text: Optional[str] = None
        try:
            registry_policy_response = client.get_registry_policy()
            registry_policy_text = registry_policy_response.get('policyText')
        except botocore.exceptions.ClientError as policy_error:
            error_code = policy_error.response.get('Error', {}).get('Code', '')
            if error_code != 'RegistryPolicyNotFoundException':
                logger.warning(f'Failed to get registry policy: {policy_error}')

        # Get repository creation template
        template_policy_text: Optional[str] = None
        try:
            template_response = client.describe_repository_creation_templates(
                prefixes=[ecr_repository_prefix]
            )
            templates = template_response.get('repositoryCreationTemplates', [])
            if templates:
                template_policy_text = templates[0].get('repositoryPolicy')
        except botocore.exceptions.ClientError as template_error:
            error_code = template_error.response.get('Error', {}).get('Code', '')
            if error_code != 'TemplateNotFoundException':
                logger.warning(f'Failed to get repository creation template: {template_error}')

        # Evaluate usability
        usability = evaluate_pull_through_cache_healthomics_usability(
            registry_policy_text=registry_policy_text,
            template_policy_text=template_policy_text,
            ecr_repository_prefix=ecr_repository_prefix,
        )

        result['healthomics_usable'] = usability['healthomics_usable']
        result['usability_details'] = usability

        return result

    except Exception as e:
        logger.warning(f'Error checking pull-through cache HealthOmics usability: {e}')
        return result


async def check_container_availability(
    ctx: Context,
    repository_name: str = Field(
        ...,
        description='ECR repository name (e.g., "my-repo" or "docker-hub/library/ubuntu")',
    ),
    image_tag: str = Field(
        'latest',
        description='Image tag to check (default: "latest")',
    ),
    image_digest: Optional[str] = Field(
        None,
        description='Image digest (sha256:...) - if provided, takes precedence over tag',
    ),
    initiate_pull_through: bool = Field(
        False,
        description='If True and the image is not found in a pull-through cache repository '
        'that is accessible to HealthOmics, attempt to initiate the pull-through '
        'using batch_get_image API call',
    ),
) -> Dict[str, Any]:
    """Check if a container image is available in ECR and accessible by HealthOmics.

    Queries ECR to determine if a specific container image exists in a repository
    and whether HealthOmics has the required permissions to pull the image.
    For pull-through cache repositories, indicates that the image may be pulled
    on first access even if not currently cached.

    When initiate_pull_through is True and the image is not found in a pull-through
    cache repository that is accessible to HealthOmics, this function will attempt
    to initiate the pull-through using ECR's batch_get_image API call. This triggers
    ECR to pull the image from the upstream registry and cache it locally.

    Args:
        ctx: MCP context for error reporting
        repository_name: ECR repository name (e.g., "my-repo" or "docker-hub/library/ubuntu")
        image_tag: Image tag to check (default: "latest")
        image_digest: Image digest (sha256:...) - if provided, takes precedence over tag
        initiate_pull_through: If True, attempt to initiate pull-through cache for
            missing images in accessible pull-through cache repositories

    Returns:
        Dictionary containing:
        - available: Whether the image is available
        - image: Image details if available (digest, size, push timestamp)
        - repository_exists: Whether the repository exists
        - is_pull_through_cache: Whether this is a pull-through cache repository
        - healthomics_accessible: Whether HealthOmics can access the image
        - missing_permissions: List of missing ECR permissions for HealthOmics
        - message: Human-readable status message
        - pull_through_initiated: Whether a pull-through was initiated
        - pull_through_initiation_message: Message about pull-through initiation result
    """
    # Validate repository name
    if not repository_name or not repository_name.strip():
        await ctx.error('Repository name is required and cannot be empty')
        return ContainerAvailabilityResponse(
            available=False,
            repository_exists=False,
            is_pull_through_cache=False,
            message='Repository name is required and cannot be empty',
        ).model_dump()

    repository_name = repository_name.strip()

    # Validate image digest format if provided
    if image_digest:
        image_digest = image_digest.strip()
        if not image_digest.startswith('sha256:'):
            await ctx.error('Invalid image digest format. Must start with "sha256:"')
            return ContainerAvailabilityResponse(
                available=False,
                repository_exists=True,
                is_pull_through_cache=_is_pull_through_cache_repository(repository_name),
                message='Invalid image digest format. Must start with "sha256:"',
            ).model_dump()

    # Detect if this is a pull-through cache repository
    is_ptc = _is_pull_through_cache_repository(repository_name)

    client = get_ecr_client()

    # Build image identifier for describe_images API
    image_ids: List[Dict[str, str]] = []
    if image_digest:
        image_ids.append({'imageDigest': image_digest})
    else:
        image_ids.append({'imageTag': image_tag})

    try:
        response = client.describe_images(
            repositoryName=repository_name,
            imageIds=image_ids,
        )

        # Process the image details
        image_details = response.get('imageDetails', [])
        if image_details:
            image_detail = image_details[0]

            # Extract image information
            digest = image_detail.get('imageDigest', '')
            size_bytes = image_detail.get('imageSizeInBytes')
            pushed_at = image_detail.get('imagePushedAt')

            # Get the tag - use the requested tag or the first available tag
            tags = image_detail.get('imageTags', [])
            tag = image_tag if image_tag in tags else (tags[0] if tags else None)

            container_image = ContainerImage(
                repository_name=repository_name,
                image_tag=tag,
                image_digest=digest,
                image_size_bytes=size_bytes,
                pushed_at=pushed_at,
                exists=True,
            )

            # Check HealthOmics accessibility by getting the repository policy
            healthomics_accessible = HealthOmicsAccessStatus.UNKNOWN
            missing_permissions: List[str] = []

            try:
                policy_response = client.get_repository_policy(repositoryName=repository_name)
                policy_text = policy_response.get('policyText')
                healthomics_accessible, missing_permissions = check_repository_healthomics_access(
                    policy_text
                )
            except botocore.exceptions.ClientError as policy_error:
                error_code = policy_error.response.get('Error', {}).get('Code', '')
                if error_code == 'RepositoryPolicyNotFoundException':
                    # No policy means HealthOmics cannot access the repository
                    healthomics_accessible = HealthOmicsAccessStatus.NOT_ACCESSIBLE
                    missing_permissions = list(ECR_REQUIRED_REPOSITORY_ACTIONS)
                    logger.debug(
                        f'Repository {repository_name} has no policy, '
                        'marking as not accessible by HealthOmics'
                    )
                else:
                    # Other errors - mark as unknown
                    logger.warning(
                        f'Failed to get policy for repository {repository_name}: '
                        f'{error_code} - {policy_error.response.get("Error", {}).get("Message", "")}'
                    )
                    healthomics_accessible = HealthOmicsAccessStatus.UNKNOWN

            # Build message based on availability and accessibility
            message = f'Image found: {repository_name}:{tag or digest}'
            if healthomics_accessible == HealthOmicsAccessStatus.NOT_ACCESSIBLE:
                message += (
                    '. WARNING: HealthOmics cannot access this image - missing permissions: '
                    + ', '.join(missing_permissions)
                )
            elif healthomics_accessible == HealthOmicsAccessStatus.UNKNOWN:
                message += '. HealthOmics accessibility could not be determined.'

            return ContainerAvailabilityResponse(
                available=True,
                image=container_image,
                repository_exists=True,
                is_pull_through_cache=is_ptc,
                healthomics_accessible=healthomics_accessible,
                missing_permissions=missing_permissions,
                message=message,
            ).model_dump()
        else:
            # No image details returned - image not found
            identifier = image_digest if image_digest else f'tag:{image_tag}'
            message = f'Image not found: {repository_name} ({identifier})'
            if is_ptc:
                message += '. This is a pull-through cache repository - the image may be pulled on first access.'

            return ContainerAvailabilityResponse(
                available=False,
                repository_exists=True,
                is_pull_through_cache=is_ptc,
                message=message,
            ).model_dump()

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'RepositoryNotFoundException':
            logger.debug(f'Repository not found: {repository_name}')
            message = f'Repository not found: {repository_name}'

            # Check if we should initiate pull-through
            pull_through_initiated = False
            pull_through_initiation_message: Optional[str] = None

            if is_ptc and initiate_pull_through:
                # Check if the pull-through cache is usable by HealthOmics
                ptc_usability = _check_pull_through_cache_healthomics_usability(repository_name)

                if ptc_usability['healthomics_usable']:
                    logger.info(
                        f'Initiating pull-through cache for {repository_name}:{image_tag} '
                        '(repository does not exist yet)'
                    )
                    success, ptc_message, image_details = initiate_pull_through_cache(
                        client,
                        repository_name,
                        image_tag=image_tag,
                        image_digest=image_digest,
                    )
                    pull_through_initiated = success
                    pull_through_initiation_message = ptc_message

                    if success and image_details:
                        # Image was successfully pulled - return as available
                        container_image = ContainerImage(
                            repository_name=repository_name,
                            image_tag=image_details.get('imageTag'),
                            image_digest=image_details.get('imageDigest', ''),
                            exists=True,
                        )
                        return ContainerAvailabilityResponse(
                            available=True,
                            image=container_image,
                            repository_exists=True,
                            is_pull_through_cache=True,
                            healthomics_accessible=HealthOmicsAccessStatus.ACCESSIBLE,
                            message=f'Image pulled via pull-through cache: {repository_name}:{image_tag}',
                            pull_through_initiated=True,
                            pull_through_initiation_message=ptc_message,
                        ).model_dump()
                    else:
                        message += f'. Pull-through initiation attempted: {ptc_message}'
                else:
                    pull_through_initiation_message = (
                        'Pull-through cache is not usable by HealthOmics. '
                        'Ensure registry policy and repository template are configured correctly.'
                    )
                    message += f'. {pull_through_initiation_message}'
            elif is_ptc:
                message += '. This appears to be a pull-through cache repository - it may be created on first image pull.'

            return ContainerAvailabilityResponse(
                available=False,
                repository_exists=False,
                is_pull_through_cache=is_ptc,
                message=message,
                pull_through_initiated=pull_through_initiated,
                pull_through_initiation_message=pull_through_initiation_message,
            ).model_dump()

        elif error_code == 'ImageNotFoundException':
            identifier = image_digest if image_digest else f'tag:{image_tag}'
            logger.debug(f'Image not found: {repository_name} ({identifier})')
            message = f'Image not found: {repository_name} ({identifier})'

            # Check if we should initiate pull-through
            pull_through_initiated = False
            pull_through_initiation_message: Optional[str] = None

            if is_ptc and initiate_pull_through:
                # Check if the pull-through cache is usable by HealthOmics
                ptc_usability = _check_pull_through_cache_healthomics_usability(repository_name)

                if ptc_usability['healthomics_usable']:
                    logger.info(f'Initiating pull-through cache for {repository_name}:{image_tag}')
                    success, ptc_message, image_details = initiate_pull_through_cache(
                        client,
                        repository_name,
                        image_tag=image_tag,
                        image_digest=image_digest,
                    )
                    pull_through_initiated = success
                    pull_through_initiation_message = ptc_message

                    if success and image_details:
                        # Image was successfully pulled - return as available
                        container_image = ContainerImage(
                            repository_name=repository_name,
                            image_tag=image_details.get('imageTag'),
                            image_digest=image_details.get('imageDigest', ''),
                            exists=True,
                        )
                        return ContainerAvailabilityResponse(
                            available=True,
                            image=container_image,
                            repository_exists=True,
                            is_pull_through_cache=True,
                            healthomics_accessible=HealthOmicsAccessStatus.ACCESSIBLE,
                            message=f'Image pulled via pull-through cache: {repository_name}:{image_tag}',
                            pull_through_initiated=True,
                            pull_through_initiation_message=ptc_message,
                        ).model_dump()
                    else:
                        message += f'. Pull-through initiation attempted: {ptc_message}'
                else:
                    pull_through_initiation_message = (
                        'Pull-through cache is not usable by HealthOmics. '
                        'Ensure registry policy and repository template are configured correctly.'
                    )
                    message += f'. {pull_through_initiation_message}'
            elif is_ptc:
                message += '. This is a pull-through cache repository - the image may be pulled on first access.'

            return ContainerAvailabilityResponse(
                available=False,
                repository_exists=True,
                is_pull_through_cache=is_ptc,
                message=message,
                pull_through_initiated=pull_through_initiated,
                pull_through_initiation_message=pull_through_initiation_message,
            ).model_dump()

        elif error_code == 'AccessDeniedException':
            required_actions = ['ecr:DescribeImages']
            logger.error(f'Access denied to ECR: {error_message}')
            await ctx.error(
                f'Access denied to ECR. Ensure IAM permissions include: {required_actions}'
            )
            raise

        else:
            logger.error(f'ECR API error: {error_code} - {error_message}')
            await ctx.error(f'ECR error: {error_message}')
            raise

    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error accessing ECR: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise

    except Exception as e:
        error_message = f'Unexpected error checking container availability: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def list_pull_through_cache_rules(
    ctx: Context,
    max_results: int = Field(
        100,
        description='Maximum number of results to return',
        ge=1,
        le=1000,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Pagination token from a previous response',
    ),
) -> Dict[str, Any]:
    """List pull-through cache rules with HealthOmics usability status.

    Lists all ECR pull-through cache rules in the current region and evaluates
    each rule's usability by HealthOmics. A pull-through cache is usable by
    HealthOmics if:
    1. The registry permissions policy grants HealthOmics the required permissions
    2. A repository creation template exists for the prefix
    3. The template grants HealthOmics the required image pull permissions

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of results to return (default: 100, max: 1000)
        next_token: Pagination token from a previous response

    Returns:
        Dictionary containing:
        - rules: List of pull-through cache rules with usability status
        - next_token: Pagination token if more results are available
    """
    client = get_ecr_client()

    # Build parameters for describe_pull_through_cache_rules API
    params: Dict[str, Any] = {'maxResults': max_results}
    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.describe_pull_through_cache_rules(**params)

        ptc_rules = response.get('pullThroughCacheRules', [])

        # If no rules exist, return empty list with guidance
        if not ptc_rules:
            logger.info('No pull-through cache rules found in the region')
            return PullThroughCacheListResponse(
                rules=[],
                next_token=None,
            ).model_dump()

        # Get registry permissions policy once (applies to all rules)
        registry_policy_text: Optional[str] = None
        try:
            registry_policy_response = client.get_registry_policy()
            registry_policy_text = registry_policy_response.get('policyText')
        except botocore.exceptions.ClientError as policy_error:
            error_code = policy_error.response.get('Error', {}).get('Code', '')
            if error_code == 'RegistryPolicyNotFoundException':
                logger.debug('No registry permissions policy found')
                registry_policy_text = None
            else:
                logger.warning(
                    f'Failed to get registry policy: {error_code} - '
                    f'{policy_error.response.get("Error", {}).get("Message", "")}'
                )
                registry_policy_text = None

        # Process each pull-through cache rule
        rules: List[PullThroughCacheRule] = []
        for ptc_rule in ptc_rules:
            ecr_repository_prefix = ptc_rule.get('ecrRepositoryPrefix', '')
            upstream_registry_url = ptc_rule.get('upstreamRegistryUrl', '')
            credential_arn = ptc_rule.get('credentialArn')
            created_at = ptc_rule.get('createdAt')
            updated_at = ptc_rule.get('updatedAt')

            # Get repository creation template for this prefix
            template_policy_text: Optional[str] = None
            try:
                template_response = client.describe_repository_creation_templates(
                    prefixes=[ecr_repository_prefix]
                )
                templates = template_response.get('repositoryCreationTemplates', [])
                if templates:
                    # Get the applied policy from the template
                    template = templates[0]
                    template_policy_text = template.get('repositoryPolicy')
            except botocore.exceptions.ClientError as template_error:
                error_code = template_error.response.get('Error', {}).get('Code', '')
                if error_code == 'TemplateNotFoundException':
                    logger.debug(
                        f'No repository creation template found for prefix: {ecr_repository_prefix}'
                    )
                    template_policy_text = None
                else:
                    logger.warning(
                        f'Failed to get repository creation template for {ecr_repository_prefix}: '
                        f'{error_code} - {template_error.response.get("Error", {}).get("Message", "")}'
                    )
                    template_policy_text = None

            # Evaluate HealthOmics usability
            usability = evaluate_pull_through_cache_healthomics_usability(
                registry_policy_text=registry_policy_text,
                template_policy_text=template_policy_text,
                ecr_repository_prefix=ecr_repository_prefix,
            )

            # Create PullThroughCacheRule model
            rule = PullThroughCacheRule(
                ecr_repository_prefix=ecr_repository_prefix,
                upstream_registry_url=upstream_registry_url,
                credential_arn=credential_arn,
                created_at=created_at,
                updated_at=updated_at,
                healthomics_usable=usability['healthomics_usable'],
                registry_permission_granted=usability['registry_permission_granted'],
                repository_template_exists=usability['repository_template_exists'],
                repository_template_permission_granted=usability[
                    'repository_template_permission_granted'
                ],
            )
            rules.append(rule)

        # Build response
        response_next_token = response.get('nextToken')
        result = PullThroughCacheListResponse(
            rules=rules,
            next_token=response_next_token,
        )

        return result.model_dump()

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'AccessDeniedException':
            required_actions = [
                'ecr:DescribePullThroughCacheRules',
                'ecr:GetRegistryPolicy',
                'ecr:DescribeRepositoryCreationTemplates',
            ]
            logger.error(f'Access denied to ECR: {error_message}')
            await ctx.error(
                f'Access denied to ECR. Ensure IAM permissions include: {required_actions}'
            )
            raise
        else:
            logger.error(f'ECR API error: {error_code} - {error_message}')
            await ctx.error(f'ECR error: {error_message}')
            raise

    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error accessing ECR: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise

    except Exception as e:
        error_message = f'Unexpected error listing pull-through cache rules: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def create_pull_through_cache_for_healthomics(
    ctx: Context,
    upstream_registry: str = Field(
        ...,
        description='Upstream registry type: docker-hub, quay, or ecr-public',
    ),
    ecr_repository_prefix: Optional[str] = Field(
        None,
        description='ECR repository prefix (defaults to registry type name)',
    ),
    credential_arn: Optional[str] = Field(
        None,
        description='Secrets Manager ARN for registry credentials (required for docker-hub)',
    ),
) -> Dict[str, Any]:
    """Create a pull-through cache rule configured for HealthOmics.

    Creates an ECR pull-through cache rule for the specified upstream registry
    and configures the necessary permissions for HealthOmics to use it. This includes:
    1. Creating the pull-through cache rule
    2. Updating the registry permissions policy to allow HealthOmics to create
       repositories and import images
    3. Creating a repository creation template that grants HealthOmics the
       required permissions to pull images

    Args:
        ctx: MCP context for error reporting
        upstream_registry: Upstream registry type (docker-hub, quay, or ecr-public)
        ecr_repository_prefix: ECR repository prefix (defaults to registry type name)
        credential_arn: Secrets Manager ARN for registry credentials
                       (required for docker-hub, optional for others)

    Returns:
        Dictionary containing:
        - success: Whether the operation was successful
        - rule: Created pull-through cache rule details
        - registry_policy_updated: Whether the registry policy was updated
        - repository_template_created: Whether the repository template was created
        - message: Human-readable status message
    """
    # Validate upstream registry type
    try:
        registry_type = UpstreamRegistry(upstream_registry)
    except ValueError:
        valid_types = [r.value for r in UpstreamRegistry]
        error_msg = (
            f'Invalid upstream registry type: {upstream_registry}. '
            f'Valid options are: {", ".join(valid_types)}'
        )
        logger.error(error_msg)
        return {
            'success': False,
            'rule': None,
            'registry_policy_updated': False,
            'repository_template_created': False,
            'message': error_msg,
        }

    # Validate credential ARN requirement for Docker Hub
    if registry_type == UpstreamRegistry.DOCKER_HUB and not credential_arn:
        error_msg = (
            'Credential ARN is required for Docker Hub pull-through cache. '
            'Please provide a Secrets Manager ARN containing Docker Hub credentials.'
        )
        await ctx.error(error_msg)
        logger.error(error_msg)
        return {
            'success': False,
            'rule': None,
            'registry_policy_updated': False,
            'repository_template_created': False,
            'message': error_msg,
        }

    # Map registry type to upstream URL
    upstream_url = UPSTREAM_REGISTRY_URLS[registry_type]

    # Use default prefix if not provided
    prefix = ecr_repository_prefix or DEFAULT_ECR_PREFIXES.get(
        upstream_registry, upstream_registry
    )

    client = get_ecr_client()

    # Track what was created/updated
    rule_created = False
    registry_policy_updated = False
    repository_template_created = False
    created_rule: Optional[PullThroughCacheRule] = None

    # Initialize ptc_response with default values
    ptc_response: Dict[str, Any] = {
        'ecrRepositoryPrefix': prefix,
        'upstreamRegistryUrl': upstream_url,
        'credentialArn': credential_arn,
        'createdAt': None,
    }

    try:
        # Step 1: Create pull-through cache rule
        ptc_params: Dict[str, Any] = {
            'ecrRepositoryPrefix': prefix,
            'upstreamRegistryUrl': upstream_url,
        }
        if credential_arn:
            ptc_params['credentialArn'] = credential_arn

        try:
            create_response = client.create_pull_through_cache_rule(**ptc_params)
            rule_created = True
            # Update ptc_response with actual response values
            ptc_response = {
                'ecrRepositoryPrefix': create_response.get('ecrRepositoryPrefix', prefix),
                'upstreamRegistryUrl': create_response.get('upstreamRegistryUrl', upstream_url),
                'credentialArn': create_response.get('credentialArn'),
                'createdAt': create_response.get('createdAt'),
            }
            logger.info(
                f'Created pull-through cache rule for {upstream_registry} with prefix {prefix}'
            )
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'PullThroughCacheRuleAlreadyExistsException':
                # Rule already exists - this is acceptable, continue with permissions
                logger.info(
                    f'Pull-through cache rule already exists for prefix {prefix}. '
                    'Proceeding to verify/update permissions.'
                )
                # Get existing rule details
                try:
                    existing_rules = client.describe_pull_through_cache_rules(
                        ecrRepositoryPrefixes=[prefix]
                    )
                    rules = existing_rules.get('pullThroughCacheRules', [])
                    if rules:
                        existing_rule = rules[0]
                        ptc_response = {
                            'ecrRepositoryPrefix': existing_rule.get('ecrRepositoryPrefix'),
                            'upstreamRegistryUrl': existing_rule.get('upstreamRegistryUrl'),
                            'credentialArn': existing_rule.get('credentialArn'),
                            'createdAt': existing_rule.get('createdAt'),
                        }
                except Exception as describe_error:
                    logger.warning(f'Failed to get existing rule details: {describe_error}')
                    # ptc_response already has default values
            else:
                raise

        # Step 2: Update registry permissions policy with HealthOmics access
        registry_policy_updated = await _update_registry_policy_for_healthomics(
            client, ctx, prefix
        )

        # Step 3: Create repository creation template with HealthOmics permissions
        repository_template_created = await _create_repository_template_for_healthomics(
            client, ctx, prefix
        )

        # Build the created rule model
        # Extract created_at - it may be a datetime or None
        created_at_value = ptc_response.get('createdAt')

        created_rule = PullThroughCacheRule(
            ecr_repository_prefix=str(ptc_response.get('ecrRepositoryPrefix', prefix)),
            upstream_registry_url=str(ptc_response.get('upstreamRegistryUrl', upstream_url)),
            credential_arn=ptc_response.get('credentialArn'),
            created_at=created_at_value if isinstance(created_at_value, datetime) else None,
            healthomics_usable=registry_policy_updated and repository_template_created,
            registry_permission_granted=registry_policy_updated,
            repository_template_exists=repository_template_created,
            repository_template_permission_granted=repository_template_created,
        )

        # Build success message
        if rule_created:
            message = f'Successfully created pull-through cache rule for {upstream_registry} with prefix "{prefix}".'
        else:
            message = f'Pull-through cache rule for prefix "{prefix}" already exists.'

        if registry_policy_updated and repository_template_created:
            message += ' HealthOmics permissions have been configured.'
        elif registry_policy_updated:
            message += ' Registry policy updated, but repository template creation failed.'
        elif repository_template_created:
            message += ' Repository template created, but registry policy update failed.'
        else:
            message += ' Warning: Failed to configure HealthOmics permissions.'

        return {
            'success': True,
            'rule': created_rule.model_dump() if created_rule else None,
            'registry_policy_updated': registry_policy_updated,
            'repository_template_created': repository_template_created,
            'message': message,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'AccessDeniedException':
            required_actions = [
                'ecr:CreatePullThroughCacheRule',
                'ecr:PutRegistryPolicy',
                'ecr:CreateRepositoryCreationTemplate',
            ]
            logger.error(f'Access denied to ECR: {error_message}')
            await ctx.error(
                f'Access denied to ECR. Ensure IAM permissions include: {required_actions}'
            )
            return {
                'success': False,
                'rule': created_rule.model_dump() if created_rule else None,
                'registry_policy_updated': registry_policy_updated,
                'repository_template_created': repository_template_created,
                'message': f'Access denied: {error_message}',
            }
        elif error_code == 'InvalidParameterException':
            logger.error(f'Invalid parameter: {error_message}')
            return {
                'success': False,
                'rule': None,
                'registry_policy_updated': False,
                'repository_template_created': False,
                'message': f'Invalid parameter: {error_message}',
            }
        elif error_code == 'LimitExceededException':
            logger.error(f'Limit exceeded: {error_message}')
            return {
                'success': False,
                'rule': None,
                'registry_policy_updated': False,
                'repository_template_created': False,
                'message': f'Limit exceeded: {error_message}',
            }
        else:
            logger.error(f'ECR API error: {error_code} - {error_message}')
            await ctx.error(f'ECR error: {error_message}')
            return {
                'success': False,
                'rule': created_rule.model_dump() if created_rule else None,
                'registry_policy_updated': registry_policy_updated,
                'repository_template_created': repository_template_created,
                'message': f'ECR error: {error_message}',
            }

    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error accessing ECR: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return {
            'success': False,
            'rule': created_rule.model_dump() if created_rule else None,
            'registry_policy_updated': registry_policy_updated,
            'repository_template_created': repository_template_created,
            'message': error_message,
        }

    except Exception as e:
        error_message = f'Unexpected error creating pull-through cache: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return {
            'success': False,
            'rule': created_rule.model_dump() if created_rule else None,
            'registry_policy_updated': registry_policy_updated,
            'repository_template_created': repository_template_created,
            'message': error_message,
        }


async def _update_registry_policy_for_healthomics(
    client: Any,
    ctx: Context,
    ecr_repository_prefix: str,
) -> bool:
    """Update the ECR registry permissions policy to allow HealthOmics access.

    Adds or updates the registry permissions policy to grant the HealthOmics
    principal (omics.amazonaws.com) the required permissions:
    - ecr:CreateRepository
    - ecr:BatchImportUpstreamImage

    Args:
        client: ECR boto3 client
        ctx: MCP context for error reporting
        ecr_repository_prefix: The ECR repository prefix for resource restrictions

    Returns:
        True if the policy was successfully updated, False otherwise
    """
    try:
        # Get existing registry policy
        existing_policy: Optional[Dict[str, Any]] = None
        try:
            policy_response = client.get_registry_policy()
            policy_text = policy_response.get('policyText')
            if policy_text:
                existing_policy = json.loads(policy_text)
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'RegistryPolicyNotFoundException':
                logger.debug('No existing registry policy found, creating new one')
                existing_policy = None
            else:
                raise

        # Build the HealthOmics statement
        healthomics_statement = {
            'Sid': 'HealthOmicsPullThroughCacheAccess',
            'Effect': 'Allow',
            'Principal': {'Service': HEALTHOMICS_PRINCIPAL},
            'Action': ECR_REQUIRED_REGISTRY_ACTIONS,
            'Resource': '*',
        }

        # Build or update the policy
        if existing_policy is None:
            # Create new policy
            new_policy = {
                'Version': '2012-10-17',
                'Statement': [healthomics_statement],
            }
        else:
            # Update existing policy
            statements = existing_policy.get('Statement', [])
            if not isinstance(statements, list):
                statements = [statements]

            # Check if HealthOmics statement already exists
            healthomics_statement_exists = False
            for i, stmt in enumerate(statements):
                if stmt.get('Sid') == 'HealthOmicsPullThroughCacheAccess':
                    # Update existing statement
                    statements[i] = healthomics_statement
                    healthomics_statement_exists = True
                    break

            if not healthomics_statement_exists:
                statements.append(healthomics_statement)

            new_policy = {
                'Version': existing_policy.get('Version', '2012-10-17'),
                'Statement': statements,
            }

        # Apply the policy
        client.put_registry_policy(policyText=json.dumps(new_policy))
        logger.info('Successfully updated registry permissions policy for HealthOmics')
        return True

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f'Failed to update registry policy: {error_code} - {error_message}')
        return False

    except Exception as e:
        logger.error(f'Unexpected error updating registry policy: {str(e)}')
        return False


async def _create_repository_template_for_healthomics(
    client: Any,
    ctx: Context,
    ecr_repository_prefix: str,
) -> bool:
    """Create a repository creation template with HealthOmics permissions.

    Creates a repository creation template for the specified prefix that
    automatically applies a policy granting HealthOmics the required permissions:
    - ecr:BatchGetImage
    - ecr:GetDownloadUrlForLayer

    Args:
        client: ECR boto3 client
        ctx: MCP context for error reporting
        ecr_repository_prefix: The ECR repository prefix for the template

    Returns:
        True if the template was successfully created, False otherwise
    """
    try:
        # Build the repository policy for HealthOmics access
        repository_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsImagePullAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': HEALTHOMICS_PRINCIPAL},
                    'Action': ECR_REQUIRED_REPOSITORY_ACTIONS,
                }
            ],
        }

        # Try to create the template
        try:
            client.create_repository_creation_template(
                prefix=ecr_repository_prefix,
                description=f'Repository template for HealthOmics pull-through cache ({ecr_repository_prefix})',
                appliedFor=['PULL_THROUGH_CACHE'],
                repositoryPolicy=json.dumps(repository_policy),
            )
            logger.info(
                f'Successfully created repository creation template for prefix {ecr_repository_prefix}'
            )
            return True

        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'TemplateAlreadyExistsException':
                # Template already exists - try to update it
                logger.info(
                    f'Repository creation template already exists for prefix {ecr_repository_prefix}. '
                    'Attempting to update.'
                )
                try:
                    client.update_repository_creation_template(
                        prefix=ecr_repository_prefix,
                        description=f'Repository template for HealthOmics pull-through cache ({ecr_repository_prefix})',
                        appliedFor=['PULL_THROUGH_CACHE'],
                        repositoryPolicy=json.dumps(repository_policy),
                    )
                    logger.info(
                        f'Successfully updated repository creation template for prefix {ecr_repository_prefix}'
                    )
                    return True
                except Exception as update_error:
                    logger.warning(
                        f'Failed to update existing template: {update_error}. '
                        'Template may already have correct permissions.'
                    )
                    # Check if existing template has correct permissions
                    try:
                        template_response = client.describe_repository_creation_templates(
                            prefixes=[ecr_repository_prefix]
                        )
                        templates = template_response.get('repositoryCreationTemplates', [])
                        if templates:
                            template_policy = templates[0].get('repositoryPolicy')
                            if template_policy:
                                # Template exists with a policy - consider it successful
                                return True
                    except Exception:
                        pass
                    return False
            else:
                raise

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(
            f'Failed to create repository creation template: {error_code} - {error_message}'
        )
        return False

    except Exception as e:
        logger.error(f'Unexpected error creating repository creation template: {str(e)}')
        return False


async def validate_healthomics_ecr_config(
    ctx: Context,
) -> Dict[str, Any]:
    """Validate ECR configuration for HealthOmics workflows.

    Performs a comprehensive validation of the ECR configuration to ensure
    HealthOmics workflows can access container images through pull-through caches.
    This includes checking:
    1. All pull-through cache rules in the region
    2. Registry permissions policy for HealthOmics principal
    3. Repository creation templates for each pull-through cache prefix
    4. Template permissions include required actions

    For each issue found, provides specific remediation steps.

    Args:
        ctx: MCP context for error reporting

    Returns:
        Dictionary containing:
        - valid: Whether the configuration is valid for HealthOmics
        - issues: List of validation issues with remediation steps
        - pull_through_caches_checked: Number of pull-through cache rules checked
        - repositories_checked: Number of repositories checked
    """
    from awslabs.aws_healthomics_mcp_server.models.ecr import (
        ValidationIssue,
        ValidationResult,
    )
    from awslabs.aws_healthomics_mcp_server.utils.ecr_utils import (
        check_registry_policy_healthomics_access,
        check_repository_template_healthomics_access,
    )

    client = get_ecr_client()
    issues: List[ValidationIssue] = []
    pull_through_caches_checked = 0
    repositories_checked = 0

    try:
        # Step 1: Get all pull-through cache rules
        ptc_rules = []
        next_token = None

        while True:
            params: Dict[str, Any] = {'maxResults': 100}
            if next_token:
                params['nextToken'] = next_token

            response = client.describe_pull_through_cache_rules(**params)
            ptc_rules.extend(response.get('pullThroughCacheRules', []))
            next_token = response.get('nextToken')

            if not next_token:
                break

        pull_through_caches_checked = len(ptc_rules)

        # If no pull-through cache rules exist, add an info issue
        if not ptc_rules:
            issues.append(
                ValidationIssue(
                    severity='info',
                    component='pull_through_cache',
                    message='No pull-through cache rules found in this region.',
                    remediation=(
                        'To use container images from public registries (Docker Hub, Quay.io, ECR Public) '
                        'in HealthOmics workflows, create pull-through cache rules using the '
                        'create_pull_through_cache_for_healthomics tool or the AWS Console.'
                    ),
                )
            )
            # Return early - no further validation needed
            result = ValidationResult(
                valid=True,  # No rules means nothing to validate
                issues=issues,
                pull_through_caches_checked=pull_through_caches_checked,
                repositories_checked=repositories_checked,
            )
            return result.model_dump()

        # Step 2: Check registry permissions policy
        registry_policy_text: Optional[str] = None
        try:
            registry_policy_response = client.get_registry_policy()
            registry_policy_text = registry_policy_response.get('policyText')
        except botocore.exceptions.ClientError as policy_error:
            error_code = policy_error.response.get('Error', {}).get('Code', '')
            if error_code == 'RegistryPolicyNotFoundException':
                logger.debug('No registry permissions policy found')
                registry_policy_text = None
            else:
                logger.warning(
                    f'Failed to get registry policy: {error_code} - '
                    f'{policy_error.response.get("Error", {}).get("Message", "")}'
                )
                registry_policy_text = None

        # Check if registry policy grants HealthOmics access
        registry_permission_granted, missing_registry_permissions = (
            check_registry_policy_healthomics_access(registry_policy_text)
        )

        if not registry_permission_granted:
            if registry_policy_text is None:
                issues.append(
                    ValidationIssue(
                        severity='error',
                        component='registry_policy',
                        message='No ECR registry permissions policy exists.',
                        remediation=(
                            'Create a registry permissions policy that grants the HealthOmics service '
                            f'principal ({HEALTHOMICS_PRINCIPAL}) the following actions: '
                            f'{", ".join(ECR_REQUIRED_REGISTRY_ACTIONS)}. '
                            'You can use the create_pull_through_cache_for_healthomics tool to '
                            'automatically configure this, or use the AWS Console to add the policy.'
                        ),
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        severity='error',
                        component='registry_policy',
                        message=(
                            f'Registry permissions policy does not grant HealthOmics the required permissions. '
                            f'Missing actions: {", ".join(missing_registry_permissions)}'
                        ),
                        remediation=(
                            f'Update the registry permissions policy to grant the HealthOmics service '
                            f'principal ({HEALTHOMICS_PRINCIPAL}) the following actions: '
                            f'{", ".join(missing_registry_permissions)}. '
                            'This allows HealthOmics to create repositories and import images from '
                            'upstream registries through pull-through cache.'
                        ),
                    )
                )

        # Step 3 & 4: Check repository creation templates for each prefix
        for ptc_rule in ptc_rules:
            ecr_repository_prefix = ptc_rule.get('ecrRepositoryPrefix', '')
            upstream_registry_url = ptc_rule.get('upstreamRegistryUrl', '')

            # Get repository creation template for this prefix
            template_policy_text: Optional[str] = None
            template_found = False

            try:
                template_response = client.describe_repository_creation_templates(
                    prefixes=[ecr_repository_prefix]
                )
                templates = template_response.get('repositoryCreationTemplates', [])
                if templates:
                    template_found = True
                    template = templates[0]
                    template_policy_text = template.get('repositoryPolicy')
            except botocore.exceptions.ClientError as template_error:
                error_code = template_error.response.get('Error', {}).get('Code', '')
                if error_code == 'TemplateNotFoundException':
                    logger.debug(
                        f'No repository creation template found for prefix: {ecr_repository_prefix}'
                    )
                    template_found = False
                else:
                    logger.warning(
                        f'Failed to get repository creation template for {ecr_repository_prefix}: '
                        f'{error_code} - {template_error.response.get("Error", {}).get("Message", "")}'
                    )
                    template_found = False

            # Check template existence
            if not template_found:
                issues.append(
                    ValidationIssue(
                        severity='error',
                        component='repository_template',
                        message=(
                            f'No repository creation template exists for pull-through cache prefix '
                            f'"{ecr_repository_prefix}" (upstream: {upstream_registry_url}).'
                        ),
                        remediation=(
                            f'Create a repository creation template for prefix "{ecr_repository_prefix}" '
                            f'that grants the HealthOmics service principal ({HEALTHOMICS_PRINCIPAL}) '
                            f'the following actions: {", ".join(ECR_REQUIRED_REPOSITORY_ACTIONS)}. '
                            'This ensures repositories created by pull-through cache automatically '
                            'have the correct permissions for HealthOmics. You can use the '
                            'create_pull_through_cache_for_healthomics tool to configure this automatically.'
                        ),
                    )
                )
                continue

            # Check template permissions
            template_exists, template_permission_granted, missing_template_permissions = (
                check_repository_template_healthomics_access(template_policy_text)
            )

            if not template_permission_granted:
                if template_policy_text is None:
                    issues.append(
                        ValidationIssue(
                            severity='error',
                            component='repository_template',
                            message=(
                                f'Repository creation template for prefix "{ecr_repository_prefix}" '
                                f'does not have a repository policy configured.'
                            ),
                            remediation=(
                                f'Update the repository creation template for prefix "{ecr_repository_prefix}" '
                                f'to include a repository policy that grants the HealthOmics service '
                                f'principal ({HEALTHOMICS_PRINCIPAL}) the following actions: '
                                f'{", ".join(ECR_REQUIRED_REPOSITORY_ACTIONS)}. '
                                'This allows HealthOmics to pull images from repositories created by '
                                'pull-through cache.'
                            ),
                        )
                    )
                else:
                    issues.append(
                        ValidationIssue(
                            severity='error',
                            component='repository_template',
                            message=(
                                f'Repository creation template for prefix "{ecr_repository_prefix}" '
                                f'does not grant HealthOmics the required permissions. '
                                f'Missing actions: {", ".join(missing_template_permissions)}'
                            ),
                            remediation=(
                                f'Update the repository creation template for prefix "{ecr_repository_prefix}" '
                                f'to grant the HealthOmics service principal ({HEALTHOMICS_PRINCIPAL}) '
                                f'the following actions: {", ".join(missing_template_permissions)}. '
                                'This allows HealthOmics to pull images from repositories created by '
                                'pull-through cache.'
                            ),
                        )
                    )

        # Determine overall validity
        # Configuration is valid if there are no error-level issues
        has_errors = any(issue.severity == 'error' for issue in issues)
        valid = not has_errors

        # Add success message if all checks pass
        if valid and pull_through_caches_checked > 0:
            issues.append(
                ValidationIssue(
                    severity='info',
                    component='pull_through_cache',
                    message=(
                        f'ECR configuration is valid for HealthOmics. '
                        f'{pull_through_caches_checked} pull-through cache rule(s) checked.'
                    ),
                    remediation='No action required. Your ECR configuration is ready for HealthOmics workflows.',
                )
            )

        result = ValidationResult(
            valid=valid,
            issues=issues,
            pull_through_caches_checked=pull_through_caches_checked,
            repositories_checked=repositories_checked,
        )

        return result.model_dump()

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'AccessDeniedException':
            required_actions = [
                'ecr:DescribePullThroughCacheRules',
                'ecr:GetRegistryPolicy',
                'ecr:DescribeRepositoryCreationTemplates',
            ]
            logger.error(f'Access denied to ECR: {error_message}')
            await ctx.error(
                f'Access denied to ECR. Ensure IAM permissions include: {required_actions}'
            )
            raise
        else:
            logger.error(f'ECR API error: {error_code} - {error_message}')
            await ctx.error(f'ECR error: {error_message}')
            raise

    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error accessing ECR: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise

    except Exception as e:
        error_message = f'Unexpected error validating ECR configuration: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def grant_healthomics_repository_access(
    ctx: Context,
    repository_name: str = Field(
        ...,
        description='ECR repository name to grant HealthOmics access to',
    ),
) -> Dict[str, Any]:
    """Grant HealthOmics access to an ECR repository.

    Updates the repository policy to allow the HealthOmics service principal
    (omics.amazonaws.com) to pull images. This adds the required permissions:
    - ecr:BatchGetImage
    - ecr:GetDownloadUrlForLayer

    If the repository already has a policy, the HealthOmics permissions are added
    while preserving existing statements. If no policy exists, a new policy is created.

    Args:
        ctx: MCP context for error reporting
        repository_name: ECR repository name to grant access to

    Returns:
        Dictionary containing:
        - success: Whether the operation was successful
        - repository_name: The repository that was updated
        - policy_updated: Whether an existing policy was updated
        - policy_created: Whether a new policy was created
        - previous_healthomics_accessible: Previous accessibility status
        - current_healthomics_accessible: Current accessibility status after update
        - message: Human-readable status message
    """
    from awslabs.aws_healthomics_mcp_server.models.ecr import GrantAccessResponse

    # Validate repository name
    if not repository_name or not repository_name.strip():
        await ctx.error('Repository name is required and cannot be empty')
        return GrantAccessResponse(
            success=False,
            repository_name='',
            message='Repository name is required and cannot be empty',
        ).model_dump()

    repository_name = repository_name.strip()
    client = get_ecr_client()

    # Check current accessibility status
    previous_status = HealthOmicsAccessStatus.UNKNOWN
    existing_policy: Optional[Dict[str, Any]] = None

    try:
        policy_response = client.get_repository_policy(repositoryName=repository_name)
        policy_text = policy_response.get('policyText')
        if policy_text:
            existing_policy = json.loads(policy_text)
            previous_status, _ = check_repository_healthomics_access(policy_text)
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'RepositoryPolicyNotFoundException':
            # No policy exists - we'll create one
            previous_status = HealthOmicsAccessStatus.NOT_ACCESSIBLE
            existing_policy = None
        elif error_code == 'RepositoryNotFoundException':
            await ctx.error(f'Repository not found: {repository_name}')
            return GrantAccessResponse(
                success=False,
                repository_name=repository_name,
                message=f'Repository not found: {repository_name}',
            ).model_dump()
        else:
            logger.warning(f'Failed to get repository policy: {e}')
            await ctx.error(f'Failed to get repository policy: {e}')
            raise

    # If already accessible, return success without changes
    if previous_status == HealthOmicsAccessStatus.ACCESSIBLE:
        return GrantAccessResponse(
            success=True,
            repository_name=repository_name,
            policy_updated=False,
            policy_created=False,
            previous_healthomics_accessible=previous_status,
            current_healthomics_accessible=HealthOmicsAccessStatus.ACCESSIBLE,
            message=f'Repository {repository_name} already grants HealthOmics access. No changes needed.',
        ).model_dump()

    # Build the HealthOmics access statement
    healthomics_statement = {
        'Sid': 'HealthOmicsAccess',
        'Effect': 'Allow',
        'Principal': {'Service': HEALTHOMICS_PRINCIPAL},
        'Action': list(ECR_REQUIRED_REPOSITORY_ACTIONS),
    }

    # Build the new policy
    policy_created = False
    policy_updated = False

    if existing_policy is None:
        # Create a new policy
        new_policy = {
            'Version': '2012-10-17',
            'Statement': [healthomics_statement],
        }
        policy_created = True
    else:
        # Update existing policy - remove any existing HealthOmics statements first
        statements = existing_policy.get('Statement', [])
        if isinstance(statements, dict):
            statements = [statements]

        # Filter out existing HealthOmics statements to avoid duplicates
        filtered_statements = []
        for stmt in statements:
            principal = stmt.get('Principal', {})
            is_healthomics = False
            if isinstance(principal, dict):
                service = principal.get('Service')
                if service == HEALTHOMICS_PRINCIPAL:
                    is_healthomics = True
                elif isinstance(service, list) and HEALTHOMICS_PRINCIPAL in service:
                    is_healthomics = True
            elif principal == HEALTHOMICS_PRINCIPAL:
                is_healthomics = True

            if not is_healthomics:
                filtered_statements.append(stmt)

        # Add the new HealthOmics statement
        filtered_statements.append(healthomics_statement)

        new_policy = {
            'Version': existing_policy.get('Version', '2012-10-17'),
            'Statement': filtered_statements,
        }
        policy_updated = True

    # Apply the policy
    try:
        client.set_repository_policy(
            repositoryName=repository_name,
            policyText=json.dumps(new_policy),
        )
        logger.info(f'Successfully updated repository policy for {repository_name}')
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'AccessDeniedException':
            await ctx.error(
                f'Access denied. Ensure IAM permissions include ecr:SetRepositoryPolicy '
                f'for repository {repository_name}'
            )
            raise
        else:
            logger.error(f'Failed to set repository policy: {error_code} - {error_message}')
            await ctx.error(f'Failed to set repository policy: {error_message}')
            raise

    # Verify the update
    current_status = HealthOmicsAccessStatus.UNKNOWN
    try:
        verify_response = client.get_repository_policy(repositoryName=repository_name)
        verify_policy_text = verify_response.get('policyText')
        current_status, _ = check_repository_healthomics_access(verify_policy_text)
    except Exception as e:
        logger.warning(f'Failed to verify policy update: {e}')
        # Assume success since set_repository_policy didn't raise
        current_status = HealthOmicsAccessStatus.ACCESSIBLE

    action = 'created' if policy_created else 'updated'
    return GrantAccessResponse(
        success=True,
        repository_name=repository_name,
        policy_updated=policy_updated,
        policy_created=policy_created,
        previous_healthomics_accessible=previous_status,
        current_healthomics_accessible=current_status,
        message=f'Successfully {action} repository policy for {repository_name}. '
        f'HealthOmics can now pull images from this repository.',
    ).model_dump()


async def create_container_registry_map(
    ctx: Context,
    ecr_account_id: Optional[str] = Field(
        default=None,
        description='AWS account ID for ECR repositories. If not provided, uses the current AWS account.',
    ),
    ecr_region: Optional[str] = Field(
        default=None,
        description='AWS region for ECR repositories. If not provided, uses the current configured region.',
    ),
    include_pull_through_caches: bool = Field(
        default=True,
        description='If true, automatically discovers HealthOmics-usable ECR pull-through cache rules and creates registry mappings for them.',
    ),
    additional_registry_mappings: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Additional registry mappings to include beyond discovered pull-through caches. Each mapping has 'upstreamRegistryUrl' and 'ecrRepositoryPrefix'.",
    ),
    image_mappings: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="List of specific image mappings for container overrides. Each mapping has 'sourceImage' and 'destinationImage'. These take precedence over registry mappings.",
    ),
    output_format: str = Field(
        default='json',
        description="Output format: 'json' for raw JSON string, 'dict' for Python dictionary",
    ),
) -> Dict[str, Any]:
    """Create a container registry map for HealthOmics workflows.

    Creates a container registry map file that can be used when creating HealthOmics
    workflows. Registry mappings allow workflows to use container images from upstream
    registries (Docker Hub, Quay.io, ECR Public) without modifying the workflow
    definition. The mappings redirect container pulls to your private ECR pull-through
    caches.

    By default, this tool discovers all HealthOmics-usable pull-through cache rules
    in your ECR registry and creates mappings for them. You can also provide additional
    registry mappings or specific image mappings for container overrides.

    Args:
        ctx: MCP context for error reporting
        ecr_account_id: AWS account ID for ECR repositories. If not provided,
            uses the current AWS account.
        ecr_region: AWS region for ECR repositories. If not provided,
            uses the current configured region.
        include_pull_through_caches: If true, automatically discovers HealthOmics-usable
            ECR pull-through cache rules and creates registry mappings for them.
        additional_registry_mappings: Additional registry mappings to include beyond
            discovered pull-through caches. Each mapping should have 'upstreamRegistryUrl'
            and 'ecrRepositoryPrefix' keys.
        image_mappings: List of specific image mappings for container overrides.
            Each mapping should have 'sourceImage' and 'destinationImage' keys.
            These take precedence over registry mappings.
        output_format: Output format - 'json' for raw JSON string, 'dict' for dictionary.

    Returns:
        Dictionary containing:
        - success: Whether the operation was successful
        - account_id: AWS account ID used
        - region: AWS region used
        - discovered_healthomics_usable_caches: Number of HealthOmics-usable caches found
        - container_registry_map: The generated container registry map
        - json_output: Pretty-printed JSON string ready for use
        - usage_hint: Instructions for using the generated map
    """
    from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_account_id, get_region

    # Resolve account ID
    resolved_account_id = ecr_account_id
    if not resolved_account_id:
        try:
            resolved_account_id = get_account_id()
        except Exception as e:
            logger.error(f'Failed to get AWS account ID: {e}')
            await ctx.error(f'Failed to get AWS account ID: {e}')
            return {
                'success': False,
                'account_id': None,
                'region': None,
                'discovered_healthomics_usable_caches': 0,
                'container_registry_map': {},
                'json_output': '{}',
                'message': f'Failed to get AWS account ID: {e}',
            }

    # Resolve region
    resolved_region = ecr_region
    if not resolved_region:
        resolved_region = get_region()

    # Discover HealthOmics-usable pull-through caches
    registry_mappings: List[Dict[str, str]] = []
    discovered_count = 0

    if include_pull_through_caches:
        try:
            # Pass explicit values since Field defaults aren't processed in direct calls
            ptc_result = await list_pull_through_cache_rules(ctx, max_results=100, next_token=None)
            rules = ptc_result.get('rules', [])

            for rule in rules:
                if rule.get('healthomics_usable'):
                    registry_mappings.append(
                        {
                            'upstreamRegistryUrl': rule['upstream_registry_url'],
                            'ecrRepositoryPrefix': rule['ecr_repository_prefix'],
                        }
                    )
                    discovered_count += 1

            logger.info(
                f'Discovered {discovered_count} HealthOmics-usable pull-through cache rules'
            )
        except Exception as e:
            logger.warning(f'Failed to discover pull-through cache rules: {e}')
            await ctx.error(f'Warning: Failed to discover pull-through cache rules: {e}')

    # Merge additional registry mappings
    if additional_registry_mappings:
        existing_urls = {m['upstreamRegistryUrl'] for m in registry_mappings}

        for mapping in additional_registry_mappings:
            # Validate mapping has required keys
            if 'upstreamRegistryUrl' not in mapping or 'ecrRepositoryPrefix' not in mapping:
                logger.warning(
                    f'Skipping invalid registry mapping (missing required keys): {mapping}'
                )
                continue

            upstream_url = mapping['upstreamRegistryUrl']
            if upstream_url in existing_urls:
                # Replace existing with user-provided
                registry_mappings = [
                    m for m in registry_mappings if m['upstreamRegistryUrl'] != upstream_url
                ]
            else:
                existing_urls.add(upstream_url)

            registry_mappings.append(
                {
                    'upstreamRegistryUrl': upstream_url,
                    'ecrRepositoryPrefix': mapping['ecrRepositoryPrefix'],
                }
            )

    # Validate and process image mappings
    validated_image_mappings: List[Dict[str, str]] = []
    if image_mappings:
        for mapping in image_mappings:
            if 'sourceImage' not in mapping or 'destinationImage' not in mapping:
                logger.warning(
                    f'Skipping invalid image mapping (missing required keys): {mapping}'
                )
                continue
            validated_image_mappings.append(
                {
                    'sourceImage': mapping['sourceImage'],
                    'destinationImage': mapping['destinationImage'],
                }
            )

    # Build the container registry map
    container_map: Dict[str, Any] = {}
    if registry_mappings:
        container_map['registryMappings'] = registry_mappings
    if validated_image_mappings:
        container_map['imageMappings'] = validated_image_mappings

    # Generate JSON output
    json_output = json.dumps(container_map, indent=4)

    return {
        'success': True,
        'account_id': resolved_account_id,
        'region': resolved_region,
        'discovered_healthomics_usable_caches': discovered_count,
        'container_registry_map': container_map,
        'json_output': json_output,
        'usage_hint': 'Save this as container-registry-map.json and reference it when creating HealthOmics workflows with the containerRegistryMap parameter.',
    }


# Mapping of upstream registry URLs to their pull-through cache detection
REGISTRY_URL_TO_TYPE = {
    'registry-1.docker.io': 'docker-hub',
    'docker.io': 'docker-hub',
    'quay.io': 'quay',
    'public.ecr.aws': 'ecr-public',
}


def _parse_container_image_reference(image_ref: str) -> Dict[str, Any]:
    """Parse a container image reference into its components.

    Handles various formats:
    - ubuntu:latest -> registry-1.docker.io/library/ubuntu:latest
    - myorg/myimage:v1 -> registry-1.docker.io/myorg/myimage:v1
    - quay.io/org/image:tag -> quay.io/org/image:tag
    - registry-1.docker.io/library/ubuntu@sha256:abc123 -> with digest

    Args:
        image_ref: Container image reference string

    Returns:
        Dictionary containing:
        - registry: The registry URL (e.g., 'registry-1.docker.io')
        - repository: The repository path (e.g., 'library/ubuntu')
        - tag: The image tag (e.g., 'latest') or None
        - digest: The image digest (e.g., 'sha256:...') or None
        - full_reference: The fully qualified image reference
    """
    # Default values
    registry = 'registry-1.docker.io'
    repository = ''
    tag: Optional[str] = None
    digest: Optional[str] = None

    # Check for digest
    if '@' in image_ref:
        ref_part, digest = image_ref.rsplit('@', 1)
        image_ref = ref_part
    elif ':' in image_ref:
        # Check if the colon is for a tag (not a port in registry)
        parts = image_ref.split('/')
        if ':' in parts[-1]:
            # The colon is in the last part, so it's a tag
            last_part = parts[-1]
            if ':' in last_part:
                name, tag = last_part.rsplit(':', 1)
                parts[-1] = name
                image_ref = '/'.join(parts)

    # Default tag if neither tag nor digest specified
    if tag is None and digest is None:
        tag = 'latest'

    # Parse registry and repository
    parts = image_ref.split('/')

    # Check if first part looks like a registry (contains . or :)
    if len(parts) > 1 and ('.' in parts[0] or ':' in parts[0]):
        registry = parts[0]
        repository = '/'.join(parts[1:])
    elif len(parts) == 1:
        # Single name like 'ubuntu' -> library/ubuntu on Docker Hub
        registry = 'registry-1.docker.io'
        repository = f'library/{parts[0]}'
    else:
        # org/image format -> Docker Hub
        registry = 'registry-1.docker.io'
        repository = '/'.join(parts)

    # Normalize docker.io to registry-1.docker.io
    if registry == 'docker.io':
        registry = 'registry-1.docker.io'

    # Build full reference
    if digest:
        full_reference = f'{registry}/{repository}@{digest}'
    elif tag:
        full_reference = f'{registry}/{repository}:{tag}'
    else:
        full_reference = f'{registry}/{repository}'

    return {
        'registry': registry,
        'repository': repository,
        'tag': tag,
        'digest': digest,
        'full_reference': full_reference,
    }


def _find_matching_pull_through_cache(
    registry: str,
    ptc_rules: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Find a pull-through cache rule that matches the given registry.

    Args:
        registry: The upstream registry URL
        ptc_rules: List of pull-through cache rules

    Returns:
        Matching pull-through cache rule or None
    """
    for rule in ptc_rules:
        upstream_url = rule.get('upstreamRegistryUrl', '')
        # Normalize URLs for comparison
        if upstream_url == registry:
            return rule
        # Handle docker.io vs registry-1.docker.io
        if registry in ('docker.io', 'registry-1.docker.io'):
            if upstream_url in ('docker.io', 'registry-1.docker.io'):
                return rule
    return None


# Registries that support ECR pull-through cache
PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES = {
    'registry-1.docker.io',
    'docker.io',
    'quay.io',
    'public.ecr.aws',
    'ghcr.io',
    'registry.k8s.io',
}

# CodeBuild project name for image cloning
CODEBUILD_PROJECT_NAME = 'healthomics-container-clone'


def _get_or_create_codebuild_project(
    codebuild_client: Any,
    iam_client: Any,
    account_id: str,
    region: str,
) -> str:
    """Get or create the CodeBuild project for container cloning.

    Args:
        codebuild_client: boto3 CodeBuild client
        iam_client: boto3 IAM client
        account_id: AWS account ID
        region: AWS region

    Returns:
        CodeBuild project name

    Raises:
        Exception: If project creation fails
    """
    # Check if project exists
    try:
        codebuild_client.batch_get_projects(names=[CODEBUILD_PROJECT_NAME])
        projects = codebuild_client.batch_get_projects(names=[CODEBUILD_PROJECT_NAME])
        if projects.get('projects'):
            logger.debug(f'CodeBuild project {CODEBUILD_PROJECT_NAME} already exists')
            return CODEBUILD_PROJECT_NAME
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code != 'ResourceNotFoundException':
            raise

    logger.info(f'Creating CodeBuild project: {CODEBUILD_PROJECT_NAME}')

    # Create IAM role for CodeBuild
    role_name = 'healthomics-container-clone-role'
    role_arn = f'arn:aws:iam::{account_id}:role/{role_name}'

    # Check if role exists, create if not
    try:
        iam_client.get_role(RoleName=role_name)
        logger.debug(f'IAM role {role_name} already exists')
    except iam_client.exceptions.NoSuchEntityException:
        logger.info(f'Creating IAM role: {role_name}')

        # Trust policy for CodeBuild
        trust_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'codebuild.amazonaws.com'},
                    'Action': 'sts:AssumeRole',
                }
            ],
        }

        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for HealthOmics container clone CodeBuild project',
        )

        # Attach policy for ECR and CloudWatch Logs
        policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'ecr:GetAuthorizationToken',
                        'ecr:BatchCheckLayerAvailability',
                        'ecr:GetDownloadUrlForLayer',
                        'ecr:BatchGetImage',
                        'ecr:PutImage',
                        'ecr:InitiateLayerUpload',
                        'ecr:UploadLayerPart',
                        'ecr:CompleteLayerUpload',
                    ],
                    'Resource': '*',
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents',
                    ],
                    'Resource': f'arn:aws:logs:{region}:{account_id}:log-group:/aws/codebuild/{CODEBUILD_PROJECT_NAME}*',
                },
            ],
        }

        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='healthomics-container-clone-policy',
            PolicyDocument=json.dumps(policy_document),
        )

        # Wait for role to propagate
        import time

        time.sleep(10)

    # Create CodeBuild project
    codebuild_client.create_project(
        name=CODEBUILD_PROJECT_NAME,
        description='Clone container images to ECR for HealthOmics workflows',
        source={
            'type': 'NO_SOURCE',
            'buildspec': """version: 0.2
phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
  build:
    commands:
      - echo Pulling source image...
      - docker pull $SOURCE_IMAGE
      - echo Tagging image...
      - docker tag $SOURCE_IMAGE $TARGET_IMAGE
      - echo Pushing to ECR...
      - docker push $TARGET_IMAGE
  post_build:
    commands:
      - echo Build completed on `date`
""",
        },
        artifacts={'type': 'NO_ARTIFACTS'},
        environment={
            'type': 'LINUX_CONTAINER',
            'image': 'aws/codebuild/amazonlinux2-x86_64-standard:5.0',
            'computeType': 'BUILD_GENERAL1_SMALL',
            'privilegedMode': True,  # Required for Docker
        },
        serviceRole=role_arn,
        timeoutInMinutes=30,
        queuedTimeoutInMinutes=60,
    )

    logger.info(f'Created CodeBuild project: {CODEBUILD_PROJECT_NAME}')
    return CODEBUILD_PROJECT_NAME


async def _copy_image_via_codebuild(
    ctx: Context,
    source_image: str,
    target_repo: str,
    target_tag: str,
    account_id: str,
    region: str,
) -> Dict[str, Any]:
    """Copy a container image to ECR using CodeBuild.

    Args:
        ctx: MCP context
        source_image: Full source image reference
        target_repo: Target ECR repository name
        target_tag: Target image tag
        account_id: AWS account ID
        region: AWS region

    Returns:
        Dictionary with success status, digest, and message
    """
    from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
        get_codebuild_client,
        get_iam_client,
    )

    codebuild_client = get_codebuild_client()
    iam_client = get_iam_client()

    ecr_registry = f'{account_id}.dkr.ecr.{region}.amazonaws.com'
    target_image = f'{ecr_registry}/{target_repo}:{target_tag}'

    try:
        # Ensure CodeBuild project exists
        project_name = _get_or_create_codebuild_project(
            codebuild_client, iam_client, account_id, region
        )

        # Start the build
        logger.info(f'Starting CodeBuild to copy {source_image} to {target_image}')

        build_response = codebuild_client.start_build(
            projectName=project_name,
            environmentVariablesOverride=[
                {'name': 'SOURCE_IMAGE', 'value': source_image, 'type': 'PLAINTEXT'},
                {'name': 'TARGET_IMAGE', 'value': target_image, 'type': 'PLAINTEXT'},
                {'name': 'TARGET_REPO', 'value': target_repo, 'type': 'PLAINTEXT'},
                {'name': 'TARGET_TAG', 'value': target_tag, 'type': 'PLAINTEXT'},
                {'name': 'ECR_REGISTRY', 'value': ecr_registry, 'type': 'PLAINTEXT'},
            ],
        )

        build_id = build_response['build']['id']
        logger.info(f'Started CodeBuild build: {build_id}')

        # Poll for completion
        import asyncio

        max_wait_seconds = 300  # 5 minutes
        poll_interval = 10
        elapsed = 0

        while elapsed < max_wait_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            builds = codebuild_client.batch_get_builds(ids=[build_id])
            if not builds.get('builds'):
                continue

            build = builds['builds'][0]
            status = build.get('buildStatus')

            if status == 'SUCCEEDED':
                logger.info(f'CodeBuild completed successfully: {build_id}')

                # Get the image digest from ECR
                ecr_client = get_ecr_client()
                try:
                    images = ecr_client.describe_images(
                        repositoryName=target_repo,
                        imageIds=[{'imageTag': target_tag}],
                    )
                    if images.get('imageDetails'):
                        digest = images['imageDetails'][0].get('imageDigest', '')
                        return {
                            'success': True,
                            'digest': digest,
                            'message': f'Successfully copied {source_image} to {target_image}',
                        }
                except Exception as e:
                    logger.warning(f'Failed to get image digest: {e}')

                return {
                    'success': True,
                    'digest': None,
                    'message': f'Successfully copied {source_image} to {target_image}',
                }

            elif status in ('FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT'):
                error_msg = f'CodeBuild failed with status: {status}'
                phases = build.get('phases', [])
                for phase in phases:
                    if phase.get('phaseStatus') == 'FAILED':
                        contexts = phase.get('contexts', [])
                        if contexts:
                            error_msg += f' - {contexts[0].get("message", "")}'
                        break

                logger.error(error_msg)
                return {
                    'success': False,
                    'digest': None,
                    'message': error_msg,
                }

            logger.debug(f'CodeBuild status: {status}, waiting...')

        # Timeout
        return {
            'success': False,
            'digest': None,
            'message': f'CodeBuild timed out after {max_wait_seconds} seconds. Build ID: {build_id}',
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f'CodeBuild error: {error_code} - {error_message}')
        return {
            'success': False,
            'digest': None,
            'message': f'CodeBuild error: {error_message}',
        }

    except Exception as e:
        logger.error(f'Unexpected error in CodeBuild copy: {e}')
        return {
            'success': False,
            'digest': None,
            'message': f'Unexpected error: {str(e)}',
        }


async def clone_container_to_ecr(
    ctx: Context,
    source_image: str = Field(
        ...,
        description='Source container image reference (e.g., "ubuntu:latest", '
        '"myorg/myimage:v1", "quay.io/org/image:tag")',
    ),
    target_repository_name: Optional[str] = Field(
        None,
        description='Target ECR repository name. Only used if no pull-through cache exists. '
        'If not provided, derives from source image.',
    ),
    target_image_tag: Optional[str] = Field(
        None,
        description='Target image tag. If not provided, uses source tag or "latest".',
    ),
) -> Dict[str, Any]:
    """Clone a container image to a private ECR repository for HealthOmics use.

    This tool copies a container image from an upstream registry (Docker Hub, Quay.io,
    ECR Public) to your private ECR repository with appropriate HealthOmics access
    permissions. It uses ECR pull-through cache to perform the copy.

    The tool will:
    1. Parse the source image reference (handling Docker Hub shorthand like "ubuntu:latest")
    2. Find an existing pull-through cache rule for the source registry
    3. Use the pull-through cache to pull the image into ECR
    4. Grant HealthOmics access permissions to the repository
    5. Return the ECR URI and digest for use in workflows

    Image reference formats supported:
    - "ubuntu:latest" -> registry-1.docker.io/library/ubuntu:latest
    - "myorg/myimage:v1" -> registry-1.docker.io/myorg/myimage:v1
    - "quay.io/biocontainers/samtools:1.17" -> quay.io/biocontainers/samtools:1.17
    - "public.ecr.aws/lts/ubuntu:22.04" -> public.ecr.aws/lts/ubuntu:22.04

    Args:
        ctx: MCP context for error reporting
        source_image: Source container image reference
        target_repository_name: Target ECR repository name (only used if no pull-through
            cache exists; optional)
        target_image_tag: Target image tag (optional)

    Returns:
        Dictionary containing:
        - success: Whether the operation was successful
        - source_image: Original source image reference
        - source_registry: Source registry URL
        - source_digest: Source image digest (if available)
        - ecr_uri: ECR URI of the cloned image
        - ecr_digest: ECR image digest
        - repository_created: Whether a new repository was created
        - used_pull_through_cache: Whether pull-through cache was used
        - pull_through_cache_prefix: The pull-through cache prefix used (if any)
        - healthomics_accessible: Whether HealthOmics can access the image
        - message: Human-readable status message
    """
    from awslabs.aws_healthomics_mcp_server.models.ecr import (
        CloneContainerResponse,
        HealthOmicsAccessStatus,
    )
    from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_account_id, get_region

    # Validate source image
    if not source_image or not source_image.strip():
        await ctx.error('Source image is required and cannot be empty')
        return CloneContainerResponse(
            success=False,
            source_image='',
            source_registry='',
            message='Source image is required and cannot be empty',
        ).model_dump()

    source_image = source_image.strip()

    # Parse the source image reference
    parsed = _parse_container_image_reference(source_image)
    source_registry = parsed['registry']
    source_repository = parsed['repository']
    source_tag = parsed['tag']
    source_digest = parsed['digest']

    logger.info(
        f'Cloning container image: registry={source_registry}, '
        f'repository={source_repository}, tag={source_tag}, digest={source_digest}'
    )

    client = get_ecr_client()

    # Get account ID and region for ECR URI construction
    try:
        account_id = get_account_id()
        region = get_region()
    except Exception as e:
        logger.error(f'Failed to get AWS account info: {e}')
        await ctx.error(f'Failed to get AWS account info: {e}')
        return CloneContainerResponse(
            success=False,
            source_image=source_image,
            source_registry=source_registry,
            message=f'Failed to get AWS account info: {e}',
        ).model_dump()

    # Determine target tag
    ecr_tag = target_image_tag or source_tag or 'latest'

    # Find pull-through cache for source registry
    ptc_prefix: Optional[str] = None
    try:
        ptc_response = client.describe_pull_through_cache_rules()
        for rule in ptc_response.get('pullThroughCacheRules', []):
            upstream_url = rule.get('upstreamRegistryUrl', '')
            if upstream_url == source_registry or (
                source_registry in ('docker.io', 'registry-1.docker.io')
                and upstream_url in ('docker.io', 'registry-1.docker.io')
            ):
                ptc_prefix = rule.get('ecrRepositoryPrefix')
                break
    except Exception as e:
        logger.warning(f'Failed to check pull-through cache rules: {e}')

    repository_created = False
    ecr_digest: Optional[str] = None

    try:
        if ptc_prefix:
            # Use pull-through cache
            ecr_repository_name = f'{ptc_prefix}/{source_repository}'
            ecr_uri_base = f'{account_id}.dkr.ecr.{region}.amazonaws.com/{ecr_repository_name}'

            logger.info(f'Using pull-through cache prefix "{ptc_prefix}" to clone {source_image}')

            # Build image identifier
            image_ids: List[Dict[str, str]] = []
            if source_digest:
                image_ids.append({'imageDigest': source_digest})
            else:
                image_ids.append({'imageTag': ecr_tag})

            # batch_get_image triggers the pull-through cache
            response = client.batch_get_image(
                repositoryName=ecr_repository_name,
                imageIds=image_ids,
                acceptedMediaTypes=[
                    'application/vnd.docker.distribution.manifest.v2+json',
                    'application/vnd.oci.image.manifest.v1+json',
                ],
            )

            images = response.get('images', [])
            failures = response.get('failures', [])

            if images:
                image = images[0]
                image_id = image.get('imageId', {})
                ecr_digest = image_id.get('imageDigest', '')
                pulled_tag = image_id.get('imageTag', ecr_tag)

                ecr_uri = f'{ecr_uri_base}:{pulled_tag}'
                if ecr_digest:
                    ecr_uri = f'{ecr_uri_base}@{ecr_digest}'

                # Grant HealthOmics access
                try:
                    await grant_healthomics_repository_access(
                        ctx, repository_name=ecr_repository_name
                    )
                except Exception as grant_err:
                    logger.warning(f'Failed to grant HealthOmics access: {grant_err}')

                return CloneContainerResponse(
                    success=True,
                    source_image=source_image,
                    source_registry=source_registry,
                    source_digest=source_digest,
                    ecr_uri=ecr_uri,
                    ecr_digest=ecr_digest,
                    repository_created=False,
                    used_pull_through_cache=True,
                    pull_through_cache_prefix=ptc_prefix,
                    healthomics_accessible=HealthOmicsAccessStatus.ACCESSIBLE,
                    message=f'Successfully cloned {source_image} to {ecr_uri} via pull-through cache',
                ).model_dump()

            elif failures:
                failure = failures[0]
                failure_code = failure.get('failureCode', '')
                failure_reason = failure.get('failureReason', '')
                error_msg = f'Pull-through cache failed: {failure_code} - {failure_reason}'
                logger.error(error_msg)
                await ctx.error(error_msg)
                return CloneContainerResponse(
                    success=False,
                    source_image=source_image,
                    source_registry=source_registry,
                    message=error_msg,
                ).model_dump()

            else:
                error_msg = 'Pull-through cache returned no images'
                logger.error(error_msg)
                return CloneContainerResponse(
                    success=False,
                    source_image=source_image,
                    source_registry=source_registry,
                    message=error_msg,
                ).model_dump()

        else:
            # No pull-through cache available
            ecr_repository_name = target_repository_name or source_repository.replace('/', '-')
            ecr_uri_base = f'{account_id}.dkr.ecr.{region}.amazonaws.com/{ecr_repository_name}'

            logger.info(
                f'No pull-through cache for {source_registry}. '
                f'Creating repository {ecr_repository_name}.'
            )

            # Check if repository exists, create if not
            try:
                client.describe_repositories(repositoryNames=[ecr_repository_name])
                logger.debug(f'Repository {ecr_repository_name} already exists')
            except botocore.exceptions.ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == 'RepositoryNotFoundException':
                    logger.info(f'Creating repository: {ecr_repository_name}')
                    client.create_repository(
                        repositoryName=ecr_repository_name,
                        imageScanningConfiguration={'scanOnPush': True},
                        imageTagMutability='MUTABLE',
                    )
                    repository_created = True
                    logger.info(f'Created repository: {ecr_repository_name}')
                else:
                    raise

            # Grant HealthOmics access
            try:
                await grant_healthomics_repository_access(ctx, repository_name=ecr_repository_name)
            except Exception as grant_error:
                logger.warning(f'Failed to grant HealthOmics access: {grant_error}')

            ecr_uri = f'{ecr_uri_base}:{ecr_tag}'

            # Check if registry supports pull-through cache
            registry_supports_ptc = source_registry in PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES

            if registry_supports_ptc:
                # Registry supports pull-through cache but none is configured
                # Suggest creating one
                return CloneContainerResponse(
                    success=False,
                    source_image=source_image,
                    source_registry=source_registry,
                    source_digest=source_digest,
                    ecr_uri=ecr_uri,
                    ecr_digest=None,
                    repository_created=repository_created,
                    used_pull_through_cache=False,
                    used_codebuild=False,
                    pull_through_cache_prefix=None,
                    healthomics_accessible=HealthOmicsAccessStatus.ACCESSIBLE,
                    message=(
                        f'No pull-through cache configured for {source_registry}. '
                        f'Repository {ecr_repository_name} created with HealthOmics permissions. '
                        f'To clone the image, create a pull-through cache using '
                        f'CreatePullThroughCacheForHealthOmics, then retry this operation.'
                    ),
                ).model_dump()
            else:
                # Registry does NOT support pull-through cache (e.g., wave.seqera.io)
                # Use CodeBuild to copy the image
                logger.info(
                    f'Registry {source_registry} does not support pull-through cache. '
                    f'Using CodeBuild to copy image.'
                )

                full_source_image = parsed['full_reference']
                codebuild_result = await _copy_image_via_codebuild(
                    ctx=ctx,
                    source_image=full_source_image,
                    target_repo=ecr_repository_name,
                    target_tag=ecr_tag,
                    account_id=account_id,
                    region=region,
                )

                if codebuild_result['success']:
                    ecr_digest = codebuild_result.get('digest')
                    final_ecr_uri = ecr_uri
                    if ecr_digest:
                        final_ecr_uri = f'{ecr_uri_base}@{ecr_digest}'

                    return CloneContainerResponse(
                        success=True,
                        source_image=source_image,
                        source_registry=source_registry,
                        source_digest=source_digest,
                        ecr_uri=final_ecr_uri,
                        ecr_digest=ecr_digest,
                        repository_created=repository_created,
                        used_pull_through_cache=False,
                        used_codebuild=True,
                        pull_through_cache_prefix=None,
                        healthomics_accessible=HealthOmicsAccessStatus.ACCESSIBLE,
                        message=(
                            f'Successfully cloned {source_image} to {final_ecr_uri} via CodeBuild'
                        ),
                    ).model_dump()
                else:
                    # CodeBuild failed - return error with manual instructions
                    return CloneContainerResponse(
                        success=False,
                        source_image=source_image,
                        source_registry=source_registry,
                        source_digest=source_digest,
                        ecr_uri=ecr_uri,
                        ecr_digest=None,
                        repository_created=repository_created,
                        used_pull_through_cache=False,
                        used_codebuild=False,
                        pull_through_cache_prefix=None,
                        healthomics_accessible=HealthOmicsAccessStatus.ACCESSIBLE,
                        message=(
                            f'CodeBuild copy failed: {codebuild_result["message"]}. '
                            f'Repository {ecr_repository_name} created with HealthOmics permissions. '
                            f'To manually push: docker pull {full_source_image} && '
                            f'docker tag {full_source_image} {ecr_uri} && '
                            f'aws ecr get-login-password --region {region} | '
                            f'docker login --username AWS --password-stdin '
                            f'{account_id}.dkr.ecr.{region}.amazonaws.com && '
                            f'docker push {ecr_uri}'
                        ),
                    ).model_dump()

    except botocore.exceptions.ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'AccessDeniedException':
            required_actions = [
                'ecr:DescribePullThroughCacheRules',
                'ecr:DescribeRepositories',
                'ecr:CreateRepository',
                'ecr:BatchGetImage',
                'ecr:SetRepositoryPolicy',
            ]
            logger.error(f'Access denied to ECR: {error_message}')
            await ctx.error(
                f'Access denied to ECR. Ensure IAM permissions include: {required_actions}'
            )
            return CloneContainerResponse(
                success=False,
                source_image=source_image,
                source_registry=source_registry,
                message=f'Access denied: {error_message}',
            ).model_dump()
        else:
            logger.error(f'ECR API error: {error_code} - {error_message}')
            await ctx.error(f'ECR error: {error_message}')
            return CloneContainerResponse(
                success=False,
                source_image=source_image,
                source_registry=source_registry,
                message=f'ECR error: {error_message}',
            ).model_dump()

    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error accessing ECR: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return CloneContainerResponse(
            success=False,
            source_image=source_image,
            source_registry=source_registry,
            message=error_message,
        ).model_dump()

    except Exception as e:
        error_message = f'Unexpected error cloning container: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return CloneContainerResponse(
            success=False,
            source_image=source_image,
            source_registry=source_registry,
            message=error_message,
        ).model_dump()
