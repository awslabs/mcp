"""
Unit tests for containerization API.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from awslabs.ecs_mcp_server.api.containerize import (
    _generate_containerization_guidance,
    containerize_app,
)

# ----------------------------------------------------------------------------
# Basic Containerize App Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_containerize_app():
    """Test containerize_app function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Call containerize_app
        result = await containerize_app(
            app_path=temp_dir,
            port=8000,
        )

        # Verify the result contains expected keys
        assert "container_port" in result
        assert "base_image" in result
        assert "guidance" in result

        # Verify the container port was set to the provided value
        assert result["container_port"] == 8000

        # Verify guidance contains expected sections
        assert "dockerfile_guidance" in result["guidance"]
        assert "docker_compose_guidance" in result["guidance"]
        assert "build_guidance" in result["guidance"]
        assert "run_guidance" in result["guidance"]
        assert "troubleshooting" in result["guidance"]
        assert "next_steps" in result["guidance"]

        # Verify validation guidance is included
        assert "validation_guidance" in result["guidance"]
        assert "hadolint" in result["guidance"]["validation_guidance"]


@pytest.mark.anyio
async def test_containerize_app_default_base_image():
    """Test containerize_app function with default base image."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Call containerize_app with no base_image
        result = await containerize_app(app_path=temp_dir, port=8000)

        # Verify the base image was set to the default value
        assert "public.ecr.aws" in result["base_image"]


# ----------------------------------------------------------------------------
# Path and Port Variation Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_containerize_app_with_different_paths():
    """Test containerize_app with various app path formats."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Absolute path
        result_abs = await containerize_app(app_path=temp_dir, port=8080)

        # Relative path (assuming we're running from the project root)
        rel_path = os.path.relpath(temp_dir)
        result_rel = await containerize_app(app_path=rel_path, port=8080)

        # Path with trailing slash
        result_trailing = await containerize_app(app_path=f"{temp_dir}/", port=8080)

        # All results should contain the same structure
        assert result_abs["container_port"] == 8080
        assert result_rel["container_port"] == 8080
        assert result_trailing["container_port"] == 8080

        # Ensure base image is consistent
        assert "public.ecr.aws" in result_abs["base_image"]
        assert result_abs["base_image"] == result_rel["base_image"]
        assert result_abs["base_image"] == result_trailing["base_image"]


