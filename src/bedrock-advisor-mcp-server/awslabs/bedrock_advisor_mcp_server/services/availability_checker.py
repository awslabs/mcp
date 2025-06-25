"""
Model availability checker for Bedrock models across AWS regions.

This module provides functionality to check the availability of Bedrock
foundation models across different AWS regions, helping users make informed
decisions about model selection based on their regional deployment needs.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from typing_extensions import TypedDict

from ..models.bedrock import BedrockModel, ModelAvailability, ModelStatus
from ..utils.errors import RegionNotSupportedError, ServiceUnavailableError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RegionInfo(TypedDict):
    """Type definition for region information."""

    region_name: str
    region_display_name: str
    is_active: bool


class ModelRegionAvailability(TypedDict):
    """Type definition for model availability in a region."""

    model_id: str
    model_name: str
    provider: str
    is_available: bool
    status: str


class AvailabilityChecker:
    """
    Service for checking Bedrock model availability across AWS regions.

    This service provides functionality to check the availability of Bedrock
    foundation models across different AWS regions, helping users make informed
    decisions about model selection based on their regional deployment needs.
    """

    def __init__(self):
        """Initialize the availability checker."""
        # Define common AWS regions where Bedrock is available
        self.bedrock_regions = [
            {
                "region_name": "us-east-1",
                "region_display_name": "US East (N. Virginia)",
                "is_active": True,
            },
            {
                "region_name": "us-west-2",
                "region_display_name": "US West (Oregon)",
                "is_active": True,
            },
            {
                "region_name": "eu-west-1",
                "region_display_name": "Europe (Ireland)",
                "is_active": True,
            },
            {
                "region_name": "ap-northeast-1",
                "region_display_name": "Asia Pacific (Tokyo)",
                "is_active": True,
            },
            {
                "region_name": "ap-southeast-1",
                "region_display_name": "Asia Pacific (Singapore)",
                "is_active": True,
            },
            {
                "region_name": "eu-central-1",
                "region_display_name": "Europe (Frankfurt)",
                "is_active": True,
            },
            {
                "region_name": "ap-south-1",
                "region_display_name": "Asia Pacific (Mumbai)",
                "is_active": True,
            },
            {
                "region_name": "ca-central-1",
                "region_display_name": "Canada (Central)",
                "is_active": True,
            },
        ]

        # Cache for region availability
        self._region_model_cache: Dict[str, List[str]] = {}
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl_seconds = 3600  # Cache for 1 hour

    def get_bedrock_regions(self) -> List[RegionInfo]:
        """
        Get list of AWS regions where Bedrock is available.

        Returns:
            List of region information dictionaries
        """
        return self.bedrock_regions

    async def check_model_availability(
        self, model_id: str, regions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check availability of a specific model across regions.

        This method checks whether a specific model is available in the
        specified regions, or across all Bedrock regions if no regions
        are specified.

        Args:
            model_id: The model ID to check
            regions: Optional list of regions to check (defaults to all Bedrock regions)

        Returns:
            Dict with availability information
        """
        # Use all Bedrock regions if none specified
        if not regions:
            regions = [region["region_name"] for region in self.bedrock_regions]

        # Validate regions
        for region in regions:
            if region not in [r["region_name"] for r in self.bedrock_regions]:
                raise RegionNotSupportedError(
                    region=region,
                    supported_regions=[r["region_name"] for r in self.bedrock_regions],
                )

        # Check availability in each region
        availability_results = []
        for region in regions:
            is_available, status = await self._check_model_in_region(model_id, region)

            # Get region display name
            region_info = next(
                (r for r in self.bedrock_regions if r["region_name"] == region), None
            )
            region_display_name = (
                region_info["region_display_name"] if region_info else region
            )

            availability_results.append(
                {
                    "region": region,
                    "region_display_name": region_display_name,
                    "is_available": is_available,
                    "status": status,
                }
            )

        # Count available regions
        available_regions = [r for r in availability_results if r["is_available"]]

        return {
            "model_id": model_id,
            "availability": availability_results,
            "available_regions_count": len(available_regions),
            "total_regions_checked": len(regions),
            "availability_percentage": (len(available_regions) / len(regions)) * 100
            if regions
            else 0,
        }

    async def check_region_availability(
        self, region: str, model_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check availability of models in a specific region.

        This method checks which models are available in a specific region,
        optionally filtering to a specific set of models if provided.

        Args:
            region: The AWS region to check
            model_ids: Optional list of model IDs to check (defaults to all models)

        Returns:
            Dict with availability information
        """
        # Validate region
        if region not in [r["region_name"] for r in self.bedrock_regions]:
            raise RegionNotSupportedError(
                region=region,
                supported_regions=[r["region_name"] for r in self.bedrock_regions],
            )

        # Get all models in the region
        available_models = await self._get_models_in_region(region)

        # Filter to specific models if provided
        if model_ids:
            model_availability = []
            for model_id in model_ids:
                is_available = model_id in available_models
                model_availability.append(
                    {
                        "model_id": model_id,
                        "is_available": is_available,
                        "status": "ACTIVE" if is_available else "NOT_AVAILABLE",
                    }
                )
        else:
            # Return all available models
            model_availability = [
                {"model_id": model_id, "is_available": True, "status": "ACTIVE"}
                for model_id in available_models
            ]

        # Get region display name
        region_info = next(
            (r for r in self.bedrock_regions if r["region_name"] == region), None
        )
        region_display_name = (
            region_info["region_display_name"] if region_info else region
        )

        return {
            "region": region,
            "region_display_name": region_display_name,
            "available_models_count": len(available_models),
            "models": model_availability,
        }

    async def compare_model_availability(self, model_ids: List[str]) -> Dict[str, Any]:
        """
        Compare availability of multiple models across regions.

        This method checks and compares the availability of multiple models
        across all Bedrock regions, helping users identify which models are
        available in which regions for multi-region deployments.

        Args:
            model_ids: List of model IDs to compare

        Returns:
            Dict with comparison results
        """
        if not model_ids:
            raise ValueError("At least one model ID must be provided")

        # Check availability for each model across all regions
        model_results = []
        for model_id in model_ids:
            result = await self.check_model_availability(model_id)
            model_results.append(result)

        # Generate region comparison
        region_comparison = {}
        for region in self.bedrock_regions:
            region_name = region["region_name"]
            region_comparison[region_name] = {
                "region_display_name": region["region_display_name"],
                "models": {},
            }

            for result in model_results:
                model_id = result["model_id"]
                region_availability = next(
                    (r for r in result["availability"] if r["region"] == region_name),
                    {"is_available": False, "status": "UNKNOWN"},
                )

                region_comparison[region_name]["models"][model_id] = {
                    "is_available": region_availability["is_available"],
                    "status": region_availability["status"],
                }

        # Generate model comparison
        model_comparison = {}
        for result in model_results:
            model_id = result["model_id"]
            available_regions = [
                r["region"] for r in result["availability"] if r["is_available"]
            ]

            model_comparison[model_id] = {
                "available_regions": available_regions,
                "available_regions_count": len(available_regions),
                "availability_percentage": result["availability_percentage"],
            }

        # Find regions where all models are available
        all_regions = [region["region_name"] for region in self.bedrock_regions]
        common_regions = []

        for region in all_regions:
            if all(
                region_comparison[region]["models"][model_id]["is_available"]
                for model_id in model_ids
            ):
                common_regions.append(region)

        return {
            "models_compared": len(model_ids),
            "regions_checked": len(all_regions),
            "common_regions": common_regions,
            "common_regions_count": len(common_regions),
            "model_comparison": model_comparison,
            "region_comparison": region_comparison,
        }

    async def update_model_availability(self, model: BedrockModel) -> ModelAvailability:
        """
        Update availability information for a model.

        This method checks the availability of a model across all Bedrock
        regions and updates its availability information.

        Args:
            model: The model to update

        Returns:
            Updated ModelAvailability object
        """
        # Check availability across all regions
        all_regions = [region["region_name"] for region in self.bedrock_regions]
        available_regions = []

        for region in all_regions:
            is_available, _ = await self._check_model_in_region(model.model_id, region)
            if is_available:
                available_regions.append(region)

        # Determine status based on availability
        if not available_regions:
            status = ModelStatus.DEPRECATED
        elif len(available_regions) < len(all_regions) / 2:
            status = ModelStatus.LEGACY
        else:
            status = ModelStatus.ACTIVE

        # Create updated availability
        return ModelAvailability(
            regions=available_regions,
            status=status,
            last_checked=datetime.now().strftime("%Y-%m-%d"),
        )

    async def _check_model_in_region(
        self, model_id: str, region: str
    ) -> Tuple[bool, str]:
        """
        Check if a specific model is available in a region.

        Args:
            model_id: The model ID to check
            region: The AWS region to check

        Returns:
            Tuple of (is_available, status)
        """
        try:
            # Check cache first
            if region in self._region_model_cache:
                return model_id in self._region_model_cache[region], "ACTIVE"

            # Get all models in the region
            available_models = await self._get_models_in_region(region)

            # Check if the model is in the list
            return model_id in available_models, "ACTIVE"

        except ServiceUnavailableError:
            # If we can't access the region, assume the model is not available
            return False, "REGION_UNAVAILABLE"
        except Exception as e:
            logger.warning(f"Error checking model {model_id} in region {region}: {e}")
            return False, "CHECK_FAILED"

    async def _get_models_in_region(self, region: str) -> List[str]:
        """
        Get all available models in a specific region.

        Args:
            region: The AWS region to check

        Returns:
            List of available model IDs
        """
        # Check cache first
        if region in self._region_model_cache:
            return self._region_model_cache[region]

        try:
            # Create a Bedrock client for the region
            client = boto3.client("bedrock", region_name=region)

            # Get foundation models
            response = client.list_foundation_models()

            # Extract model IDs
            model_ids = [
                model["modelId"] for model in response.get("modelSummaries", [])
            ]

            # Update cache
            self._region_model_cache[region] = model_ids
            self._cache_timestamp = time.time()

            return model_ids

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Bedrock API error in region {region} ({error_code}): {e}")

            if error_code == "UnauthorizedOperation":
                raise ServiceUnavailableError(
                    "bedrock",
                    f"Insufficient permissions to access Bedrock in region {region}",
                )
            elif error_code == "EndpointConnectionError":
                # Bedrock might not be available in this region
                self._region_model_cache[region] = []
                return []
            else:
                raise ServiceUnavailableError(
                    "bedrock", f"Bedrock API error in region {region}: {e}"
                )

        except Exception as e:
            logger.error(f"Unexpected error accessing Bedrock in region {region}: {e}")
            raise ServiceUnavailableError(
                "bedrock", f"Unexpected error in region {region}: {e}"
            )
