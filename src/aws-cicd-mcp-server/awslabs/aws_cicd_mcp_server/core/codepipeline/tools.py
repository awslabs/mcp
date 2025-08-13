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

"""CodePipeline tools for AWS CI/CD MCP Server."""

import boto3
from awslabs.aws_cicd_mcp_server.core.common.config import AWS_REGION, READ_ONLY_MODE
from awslabs.aws_cicd_mcp_server.core.common.decorators import handle_exceptions
from awslabs.aws_cicd_mcp_server.core.common.utils import paginate_results, validate_iam_role, validate_s3_bucket
from pydantic import Field
from typing import Annotated, Dict, List, Optional

@handle_exceptions
async def list_pipelines(
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION,
    max_items: Annotated[Optional[int], Field(description="Maximum items to return")] = None
) -> Dict:
    """List all CodePipeline pipelines in the specified region with pagination."""
    client = boto3.client('codepipeline', region_name=region)
    
    pipelines = paginate_results(
        client, 'list_pipelines', 'pipelines', max_items=max_items
    )
    
    return {
        "pipelines": [p['name'] for p in pipelines],
        "count": len(pipelines),
        "region": region
    }

@handle_exceptions
async def get_pipeline_details(
    pipeline_name: Annotated[str, Field(description="Name of the CodePipeline pipeline")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get detailed information about a specific CodePipeline pipeline."""
    client = boto3.client('codepipeline', region_name=region)
    
    pipeline_response = client.get_pipeline(name=pipeline_name)
    state_response = client.get_pipeline_state(name=pipeline_name)
    
    return {
        "pipeline": pipeline_response['pipeline'],
        "state": state_response,
        "metadata": pipeline_response.get('metadata', {})
    }

@handle_exceptions
async def start_pipeline_execution(
    pipeline_name: Annotated[str, Field(description="Name of the CodePipeline pipeline to start")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Start execution of a CodePipeline pipeline."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot start pipeline execution."}
    
    client = boto3.client('codepipeline', region_name=region)
    response = client.start_pipeline_execution(name=pipeline_name)
    
    return {
        "pipeline_execution_id": response['pipelineExecutionId'],
        "pipeline_name": pipeline_name,
        "status": "Started"
    }

@handle_exceptions
async def get_pipeline_execution_history(
    pipeline_name: Annotated[str, Field(description="Name of the CodePipeline pipeline")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION,
    max_items: Annotated[Optional[int], Field(description="Maximum items to return")] = None
) -> Dict:
    """Get execution history for a CodePipeline pipeline with pagination."""
    client = boto3.client('codepipeline', region_name=region)
    
    executions = paginate_results(
        client, 'list_pipeline_executions', 'pipelineExecutionSummaries',
        pipelineName=pipeline_name, max_items=max_items
    )
    
    return {
        "pipeline_name": pipeline_name,
        "executions": executions,
        "region": region
    }

@handle_exceptions
async def create_pipeline(
    pipeline_name: Annotated[str, Field(description="Name of the pipeline to create")],
    role_arn: Annotated[str, Field(description="IAM role ARN for the pipeline")],
    artifact_store_bucket: Annotated[str, Field(description="S3 bucket for artifacts")],
    source_repo: Annotated[str, Field(description="Source repository name")],
    source_branch: Annotated[str, Field(description="Source branch", default="main")] = "main",
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new CodePipeline pipeline with resource validation."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create pipeline."}
    
    # Validate dependencies
    if not await validate_iam_role(role_arn, region):
        return {"error": f"IAM role {role_arn} not found or not accessible"}
    
    if not await validate_s3_bucket(artifact_store_bucket, region):
        return {"error": f"S3 bucket {artifact_store_bucket} not found or not accessible"}
    
    client = boto3.client('codepipeline', region_name=region)
    
    pipeline_definition = {
        "name": pipeline_name,
        "roleArn": role_arn,
        "artifactStore": {
            "type": "S3",
            "location": artifact_store_bucket
        },
        "stages": [
            {
                "name": "Source",
                "actions": [{
                    "name": "SourceAction",
                    "actionTypeId": {
                        "category": "Source",
                        "owner": "AWS",
                        "provider": "CodeCommit",
                        "version": "1"
                    },
                    "configuration": {
                        "RepositoryName": source_repo,
                        "BranchName": source_branch
                    },
                    "outputArtifacts": [{"name": "SourceOutput"}]
                }]
            }
        ]
    }
    
    response = client.create_pipeline(pipeline=pipeline_definition)
    
    return {
        "pipeline_name": pipeline_name,
        "status": "Created",
        "pipeline_arn": response.get('pipeline', {}).get('name')
    }

@handle_exceptions
async def update_pipeline(
    pipeline_name: Annotated[str, Field(description="Name of the pipeline to update")],
    role_arn: Annotated[str, Field(description="IAM role ARN for the pipeline")],
    artifact_store_bucket: Annotated[str, Field(description="S3 bucket for artifacts")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Update an existing CodePipeline pipeline with validation."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot update pipeline."}
    
    # Validate dependencies
    if not await validate_iam_role(role_arn, region):
        return {"error": f"IAM role {role_arn} not found or not accessible"}
    
    if not await validate_s3_bucket(artifact_store_bucket, region):
        return {"error": f"S3 bucket {artifact_store_bucket} not found or not accessible"}
    
    client = boto3.client('codepipeline', region_name=region)
    
    # Get existing pipeline
    existing = client.get_pipeline(name=pipeline_name)
    pipeline_def = existing['pipeline']
    
    # Update basic properties
    pipeline_def['roleArn'] = role_arn
    pipeline_def['artifactStore']['location'] = artifact_store_bucket
    
    response = client.update_pipeline(pipeline=pipeline_def)
    
    return {
        "pipeline_name": pipeline_name,
        "status": "Updated"
    }

@handle_exceptions
async def delete_pipeline(
    pipeline_name: Annotated[str, Field(description="Name of the pipeline to delete")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Delete a CodePipeline pipeline."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot delete pipeline."}
    
    client = boto3.client('codepipeline', region_name=region)
    client.delete_pipeline(name=pipeline_name)
    
    return {
        "pipeline_name": pipeline_name,
        "status": "Deleted"
    }