@pytest.mark.anyio
async def test_containerize_app_with_different_ports():
    """Test containerize_app with different port numbers."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with different ports
        ports = [80, 443, 3000, 8080]

        for port in ports:
            result = await containerize_app(app_path=temp_dir, port=port)

            # Verify port is correctly set in result
            assert result["container_port"] == port

            # Verify port is included in run guidance commands
            run_guidance = result["guidance"]["run_guidance"]
            assert f"-p {port}:{port}" in run_guidance["direct_run"]["commands"]["finch"]
            assert f"-p {port}:{port}" in run_guidance["direct_run"]["commands"]["docker"]

            # Verify port is in app access info
            assert f"http://localhost:{port}" in run_guidance["accessing_app"]["description"]

            # Verify port in next steps
            next_steps = result["guidance"]["next_steps"]["steps"]
            assert any(f"http://localhost:{port}" in step for step in next_steps)


# ----------------------------------------------------------------------------
# Content Validation Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_containerize_app_content_validation():
    """Test containerize_app for complete content validation."""
    with tempfile.TemporaryDirectory(prefix="test-app") as temp_dir:
        # Extract expected app name from temp dir
        app_name = os.path.basename(temp_dir).lower()
        port = 8000

        # Call containerize_app
        result = await containerize_app(app_path=temp_dir, port=port)

        # Validate the guidance structure and content
        guidance = result["guidance"]

        # Validate Dockerfile guidance
        assert "dockerfile_guidance" in guidance
        dockerfile_guidance = guidance["dockerfile_guidance"]
        assert "description" in dockerfile_guidance
        assert "base_image" in dockerfile_guidance
        assert "best_practices" in dockerfile_guidance
        assert len(dockerfile_guidance["best_practices"]) >= 5
        assert any(
            "multi-stage builds" in practice for practice in dockerfile_guidance["best_practices"]
        )

        # Validate docker-compose guidance
        assert "docker_compose_guidance" in guidance
        docker_compose_guidance = guidance["docker_compose_guidance"]
        assert "description" in docker_compose_guidance
        assert "best_practices" in docker_compose_guidance
        assert len(docker_compose_guidance["best_practices"]) >= 3

        # Validate build guidance
        assert "build_guidance" in guidance
        build_guidance = guidance["build_guidance"]
        assert "description" in build_guidance
        assert "recommended_tool" in build_guidance
        assert "tool_comparison" in build_guidance
        assert "finch" in build_guidance["tool_comparison"]
        assert "docker" in build_guidance["tool_comparison"]

        # Verify app name in build commands
        assert app_name in build_guidance["tool_comparison"]["finch"]["build_command"]
        assert app_name in build_guidance["tool_comparison"]["docker"]["build_command"]

        # Validate architecture guidance
        assert "architecture_guidance" in build_guidance
        assert "arm64" in build_guidance["architecture_guidance"]["architecture_options"]
        assert "amd64" in build_guidance["architecture_guidance"]["architecture_options"]
        assert (
            app_name
            in build_guidance["architecture_guidance"]["architecture_options"]["arm64"][
                "finch_command"
            ]
        )
        assert (
            app_name
            in build_guidance["architecture_guidance"]["architecture_options"]["arm64"][
                "docker_command"
            ]
        )

        # Validate run guidance
        assert "run_guidance" in guidance
        run_guidance = guidance["run_guidance"]
        assert "description" in run_guidance
        assert "recommended_tool" in run_guidance
        assert "docker_compose" in run_guidance
        assert "direct_run" in run_guidance
        assert "accessing_app" in run_guidance

        # Verify port and app name in run commands
        assert f"-p {port}:{port}" in run_guidance["direct_run"]["commands"]["finch"]
        assert f"-p {port}:{port}" in run_guidance["direct_run"]["commands"]["docker"]
        assert app_name in run_guidance["direct_run"]["commands"]["finch"]
        assert app_name in run_guidance["direct_run"]["commands"]["docker"]
        assert f"http://localhost:{port}" in run_guidance["accessing_app"]["description"]

        # Validate troubleshooting section
        assert "troubleshooting" in guidance
        troubleshooting = guidance["troubleshooting"]
        assert "port_conflicts" in troubleshooting
        assert "build_failures" in troubleshooting
        assert "container_crashes" in troubleshooting
        assert f"Port {port}" in troubleshooting["port_conflicts"]["issue"]

        # Validate next_steps section
        assert "next_steps" in guidance
        next_steps = guidance["next_steps"]
        assert "description" in next_steps
        assert "steps" in next_steps
        assert len(next_steps["steps"]) >= 7


# ----------------------------------------------------------------------------
# Direct Function Tests
# ----------------------------------------------------------------------------


def test_generate_containerization_guidance_directly():
    """Test _generate_containerization_guidance function directly."""
    app_path = "/test/path/my-app"
    port = 5000
    base_image = "test-base-image"

    # Call the private function directly
    guidance = _generate_containerization_guidance(
        app_path=app_path,
        port=port,
        base_image=base_image,
    )

    # Verify the function extracted the correct app name
    app_name = "my-app"

    # Validate build guidance contains the app name
    assert app_name in guidance["build_guidance"]["tool_comparison"]["finch"]["build_command"]
    assert app_name in guidance["build_guidance"]["tool_comparison"]["docker"]["build_command"]

    # Validate port is included in the guidance
    assert f"-p {port}:{port}" in guidance["run_guidance"]["direct_run"]["commands"]["finch"]
    assert f"-p {port}:{port}" in guidance["run_guidance"]["direct_run"]["commands"]["docker"]
    assert f"http://localhost:{port}" in guidance["run_guidance"]["accessing_app"]["description"]

    # Validate next steps include port
    next_steps = guidance["next_steps"]["steps"]
    assert any(f"http://localhost:{port}" in step for step in next_steps)

    # Validate build commands include app name
    # The app name should be in step 4 (index 3)
    assert app_name in next_steps[3]

    # Validate troubleshooting includes port
    assert f"Port {port}" in guidance["troubleshooting"]["port_conflicts"]["issue"]


# ----------------------------------------------------------------------------
# Parameterized Tests
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "app_path,expected_app_name",
    [
        ("/path/to/my-app", "my-app"),
        # Note: Paths with trailing slashes extract empty names
        ("my-app", "my-app"),
        ("./my-app", "my-app"),
        ("/my-app", "my-app"),
        ("/path/to/My-App", "my-app"),  # lowercased
    ],
)
def test_app_name_extraction(app_path, expected_app_name):
    """Test app name extraction from different path formats."""
    port = 8000
    base_image = "test-base-image"

    # Call the function
    guidance = _generate_containerization_guidance(
        app_path=app_path,
        port=port,
        base_image=base_image,
    )

    # Verify app name is correctly extracted and included in guidance
    assert (
        expected_app_name in guidance["build_guidance"]["tool_comparison"]["finch"]["build_command"]
    )
    assert (
        expected_app_name
        in guidance["build_guidance"]["tool_comparison"]["docker"]["build_command"]
    )
    assert (
        expected_app_name
        in guidance["build_guidance"]["architecture_guidance"]["architecture_options"]["arm64"][
            "finch_command"
        ]
    )
    assert expected_app_name in guidance["next_steps"]["steps"][3]


@pytest.mark.parametrize(
    "port",
    [80, 443, 3000, 8080, 5000],
)
def test_port_inclusion(port):
    """Test port is correctly included in guidance for various port numbers."""
    app_path = "/test/path/my-app"
    base_image = "test-base-image"

    # Call the function
    guidance = _generate_containerization_guidance(
        app_path=app_path,
        port=port,
        base_image=base_image,
    )

    # Verify port in run commands
    assert f"-p {port}:{port}" in guidance["run_guidance"]["direct_run"]["commands"]["finch"]
    assert f"-p {port}:{port}" in guidance["run_guidance"]["direct_run"]["commands"]["docker"]

    # Verify port in accessing app
    assert f"http://localhost:{port}" in guidance["run_guidance"]["accessing_app"]["description"]

    # Verify port in troubleshooting
    assert f"Port {port}" in guidance["troubleshooting"]["port_conflicts"]["issue"]

    # Verify port in next steps
    assert any(f"http://localhost:{port}" in step for step in guidance["next_steps"]["steps"])


# ----------------------------------------------------------------------------
# Mock Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_containerize_app_with_mocked_guidance():
    """Test containerize_app with mocked _generate_containerization_guidance."""
    mock_guidance = {
        "test_key": "test_value",
        "another_key": {
            "nested_key": "nested_value",
        },
    }

    with patch(
        "awslabs.ecs_mcp_server.api.containerize._generate_containerization_guidance",
        return_value=mock_guidance,
    ) as mock_generate:
        result = await containerize_app(app_path="/test/path", port=8000)

        # Verify the function was called with correct arguments
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args[1]
        assert call_args["app_path"] == "/test/path"
        assert call_args["port"] == 8000
        assert "public.ecr.aws" in call_args["base_image"]

        # Verify the result contains the mocked guidance
        assert result["guidance"] == mock_guidance
        assert result["container_port"] == 8000


# ----------------------------------------------------------------------------
# Comprehensive Content Tests
# ----------------------------------------------------------------------------


def test_content_validation_for_all_guidance_sections():
    """Test that all expected guidance sections are present and properly formed."""
    app_path = "/test/path/my-app"
    port = 8000
    base_image = "test-base-image"

    # Generate guidance
    guidance = _generate_containerization_guidance(
        app_path=app_path,
        port=port,
        base_image=base_image,
    )

    # Check all expected top-level sections
    expected_sections = [
        "dockerfile_guidance",
        "docker_compose_guidance",
        "validation_guidance",
        "build_guidance",
        "run_guidance",
        "troubleshooting",
        "next_steps",
    ]

    for section in expected_sections:
        assert section in guidance

    # Validate validation_guidance
    validation = guidance["validation_guidance"]
    assert "hadolint" in validation
    assert "description" in validation["hadolint"]
    assert "installation_steps" in validation["hadolint"]
    assert "usage" in validation["hadolint"]
    assert "benefits" in validation["hadolint"]
    assert "common_rules" in validation["hadolint"]
    assert len(validation["hadolint"]["common_rules"]) >= 3

    # Validate build_guidance
    build = guidance["build_guidance"]
    assert "tool_comparison" in build
    assert "finch" in build["tool_comparison"]
    assert "docker" in build["tool_comparison"]
    assert "installation_steps" in build["tool_comparison"]["finch"]
    assert "build_command" in build["tool_comparison"]["finch"]
    assert "installation_steps" in build["tool_comparison"]["docker"]
    assert "build_command" in build["tool_comparison"]["docker"]

    # Validate architecture_guidance
    arch = build["architecture_guidance"]
    assert "architecture_options" in arch
    assert "arm64" in arch["architecture_options"]
    assert "amd64" in arch["architecture_options"]
    assert "description" in arch["architecture_options"]["arm64"]
    assert "finch_command" in arch["architecture_options"]["arm64"]
    assert "docker_command" in arch["architecture_options"]["arm64"]
    assert "benefits" in arch["architecture_options"]["arm64"]

    # Validate troubleshooting
    ts = guidance["troubleshooting"]
    assert "port_conflicts" in ts
    assert "build_failures" in ts
    assert "container_crashes" in ts
    assert "issue" in ts["port_conflicts"]
    assert "solution" in ts["port_conflicts"]
    assert "issue" in ts["build_failures"]
    assert "solutions" in ts["build_failures"]
    assert len(ts["build_failures"]["solutions"]) >= 2

    # Validate next_steps
    ns = guidance["next_steps"]
    assert "steps" in ns
    assert len(ns["steps"]) >= 7
