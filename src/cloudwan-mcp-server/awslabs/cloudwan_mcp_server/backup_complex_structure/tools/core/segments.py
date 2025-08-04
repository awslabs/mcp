"""
CloudWAN Segments MCP Tool.

This module provides tools for discovering and analyzing CloudWAN segments
across all core networks in the AWS account.
"""

import logging
import asyncio
import time
from typing import Any, Dict, List, Optional

from pydantic import (
    Field,
    BaseModel,
    validator,
    ValidationError as PydanticValidationError,
)

from ...aws.client_manager import AWSClientManager
from ...aws.rate_limiter import (
    with_rate_limiter,
    RateLimitExceededError,
)
from ...config import CloudWANConfig
from ...models.base import (
    NetworkSegment,
    SegmentAllowFilter,
    CloudWANSegmentsResponse,
)
from ..base import BaseMCPTool, handle_errors, ValidationError, AWSOperationError
from ...models.cache import memory_cache, CacheKey, cached_aws_request, cache
from ...utils.validators import validate_aws_region
from ...utils.cloudwan_validators import CloudWANValidator


class CloudWANSegmentsToolInput(BaseModel):
    """Input schema for CloudWANSegmentsTool."""

    core_network_id: Optional[str] = Field(
        default=None,
        description="Core network ID to retrieve segments for (default: all core networks)",
    )
    regions: Optional[List[str]] = Field(
        default=None,
        description="AWS regions to search in (default: all configured regions)",
    )
    include_attachments: bool = Field(
        default=False, description="Include attachment counts for each segment"
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Specific policy version to analyze (default: LIVE policy)",
    )

    # Validators
    @validator("core_network_id")
    def validate_core_network_id(cls, v):
        """Validate core_network_id format if provided."""
        if v is None:
            return v
        try:
            return CloudWANValidator.validate_core_network_id(v)
        except ValueError as e:
            raise PydanticValidationError(
                errors=[
                    {
                        "loc": ("core_network_id",),
                        "msg": str(e),
                        "type": "value_error.core_network_id",
                    }
                ]
            )

    @validator("policy_version")
    def validate_policy_version(cls, v):
        """Validate policy_version format if provided."""
        if v is None:
            return v
        try:
            return CloudWANValidator.validate_policy_version_id(v)
        except ValueError as e:
            raise PydanticValidationError(
                errors=[
                    {
                        "loc": ("policy_version",),
                        "msg": str(e),
                        "type": "value_error.policy_version",
                    }
                ]
            )

    @validator("regions")
    def validate_regions(cls, v):
        """Validate regions if provided."""
        if v is None:
            return v

        validated_regions = []
        invalid_regions = []

        for region in v:
            try:
                validated_region = validate_aws_region(region)
                validated_regions.append(validated_region)
            except ValueError as e:
                invalid_regions.append(f"{region}: {str(e)}")

        if invalid_regions:
            raise PydanticValidationError(
                errors=[
                    {
                        "loc": ("regions",),
                        "msg": f"Invalid regions provided: {', '.join(invalid_regions)}",
                        "type": "value_error.regions",
                    }
                ]
            )

        return validated_regions


