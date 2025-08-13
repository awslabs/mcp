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
from botocore.exceptions import ClientError
from loguru import logger
from pydantic import Field
from typing import Annotated, Dict, List

async def list_pipelines(
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict[str, List[str]]:
    """List all CodePipeline pipelines in the specified region."""
    try:
        client = boto3.client('codepipeline', region_name=region)
        response = client.list_pipelines()
        
        pipelines = [pipeline['name'] for pipeline in response.get('pipelines', [])]
        
        return {
            "pipelines": pipelines,
            "count": len(pipelines),
            "region": region
        }
    except ClientError as e:
        logger.error(f"Error listing pipelines: {e}")
        return {"error": str(e), "pipelines": []}

async def get_pipeline_details(
    pipeline_name: Annotated[str, Field(description="Name of the CodePipeline pipeline")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get detailed information about a specific CodePipeline pipeline."""
    try:
        client = boto3.client('codepipeline', region_name=region)
        
        pipeline_response = client.get_pipeline(name=pipeline_name)
        state_response = client.get_pipeline_state(name=pipeline_name)
        
        return {
            "pipeline": pipeline_response['pipeline'],
            "state": state_response,
            "metadata": pipeline_response.get('metadata', {})
        }
    except ClientError as e:
        logger.error(f"Error getting pipeline details: {e}")
        return {"error": str(e)}

async def start_pipeline_execution(
    pipeline_name: Annotated[str, Field(description="Name of the CodePipeline pipeline to start")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Start execution of a CodePipeline pipeline."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot start pipeline execution."}
    
    try:
        client = boto3.client('codepipeline', region_name=region)
        response = client.start_pipeline_execution(name=pipeline_name)
        
        return {
            "pipeline_execution_id": response['pipelineExecutionId'],
            "pipeline_name": pipeline_name,
            "status": "Started"
        }
    except ClientError as e:
        logger.error(f"Error starting pipeline execution: {e}")
        return {"error": str(e)}

async def get_pipeline_execution_history(
    pipeline_name: Annotated[str, Field(description="Name of the CodePipeline pipeline")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get execution history for a CodePipeline pipeline."""
    try:
        client = boto3.client('codepipeline', region_name=region)
        response = client.list_pipeline_executions(pipelineName=pipeline_name)
        
        return {
            "pipeline_name": pipeline_name,
            "executions": response.get('pipelineExecutionSummaries', []),
            "region": region
        }
    except ClientError as e:
        logger.error(f"Error getting pipeline execution history: {e}")
        return {"error": str(e)}

async def create_pipeline(
    pipeline_name: Annotated[str, Field(description="Name of the pipeline to create")],
    role_arn: Annotated[str, Field(description="IAM role ARN for the pipeline")],
    artifact_store_bucket: Annotated[str, Field(description="S3 bucket for artifacts")],
    source_repo: Annotated[str, Field(description="Source repository name")],
    source_branch: Annotated[str, Field(description="Source branch", default="main")] = "main",
    pipeline_type: Annotated[str, Field(description="Pipeline type", default="V2")] = "V2",
    execution_mode: Annotated[str, Field(description="Execution mode", default="QUEUED")] = "QUEUED",
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new CodePipeline pipeline with AWS authorized defaults."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create pipeline."}
    
    try:
        from awslabs.aws_cicd_mcp_server.core.common.defaults import get_codepipeline_defaults
        
        client = boto3.client('codepipeline', region_name=region)
        
        # Get defaults
        defaults = get_codepipeline_defaults()
        
        pipeline_definition = {
            "name": pipeline_name,
            "roleArn": role_arn,
            "artifactStore": {
                "type": "S3",
                "location": artifact_store_bucket
            },
            "pipelineType": pipeline_type,
            "executionMode": execution_mode,
            "stages": [
                {
                    "name": "Source",
                    "actions": [{
                        "name": "SourceAction",
                        "actionTypeId": {
                            "category": "Source",
                            "owner": "AWS",
                            "provider": defaults["source"]["provider"],
                            "version": defaults["source"]["version"]
                        },
                        "configuration": {
                            "RepositoryName": source_repo,
                            "BranchName": source_branch,
                            "OutputArtifactFormat": defaults["source"]["outputFormat"]
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
            "pipeline_arn": response.get('pipeline', {}).get('name'),
            "defaults_applied": {
                "pipeline_type": pipeline_type,
                "execution_mode": execution_mode,
                "source_branch": source_branch
            }
        }
    except ClientError as e:
        logger.error(f"Error creating pipeline: {e}")
        return {"error": str(e)}

async def update_pipeline(
    pipeline_name: Annotated[str, Field(description="Name of the pipeline to update")],
    role_arn: Annotated[str, Field(description="IAM role ARN for the pipeline")],
    artifact_store_bucket: Annotated[str, Field(description="S3 bucket for artifacts")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Update an existing CodePipeline pipeline."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot update pipeline."}
    
    try:
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
    except ClientError as e:
        logger.error(f"Error updating pipeline: {e}")
        return {"error": str(e)}

async def delete_pipeline(
    pipeline_name: Annotated[str, Field(description="Name of the pipeline to delete")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Delete a CodePipeline pipeline."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot delete pipeline."}
    
    try:
        client = boto3.client('codepipeline', region_name=region)
        client.delete_pipeline(name=pipeline_name)
        
        return {
            "pipeline_name": pipeline_name,
            "status": "Deleted"
        }
    except ClientError as e:
        logger.error(f"Error deleting pipeline: {e}")
        return {"error": str(e)}


