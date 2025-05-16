"""
Pydantic models for the Finch MCP server.

This module defines the data models used for request and response validation
in the Finch MCP server tools.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BuildImageRequest(BaseModel):
    """Request model for building a container image."""
    
    dockerfile_path: str = Field(
        ..., 
        description="Absolute path to the Dockerfile"
    )
    context_path: str = Field(
        ..., 
        description="Absolute path to the build context directory"
    )
    tags: Optional[List[str]] = Field(
        None, 
        description="List of tags to apply to the image (e.g., ['myimage:latest', 'myimage:v1'])"
    )
    platforms: Optional[List[str]] = Field(
        None, 
        description="List of target platforms (e.g., ['linux/amd64', 'linux/arm64'])"
    )
    target: Optional[str] = Field(
        None, 
        description="Target build stage to build"
    )
    no_cache: bool = Field(
        False, 
        description="Whether to disable cache"
    )
    pull: bool = Field(
        False, 
        description="Whether to always pull base images"
    )
    add_hosts: Optional[List[str]] = Field(
        None, 
        description="List of custom host-to-IP mappings"
    )
    allow: Optional[List[str]] = Field(
        None, 
        description="List of extra privileged entitlements"
    )
    build_contexts: Optional[List[str]] = Field(
        None, 
        description="List of additional build contexts"
    )
    outputs: Optional[str] = Field(
        None, 
        description="Output destination"
    )
    cache_from: Optional[List[str]] = Field(
        None, 
        description="List of external cache sources"
    )
    cache_to: Optional[List[str]] = Field(
        None, 
        description="List of cache export destinations"
    )
    quiet: bool = Field(
        False, 
        description="Whether to suppress build output"
    )
    progress: str = Field(
        "auto", 
        description="Type of progress output"
    )


class PushImageRequest(BaseModel):
    """Request model for pushing a container image."""
    
    image: str = Field(
        ..., 
        description="The full image name to push, including the repository URL and tag"
    )


class Result(BaseModel):
    """Base model for operation results."""
    
    status: str = Field(
        ..., 
        description="Status of the operation ('success', 'error', etc.)"
    )
    message: str = Field(
        ..., 
        description="Descriptive message about the result of the operation"
    )
    stdout: Optional[str] = Field(
        None, 
        description="Standard output from the command if successful"
    )
    stderr: Optional[str] = Field(
        None, 
        description="Standard error output if the command failed"
    )
