"""Tests for AWS FIS FastMCP Server tools."""

import json
import unittest
from unittest.mock import MagicMock, patch

# Import the tools from your module
# This assumes you'll move the tools to a separate module
from aws_fis_mcp.tools import (
    list_experiment_templates,
    get_experiment_template,
    list_experiments,
    get_experiment,
)


class TestFISTools(unittest.TestCase):
    """Test cases for AWS FIS FastMCP Server tools."""

    @patch("boto3.client")
    def test_list_experiment_templates(self, mock_boto_client):
        """Test listing experiment templates."""
        # Setup mock
        mock_fis = MagicMock()
        mock_boto_client.return_value = mock_fis
        mock_fis.list_experiment_templates.return_value = {
            "experimentTemplates": [
                {
                    "id": "template-123",
                    "experimentTemplateId": "test-template",
                    "description": "Test template",
                    "creationTime": "2023-01-01T00:00:00Z",
                    "lastUpdateTime": "2023-01-02T00:00:00Z",
                    "tags": {"Name": "Test"},
                }
            ]
        }

        # Call function
        result = list_experiment_templates()

        # Verify
        mock_boto_client.assert_called_once_with("fis", region_name="us-east-1")
        mock_fis.list_experiment_templates.assert_called_once()
        
        # Parse result and check content
        result_json = json.loads(result)
        self.assertEqual(len(result_json), 1)
        self.assertEqual(result_json[0]["id"], "template-123")
        self.assertEqual(result_json[0]["name"], "test-template")

    @patch("boto3.client")
    def test_get_experiment_template(self, mock_boto_client):
        """Test getting experiment template details."""
        # Setup mock
        mock_fis = MagicMock()
        mock_boto_client.return_value = mock_fis
        mock_fis.get_experiment_template.return_value = {
            "experimentTemplate": {
                "id": "template-123",
                "description": "Test template",
                "targets": {"target1": {"resourceType": "aws:ec2:instance"}},
                "actions": {"action1": {"actionId": "aws:ec2:stop-instances"}},
                "stopConditions": [{"source": "none"}],
                "roleArn": "arn:aws:iam::123456789012:role/FisRole",
                "tags": {"Name": "Test"},
            }
        }

        # Call function
        result = get_experiment_template("template-123")

        # Verify
        mock_boto_client.assert_called_once_with("fis", region_name="us-east-1")
        mock_fis.get_experiment_template.assert_called_once_with(id="template-123")
        
        # Parse result and check content
        result_json = json.loads(result)
        self.assertEqual(result_json["id"], "template-123")
        self.assertEqual(result_json["description"], "Test template")
        self.assertIn("targets", result_json)
        self.assertIn("actions", result_json)

    @patch("boto3.client")
    def test_list_experiments(self, mock_boto_client):
        """Test listing experiments."""
        # Setup mock
        mock_fis = MagicMock()
        mock_boto_client.return_value = mock_fis
        mock_fis.list_experiments.return_value = {
            "experiments": [
                {
                    "id": "experiment-123",
                    "experimentTemplateId": "template-123",
                    "state": {"status": "completed"},
                    "startTime": "2023-01-01T00:00:00Z",
                    "endTime": "2023-01-01T01:00:00Z",
                    "tags": {"Name": "Test"},
                }
            ]
        }

        # Call function
        result = list_experiments()

        # Verify
        mock_boto_client.assert_called_once_with("fis", region_name="us-east-1")
        mock_fis.list_experiments.assert_called_once()
        
        # Parse result and check content
        result_json = json.loads(result)
        self.assertEqual(len(result_json), 1)
        self.assertEqual(result_json[0]["id"], "experiment-123")
        self.assertEqual(result_json[0]["experimentTemplateId"], "template-123")
        self.assertEqual(result_json[0]["state"], "completed")

    @patch("boto3.client")
    def test_get_experiment(self, mock_boto_client):
        """Test getting experiment details."""
        # Setup mock
        mock_fis = MagicMock()
        mock_boto_client.return_value = mock_fis
        mock_fis.get_experiment.return_value = {
            "experiment": {
                "id": "experiment-123",
                "experimentTemplateId": "template-123",
                "state": {"status": "completed"},
                "targets": {"target1": {"resourceType": "aws:ec2:instance"}},
                "actions": {"action1": {"actionId": "aws:ec2:stop-instances"}},
                "startTime": "2023-01-01T00:00:00Z",
                "endTime": "2023-01-01T01:00:00Z",
                "tags": {"Name": "Test"},
            }
        }

        # Call function
        result = get_experiment("experiment-123")

        # Verify
        mock_boto_client.assert_called_once_with("fis", region_name="us-east-1")
        mock_fis.get_experiment.assert_called_once_with(id="experiment-123")
        
        # Parse result and check content
        result_json = json.loads(result)
        self.assertEqual(result_json["id"], "experiment-123")
        self.assertEqual(result_json["experimentTemplateId"], "template-123")
        self.assertIn("state", result_json)
        self.assertIn("targets", result_json)
        self.assertIn("actions", result_json)


if __name__ == "__main__":
    unittest.main()
