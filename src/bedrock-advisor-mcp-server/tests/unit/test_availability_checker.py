"""
Unit tests for the AvailabilityChecker class.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from awslabs.bedrock_advisor_mcp_server.services.availability_checker import AvailabilityChecker
from awslabs.bedrock_advisor_mcp_server.utils.errors import RegionNotSupportedError


class TestAvailabilityChecker(unittest.TestCase):
    """Test cases for the AvailabilityChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.checker = AvailabilityChecker()
        self.regions = [
            {"region_name": "us-east-1", "region_display_name": "US East (N. Virginia)", "is_active": True},
            {"region_name": "us-west-2", "region_display_name": "US West (Oregon)", "is_active": True},
        ]
        self.checker.bedrock_regions = self.regions

    def test_get_bedrock_regions(self):
        """Test the get_bedrock_regions method."""
        regions = self.checker.get_bedrock_regions()
        self.assertEqual(len(regions), 2)
        self.assertEqual(regions[0]["region_name"], "us-east-1")
        self.assertEqual(regions[1]["region_name"], "us-west-2")

    @patch('bedrock_advisor.services.availability_checker.AvailabilityChecker._get_models_in_region')
    def test_check_model_availability_with_valid_regions(self, mock_get_models):
        """Test check_model_availability with valid regions."""
        # Mock the _get_models_in_region method
        mock_get_models.return_value = ["model1", "model2", "model3"]

        # Run the test
        result = asyncio.run(self.checker.check_model_availability("model1", ["us-east-1", "us-west-2"]))

        # Verify the result
        self.assertEqual(result["model_id"], "model1")
        self.assertEqual(len(result["availability"]), 2)
        self.assertEqual(result["available_regions_count"], 2)
        self.assertEqual(result["total_regions_checked"], 2)
        self.assertEqual(result["availability_percentage"], 100.0)

        # Verify the availability details
        for item in result["availability"]:
            self.assertIn(item["region"], ["us-east-1", "us-west-2"])
            self.assertTrue(item["is_available"])
            self.assertEqual(item["status"], "ACTIVE")

    @patch('bedrock_advisor.services.availability_checker.AvailabilityChecker._get_models_in_region')
    def test_check_model_availability_with_unavailable_model(self, mock_get_models):
        """Test check_model_availability with a model that's not available in any region."""
        # Mock the _get_models_in_region method
        mock_get_models.return_value = ["model2", "model3"]

        # Run the test
        result = asyncio.run(self.checker.check_model_availability("model1", ["us-east-1", "us-west-2"]))

        # Verify the result
        self.assertEqual(result["model_id"], "model1")
        self.assertEqual(len(result["availability"]), 2)
        self.assertEqual(result["available_regions_count"], 0)
        self.assertEqual(result["total_regions_checked"], 2)
        self.assertEqual(result["availability_percentage"], 0.0)

        # Verify the availability details
        for item in result["availability"]:
            self.assertIn(item["region"], ["us-east-1", "us-west-2"])
            self.assertFalse(item["is_available"])
            self.assertEqual(item["status"], "ACTIVE")

    def test_check_model_availability_with_invalid_region(self):
        """Test check_model_availability with an invalid region."""
        with self.assertRaises(RegionNotSupportedError):
            asyncio.run(self.checker.check_model_availability("model1", ["invalid-region"]))

    @patch('bedrock_advisor.services.availability_checker.AvailabilityChecker._get_models_in_region')
    def test_check_region_availability_with_specific_models(self, mock_get_models):
        """Test check_region_availability with specific models."""
        # Mock the _get_models_in_region method
        mock_get_models.return_value = ["model1", "model2", "model3"]

        # Run the test
        result = asyncio.run(self.checker.check_region_availability("us-east-1", ["model1", "model4"]))

        # Verify the result
        self.assertEqual(result["region"], "us-east-1")
        self.assertEqual(result["region_display_name"], "US East (N. Virginia)")
        self.assertEqual(result["available_models_count"], 3)
        self.assertEqual(len(result["models"]), 2)

        # Verify the models details
        model1 = next((m for m in result["models"] if m["model_id"] == "model1"), None)
        model4 = next((m for m in result["models"] if m["model_id"] == "model4"), None)

        self.assertIsNotNone(model1)
        self.assertIsNotNone(model4)
        self.assertTrue(model1["is_available"])
        self.assertFalse(model4["is_available"])
        self.assertEqual(model1["status"], "ACTIVE")
        self.assertEqual(model4["status"], "NOT_AVAILABLE")

    def test_check_region_availability_with_invalid_region(self):
        """Test check_region_availability with an invalid region."""
        with self.assertRaises(RegionNotSupportedError):
            asyncio.run(self.checker.check_region_availability("invalid-region"))

    @patch('bedrock_advisor.services.availability_checker.AvailabilityChecker._get_models_in_region')
    def test_compare_model_availability(self, mock_get_models):
        """Test compare_model_availability."""
        # Mock the _get_models_in_region method
        mock_get_models.return_value = ["model1", "model2"]

        # Run the test
        result = asyncio.run(self.checker.compare_model_availability(["model1", "model2"]))

        # Verify the result
        self.assertEqual(result["models_compared"], 2)
        self.assertEqual(result["regions_checked"], 2)
        self.assertEqual(len(result["common_regions"]), 2)
        self.assertEqual(result["common_regions_count"], 2)

        # Verify the model comparison
        self.assertIn("model1", result["model_comparison"])
        self.assertIn("model2", result["model_comparison"])

        for model_id in ["model1", "model2"]:
            model_data = result["model_comparison"][model_id]
            self.assertEqual(len(model_data["available_regions"]), 2)
            self.assertEqual(model_data["available_regions_count"], 2)
            self.assertEqual(model_data["availability_percentage"], 100.0)

        # Verify the region comparison
        for region in ["us-east-1", "us-west-2"]:
            self.assertIn(region, result["region_comparison"])
            region_data = result["region_comparison"][region]
            self.assertIn("models", region_data)
            self.assertIn("model1", region_data["models"])
            self.assertIn("model2", region_data["models"])
            self.assertTrue(region_data["models"]["model1"]["is_available"])
            self.assertTrue(region_data["models"]["model2"]["is_available"])

    def test_compare_model_availability_with_empty_list(self):
        """Test compare_model_availability with an empty list."""
        with self.assertRaises(ValueError):
            asyncio.run(self.checker.compare_model_availability([]))

    @patch('boto3.client')
    def test_get_models_in_region_success(self, mock_boto3_client):
        """Test _get_models_in_region with successful API call."""
        # Mock the boto3 client
        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {"modelId": "model1"},
                {"modelId": "model2"},
                {"modelId": "model3"}
            ]
        }
        mock_boto3_client.return_value = mock_client

        # Run the test
        result = asyncio.run(self.checker._get_models_in_region("us-east-1"))

        # Verify the result
        self.assertEqual(len(result), 3)
        self.assertIn("model1", result)
        self.assertIn("model2", result)
        self.assertIn("model3", result)

        # Verify the cache
        self.assertIn("us-east-1", self.checker._region_model_cache)
        self.assertEqual(len(self.checker._region_model_cache["us-east-1"]), 3)

    @patch('boto3.client')
    def test_get_models_in_region_with_client_error(self, mock_boto3_client):
        """Test _get_models_in_region with ClientError."""
        # Mock the boto3 client to raise ClientError
        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = Exception("Test error")
        mock_boto3_client.return_value = mock_client

        # Run the test and expect an exception
        with self.assertRaises(Exception):
            asyncio.run(self.checker._get_models_in_region("us-east-1"))


