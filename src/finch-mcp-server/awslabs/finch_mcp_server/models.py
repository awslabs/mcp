"""Pydantic models for the Finch MCP server.

This module defines the data models used for request and response validation
in the Finch MCP server tools.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class BuildImageRequest(BaseModel):
    """Request model for building a container image."""

    dockerfile_path: str = Field(..., description='Absolute path to the Dockerfile')
    context_path: str = Field(..., description='Absolute path to the build context directory')
    tags: Optional[List[str]] = Field(
        None,
        description="List of tags to apply to the image (e.g., ['myimage:latest', 'myimage:v1'])",
    )
    platforms: Optional[List[str]] = Field(
        None, description="List of target platforms (e.g., ['linux/amd64', 'linux/arm64'])"
    )
    target: Optional[str] = Field(None, description='Target build stage to build')
    no_cache: bool = Field(False, description='Whether to disable cache')
    pull: bool = Field(False, description='Whether to always pull base images')
    build_contexts: Optional[List[str]] = Field(
        None, description='List of additional build contexts'
    )
    outputs: Optional[str] = Field(None, description='Output destination')
    cache_from: Optional[List[str]] = Field(None, description='List of external cache sources')
    quiet: bool = Field(False, description='Whether to suppress build output')
    progress: str = Field('auto', description='Type of progress output')


class PushImageRequest(BaseModel):
    """Request model for pushing a container image."""

    image: str = Field(
        ..., description='The full image name to push, including the repository URL and tag'
    )


class CreateEcrRepoRequest(BaseModel):
    """Request model for checking if an ECR repository exists and creating it if it doesn't."""

    app_name: str = Field(
        ..., description='The name of the application/repository to check or create in ECR'
    )


class Result(BaseModel):
    """Base model for operation results."""

    status: str = Field(..., description="Status of the operation ('success', 'error', etc.)")
    message: str = Field(..., description='Descriptive message about the result of the operation')
