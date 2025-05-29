"""
API for containerizing web applications.

This module provides guidance on how to containerize web applications
with best practices for Docker image building and container runtime selection.
"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def containerize_app(
    app_path: str,
    port: int,
) -> Dict[str, Any]:
    """
    Provides guidance for containerizing a web application.

    This function provides guidance on how to build Docker images for web applications,
    including recommendations for base images, build tools, and architecture choices.
    It does not generate Dockerfile or docker-compose.yml files.

    Args:
        app_path: Path to the web application directory
        port: Port the application listens on

    Returns:
        Dict containing containerization guidance
    """
    logger.info(f"Generating containerization guidance for web application at {app_path}")

    base_image = (
        "Slim Docker Library Images from public.ecr.aws "
        "(eg public.ecr.aws/docker/library/node:20.19.2-slim)"
    )

    # Create guidance for building and running the container
    containerization_guidance = _generate_containerization_guidance(
        app_path=app_path,
        port=port,
        base_image=base_image,
    )

    return {
        "container_port": port,
        "base_image": base_image,
        "guidance": containerization_guidance,
    }


def _generate_containerization_guidance(
    app_path: str,
    port: int,
    base_image: str,
) -> Dict[str, Any]:
    """
    Generates guidance for building and running the container.

    Provides recommendations for container tools, architecture choices,
    and troubleshooting steps.
    """

    app_name = os.path.basename(app_path).lower()

    # Generate guidance for creating Dockerfile
    dockerfile_guidance = {
        "description": "How to create a Dockerfile for your application",
        "base_image": base_image,
        "best_practices": [
            "Use multi-stage builds to reduce image size",
            "Install only production dependencies",
            "Use npm install instead of npm ci for node and express applications"
            "Remove unnecessary files and build artifacts",
            "Use specific versions for base images instead of 'latest'",
            "Run as a non-root user for security",
            "Use Hadolint to validate your Dockerfile (see validation guidance)",
        ],
    }

    # Generate guidance for creating docker-compose.yml
    docker_compose_guidance = {
        "description": "How to create a docker-compose.yml file for local testing",
        "best_practices": [
            "Use environment variables for configuration",
            "Define volumes for persistent data",
            "Set resource limits for containers",
            "Use health checks to ensure services are running correctly",
        ],
    }

    # Generate guidance
    guidance = {
        "dockerfile_guidance": dockerfile_guidance,
        "docker_compose_guidance": docker_compose_guidance,
        "validation_guidance": {
            "description": "How to validate your Dockerfile",
            "hadolint": {
                "description": (
                    "Hadolint is a Dockerfile linter that helps identify issues "
                    "and enforce best practices"
                ),
                "installation_steps": [
                    "Using Homebrew: brew install hadolint",
                    "Using Docker: docker pull hadolint/hadolint",
                    "Or download from https://github.com/hadolint/hadolint/releases",
                ],
                "usage": [
                    "Direct usage: hadolint Dockerfile",
                    "Using Docker: docker run --rm -i hadolint/hadolint < Dockerfile",
                ],
                "benefits": [
                    "Identifies common mistakes in Dockerfiles",
                    "Enforces best practices for more efficient containers",
                    "Integrates with CI/CD pipelines for automated validation",
                    "Helps create more secure and optimized containers",
                ],
                "common_rules": [
                    "DL3006: Always tag the version of an image explicitly",
                    "DL3008: Pin versions in apt-get install",
                    "DL3025: Use COPY instead of ADD for files and folders",
                    "DL3059: Multiple consecutive RUNs should be combined",
                ],
            },
        },
        "build_guidance": {
            "description": "How to build the Docker image for your application",
            "recommended_tool": "finch",
            "tool_comparison": {
                "finch": {
                    "description": (
                        "Finch is a container runtime that's compatible with Docker "
                        "and recommended for AWS workloads"
                    ),
                    "installation_steps": [
                        "Visit https://github.com/runfinch/finch/releases",
                        "Download the latest release for your platform",
                        "Follow the installation instructions in the README",
                    ],
                    "benefits": [
                        "Native support for both ARM64 and x86_64 architectures",
                        "No Docker Desktop license required for commercial use",
                        "Optimized for AWS deployments",
                        "Better performance for local development",
                        "Simplified container management",
                    ],
                    "build_command": f"finch build -t {app_name}:<image_version> .",
                },
                "docker": {
                    "description": "Docker is the standard container runtime",
                    "installation_steps": [
                        "Visit https://docs.docker.com/get-docker/",
                        "Download Docker Desktop for your platform",
                        "Follow the installation instructions",
                    ],
                    "note": (
                        "Docker Desktop requires a paid license for commercial use "
                        "in larger organizations"
                    ),
                    "build_command": f"docker build -t {app_name}:<image_version> .",
                },
            },
            "architecture_guidance": {
                "description": "Building for different CPU architectures",
                "recommended_architecture": "arm64",
                "architecture_options": {
                    "arm64": {
                        "description": "ARM64 (Apple Silicon, AWS Graviton)",
                        "finch_command": (
                            f"finch build --platform linux/arm64 -t {app_name}:<image_version> ."
                        ),
                        "docker_command": (
                            f"docker build --platform linux/arm64 -t {app_name}:<image_version> ."
                        ),
                        "benefits": [
                            "Better performance on ARM-based systems",
                            "Lower cost on AWS Graviton instances",
                        ],
                    },
                    "amd64": {
                        "description": "AMD64/x86_64 (Intel/AMD)",
                        "finch_command": (
                            f"finch build --platform linux/amd64 -t {app_name}:<image_version> ."
                        ),
                        "docker_command": (
                            f"docker build --platform linux/amd64 -t {app_name}:<image_version> ."
                        ),
                        "benefits": ["Wider compatibility with existing systems"],
                    },
                },
            },
        },
        "run_guidance": {
            "description": "How to run your containerized application locally",
            "recommended_tool": "finch",
            "recommended_command": "finch compose up",
            "docker_compose": {
                "description": "Using docker-compose for local testing (recommended)",
                "commands": {"finch": "finch compose up", "docker": "docker-compose up"},
                "benefits": [
                    "Simulates a production-like environment",
                    "Easy to configure environment variables",
                    "Supports multi-container applications",
                ],
            },
            "direct_run": {
                "description": "Running the container directly",
                "commands": {
                    "finch": f"finch run -p {port}:{port} {app_name}:<image_version>",
                    "docker": f"docker run -p {port}:{port} {app_name}:<image_version>",
                },
            },
            "accessing_app": {
                "description": f"Your application will be available at http://localhost:{port}"
            },
        },
        "troubleshooting": {
            "description": "Common issues and solutions",
            "port_conflicts": {
                "issue": f"Port {port} is already in use",
                "solution": (
                    "Change the port mapping in docker-compose.yml or use a different "
                    "port with the -p flag"
                ),
            },
            "build_failures": {
                "issue": "Image fails to build",
                "solutions": [
                    "Check the Dockerfile for syntax errors",
                    "Ensure all required files are in the correct location",
                    "Verify that the base image is compatible with your application",
                ],
            },
            "container_crashes": {
                "issue": "Container exits immediately after starting",
                "solutions": [
                    "Check the container logs with 'docker logs' or 'finch logs'",
                    "Ensure the CMD or ENTRYPOINT is correctly specified",
                    "Verify that all required environment variables are set",
                ],
            },
        },
        "next_steps": {
            "description": "Steps to containerize and deploy your application",
            "steps": [
                "1. Create a Dockerfile using the dockerfile_guidance above",
                "2. Create a docker-compose.yml file using the docker_compose_guidance above",
                "3. (Optional) If hadolint is installed, validate your Dockerfile: "
                "hadolint Dockerfile",
                "4. Build your container image using Finch if installed: finch build -t "
                + app_name
                + ":<version> ., or Docker if Finch is not available: docker build -t "
                + app_name
                + ":<version> .",
                "5. Run your containerized application using Finch if installed: finch compose up, "
                "or Docker if Finch is not available: docker-compose up",
                "6. Verify your application works correctly at http://localhost:" + str(port),
                "7. Identify appropriate health check paths by examining your application's routes "
                "or file structure - look for endpoints like /health, /status, /ping, "
                "or root path / that return HTTP 200 responses",
                "8. Use the create_ecs_infrastructure tool to deploy your application to AWS ECS "
                "with forceDeploy=False if you want to review the architecture first, or "
                "forceDeploy=True if you are prototyping and have your AWS profile set up in the "
                "ECS MCP Server. forceDeploy=True must be done sequentially: steps 1,2,3.",
            ],
        },
    }

    return guidance
