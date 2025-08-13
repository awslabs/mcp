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
from awslabs.aws_cicd_mcp_server.core.common.decorators import handle_exceptions
from awslabs.aws_cicd_mcp_server.core.common.utils import paginate_results, validate_iam_role
from pydantic import Field
from typing import Annotated, Dict, List, Optional

@handle_exceptions
async def list_projects(
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION,
    max_items: Annotated[Optional[int], Field(description="Maximum items to return")] = None
) -> Dict:
    """List all CodeBuild projects in the specified region with pagination."""
    client = boto3.client('codebuild', region_name=region)
    
    projects = paginate_results(
        client, 'list_projects', 'projects', max_items=max_items
    )
    
    return {
        "projects": projects,
        "count": len(projects),
        "region": region
    }

@handle_exceptions
async def get_project_details(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get detailed information about a specific CodeBuild project."""
    client = boto3.client('codebuild', region_name=region)
    response = client.batch_get_projects(names=[project_name])
    
    projects = response.get('projects', [])
    if not projects:
        return {"error": f"Project {project_name} not found"}
    
    return {
        "project": projects[0],
        "project_name": project_name
    }

@handle_exceptions
async def start_build(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project")],
    source_version: Annotated[Optional[str], Field(description="Source version to build")] = None,
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Start a CodeBuild project build."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot start build."}
    
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

@handle_exceptions
async def get_build_logs(
    build_id: Annotated[str, Field(description="CodeBuild build ID")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get build logs for a specific CodeBuild build with actual log content."""
    client = boto3.client('codebuild', region_name=region)
    response = client.batch_get_builds(ids=[build_id])
    
    builds = response.get('builds', [])
    if not builds:
        return {"error": f"Build {build_id} not found"}
    
    build = builds[0]
    logs_info = build.get('logs', {})
    
    # Try to fetch actual log content
    log_content = None
    if logs_info.get('groupName') and logs_info.get('streamName'):
        try:
            logs_client = boto3.client('logs', region_name=region)
            log_response = logs_client.get_log_events(
                logGroupName=logs_info['groupName'],
                logStreamName=logs_info['streamName']
            )
            log_content = [event['message'] for event in log_response.get('events', [])]
        except Exception:
            log_content = "Log content not accessible"
    
    return {
        "build_id": build_id,
        "logs_location": logs_info.get('groupName'),
        "logs_stream": logs_info.get('streamName'),
        "build_status": build.get('buildStatus'),
        "logs_deep_link": logs_info.get('deepLink'),
        "log_content": log_content
    }

@handle_exceptions
async def create_project(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project")],
    service_role: Annotated[str, Field(description="IAM service role ARN")],
    source_location: Annotated[str, Field(description="Source location (repo URL or S3 path)")],
    source_type: Annotated[str, Field(description="Source type (CODECOMMIT, GITHUB, S3)", default="CODECOMMIT")] = "CODECOMMIT",
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new CodeBuild project with validation."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create project."}
    
    # Validate IAM role
    if not await validate_iam_role(service_role, region):
        return {"error": f"IAM role {service_role} not found or not accessible"}
    
    client = boto3.client('codebuild', region_name=region)
    
    project_config = {
        "name": project_name,
        "source": {
            "type": source_type,
            "location": source_location
        },
        "artifacts": {
            "type": "NO_ARTIFACTS"
        },
        "environment": {
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/amazonlinux2-x86_64-standard:3.0",
            "computeType": "BUILD_GENERAL1_SMALL"
        },
        "serviceRole": service_role
    }
    
    response = client.create_project(**project_config)
    
    return {
        "project_name": project_name,
        "status": "Created",
        "arn": response['project']['arn']
    }

@handle_exceptions
async def update_project(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project")],
    service_role: Annotated[str, Field(description="IAM service role ARN")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Update an existing CodeBuild project with validation."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot update project."}
    
    # Validate IAM role
    if not await validate_iam_role(service_role, region):
        return {"error": f"IAM role {service_role} not found or not accessible"}
    
    client = boto3.client('codebuild', region_name=region)
    
    response = client.update_project(
        name=project_name,
        serviceRole=service_role
    )
    
    return {
        "project_name": project_name,
        "status": "Updated"
    }

@handle_exceptions
async def delete_project(
    project_name: Annotated[str, Field(description="Name of the CodeBuild project to delete")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Delete a CodeBuild project."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot delete project."}
    
    client = boto3.client('codebuild', region_name=region)
    client.delete_project(name=project_name)
    
    return {
        "project_name": project_name,
        "status": "Deleted"
    }
