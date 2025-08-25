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

"""CodeDeploy tools for AWS CI/CD MCP Server."""

import boto3
from awslabs.aws_cicd_mcp_server.core.common.config import AWS_REGION, READ_ONLY_MODE
from awslabs.aws_cicd_mcp_server.core.common.decorators import handle_exceptions
from awslabs.aws_cicd_mcp_server.core.common.utils import paginate_results
from botocore.exceptions import ClientError
from loguru import logger
from pydantic import Field
from typing import Annotated, Dict, List, Optional

@handle_exceptions
async def list_applications(
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION,
    max_items: Annotated[Optional[int], Field(description="Maximum items to return")] = None
) -> Dict:
    """List all CodeDeploy applications in the specified region."""
    client = boto3.client('codedeploy', region_name=region)
    
    applications = paginate_results(
        client, 'list_applications', 'applications', max_items=max_items
    )
    
    return {
        "applications": applications,
        "count": len(applications),
        "region": region
    }

async def get_application_details(
    application_name: Annotated[str, Field(description="Name of the CodeDeploy application")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get detailed information about a specific CodeDeploy application."""
    try:
        client = boto3.client('codedeploy', region_name=region)
        response = client.get_application(applicationName=application_name)
        
        return {
            "application": response.get('application', {}),
            "application_name": application_name
        }
    except ClientError as e:
        logger.error(f"Error getting application details: {e}")
        return {"error": str(e)}

async def list_deployment_groups(
    application_name: Annotated[str, Field(description="Name of the CodeDeploy application")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """List deployment groups for a CodeDeploy application."""
    try:
        client = boto3.client('codedeploy', region_name=region)
        response = client.list_deployment_groups(applicationName=application_name)
        
        deployment_groups = response.get('deploymentGroups', [])
        
        return {
            "application_name": application_name,
            "deployment_groups": deployment_groups,
            "count": len(deployment_groups)
        }
    except ClientError as e:
        logger.error(f"Error listing deployment groups: {e}")
        return {"error": str(e)}

async def create_deployment(
    application_name: Annotated[str, Field(description="Name of the CodeDeploy application")],
    deployment_group_name: Annotated[str, Field(description="Name of the deployment group")],
    s3_location_bucket: Annotated[str, Field(description="S3 bucket containing deployment artifacts")],
    s3_location_key: Annotated[str, Field(description="S3 key for deployment artifacts")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new CodeDeploy deployment."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create deployment."}
    
    try:
        client = boto3.client('codedeploy', region_name=region)
        
        response = client.create_deployment(
            applicationName=application_name,
            deploymentGroupName=deployment_group_name,
            revision={
                'revisionType': 'S3',
                's3Location': {
                    'bucket': s3_location_bucket,
                    'key': s3_location_key
                }
            }
        )
        
        return {
            "deployment_id": response['deploymentId'],
            "application_name": application_name,
            "deployment_group_name": deployment_group_name,
            "status": "Created"
        }
    except ClientError as e:
        logger.error(f"Error creating deployment: {e}")
        return {"error": str(e)}

async def create_application(
    application_name: Annotated[str, Field(description="Name of the CodeDeploy application")],
    compute_platform: Annotated[str, Field(description="Compute platform (Server, Lambda, ECS)", default="Server")] = "Server",
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new CodeDeploy application."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create application."}
    
    try:
        client = boto3.client('codedeploy', region_name=region)
        
        response = client.create_application(
            applicationName=application_name,
            computePlatform=compute_platform
        )
        
        return {
            "application_name": application_name,
            "application_id": response.get('applicationId'),
            "status": "Created"
        }
    except ClientError as e:
        logger.error(f"Error creating application: {e}")
        return {"error": str(e)}

async def create_deployment_group(
    application_name: Annotated[str, Field(description="Name of the CodeDeploy application")],
    deployment_group_name: Annotated[str, Field(description="Name of the deployment group")],
    service_role_arn: Annotated[str, Field(description="Service role ARN for deployments")],
    ec2_tag_key: Annotated[str, Field(description="EC2 tag key for targeting instances")],
    ec2_tag_value: Annotated[str, Field(description="EC2 tag value for targeting instances")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new deployment group."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create deployment group."}
    
    try:
        client = boto3.client('codedeploy', region_name=region)
        
        response = client.create_deployment_group(
            applicationName=application_name,
            deploymentGroupName=deployment_group_name,
            serviceRoleArn=service_role_arn,
            ec2TagFilters=[{
                'Type': 'KEY_AND_VALUE',
                'Key': ec2_tag_key,
                'Value': ec2_tag_value
            }]
        )
        
        return {
            "application_name": application_name,
            "deployment_group_name": deployment_group_name,
            "deployment_group_id": response.get('deploymentGroupId'),
            "status": "Created"
        }
    except ClientError as e:
        logger.error(f"Error creating deployment group: {e}")
        return {"error": str(e)}

async def delete_application(
    application_name: Annotated[str, Field(description="Name of the CodeDeploy application to delete")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Delete a CodeDeploy application."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot delete application."}
    
    try:
        client = boto3.client('codedeploy', region_name=region)
        client.delete_application(applicationName=application_name)
        
        return {
            "application_name": application_name,
            "status": "Deleted"
        }
    except ClientError as e:
        logger.error(f"Error deleting application: {e}")
        return {"error": str(e)}

async def get_deployment_status(
    deployment_id: Annotated[str, Field(description="ID of the deployment")],
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Get the status of a CodeDeploy deployment."""
    try:
        client = boto3.client('codedeploy', region_name=region)
        response = client.get_deployment(deploymentId=deployment_id)
        
        return {
            "deployment_id": deployment_id,
            "deployment_info": response.get('deploymentInfo', {}),
            "region": region
        }
    except ClientError as e:
        logger.error(f"Error getting deployment status: {e}")
        return {"error": str(e)}
