# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""CodeBuild tools for AWS CI/CD MCP Server."""

import boto3
from awslabs.aws_cicd_mcp_server.core.common.config import AWS_REGION, READ_ONLY_MODE
from botocore.exceptions import ClientError
from loguru import logger
from pydantic import Field
from typing import Annotated, Dict, List, Optional

async def list_projects(
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict[str, List[str]]:
    """List all CodeBuild projects in the specified region."""
    try:
        client = boto3.client('codebuild', region_name=region)
        response = client.list_projects()
        
        projects = response.get('projects', [])
        
        return {
            "projects": projects,
            "count": len(projects),
            "region": region
        }
    except ClientError as e:
        logger.error(f"Error listing CodeBuild projects: {e}")
        return {"error": str(e), "projects": []}

async def get_project_details(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get detailed information about a specific CodeBuild project."""
    try:
        client = boto3.client('codebuild', region_name=region)
        response = client.batch_get_projects(names=[project_name])
        
        projects = response.get('projects', [])
        if not projects:
            return {"error": f"Project {project_name} not found"}
        
        return {
            "project": projects[0],
            "project_name": project_name
        }
    except ClientError as e:
        logger.error(f"Error getting project details: {e}")
        return {"error": str(e)}

async def start_build(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project")],
    source_version: Annotated[Optional[str], Field(description="Source version to build")] = None,
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Start a CodeBuild project build."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot start build."}
    
    try:
        client = boto3.client('codebuild', region_name=region)
        
        build_params = {"projectName": project_name}
        if source_version:
            build_params["sourceVersion"] = source_version
            
        response = client.start_build(**build_params)
        
        build = response['build']
        return {
            "build_id": build['id'],
            "project_name": project_name,
            "build_status": build['buildStatus'],
            "start_time": build.get('startTime'),
            "arn": build['arn']
        }
    except ClientError as e:
        logger.error(f"Error starting build: {e}")
        return {"error": str(e)}

async def get_build_logs(
    build_id: Annotated[str, Field(description="CodeBuild build ID")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get build logs for a specific CodeBuild build."""
    try:
        client = boto3.client('codebuild', region_name=region)
        response = client.batch_get_builds(ids=[build_id])
        
        builds = response.get('builds', [])
        if not builds:
            return {"error": f"Build {build_id} not found"}
        
        build = builds[0]
        logs_info = build.get('logs', {})
        
        return {
            "build_id": build_id,
            "logs_location": logs_info.get('groupName'),
            "logs_stream": logs_info.get('streamName'),
            "build_status": build.get('buildStatus'),
            "logs_deep_link": logs_info.get('deepLink')
        }
    except ClientError as e:
        logger.error(f"Error getting build logs: {e}")
        return {"error": str(e)}

async def create_project(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project")],
    service_role: Annotated[str, Field(description="IAM service role ARN")],
    source_location: Annotated[str, Field(description="Source location (repo URL or S3 path)")],
    source_type: Annotated[str, Field(description="Source type", default="CODECOMMIT")] = "CODECOMMIT",
    environment_image: Annotated[str, Field(description="Build environment image", default="aws/codebuild/amazonlinux2-x86_64-standard:5.0")] = "aws/codebuild/amazonlinux2-x86_64-standard:5.0",
    compute_type: Annotated[str, Field(description="Build compute type", default="BUILD_GENERAL1_SMALL")] = "BUILD_GENERAL1_SMALL",
    timeout_minutes: Annotated[int, Field(description="Build timeout in minutes", default=60)] = 60,
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new CodeBuild project with AWS authorized defaults."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create project."}
    
    try:
        from awslabs.aws_cicd_mcp_server.core.common.defaults import get_codebuild_defaults
        
        client = boto3.client('codebuild', region_name=region)
        
        # Get defaults and apply user overrides
        defaults = get_codebuild_defaults()
        
        project_config = {
            "name": project_name,
            "source": {
                "type": source_type,
                "location": source_location,
                "buildspec": defaults["source"]["buildspec"]
            },
            "artifacts": defaults["artifacts"],
            "environment": {
                "type": defaults["environment"]["type"],
                "image": environment_image,
                "computeType": compute_type,
                "privilegedMode": defaults["environment"]["privilegedMode"]
            },
            "serviceRole": service_role,
            "timeoutInMinutes": timeout_minutes,
            "queuedTimeoutInMinutes": defaults["queuedTimeoutInMinutes"],
            "badgeEnabled": defaults["badgeEnabled"],
            "logsConfig": defaults["logsConfig"]
        }
        
        response = client.create_project(**project_config)
        
        return {
            "project_name": project_name,
            "status": "Created",
            "arn": response['project']['arn'],
            "defaults_applied": {
                "environment_image": environment_image,
                "compute_type": compute_type,
                "timeout_minutes": timeout_minutes
            }
        }
    except ClientError as e:
        logger.error(f"Error creating project: {e}")
        return {"error": str(e)}

async def update_project(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project")],
    service_role: Annotated[str, Field(description="IAM service role ARN")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Update an existing CodeBuild project."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot update project."}
    
    try:
        client = boto3.client('codebuild', region_name=region)
        
        response = client.update_project(
            name=project_name,
            serviceRole=service_role
        )
        
        return {
            "project_name": project_name,
            "status": "Updated"
        }
    except ClientError as e:
        logger.error(f"Error updating project: {e}")
        return {"error": str(e)}

async def delete_project(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project to delete")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Delete a CodeBuild project."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot delete project."}
    
    try:
        client = boto3.client('codebuild', region_name=region)
        client.delete_project(name=project_name)
        
        return {
            "project_name": project_name,
            "status": "Deleted"
        }
    except ClientError as e:
        logger.error(f"Error deleting project: {e}")
        return {"error": str(e)}
