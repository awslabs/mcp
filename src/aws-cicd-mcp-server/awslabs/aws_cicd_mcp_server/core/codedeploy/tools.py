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
from botocore.exceptions import ClientError
from loguru import logger
from pydantic import Field
from typing import Annotated, Dict, List

async def list_applications(
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict[str, List[str]]:
    """List all CodeDeploy applications in the specified region."""
    try:
        client = boto3.client('codedeploy', region_name=region)
        response = client.list_applications()
        
        applications = response.get('applications', [])
        
        return {
            "applications": applications,
            "count": len(applications),
            "region": region
        }
    except ClientError as e:
        logger.error(f"Error listing CodeDeploy applications: {e}")
        return {"error": str(e), "applications": []}

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
    deployment_config_name: Annotated[str, Field(description="Deployment configuration name")] = None,
    auto_rollback_enabled: Annotated[bool, Field(description="Enable auto rollback", default=True)] = True,
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new CodeDeploy deployment with AWS authorized defaults."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create deployment."}
    
    try:
        from awslabs.aws_cicd_mcp_server.core.common.defaults import get_codedeploy_defaults, get_deployment_config_name
        
        client = boto3.client('codedeploy', region_name=region)
        
        # Get defaults
        defaults = get_codedeploy_defaults()
        
        # If no deployment config specified, use default for Server platform
        if not deployment_config_name:
            deployment_config_name = get_deployment_config_name("Server")
        
        deployment_params = {
            "applicationName": application_name,
            "deploymentGroupName": deployment_group_name,
            "revision": {
                "revisionType": defaults["revision"]["revisionType"],
                "s3Location": {
                    "bucket": s3_location_bucket,
                    "key": s3_location_key
                }
            },
            "deploymentConfigName": deployment_config_name
        }
        
        if auto_rollback_enabled:
            deployment_params["autoRollbackConfiguration"] = defaults["autoRollbackConfiguration"]
        
        response = client.create_deployment(**deployment_params)
        
        return {
            "deployment_id": response['deploymentId'],
            "application_name": application_name,
            "deployment_group_name": deployment_group_name,
            "status": "Created",
            "defaults_applied": {
                "deployment_config_name": deployment_config_name,
                "auto_rollback_enabled": auto_rollback_enabled
            }
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
    deployment_config_name: Annotated[str, Field(description="Deployment configuration name")] = None,
    deployment_type: Annotated[str, Field(description="Deployment type", default="IN_PLACE")] = "IN_PLACE",
    region: Annotated[str, Field(description="AWS region", default=AWS_REGION)] = AWS_REGION
) -> Dict:
    """Create a new deployment group with AWS authorized defaults."""
    if READ_ONLY_MODE:
        return {"error": "Server is in read-only mode. Cannot create deployment group."}
    
    try:
        from awslabs.aws_cicd_mcp_server.core.common.defaults import get_codedeploy_defaults, get_deployment_config_name
        
        client = boto3.client('codedeploy', region_name=region)
        
        # Get defaults
        defaults = get_codedeploy_defaults()
        
        # If no deployment config specified, use default for Server platform
        if not deployment_config_name:
            deployment_config_name = get_deployment_config_name("Server")
        
        deployment_group_params = {
            "applicationName": application_name,
            "deploymentGroupName": deployment_group_name,
            "serviceRoleArn": service_role_arn,
            "deploymentConfigName": deployment_config_name,
            "ec2TagFilters": [{
                "Type": defaults["ec2TagFilters"]["type"],
                "Key": ec2_tag_key,
                "Value": ec2_tag_value
            }],
            "deploymentStyle": {
                "deploymentType": deployment_type,
                "deploymentOption": defaults["deploymentStyle"]["deploymentOption"]
            },
            "autoRollbackConfiguration": defaults["autoRollbackConfiguration"]
        }
        
        response = client.create_deployment_group(**deployment_group_params)
        
        return {
            "application_name": application_name,
            "deployment_group_name": deployment_group_name,
            "deployment_group_id": response.get('deploymentGroupId'),
            "status": "Created",
            "defaults_applied": {
                "deployment_config_name": deployment_config_name,
                "deployment_type": deployment_type,
                "auto_rollback_enabled": True
            }
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
