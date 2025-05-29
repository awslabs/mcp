"""
Unit tests for the ARN parser utility.
"""

import unittest

from awslabs.ecs_mcp_server.utils.arn_parser import (
    get_resource_name,
    get_task_definition_name,
    is_ecs_cluster,
    is_ecs_task_definition,
    parse_arn,
)


class TestArnParser(unittest.TestCase):
    """Unit tests for the ARN parser utility."""

    def test_parse_arn_valid(self):
        """Test parsing a valid ECS task definition ARN."""
        arn = "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        parsed = parse_arn(arn)

        self.assertEqual(parsed.partition, "aws")
        self.assertEqual(parsed.service, "ecs")
        self.assertEqual(parsed.region, "us-west-2")
        self.assertEqual(parsed.account, "123456789012")
        self.assertEqual(parsed.resource_type, "task-definition")
        self.assertEqual(parsed.resource_id, "test-app:1")
        self.assertEqual(parsed.resource_name, "1")

    def test_parse_arn_cluster(self):
        """Test parsing a valid ECS cluster ARN."""
        arn = "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"
        parsed = parse_arn(arn)

        self.assertEqual(parsed.resource_type, "cluster")
        self.assertEqual(parsed.resource_id, "test-app-cluster")
        self.assertEqual(parsed.resource_name, "test-app-cluster")

    def test_parse_s3_arn(self):
        """Test parsing an S3 bucket ARN."""
        arn = "arn:aws:s3:::my-bucket"
        parsed = parse_arn(arn)

        self.assertEqual(parsed.service, "s3")
        self.assertEqual(parsed.resource_id, "my-bucket")
        self.assertEqual(parsed.resource_name, "my-bucket")

    def test_parse_invalid_arn(self):
        """Test parsing with invalid ARNs."""
        # None input
        self.assertIsNone(parse_arn(None))

        # Empty string
        self.assertIsNone(parse_arn(""))

        # Invalid format
        self.assertIsNone(parse_arn("not:an:arn"))
        self.assertIsNone(parse_arn("arn:aws:incomplete"))

    def test_get_task_definition_name(self):
        """Test getting task definition name from ARN."""
        # Valid task definition ARN
        arn = "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        self.assertEqual(get_task_definition_name(arn), "1")

        # Not a task definition ARN
        not_task_def = "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"
        self.assertIsNone(get_task_definition_name(not_task_def))

        # Invalid ARN
        self.assertIsNone(get_task_definition_name("not-an-arn"))

    def test_is_ecs_task_definition(self):
        """Test checking if an ARN represents an ECS task definition."""
        # Valid task definition ARN
        arn = "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        self.assertTrue(is_ecs_task_definition(arn))

        # Not a task definition ARN
        not_task_def = "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"
        self.assertFalse(is_ecs_task_definition(not_task_def))

        # Different service
        not_ecs = "arn:aws:s3:::my-bucket"
        self.assertFalse(is_ecs_task_definition(not_ecs))

        # Invalid ARN
        self.assertFalse(is_ecs_task_definition("not-an-arn"))

    def test_is_ecs_cluster(self):
        """Test checking if an ARN represents an ECS cluster."""
        # Valid cluster ARN
        arn = "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"
        self.assertTrue(is_ecs_cluster(arn))

        # Not a cluster ARN
        not_cluster = "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        self.assertFalse(is_ecs_cluster(not_cluster))

        # Different service
        not_ecs = "arn:aws:s3:::my-bucket"
        self.assertFalse(is_ecs_cluster(not_ecs))

        # Invalid ARN
        self.assertFalse(is_ecs_cluster("not-an-arn"))

    def test_get_resource_name(self):
        """Test getting resource name from various ARN types."""
        # Task definition ARN
        task_def_arn = "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        self.assertEqual(get_resource_name(task_def_arn), "1")

        # Cluster ARN
        cluster_arn = "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"
        self.assertEqual(get_resource_name(cluster_arn), "test-app-cluster")

        # S3 bucket ARN
        s3_arn = "arn:aws:s3:::my-bucket"
        self.assertEqual(get_resource_name(s3_arn), "my-bucket")

        # Invalid ARN
        self.assertIsNone(get_resource_name("not-an-arn"))
