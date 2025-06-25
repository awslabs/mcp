"""
Dynamic data updater for Bedrock model information.

This module handles fetching the latest model data from AWS APIs
when credentials are available, ensuring users always have current
model specifications and pricing information.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
import structlog
from botocore.exceptions import ClientError, NoCredentialsError

from ..models.bedrock import BedrockModel, ModelCapabilities
from ..utils.errors import BedrockAdvisorError

logger = structlog.get_logger(__name__)


class DataUpdateError(BedrockAdvisorError):
    """Raised when data update operations fail."""

    pass


class BedrockDataUpdater:
    """
    Handles dynamic updates of Bedrock model data from AWS APIs.

    This class fetches the latest model information, pricing, and availability
    data from AWS services when credentials are available, falling back to
    static data when necessary.
    """

    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the data updater.

        Args:
            region: AWS region for API calls
        """
        self.region = region
        self.last_update: Optional[datetime] = None
        self.update_interval = timedelta(hours=6)  # Update every 6 hours
        self._cached_models: Optional[Dict[str, BedrockModel]] = None

    async def check_aws_credentials(self) -> bool:
        """
        Check if AWS credentials are available and valid.

        Returns:
            True if credentials are available and valid, False otherwise
        """
        try:
            # Use asyncio to run the sync boto3 call
            loop = asyncio.get_event_loop()
            sts_client = boto3.client("sts", region_name=self.region)

            # Test credentials with get_caller_identity
            await loop.run_in_executor(None, sts_client.get_caller_identity)

            logger.info("AWS credentials validated successfully")
            return True

        except (NoCredentialsError, ClientError) as e:
            logger.info(
                "AWS credentials not available or invalid",
                error=str(e),
                fallback_mode=True,
            )
            return False
        except Exception as e:
            logger.warning(
                "Unexpected error checking AWS credentials",
                error=str(e),
                fallback_mode=True,
            )
            return False

    async def should_update_data(self) -> bool:
        """
        Determine if data should be updated based on last update time.

        Returns:
            True if data should be updated, False otherwise
        """
        if self.last_update is None:
            return True

        time_since_update = datetime.now() - self.last_update
        return time_since_update >= self.update_interval

    async def fetch_foundation_models(self) -> List[Dict[str, Any]]:
        """
        Fetch foundation model information from Bedrock API.

        Returns:
            List of model information dictionaries

        Raises:
            DataUpdateError: If the API call fails
        """
        try:
            loop = asyncio.get_event_loop()
            bedrock_client = boto3.client("bedrock", region_name=self.region)

            logger.info("Fetching foundation models from Bedrock API")

            # Get foundation models
            response = await loop.run_in_executor(
                None, bedrock_client.list_foundation_models
            )

            models = response.get("modelSummaries", [])
            logger.info(f"Retrieved {len(models)} foundation models from API")

            return models

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "Failed to fetch foundation models",
                error_code=error_code,
                error_message=str(e),
            )
            raise DataUpdateError(f"Bedrock API error: {error_code}")

        except Exception as e:
            logger.error("Unexpected error fetching foundation models", error=str(e))
            raise DataUpdateError(f"Unexpected error: {str(e)}")

    async def fetch_model_pricing(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch pricing information for a specific model.

        Note: This is a placeholder for pricing API integration.
        AWS doesn't currently provide a direct pricing API for Bedrock models,
        so this would need to integrate with pricing data sources.

        Args:
            model_id: The model identifier

        Returns:
            Pricing information dictionary or None if not available
        """
        # Placeholder for pricing API integration
        # This could integrate with AWS Price List API or other pricing sources
        logger.debug(f"Pricing fetch not yet implemented for model: {model_id}")
        return None

    def _convert_api_model_to_bedrock_model(
        self, api_model: Dict[str, Any]
    ) -> BedrockModel:
        """
        Convert API model data to BedrockModel instance.

        Args:
            api_model: Model data from Bedrock API

        Returns:
            BedrockModel instance
        """
        model_id = api_model.get("modelId", "")
        model_name = api_model.get("modelName", model_id)

        # Extract capabilities from API response
        inference_types = api_model.get("inferenceTypesSupported", [])
        input_modalities = api_model.get("inputModalities", [])
        output_modalities = api_model.get("outputModalities", [])

        # Create capabilities object with boolean flags
        capabilities = ModelCapabilities(
            text_generation="ON_DEMAND" in inference_types,
            code_generation=False,  # Would need API data to determine
            summarization="ON_DEMAND" in inference_types,
            question_answering="ON_DEMAND" in inference_types,
            translation=False,  # Would need API data to determine
            classification=False,  # Would need API data to determine
            embedding="EMBEDDING" in inference_types,
            multimodal="IMAGE" in input_modalities or "IMAGE" in output_modalities,
            function_calling=False,  # Would need API data to determine
            reasoning="ON_DEMAND" in inference_types,
            mathematics=False,  # Would need API data to determine
            creative="ON_DEMAND" in inference_types,
        )

        # Create BedrockModel instance
        return BedrockModel(
            model_id=model_id,
            model_name=model_name,
            provider_name=api_model.get("providerName", "Unknown"),
            model_arn=api_model.get("modelArn"),
            input_modalities=input_modalities,
            output_modalities=output_modalities,
            response_streaming_supported=True,  # Default assumption
            customizations_supported=api_model.get("customizationsSupported", []),
            inference_types_supported=inference_types,
            max_tokens=self._extract_max_output_tokens(api_model),
            context_length=self._extract_context_length(api_model),
            pricing=None,  # Would be populated from pricing API
            capabilities=capabilities,
            performance=self._estimate_performance(
                model_id, model_name, api_model.get("providerName", "Unknown")
            ),
            availability=self._estimate_availability(api_model),
        )

    def _estimate_performance(
        self, model_id: str, model_name: str, provider_name: str
    ) -> "ModelPerformance":
        """Estimate performance characteristics based on model type."""
        from ..models.bedrock import ModelPerformance

        # Basic performance estimation based on model characteristics
        if "claude" in model_name.lower():
            return ModelPerformance(
                latency_ms=2000, throughput_tokens_per_second=50, accuracy_score=0.9
            )
        elif "titan" in model_name.lower():
            return ModelPerformance(
                latency_ms=1500, throughput_tokens_per_second=75, accuracy_score=0.85
            )
        else:
            return ModelPerformance(
                latency_ms=2500, throughput_tokens_per_second=40, accuracy_score=0.8
            )

    def _estimate_availability(self, api_model: Dict[str, Any]) -> "ModelAvailability":
        """Estimate availability information."""
        from ..models.bedrock import ModelAvailability, ModelStatus

        return ModelAvailability(
            regions=["us-east-1", "us-west-2"],  # Default regions
            status=ModelStatus.ACTIVE,
        )

    def _extract_context_length(self, api_model: Dict[str, Any]) -> int:
        """Extract context length from API model data."""
        # This would parse model-specific context length information
        # For now, return a reasonable default
        return 200000  # Common context length for many models

    def _extract_max_output_tokens(self, api_model: Dict[str, Any]) -> int:
        """Extract max output tokens from API model data."""
        # This would parse model-specific output token limits
        # For now, return a reasonable default
        return 4096  # Common output limit

    async def update_model_data(self) -> Dict[str, BedrockModel]:
        """
        Update model data from AWS APIs.

        Returns:
            Dictionary of updated BedrockModel instances

        Raises:
            DataUpdateError: If the update process fails
        """
        try:
            logger.info("Starting dynamic model data update")

            # Check if we should update
            if not await self.should_update_data():
                logger.info("Model data is still fresh, skipping update")
                return self._cached_models or {}

            # Check AWS credentials
            if not await self.check_aws_credentials():
                logger.info("AWS credentials not available, using fallback data")
                raise DataUpdateError("No valid AWS credentials available")

            # Fetch foundation models
            api_models = await self.fetch_foundation_models()

            # Convert to BedrockModel instances
            updated_models = {}
            for api_model in api_models:
                try:
                    bedrock_model = self._convert_api_model_to_bedrock_model(api_model)
                    updated_models[bedrock_model.model_id] = bedrock_model
                except Exception as e:
                    logger.warning(
                        "Failed to convert API model",
                        model_id=api_model.get("modelId", "unknown"),
                        error=str(e),
                    )
                    continue

            # Update cache and timestamp
            self._cached_models = updated_models
            self.last_update = datetime.now()

            logger.info(
                "Model data update completed successfully",
                models_updated=len(updated_models),
                last_update=self.last_update.isoformat(),
            )

            return updated_models

        except DataUpdateError:
            # Re-raise data update errors
            raise
        except Exception as e:
            logger.error("Unexpected error during model data update", error=str(e))
            raise DataUpdateError(f"Update failed: {str(e)}")

    async def get_updated_models(self) -> Dict[str, BedrockModel]:
        """
        Get updated model data, attempting to fetch from AWS if possible.

        Returns:
            Dictionary of BedrockModel instances (either updated or cached)
        """
        try:
            return await self.update_model_data()
        except DataUpdateError as e:
            logger.info("Failed to update model data, will use fallback", error=str(e))
            # Return cached data if available, otherwise empty dict
            return self._cached_models or {}

    async def _initialize_dynamic_data(self) -> None:
        """Initialize dynamic data in the background."""
        try:
            await self.get_updated_models()
        except Exception as e:
            logger.error("Failed to initialize dynamic data", error=str(e))
