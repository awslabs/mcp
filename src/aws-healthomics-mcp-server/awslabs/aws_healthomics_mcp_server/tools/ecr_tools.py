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
