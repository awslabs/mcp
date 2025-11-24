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

"""
Express Mode module for ECS MCP Server.
This module provides tools for ECS Express Mode deployments.
"""

from typing import Any, Dict, Optional

from fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.express import (
    build_and_push_image_to_ecr,
    delete_app,
    validate_prerequisites,
    wait_for_service_ready,
)

# Expose API functions at module level for security wrapper in main.py
build_and_push_image_to_ecr = build_and_push_image_to_ecr
delete_app = delete_app
wait_for_service_ready = wait_for_service_ready


def register_module(mcp: FastMCP) -> None:
    """Register Express Mode module tools with the MCP server."""

    @mcp.tool(name="build_and_push_image_to_ecr")
    async def mcp_build_and_push_image_to_ecr(
        app_name: str = Field(
            ...,
            description="Name of the application (used for ECR repository and stack names)",
        ),
        app_path: str = Field(
            ...,
            description=(
                "Absolute file path to the web application directory containing the Dockerfile"
            ),
        ),
        tag: Optional[str] = Field(
            default=None,
            description="Optional image tag (if None, uses epoch timestamp)",
        ),
    ) -> Dict[str, Any]:
        """
        Creates ECR infrastructure and builds/pushes a Docker image to ECR.

        This tool automates the complete ECR setup and image deployment process:
        1. Creates ECR repository via CloudFormation
        2. Creates IAM role with ECR push/pull permissions
        3. Builds Docker image from your application
        4. Pushes image to ECR

        ## Parameters:
        - Required: app_name (Application name, 1-20 chars, lowercase letters/digits/hyphens only)
        - Required: app_path (Path to application directory with Dockerfile)
        - Optional: tag (Image tag, defaults to epoch timestamp)

        ## Prerequisites:
        - Docker installed and running locally
        - Dockerfile exists in the application directory
        - AWS credentials configured with appropriate permissions

        ## Returns:
        Dictionary containing:
        - repository_uri: ECR repository URI
        - image_tag: The tag of the pushed image
        - full_image_uri: Complete image URI with tag (use this for deployment)
        - ecr_push_pull_role_arn: ARN of the IAM role created for ECR access
        - stack_name: Name of the CloudFormation stack created

        ## Usage Examples:
        ```
        # Build and push with auto-generated tag
        build_and_push_image_to_ecr(
            app_name="my-app",
            app_path="/home/user/my-flask-app"
        )

        # Build and push with specific tag
        build_and_push_image_to_ecr(
            app_name="my-app",
            app_path="/home/user/my-flask-app",
            tag="v1.0.0"
        )
        ```

        Returns:
        ```
        {
          "repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app-repo",
          "image_tag": "1700000000",
          "full_image_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app-repo:1700000000",
          "ecr_push_pull_role_arn": "arn:aws:iam::123456789012:role/my-app-ecr-push-pull-role",
          "stack_name": "my-app-ecr-infrastructure"
        }
        ```
        """
        return await build_and_push_image_to_ecr(app_name=app_name, app_path=app_path, tag=tag)

    @mcp.tool(name="validate_ecs_express_mode_prerequisites")
    async def mcp_validate_ecs_express_mode_prerequisites(
        image_uri: str = Field(
            ...,
            description=(
                "Full ECR image URI with tag "
                "(e.g., 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:tag)"
            ),
        ),
        execution_role_arn: Optional[str] = Field(
            default=None,
            description=(
                "Optional ARN of the ECS task execution role (defaults to ecsTaskExecutionRole)"
            ),
        ),
        infrastructure_role_arn: Optional[str] = Field(
            default=None,
            description=(
                "Optional ARN of the infrastructure role for Express Gateway "
                "(defaults to ecsInfrastructureRoleForExpressServices)"
            ),
        ),
    ) -> Dict[str, Any]:
        """
        Validates prerequisites for ECS Express Mode deployment.

        This tool checks that all required resources exist and are properly configured
        before deploying an ECS Express Gateway Service.

        ## Validation Checks:
        1. Task Execution Role exists (checks default 'ecsTaskExecutionRole' if not provided)
        2. Infrastructure Role exists (checks default 'ecsInfrastructureRoleForExpressServices'
           if not provided)
        3. Docker image exists in the specified ECR repository

        ## Parameters:
        - Required: image_uri (Full ECR image URI including tag)
        - Optional: execution_role_arn (ARN of task execution role,
          defaults to 'ecsTaskExecutionRole')
        - Optional: infrastructure_role_arn (ARN of infrastructure role,
          defaults to 'ecsInfrastructureRoleForExpressServices')

        ## Required IAM Roles:

        ### Task Execution Role:
        - Allows ECS tasks to pull images and write logs
        - Must have trust policy for ecs-tasks.amazonaws.com
        - Should have AmazonECSTaskExecutionRolePolicy attached

        ### Infrastructure Role:
        - Allows ECS to provision infrastructure
        - Must have trust policy for ecs.amazonaws.com
        - Should have AmazonECSInfrastructureRoleforExpressGatewayServices attached

        ## Returns:
        Dictionary containing:
        - valid: Boolean indicating if all prerequisites are met
        - errors: List of error messages if validation fails
        - warnings: List of warning messages
        - details: Detailed validation results for each check

        ## Usage Examples:
        ```
        # Validate with default role names
        validate_ecs_express_mode_prerequisites(
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:1700000000"
        )

        # Validate with custom role ARNs
        validate_ecs_express_mode_prerequisites(
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:1700000000",
            execution_role_arn="arn:aws:iam::123456789012:role/custom-execution-role",
            infrastructure_role_arn="arn:aws:iam::123456789012:role/custom-infra-role"
        )
        ```

        Returns when successful:
        ```
        {
          "valid": true,
          "errors": [],
          "warnings": [],
          "details": {
            "execution_role": {
              "status": "valid",
              "arn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
              "name": "ecsTaskExecutionRole",
              "message": "Task Execution Role is valid"
            },
            "infrastructure_role": {
              "status": "valid",
              "arn": "arn:aws:iam::123456789012:role/ecsInfrastructureRoleForExpressServices",
              "name": "ecsInfrastructureRoleForExpressServices",
              "message": "Infrastructure Role is valid"
            },
            "image": {
              "status": "exists",
              "uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:1700000000",
              "repository": "my-app",
              "tag": "1700000000",
              "message": "Image found in ECR"
            }
          }
        }
        ```

        Returns when validation fails:
        ```
        {
          "valid": false,
          "errors": [
            "Infrastructure Role not found: "
            "arn:aws:iam::123456789012:role/ecsInfrastructureRoleForExpressServices"
          ],
          "warnings": [],
          "details": {
            "execution_role": {"status": "valid", ...},
            "infrastructure_role": {"status": "not_found", ...},
            "image": {"status": "exists", ...}
          }
        }
        ```
        """
        return await validate_prerequisites(
            image_uri=image_uri,
            execution_role_arn=execution_role_arn,
            infrastructure_role_arn=infrastructure_role_arn,
        )

    @mcp.tool(name="delete_app")
    async def mcp_delete_app(
        service_arn: str = Field(
            ...,
            description="ARN of the Express Gateway Service to delete",
        ),
        app_name: str = Field(
            ...,
            description="Name of the application (used to identify ECR stack to delete)",
        ),
    ) -> Dict[str, Any]:
        """
        Deletes a complete Express Mode deployment including service and ECR infrastructure.

        This tool performs complete cleanup of an Express Mode deployment:
        1. Deletes the Express Gateway Service
        2. Deletes the ECR CloudFormation stack (ECR repository + IAM role)

        ## Parameters:
        - Required: service_arn (ARN of Express Gateway Service)
        - Required: app_name (Application name used during deployment)

        ## What Gets Deleted:
        - Express Gateway Service and all provisioned infrastructure
          (ALB, target groups, security groups)
        - CloudFormation stack for ECR resources, including ECR repo and container images

        ## Returns:
        Dictionary containing:
        - service_deletion: Status and details of service deletion
        - ecr_deletion: Status and details of ECR stack deletion
        - summary: Overall deletion summary with list of deleted resources
        - errors: List of any errors encountered

        ## Usage Examples:
        ```
        # Delete complete deployment
        delete_app(
            service_arn="arn:aws:ecs:us-west-2:123456789012:express-service/my-api",
            app_name="my-app"
        )
        ```

        Returns on success:
        ```
        {
          "service_deletion": {
            "status": "deleted",
            "service_arn": "arn:aws:ecs:us-west-2:123456789012:express-service/my-api",
            "message": "Express Gateway Service deleted successfully"
          },
          "ecr_deletion": {
            "status": "deleted",
            "stack_name": "my-app-ecr-infrastructure",
            "message": "ECR stack deleted successfully",
            "deleted_resources": [
              "ECR repository: my-app-repo",
              "IAM role: my-app-ecr-push-pull-role"
            ]
          },
          "summary": {
            "status": "success",
            "message": "Successfully deleted Express Mode deployment for my-app",
            "deleted_resources": [
              "Express Gateway Service: arn:aws:ecs:...",
              "ECR repository: my-app-repo",
              "IAM role: my-app-ecr-push-pull-role"
            ]
          },
          "errors": []
        }
        ```

        ## Important Notes:
        - This operation requires WRITE permission (ALLOW_WRITE=true)
        - Deletion is irreversible - all container images will be deleted
        - Service deletion may take a few minutes as infrastructure is deprovisioned
        - If errors occur, partial deletion is possible (check summary for details)
        """
        return await delete_app(service_arn=service_arn, app_name=app_name)

    @mcp.tool(name="wait_for_service_ready")
    async def mcp_wait_for_service_ready(
        cluster: str = Field(
            ...,
            description="Name of the ECS cluster",
        ),
        service_name: str = Field(
            ...,
            description="Name of the ECS service",
        ),
        timeout_seconds: int = Field(
            default=300,
            description="Maximum time to wait in seconds (default: 300 = 5 minutes)",
        ),
    ) -> Dict[str, Any]:
        """
        Waits for ECS tasks in a service to reach RUNNING status.

        This tool polls the service every 10 seconds to check if tasks are running.
        It will wait up to the specified timeout before returning a timeout status.

        ## Parameters:
        - Required: cluster (ECS cluster name)
        - Required: service_name (ECS service name)
        - Optional: timeout_seconds (Max wait time, defaults to 300 seconds)

        ## Returns:
        Dictionary containing:
        - status: "success" if tasks are running, "timeout" if timeout reached,
          "failed" if an error occurred
        - message: Human-readable status message

        ## Usage Examples:
        ```
        # Wait for service with default 5-minute timeout
        wait_for_service_ready(
            cluster="my-cluster",
            service_name="my-service"
        )

        # Wait for service with custom timeout
        wait_for_service_ready(
            cluster="my-cluster",
            service_name="my-service",
            timeout_seconds=600
        )
        ```

        Returns on success:
        ```
        {
          "status": "success",
          "message": "Service is ready with 2 running task(s)"
        }
        ```

        Returns on timeout:
        ```
        {
          "status": "timeout",
          "message": "Timeout after 300s - service not ready"
        }
        ```
        """
        return await wait_for_service_ready(
            cluster=cluster, service_name=service_name, timeout_seconds=timeout_seconds
        )