class CloudWANSegmentsTool(BaseMCPTool):
    """
    Tool for discovering and analyzing CloudWAN segments.

    This tool retrieves segment information from core networks, including:
    - Segment configuration and routing policies
    - Edge locations and attachment types
    - Shared segments for route exchange
    - Attachment counts and requirements

    It supports querying specific core networks or retrieving segments
    across all core networks in the account.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """Initialize CloudWANSegmentsTool."""
        super().__init__(aws_manager, config)
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def tool_name(self) -> str:
        """Get tool name for MCP registration."""
        return "get_cloudwan_segments"

    @property
    def description(self) -> str:
        """Get tool description for MCP registration."""
        return (
            "Retrieve CloudWAN segment information from core networks.\n\n"
            "This tool provides detailed information about CloudWAN segments including:\n"
            "- Segment configuration and routing policies\n"
            "- Edge locations and allowed attachment types\n"
            "- Shared segments for route exchange\n"
            "- Attachment counts and acceptance requirements\n\n"
            "You can query a specific core network by ID or retrieve segments across all "
            "core networks in the account."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get input schema for MCP registration."""
        return CloudWANSegmentsToolInput.model_json_schema()

    @with_rate_limiter(service="networkmanager", operation="list_core_networks")
    async def _get_core_network_ids(self, regions: List[str]) -> List[str]:
        """
        Get all core network IDs across specified regions.

        Args:
            regions: AWS regions to search

        Returns:
            List of core network IDs

        Raises:
            AWSOperationError: If core network listing fails
            RateLimitExceededError: If API calls are rate limited after retries
        """
        core_network_ids = []
        try:
            for region in regions:
                try:
                    async with self.aws_manager.client_context("networkmanager", region) as client:
                        response = await client.list_core_networks()
                        for network in response.get("CoreNetworks", []):
                            core_network_ids.append(network.get("CoreNetworkId"))
                except RateLimitExceededError as e:
                    self.logger.warning(
                        f"Rate limit exceeded for list_core_networks in {region}: {str(e)}"
                    )
                    # Continue with next region if one fails due to rate limiting
                    continue
        except Exception as e:
            self.logger.error(f"Failed to list core networks: {str(e)}")
            raise AWSOperationError(f"Failed to list core networks: {str(e)}")

        if not core_network_ids:
            self.logger.warning("No core network IDs found or all regions rate limited")

        return core_network_ids

    @with_rate_limiter(service="networkmanager", operation="validate_core_network")
    async def _validate_core_network_exists(self, core_network_id: str, region: str) -> bool:
        """
        Validate that a core network ID exists in the specified region.

        Args:
            core_network_id: Core network ID to validate
            region: AWS region to check in

        Returns:
            True if core network exists, False otherwise

        Raises:
            AWSOperationError: If validation fails due to API errors
            RateLimitExceededError: If API calls are rate limited after retries
        """
        try:
            # Generate cache key parameters for efficiency
            cache_params = {"core_network_id": core_network_id, "region": region}

            # Check cache first to avoid unnecessary API calls
            cached_exists = memory_cache.get(CacheKey.CORE_NETWORK_EXISTS, **cache_params)
            if cached_exists is not None:
                self.logger.debug(f"Cache hit for core network validation: {core_network_id}")
                return cached_exists

            # Not in cache, fetch from API
            async with self.aws_manager.client_context("networkmanager", region) as client:
                try:
                    # Use list_core_networks (correct API method)
                    # This API call is now rate limited by the decorator
                    response = await client.list_core_networks()
                    # Filter to the specific core network we want
                    filtered_networks = [cn for cn in response.get('CoreNetworks', []) 
                                       if cn.get('CoreNetworkId') == core_network_id]
                    response = {'CoreNetworks': filtered_networks}
                    exists = len(response.get("CoreNetworks", [])) > 0
                except RateLimitExceededError as e:
                    self.logger.warning(f"Rate limit exceeded for list_core_networks: {str(e)}")
                    # Return false with warning when rate limited
                    return False
                except Exception as specific_e:
                    # If that fails (e.g., invalid format), fall back to listing all and checking
                    self.logger.debug(
                        f"Direct core network query failed, falling back to list: {specific_e}"
                    )
                    try:
                        # This API call is also rate limited by the decorator
                        response = await client.list_core_networks()
                        exists = any(
                            network.get("CoreNetworkId") == core_network_id
                            for network in response.get("CoreNetworks", [])
                        )
                    except RateLimitExceededError as e:
                        self.logger.warning(
                            f"Rate limit exceeded for list_core_networks fallback: {str(e)}"
                        )
                        # Return false with warning when rate limited
                        return False

            # Cache the result (5 minute TTL)
            memory_cache.set(
                exists,
                ttl=300,  # 5 minute TTL
                category=CacheKey.CORE_NETWORK_EXISTS,
                **cache_params,
            )

            return exists

        except Exception as e:
            self.logger.error(f"Failed to validate core network existence: {str(e)}")
            # Re-raise as AWSOperationError for consistent error handling
            raise AWSOperationError(
                f"Failed to validate core network: {str(e)}",
                "CORE_NETWORK_VALIDATION_ERROR",
            )

    @with_rate_limiter(service="networkmanager", operation="get_core_network_policy")
    async def _get_core_network_policy(
        self,
        core_network_id: str,
        policy_version: Optional[str] = None,
        region: str = "us-west-2",
    ) -> Dict[str, Any]:
        """
        Get core network policy document.

        Args:
            core_network_id: Core network ID
            policy_version: Specific policy version (default: LIVE)
            region: AWS region

        Returns:
            Core network policy document

        Raises:
            AWSOperationError: If policy retrieval fails
            RateLimitExceededError: If API calls are rate limited after retries
        """
        # Generate cache key parameters
        cache_params = {
            "core_network_id": core_network_id,
            "policy_version": policy_version or "LIVE",
            "region": region,
        }

        # Check cache first
        cached_response = memory_cache.get(CacheKey.CORE_NETWORK_POLICY, **cache_params)
        if cached_response:
            self.logger.debug(f"Cache hit for core network policy: {core_network_id}")
            return cached_response

        # Not in cache, fetch from API
        try:
            start_time = time.time()
            async with self.aws_manager.client_context("networkmanager", region) as client:
                if policy_version:
                    response = await cached_aws_request(
                        client,
                        "get_core_network_policy",
                        CoreNetworkId=core_network_id,
                        PolicyVersionId=policy_version,
                    )
                else:
                    # Get the LIVE policy by default
                    response = await cached_aws_request(
                        client, "get_core_network_policy", CoreNetworkId=core_network_id
                    )

                # Log the response time for monitoring
                elapsed = time.time() - start_time
                self.logger.debug(f"get_core_network_policy took {elapsed:.2f}s")

                # Cache the response (5 minute TTL for policy documents)
                memory_cache.set(
                    response,
                    ttl=300,  # 5 minute TTL
                    category=CacheKey.CORE_NETWORK_POLICY,
                    **cache_params,
                )

                return response

        except RateLimitExceededError as e:
            self.logger.warning(f"Rate limit exceeded for get_core_network_policy: {str(e)}")
            # Re-raise with more context
            raise RateLimitExceededError(
                f"Rate limit exceeded for core network policy retrieval: {str(e)}"
            )

        except Exception as e:
            self.logger.error(f"Failed to get core network policy: {str(e)}")
            raise AWSOperationError(f"Failed to get core network policy: {str(e)}")

    @with_rate_limiter(service="networkmanager", operation="list_attachments")
    async def _get_segment_attachment_counts(
        self, core_network_id: str, segment_names: List[str], region: str = "us-west-2"
    ) -> Dict[str, int]:
        """
        Get attachment counts for each segment.

        Args:
            core_network_id: Core network ID
            segment_names: List of segment names
            region: AWS region

        Returns:
            Mapping of segment names to attachment counts

        Raises:
            AWSOperationError: If attachment listing fails
            RateLimitExceededError: If API calls are rate limited after retries
        """
        attachment_counts = {segment: 0 for segment in segment_names}

        try:
            start_time = time.time()
            async with self.aws_manager.client_context("networkmanager", region) as client:
                # Use pagination to get all attachments
                paginator = client.get_paginator("list_attachments")
                page_iterator = paginator.paginate(CoreNetworkId=core_network_id)

                async for page in page_iterator:
                    for attachment in page.get("Attachments", []):
                        segment = attachment.get("SegmentName")
                        if segment in attachment_counts:
                            attachment_counts[segment] += 1

            # Log the response time for monitoring
            elapsed = time.time() - start_time
            self.logger.debug(f"list_attachments took {elapsed:.2f}s")

        except RateLimitExceededError as e:
            self.logger.warning(f"Rate limit exceeded for list_attachments: {str(e)}")
            # Don't fail the entire operation if rate limited, return partial results
            # This is a non-critical operation

        except KeyError as e:
            # Handle expected data structure errors specifically
            self.logger.warning(f"Missing expected key in attachment data: {e}")
        except ValueError as e:
            # Handle value errors (e.g., invalid parameters)
            self.logger.warning(f"Invalid parameter for list_attachments: {e}")
        except ConnectionError as e:
            # Handle network connectivity issues
            self.logger.warning(f"Network error when fetching attachments: {e}")
        except Exception as e:
            # Last resort, but still log more details
            self.logger.warning(
                f"Failed to get attachment counts: {str(e)}",
                exc_info=True,  # Include stack trace in the logs
            )
            # Don't fail the entire operation if this part fails

        return attachment_counts

    async def _parse_segments_from_policy(
        self,
        policy_doc: Dict[str, Any],
        include_attachments: bool = False,
        core_network_id: Optional[str] = None,
        region: str = "us-west-2",
    ) -> List[NetworkSegment]:
        """
        Parse segments from core network policy.

        Args:
            policy_doc: Core network policy document
            include_attachments: Whether to include attachment counts
            core_network_id: Core network ID (required if include_attachments=True)
            region: AWS region

        Returns:
            List of NetworkSegment objects
        """
        segments = []

        # Validate input parameters
        if include_attachments and not core_network_id:
            self.logger.warning(
                "include_attachments=True requires a core_network_id but none provided. "
                "Attachment counts will not be included."
            )
            include_attachments = False

        # Extract policy JSON
        policy_json = policy_doc.get("CoreNetworkPolicy", {})
        if not policy_json:
            self.logger.warning("No CoreNetworkPolicy field found in policy document")
            return segments

        # Extract segments from policy
        segments_json = policy_json.get("Segments", [])
        if not segments_json:
            self.logger.info("No segments found in policy document")
            return segments

        segment_names = []
        for segment_json in segments_json:
            # Validate required segment fields
            name = segment_json.get("Name")
            if not name:
                self.logger.warning("Skipping segment with missing name")
                continue

            try:
                # Validate segment name format
                validated_name = CloudWANValidator.validate_segment_name(name)
                segment_names.append(validated_name)

                # Parse edge locations if present
                edge_locations = segment_json.get("EdgeLocations", [])
                if edge_locations:
                    try:
                        validated_edge_locations = CloudWANValidator.validate_edge_locations(
                            edge_locations
                        )
                    except ValueError as e:
                        self.logger.warning(
                            f"Invalid edge locations for segment '{name}': {str(e)}. Using unvalidated values."
                        )
                        validated_edge_locations = edge_locations
                else:
                    validated_edge_locations = []

                # Parse shared segments if present
                shared_segments = segment_json.get("SharedSegments", [])
                validated_shared_segments = []
                if shared_segments:
                    for shared_segment in shared_segments:
                        try:
                            validated_shared_segment = CloudWANValidator.validate_segment_name(
                                shared_segment
                            )
                            validated_shared_segments.append(validated_shared_segment)
                        except ValueError as e:
                            self.logger.warning(
                                f"Invalid shared segment name '{shared_segment}': {str(e)}"
                            )
                            # Include original name for backwards compatibility
                            validated_shared_segments.append(shared_segment)

                # Parse allow filter if present
                allow_filter = None
                if "AllowFilter" in segment_json:
                    filter_json = segment_json.get("AllowFilter", {})
                    try:
                        # Validate filter types
                        validated_filter = CloudWANValidator.validate_allow_filter(filter_json)
                        allow_filter = SegmentAllowFilter(types=validated_filter.get("types", []))
                    except ValueError as e:
                        self.logger.warning(f"Invalid allow filter for segment '{name}': {str(e)}")
                        # Create allow filter with original values for backwards compatibility
                        allow_filter = SegmentAllowFilter(types=filter_json.get("Types", []))

                # Validate boolean flags
                requires_attachment_acceptance = segment_json.get(
                    "RequireAttachmentAcceptance", False
                )
                isolate_attachments = segment_json.get("IsolateAttachments", False)

                # Validate compatibility between segment settings
                try:
                    CloudWANValidator.validate_attachment_requirements(
                        requires_acceptance=requires_attachment_acceptance,
                        isolate_attachments=isolate_attachments,
                    )
                except ValueError as e:
                    self.logger.warning(f"Invalid segment configuration for '{name}': {str(e)}")

                # Create segment model with validated values
                segment = NetworkSegment(
                    name=validated_name,
                    description=segment_json.get("Description"),
                    edge_locations=validated_edge_locations,
                    shared_segments=validated_shared_segments,
                    allow_filter=allow_filter,
                    requires_attachment_acceptance=requires_attachment_acceptance,
                    isolate_attachments=isolate_attachments,
                )

                segments.append(segment)

            except Exception as e:
                self.logger.warning(f"Error processing segment '{name}': {str(e)}")
                # Skip this segment and continue with others
                continue

        # Get attachment counts if requested
        if include_attachments and core_network_id and segment_names:
            try:
                attachment_counts = await self._get_segment_attachment_counts(
                    core_network_id=core_network_id,
                    segment_names=segment_names,
                    region=region,
                )

                # Update segment objects with counts
                for segment in segments:
                    if segment.name in attachment_counts:
                        segment.attachment_count = attachment_counts[segment.name]
                    else:
                        self.logger.debug(f"No attachment count found for segment '{segment.name}'")

            except RateLimitExceededError as e:
                self.logger.warning(f"Rate limit exceeded when getting attachment counts: {str(e)}")
                # Continue without attachment counts, this is non-critical functionality

            except Exception as e:
                self.logger.warning(f"Failed to get attachment counts: {str(e)}")
                # Continue without attachment counts

        return segments

    @with_rate_limiter(service="networkmanager", operation="process_core_network")
    async def _process_core_network(
        self,
        core_network_id: str,
        include_attachments: bool,
        policy_version: Optional[str] = None,
        region: str = "us-west-2",
    ) -> CloudWANSegmentsResponse:
        """
        Process a single core network to extract segments.

        Args:
            core_network_id: Core network ID
            include_attachments: Whether to include attachment counts
            policy_version: Specific policy version
            region: AWS region

        Returns:
            CloudWANSegmentsResponse with segments information
        """
        try:
            policy_doc = await self._get_core_network_policy(
                core_network_id=core_network_id,
                policy_version=policy_version,
                region=region,
            )

            segments = await self._parse_segments_from_policy(
                policy_doc=policy_doc,
                include_attachments=include_attachments,
                core_network_id=core_network_id,
                region=region,
            )

            # Create response object
            response = CloudWANSegmentsResponse(
                core_network_id=core_network_id,
                segments=segments,
                total_segments=len(segments),
                policy_version=policy_version or "LIVE",
                regions_analyzed=[region],
            )

            return response

        except RateLimitExceededError as e:
            error_message = f"Rate limit exceeded for core network {core_network_id}: {str(e)}"
            self.logger.error(error_message)

            # Get error details
            error_details = {
                "exception_type": "RateLimitExceededError",
                "core_network_id": core_network_id,
                "region": region,
                "policy_version": policy_version or "LIVE",
            }

            # Create rate limit error response
            response = CloudWANSegmentsResponse(
                core_network_id=core_network_id,
                segments=[],
                total_segments=0,
                policy_version=policy_version or "LIVE",
                regions_analyzed=[region],
                status="rate_limited",
                error_message=error_message,
                error_details=error_details,
                failure_count=1,
            )

            return response

        except Exception as e:
            error_message = f"Failed to process core network {core_network_id}: {str(e)}"
            self.logger.error(error_message)

            # Get error details
            error_details = {
                "exception_type": e.__class__.__name__,
                "core_network_id": core_network_id,
                "region": region,
                "policy_version": policy_version or "LIVE",
            }

            # Create error response with detailed information
            response = CloudWANSegmentsResponse(
                core_network_id=core_network_id,
                segments=[],
                total_segments=0,
                policy_version=policy_version or "LIVE",
                regions_analyzed=[region],
                status="error",
                error_message=error_message,
                error_details=error_details,
                failure_count=1,
            )

            return response

    @handle_errors
    @cache(ttl=120, category=CacheKey.SEGMENT_LIST)  # 2 minute TTL for executed results
    async def execute(self, **kwargs) -> CloudWANSegmentsResponse:
        """
        Execute the CloudWAN segments tool.

        Args:
            **kwargs: Tool parameters
                - core_network_id: Optional core network ID
                - regions: Optional list of regions
                - include_attachments: Whether to include attachment counts
                - policy_version: Optional policy version

        Returns:
            CloudWANSegmentsResponse with segment information

        Raises:
            ValidationError: If any input parameters are invalid
            AWSOperationError: If AWS API calls fail
        """
        try:
            # Parse and validate input using Pydantic model
            # This will trigger all the validators we defined
            input_model = CloudWANSegmentsToolInput(**kwargs)

            # Validate regions against configured regions (if provided)
            if input_model.regions:
                self._validate_regions_against_config(input_model.regions)

            # Determine regions to search
            regions = input_model.regions or self.config.aws.regions

            # Default to us-west-2 (global service) if no regions specified
            if not regions:
                self.logger.info("No regions specified, defaulting to us-west-2")
                regions = ["us-west-2"]

            # Log regions to be used
            self.logger.debug(f"Using regions: {', '.join(regions)}")

            # Handle direct core network ID
            if input_model.core_network_id:
                # For a specific core network, we only need to query one region
                # since Network Manager is a global service
                primary_region = regions[0]

                # Validate the core network exists before proceeding
                await self._validate_core_network_availability(
                    core_network_id=input_model.core_network_id, region=primary_region
                )

                response = await self._process_core_network(
                    core_network_id=input_model.core_network_id,
                    include_attachments=input_model.include_attachments,
                    policy_version=input_model.policy_version,
                    region=primary_region,
                )

                return response
            else:
                # Query all core networks across regions
                return await self._process_all_core_networks(
                    regions=regions,
                    include_attachments=input_model.include_attachments,
                    policy_version=input_model.policy_version,
                )

        except PydanticValidationError as e:
            # Convert Pydantic validation errors to our ValidationError format
            error_details = []
            for err in e.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                error_details.append(f"{field}: {err['msg']}")

            error_message = f"Invalid input parameters: {'; '.join(error_details)}"
            self.logger.error(error_message)
            raise ValidationError(error_message, error_code="INVALID_INPUT")

        except RateLimitExceededError as e:
            # Handle rate limit errors gracefully
            error_message = f"Rate limit exceeded in CloudWANSegmentsTool: {str(e)}"
            self.logger.error(error_message)
            raise AWSOperationError(error_message, "RATE_LIMIT_ERROR")

        except Exception as e:
            # Re-raise any other exceptions that weren't caught
            self.logger.error(f"Unexpected error in CloudWANSegmentsTool: {str(e)}")
            raise

    def _validate_regions_against_config(self, regions: List[str]) -> None:
        """
        Validate that provided regions are in configured regions.

        Args:
            regions: List of regions to validate

        Raises:
            ValidationError: If any regions are not in configured regions
        """
        invalid_regions = []
        configured_regions = set(self.config.aws.regions)

        for region in regions:
            if region not in configured_regions:
                invalid_regions.append(region)

        if invalid_regions:
            error_message = (
                f"Regions not in configured regions: {', '.join(invalid_regions)}. "
                f"Configured regions: {', '.join(self.config.aws.regions)}"
            )
            self.logger.error(error_message)
            raise ValidationError(error_message, error_code="REGION_NOT_CONFIGURED")

    @with_rate_limiter(service="networkmanager", operation="validate_network_availability")
    async def _validate_core_network_availability(self, core_network_id: str, region: str) -> None:
        """
        Validate that a core network exists and is accessible.

        Args:
            core_network_id: Core network ID to validate
            region: AWS region to check in

        Raises:
            ValidationError: If core network doesn't exist or isn't accessible
            RateLimitExceededError: If API calls are rate limited after retries
        """
        try:
            core_exists = await self._validate_core_network_exists(
                core_network_id=core_network_id, region=region
            )

            if not core_exists:
                error_message = f"Core network ID not found: {core_network_id}"
                self.logger.error(error_message)
                raise ValidationError(error_message, error_code="CORE_NETWORK_NOT_FOUND")

        except RateLimitExceededError as e:
            error_message = (
                f"Rate limit exceeded for core network validation: {core_network_id} - {str(e)}"
            )
            self.logger.error(error_message)
            # Re-raise as AWSOperationError with special code for rate limiting
            raise AWSOperationError(error_message, "CORE_NETWORK_RATE_LIMIT_ERROR")

        except AWSOperationError as e:
            # Re-raise AWSOperationError with more context
            error_message = f"Failed to validate core network ID: {core_network_id} - {str(e)}"
            self.logger.error(error_message)
            raise AWSOperationError(error_message, "CORE_NETWORK_VALIDATION_ERROR")

        except Exception as e:
            # Convert other exceptions to ValidationError
            error_message = f"Failed to validate core network ID: {core_network_id} - {str(e)}"
            self.logger.error(error_message)
            raise ValidationError(error_message, error_code="CORE_NETWORK_VALIDATION_ERROR")

    @with_rate_limiter(service="networkmanager", operation="process_networks", region="us-west-2")
    async def _process_all_core_networks(
        self,
        regions: List[str],
        include_attachments: bool = False,
        policy_version: Optional[str] = None,
    ) -> CloudWANSegmentsResponse:
        """
        Process all core networks in the account.

        Args:
            regions: AWS regions to search
            include_attachments: Whether to include attachment counts
            policy_version: Optional policy version

        Returns:
            CloudWANSegmentsResponse with combined segment information
        """
        # Use the first region as primary since Network Manager is a global service
        primary_region = regions[0]

        # First, get all core network IDs
        try:
            core_network_ids = await self._get_core_network_ids(regions=[primary_region])
        except Exception as e:
            self.logger.error(f"Failed to list core networks: {str(e)}")
            raise AWSOperationError(f"Failed to list core networks: {str(e)}")

        if not core_network_ids:
            self.logger.info("No core networks found in the account")
            return CloudWANSegmentsResponse(
                core_network_id="",
                segments=[],
                total_segments=0,
                policy_version="",
                regions_analyzed=regions,
                status="success",
                error_message="No core networks found in the account",
            )

        # If only one core network found, return that directly
        if len(core_network_ids) == 1:
            self.logger.info(f"Found one core network: {core_network_ids[0]}")
            response = await self._process_core_network(
                core_network_id=core_network_ids[0],
                include_attachments=include_attachments,
                policy_version=policy_version,
                region=primary_region,
            )

            return response

        # Process each core network in parallel
        self.logger.info(f"Processing {len(core_network_ids)} core networks in parallel")
        tasks = []
        for core_id in core_network_ids:
            tasks.append(
                self._process_core_network(
                    core_network_id=core_id,
                    include_attachments=include_attachments,
                    policy_version=policy_version,
                    region=primary_region,
                )
            )

        # Process all results and combine
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results from all core networks
        all_segments = []
        errors = []
        successful_networks = []

        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
                continue

            all_segments.extend(result.segments)
            successful_networks.append(result.core_network_id)

        # Create combined response with proper success/failure counts
        combined_response = CloudWANSegmentsResponse(
            core_network_id=(",".join(successful_networks) if successful_networks else ""),
            segments=all_segments,
            total_segments=len(all_segments),
            policy_version="multiple",
            regions_analyzed=regions,
            status="partial" if errors else "success",
            error_message="\n".join(errors) if errors else None,
            success_count=len(successful_networks),
            failure_count=len(errors),
            operation_details={
                "successful_networks": successful_networks,
                "failed_networks": [e for e in errors if isinstance(e, str)],
            },
        )

        return combined_response
