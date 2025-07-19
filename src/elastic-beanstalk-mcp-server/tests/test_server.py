"""Tests for the AWS Elastic Beanstalk MCP Server."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from awslabs.elastic_beanstalk_mcp_server.main import (
    list_applications,
    describe_application,
    list_environments,
    describe_environment,
    create_application,
    create_environment,
)


class TestElasticBeanstalkMCPServer(unittest.TestCase):
    """Test cases for the AWS Elastic Beanstalk MCP Server."""

    @patch("awslabs.elastic_beanstalk_mcp_server.main.get_eb_client")
    def test_list_applications(self, mock_get_client):
        """Test listing applications."""
        # Mock the Elastic Beanstalk client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock the response
        mock_client.describe_applications.return_value = {
            "Applications": [
                {
                    "ApplicationName": "test-app",
                    "Description": "Test application",
                    "DateCreated": "2023-01-01T00:00:00Z",
                    "DateUpdated": "2023-01-01T00:00:00Z",
                }
            ]
        }
        
        # Create a mock context
        ctx = MagicMock()
        
        # Call the function
        result = list_applications(ctx)
        
        # Verify the result
        self.assertIn("applications", result)
        self.assertEqual(len(result["applications"]), 1)
        self.assertEqual(result["applications"][0]["ApplicationName"], "test-app")
        
        # Verify the client was called correctly
        mock_client.describe_applications.assert_called_once()

    @patch("awslabs.elastic_beanstalk_mcp_server.main.get_eb_client")
    def test_describe_application(self, mock_get_client):
        """Test describing an application."""
        # Mock the Elastic Beanstalk client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock the response
        mock_client.describe_applications.return_value = {
            "Applications": [
                {
                    "ApplicationName": "test-app",
                    "Description": "Test application",
                    "DateCreated": "2023-01-01T00:00:00Z",
                    "DateUpdated": "2023-01-01T00:00:00Z",
                }
            ]
        }
        
        # Create a mock context
        ctx = MagicMock()
        
        # Call the function
        result = describe_application(ctx, "test-app")
        
        # Verify the result
        self.assertIn("application", result)
        self.assertEqual(result["application"]["ApplicationName"], "test-app")
        
        # Verify the client was called correctly
        mock_client.describe_applications.assert_called_once_with(ApplicationNames=["test-app"])

    @patch("awslabs.elastic_beanstalk_mcp_server.main.get_eb_client")
    def test_list_environments(self, mock_get_client):
        """Test listing environments."""
        # Mock the Elastic Beanstalk client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock the response
        mock_client.describe_environments.return_value = {
            "Environments": [
                {
                    "EnvironmentName": "test-env",
                    "EnvironmentId": "e-abcdef123456",
                    "ApplicationName": "test-app",
                    "Status": "Ready",
                    "Health": "Green",
                }
            ]
        }
        
        # Create a mock context
        ctx = MagicMock()
        
        # Call the function
        result = list_environments(ctx, "test-app")
        
        # Verify the result
        self.assertIn("environments", result)
        self.assertEqual(len(result["environments"]), 1)
        self.assertEqual(result["environments"][0]["EnvironmentName"], "test-env")
        
        # Verify the client was called correctly
        mock_client.describe_environments.assert_called_once_with(ApplicationName="test-app")

    @patch("awslabs.elastic_beanstalk_mcp_server.main.get_eb_client")
    def test_create_application(self, mock_get_client):
        """Test creating an application."""
        # Mock the Elastic Beanstalk client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock the response
        mock_client.create_application.return_value = {
            "Application": {
                "ApplicationName": "new-app",
                "Description": "New application",
                "DateCreated": "2023-01-01T00:00:00Z",
                "DateUpdated": "2023-01-01T00:00:00Z",
            }
        }
        
        # Create a mock context
        ctx = MagicMock()
        
        # Call the function
        result = create_application(ctx, "new-app", "New application")
        
        # Verify the result
        self.assertIn("application", result)
        self.assertEqual(result["application"]["ApplicationName"], "new-app")
        
        # Verify the client was called correctly
        mock_client.create_application.assert_called_once_with(
            ApplicationName="new-app", Description="New application"
        )


if __name__ == "__main__":
    unittest.main()