@pytest.mark.asyncio
async def test_check_model_availability_async():
    """Test check_model_availability using pytest-asyncio."""
    checker = AvailabilityChecker()
    checker.bedrock_regions = [
        {"region_name": "us-east-1", "region_display_name": "US East (N. Virginia)", "is_active": True},
        {"region_name": "us-west-2", "region_display_name": "US West (Oregon)", "is_active": True},
    ]

    # Mock the _check_model_in_region method
    checker._check_model_in_region = AsyncMock(return_value=(True, "ACTIVE"))

    # Run the test
    result = await checker.check_model_availability("model1", ["us-east-1"])

    # Verify the result
    assert result["model_id"] == "model1"
    assert len(result["availability"]) == 1
    assert result["available_regions_count"] == 1
    assert result["total_regions_checked"] == 1
    assert result["availability_percentage"] == 100.0


@pytest.mark.asyncio
async def test_check_region_availability_async():
    """Test check_region_availability using pytest-asyncio."""
    checker = AvailabilityChecker()
    checker.bedrock_regions = [
        {"region_name": "us-east-1", "region_display_name": "US East (N. Virginia)", "is_active": True},
        {"region_name": "us-west-2", "region_display_name": "US West (Oregon)", "is_active": True},
    ]

    # Mock the _get_models_in_region method
    checker._get_models_in_region = AsyncMock(return_value=["model1", "model2", "model3"])

    # Run the test
    result = await checker.check_region_availability("us-east-1")

    # Verify the result
    assert result["region"] == "us-east-1"
    assert result["region_display_name"] == "US East (N. Virginia)"
    assert result["available_models_count"] == 3
    assert len(result["models"]) == 3

    # Verify all models are available
    for model in result["models"]:
        assert model["is_available"] is True
        assert model["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_compare_model_availability_async():
    """Test compare_model_availability using pytest-asyncio."""
    checker = AvailabilityChecker()
    checker.bedrock_regions = [
        {"region_name": "us-east-1", "region_display_name": "US East (N. Virginia)", "is_active": True},
        {"region_name": "us-west-2", "region_display_name": "US West (Oregon)", "is_active": True},
    ]

    # Mock the _check_model_in_region method
    checker._check_model_in_region = AsyncMock(return_value=(True, "ACTIVE"))

    # Run the test
    result = await checker.compare_model_availability(["model1", "model2"])

    # Verify the result
    assert result["models_compared"] == 2
    assert result["regions_checked"] == 2
    assert len(result["common_regions"]) == 2
    assert result["common_regions_count"] == 2

    # Verify the model comparison
    assert "model1" in result["model_comparison"]
    assert "model2" in result["model_comparison"]

    # Verify the region comparison
    for region in ["us-east-1", "us-west-2"]:
        assert region in result["region_comparison"]
        assert "models" in result["region_comparison"][region]
        assert "model1" in result["region_comparison"][region]["models"]
        assert "model2" in result["region_comparison"][region]["models"]
        assert result["region_comparison"][region]["models"]["model1"]["is_available"] is True
        assert result["region_comparison"][region]["models"]["model2"]["is_available"] is True
