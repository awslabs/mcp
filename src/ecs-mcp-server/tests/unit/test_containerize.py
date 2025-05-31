"""
Unit tests for containerization API.
"""

import tempfile
import unittest

import pytest

from awslabs.ecs_mcp_server.api.containerize import containerize_app


class TestContainerize(unittest.TestCase):
    """Tests for containerization API."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app_path = self.temp_dir.name

    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    @pytest.mark.anyio
    async def test_containerize_app(self):
        """Test containerize_app function."""
        # Call containerize_app
        result = await containerize_app(
            app_path=self.app_path,
            port=8000,
        )

        # Verify the result contains expected keys
        self.assertIn("container_port", result)
        self.assertIn("base_image", result)
        self.assertIn("guidance", result)

        # Verify the container port was set to the provided value
        self.assertEqual(result["container_port"], 8000)

        # Verify guidance contains expected sections
        self.assertIn("dockerfile_guidance", result["guidance"])
        self.assertIn("docker_compose_guidance", result["guidance"])
        self.assertIn("build_guidance", result["guidance"])
        self.assertIn("run_guidance", result["guidance"])
        self.assertIn("troubleshooting", result["guidance"])
        self.assertIn("next_steps", result["guidance"])

        # Verify validation guidance is included
        self.assertIn("validation_guidance", result["guidance"])
        self.assertIn("hadolint", result["guidance"]["validation_guidance"])

    @pytest.mark.anyio
    async def test_containerize_app_default_base_image(self):
        """Test containerize_app function with default base image."""
        # Call containerize_app with no base_image
        result = await containerize_app(app_path=self.app_path, port=8000)

        # Verify the base image was set to the default value
        self.assertIn("public.ecr.aws", result["base_image"])


if __name__ == "__main__":
    unittest.main()
