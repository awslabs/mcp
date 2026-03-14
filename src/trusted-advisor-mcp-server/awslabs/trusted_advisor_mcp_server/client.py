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
"""AWS Trusted Advisor API client for the Trusted Advisor MCP Server."""

import asyncio
import boto3
from awslabs.trusted_advisor_mcp_server import __version__
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from loguru import logger
from typing import Any, Callable, Dict, List, Optional


DEFAULT_REGION = 'us-east-1'
API_TIMEOUT = 30
MAX_RESULTS_PER_PAGE = 200


class TrustedAdvisorClient:
    """Client for interacting with the AWS Trusted Advisor API.

    This client provides a convenient async interface for interacting with the
    AWS Trusted Advisor API, handling authentication, pagination, error handling,
    and response formatting.

    Attributes:
        client: The boto3 TrustedAdvisor client.
        region_name: The AWS region name.
    """

    def __init__(self, region_name: str = DEFAULT_REGION, profile_name: Optional[str] = None):
        """Initialize the Trusted Advisor client.

        Args:
            region_name: AWS region name (default: us-east-1). The Trusted Advisor
                API is a global service accessed through us-east-1.
            profile_name: AWS profile name (optional).

        Raises:
            ClientError: If there is an error creating the boto3 client.
        """
        try:
            logger.info(
                f'Initializing Trusted Advisor client with region={region_name}, profile={profile_name}'
            )

            session_kwargs: Dict[str, str] = {'region_name': region_name}
            if profile_name:
                session_kwargs['profile_name'] = profile_name

            session = boto3.Session(**session_kwargs)

            retry_config = BotoConfig(
                retries={'max_attempts': 3, 'mode': 'standard'},
                connect_timeout=API_TIMEOUT,
                read_timeout=API_TIMEOUT,
                user_agent_extra=f'awslabs/mcp/trusted_advisor_mcp_server/{__version__}',
            )

            self.client = session.client('trustedadvisor', config=retry_config)
            self.region_name = region_name

            logger.info(f'Successfully initialized Trusted Advisor client in region {region_name}')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(
                f'Failed to initialize Trusted Advisor client: {error_code} - {error_message}'
            )
            raise
        except Exception as e:
            logger.error(f'Unexpected error initializing Trusted Advisor client: {str(e)}')
            raise

    async def _run_in_executor(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run a synchronous boto3 function in an executor for async compatibility.

        Args:
            func: The synchronous function to run.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of the function call.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _paginate(
        self, method: Callable[..., Any], result_key: str, max_pages: int = 100, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Auto-paginate a Trusted Advisor API call.

        Args:
            method: The boto3 client method to call.
            result_key: The key in the response that contains the results list.
            max_pages: Maximum number of pages to fetch (default: 100).
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            A list of all results across all pages.
        """
        all_results: List[Dict[str, Any]] = []
        next_token = None
        page_count = 0

        while True:
            if next_token:
                kwargs['nextToken'] = next_token

            response = await self._run_in_executor(method, **kwargs)
            all_results.extend(response.get(result_key, []))
            page_count += 1

            next_token = response.get('nextToken')
            if not next_token:
                break

            if page_count >= max_pages:
                logger.warning(
                    f'Pagination limit reached ({max_pages} pages). '
                    f'Results may be incomplete.'
                )
                break

        return all_results

    async def list_checks(
        self,
        pillar: Optional[str] = None,
        aws_service: Optional[str] = None,
        language: str = 'en',
    ) -> List[Dict[str, Any]]:
        """List all available Trusted Advisor checks.

        Args:
            pillar: Filter by Well-Architected pillar (optional).
            aws_service: Filter by AWS service (optional).
            language: Language code for check descriptions (default: en).

        Returns:
            A list of check summaries.
        """
        try:
            kwargs: Dict[str, Any] = {'language': language}
            if pillar:
                kwargs['pillar'] = pillar
            if aws_service:
                kwargs['awsService'] = aws_service

            logger.debug(f'Listing Trusted Advisor checks with filters: {kwargs}')
            checks = await self._paginate(self.client.list_checks, 'checkSummaries', **kwargs)

            logger.info(f'Retrieved {len(checks)} Trusted Advisor checks')
            return checks
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f'Failed to list checks: {error_code} - {error_message}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error listing checks: {str(e)}')
            raise

    async def list_recommendations(
        self,
        status: Optional[str] = None,
        pillar: Optional[str] = None,
        after_last_updated_at: Optional[str] = None,
        aws_service: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List current Trusted Advisor recommendations.

        Args:
            status: Filter by status: ok, warning, error (optional).
            pillar: Filter by Well-Architected pillar (optional).
            after_last_updated_at: Filter to recommendations updated after this ISO datetime (optional).
            aws_service: Filter by AWS service (optional).

        Returns:
            A list of recommendation summaries.
        """
        try:
            kwargs: Dict[str, Any] = {}
            if status:
                kwargs['status'] = status
            if pillar:
                kwargs['pillar'] = pillar
            if after_last_updated_at:
                kwargs['afterLastUpdatedAt'] = after_last_updated_at
            if aws_service:
                kwargs['awsService'] = aws_service

            logger.debug(f'Listing recommendations with filters: {kwargs}')
            recommendations = await self._paginate(
                self.client.list_recommendations, 'recommendationSummaries', **kwargs
            )

            logger.info(f'Retrieved {len(recommendations)} recommendations')
            return recommendations
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f'Failed to list recommendations: {error_code} - {error_message}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error listing recommendations: {str(e)}')
            raise

    async def get_recommendation(self, recommendation_identifier: str) -> Dict[str, Any]:
        """Get detailed information about a specific recommendation.

        Args:
            recommendation_identifier: The ARN or ID of the recommendation.

        Returns:
            Detailed recommendation information.
        """
        try:
            logger.debug(f'Getting recommendation: {recommendation_identifier}')
            response = await self._run_in_executor(
                self.client.get_recommendation,
                recommendationIdentifier=recommendation_identifier,
            )

            logger.info(f'Retrieved recommendation: {recommendation_identifier}')
            return response.get('recommendation', {})
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f'Failed to get recommendation: {error_code} - {error_message}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error getting recommendation: {str(e)}')
            raise

    async def list_recommendation_resources(
        self, recommendation_identifier: str
    ) -> List[Dict[str, Any]]:
        """List resources affected by a specific recommendation.

        Args:
            recommendation_identifier: The ARN or ID of the recommendation.

        Returns:
            A list of affected resources.
        """
        try:
            logger.debug(f'Listing resources for recommendation: {recommendation_identifier}')
            resources = await self._paginate(
                self.client.list_recommendation_resources,
                'recommendationResourceSummaries',
                recommendationIdentifier=recommendation_identifier,
            )

            logger.info(
                f'Retrieved {len(resources)} resources for recommendation: {recommendation_identifier}'
            )
            return resources
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f'Failed to list recommendation resources: {error_code} - {error_message}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error listing recommendation resources: {str(e)}')
            raise

    async def update_recommendation_lifecycle(
        self,
        recommendation_identifier: str,
        lifecycle_stage: str,
        update_reason: Optional[str] = None,
    ) -> None:
        """Update the lifecycle stage of a recommendation.

        Args:
            recommendation_identifier: The ARN or ID of the recommendation.
            lifecycle_stage: The new lifecycle stage: pending_response, in_progress,
                dismissed, or resolved.
            update_reason: The reason for the lifecycle update (optional).
        """
        try:
            kwargs: Dict[str, str] = {
                'recommendationIdentifier': recommendation_identifier,
                'lifecycleStage': lifecycle_stage,
            }
            if update_reason:
                kwargs['updateReason'] = update_reason

            logger.info(
                f'Updating recommendation lifecycle: {recommendation_identifier} -> {lifecycle_stage}'
            )
            await self._run_in_executor(
                self.client.update_recommendation_lifecycle, **kwargs
            )

            logger.info(
                f'Successfully updated recommendation lifecycle: {recommendation_identifier}'
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(
                f'Failed to update recommendation lifecycle: {error_code} - {error_message}'
            )
            raise
        except Exception as e:
            logger.error(f'Unexpected error updating recommendation lifecycle: {str(e)}')
            raise

    async def list_organization_recommendations(
        self,
        status: Optional[str] = None,
        pillar: Optional[str] = None,
        aws_service: Optional[str] = None,
        after_last_updated_at: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List recommendations across all accounts in AWS Organizations.

        This requires the caller to be in the management account or a delegated
        administrator account.

        Args:
            status: Filter by status: ok, warning, error (optional).
            pillar: Filter by Well-Architected pillar (optional).
            aws_service: Filter by AWS service (optional).
            after_last_updated_at: Filter to recommendations updated after this ISO datetime (optional).

        Returns:
            A list of organization recommendation summaries.
        """
        try:
            kwargs: Dict[str, Any] = {}
            if status:
                kwargs['status'] = status
            if pillar:
                kwargs['pillar'] = pillar
            if aws_service:
                kwargs['awsService'] = aws_service
            if after_last_updated_at:
                kwargs['afterLastUpdatedAt'] = after_last_updated_at

            logger.debug(f'Listing organization recommendations with filters: {kwargs}')
            recommendations = await self._paginate(
                self.client.list_organization_recommendations,
                'organizationRecommendationSummaries',
                **kwargs,
            )

            logger.info(f'Retrieved {len(recommendations)} organization recommendations')
            return recommendations
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(
                f'Failed to list organization recommendations: {error_code} - {error_message}'
            )
            raise
        except Exception as e:
            logger.error(f'Unexpected error listing organization recommendations: {str(e)}')
            raise
