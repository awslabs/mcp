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
API for ECS Express Mode operations.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.api.infrastructure import (
    create_ecr_infrastructure,
    prepare_template_files,
)
from awslabs.ecs_mcp_server.utils.aws import (
    check_ecr_image_exists,
    check_iam_role_exists_and_policy,
    get_aws_account_id,
    get_aws_client,
)
from awslabs.ecs_mcp_server.utils.docker import build_and_push_image
from awslabs.ecs_mcp_server.utils.security import validate_app_name

logger = logging.getLogger(__name__)


async def build_and_push_image_to_ecr(
    app_name: str, app_path: str, tag: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates ECR infrastructure and build & pushes an image to ECR.

    This function:
    1. Creates ECR repository and push/pull IAM role via CloudFormation
    2. Builds Docker image from your application
    3. Pushes image to the created ECR repository

    Args:
        app_name: Name of the application (used for ECR repo and stack names)
        app_path: Path to the application directory containing the Dockerfile
        tag: Optional image tag (if None, uses epoch timestamp)

    Returns:
        Dictionary containing:
            - repository_uri: ECR repository URI
            - image_tag: The tag of the pushed image
            - full_image_uri: Complete image URI with tag
            - ecr_push_pull_role_arn: ARN of the IAM role for ECR push/pull
            - stack_name: Name of the CloudFormation stack created

    Raises:
        RuntimeError: If Docker build or push fails
        FileNotFoundError: If Dockerfile is not found
    """
    logger.info(f"Creating ECR infrastructure and building image for {app_name}")

    try:
        validate_app_name(app_name)

        # Step 1: Create ECR repository infrastructure via CloudFormation
        logger.info("🏭 Creating ECR repository infrastructure...")

        # Get template content
        template_files = prepare_template_files(app_name, app_path)
        ecr_template_content = template_files["ecr_template_content"]

        # Create ECR infrastructure
        ecr_result = await create_ecr_infrastructure(
            app_name=app_name, template_content=ecr_template_content
        )

        ecr_repo_uri = ecr_result["resources"]["ecr_repository_uri"]
        ecr_role_arn = ecr_result["resources"]["ecr_push_pull_role_arn"]

        logger.info(f"✓ ECR repository created: {ecr_repo_uri}")
        logger.info(f"✓ ECR push/pull role created: {ecr_role_arn}")

        # Step 2: Build and push Docker image
        logger.info("🐳 Building and pushing Docker image...")
        image_tag = await build_and_push_image(
            app_path=app_path, repository_uri=ecr_repo_uri, tag=tag, role_arn=ecr_role_arn
        )

        # Construct the full image URI
        full_image_uri = f"{ecr_repo_uri}:{image_tag}"

        logger.info(f"✓ Docker image pushed with tag: {image_tag}")
        logger.info(f"✅ Successfully built and pushed image: {full_image_uri}")

        return {
            "repository_uri": ecr_repo_uri,
            "image_tag": image_tag,
            "full_image_uri": full_image_uri,
            "ecr_push_pull_role_arn": ecr_role_arn,
            "stack_name": ecr_result["stack_name"],
        }

    except Exception as e:
        logger.error(f"Error building and pushing image: {e}")
        raise


async def validate_prerequisites(
    image_uri: str,
    execution_role_arn: Optional[str] = None,
    infrastructure_role_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates prerequisites for ECS Express Mode deployment.

    Checks:
    1. Task Execution Role exists (checks default 'ecsTaskExecutionRole' if ARN not provided)
    2. Infrastructure Role exists (checks default 'ecsInfrastructureRoleForExpressServices'
       if ARN not provided)
    3. Image exists in ECR

    Args:
        image_uri: Full ECR image URI
            (e.g., 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:tag)
        execution_role_arn: Optional ARN of the task execution role
            (defaults to 'ecsTaskExecutionRole')
        infrastructure_role_arn: Optional ARN of the infrastructure role
            (defaults to 'ecsInfrastructureRoleForExpressServices')

    Returns:
        Dictionary containing:
            - valid: Boolean indicating if all prerequisites are met
            - errors: List of error messages if validation fails
            - warnings: List of warning messages
            - details: Dictionary with detailed validation results
    """
    logger.info("Validating ECS Express Mode prerequisites")

    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    # Get account ID for constructing default role ARNs
    account_id = await get_aws_account_id()

    # Use default role names if not provided
    if not execution_role_arn:
        execution_role_arn = f"arn:aws:iam::{account_id}:role/ecsTaskExecutionRole"
        logger.info(f"Using default task execution role: {execution_role_arn}")

    if not infrastructure_role_arn:
        infrastructure_role_arn = (
            f"arn:aws:iam::{account_id}:role/ecsInfrastructureRoleForExpressServices"
        )
        logger.info(f"Using default infrastructure role: {infrastructure_role_arn}")

    # Check Task Execution Role (only check existence, not permissions)
    exec_role_details = await check_iam_role_exists_and_policy(
        role_arn=execution_role_arn,
        expected_service_principal="ecs-tasks.amazonaws.com",
        role_type="Task Execution Role",
    )
    details["execution_role"] = exec_role_details
    if exec_role_details.get("status") != "valid":
        errors.append(exec_role_details.get("error", "Task Execution Role validation failed"))

    # Check Infrastructure Role (only check existence, not permissions)
    infra_role_details = await check_iam_role_exists_and_policy(
        role_arn=infrastructure_role_arn,
        expected_service_principal="ecs.amazonaws.com",
        role_type="Infrastructure Role",
    )
    details["infrastructure_role"] = infra_role_details
    if infra_role_details.get("status") != "valid":
        errors.append(infra_role_details.get("error", "Infrastructure Role validation failed"))

    # Check if image exists in ECR
    image_details = await check_ecr_image_exists(image_uri)
    details["image"] = image_details
    if image_details.get("status") != "exists":
        errors.append(image_details.get("error", "Image validation failed"))

    result = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }

    if result["valid"]:
        logger.info("✅ All prerequisites validated successfully")
    else:
        logger.warning(f"❌ Prerequisite validation failed with {len(errors)} error(s)")

    return result


async def delete_express_gateway_service(service_arn: str) -> Dict[str, Any]:
    """
    Deletes an Express Gateway Service.

    Args:
        service_arn: ARN of the Express Gateway Service to delete

    Returns:
        Dictionary containing deletion status and details
    """
    logger.info(f"Deleting Express Gateway Service: {service_arn}")

    try:
        ecs_client = await get_aws_client("ecs")
        response = ecs_client.delete_express_gateway_service(serviceArn=service_arn)

        logger.info("✓ Express Gateway Service deleted successfully")
        return {
            "status": "deleted",
            "service_arn": service_arn,
            "message": "Express Gateway Service deleted successfully",
            "details": response.get("service", {}),
        }

    except Exception as e:
        error_msg = f"Failed to delete Express Gateway Service: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "service_arn": service_arn,
            "error": str(e),
        }


async def delete_ecr_infrastructure(app_name: str) -> Dict[str, Any]:
    """
    Deletes the ECR CloudFormation stack for an application.

    Args:
        app_name: Name of the application (used to identify ECR stack)

    Returns:
        Dictionary containing deletion status and details
    """
    ecr_stack_name = f"{app_name}-ecr-infrastructure"
    logger.info(f"Deleting ECR CloudFormation stack: {ecr_stack_name}")

    try:
        cfn_client = await get_aws_client("cloudformation")

        # Check if stack exists
        try:
            cfn_client.describe_stacks(StackName=ecr_stack_name)
            stack_exists = True
        except cfn_client.exceptions.ClientError as e:
            if "does not exist" in str(e):
                logger.info(f"ECR stack {ecr_stack_name} not found")
                return {
                    "status": "not_found",
                    "stack_name": ecr_stack_name,
                    "message": (
                        f"ECR stack {ecr_stack_name} does not exist (may have been deleted already)"
                    ),
                }
            raise

        if stack_exists:
            # Delete the stack
            cfn_client.delete_stack(StackName=ecr_stack_name)
            logger.info(f"Waiting for ECR stack {ecr_stack_name} to be deleted...")

            # Wait for deletion to complete
            waiter = cfn_client.get_waiter("stack_delete_complete")
            waiter.wait(StackName=ecr_stack_name)

            logger.info(f"✓ ECR stack {ecr_stack_name} deleted successfully")
            return {
                "status": "deleted",
                "stack_name": ecr_stack_name,
                "message": f"ECR stack {ecr_stack_name} deleted successfully",
                "deleted_resources": [
                    f"ECR repository: {app_name}-repo",
                    f"IAM role: {app_name}-ecr-push-pull-role",
                ],
            }

        return {
            "status": "unknown",
            "stack_name": ecr_stack_name,
            "message": f"Unexpected state for ECR stack {ecr_stack_name}",
        }

    except Exception as e:
        error_msg = f"Failed to delete ECR stack: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "stack_name": ecr_stack_name,
            "error": str(e),
        }


async def delete_app(service_arn: str, app_name: str) -> Dict[str, Any]:
    """
    Deletes a complete Express Mode deployment including service and ECR infrastructure.

    This function performs a complete cleanup:
    1. Deletes the Express Gateway Service
    2. Deletes the ECR CloudFormation stack (repository + IAM role)

    Args:
        service_arn: ARN of the Express Gateway Service to delete
        app_name: Name of the application (used to identify ECR stack)

    Returns:
        Dictionary containing:
            - service_deletion: Status and details of service deletion
            - ecr_deletion: Status and details of ECR stack deletion
            - summary: Overall deletion summary
            - errors: List of any errors encountered
    """
    logger.info(f"Deleting Express Mode deployment for {app_name}")

    # Validate app_name
    validate_app_name(app_name)

    results = {
        "service_deletion": {},
        "ecr_deletion": {},
        "summary": {},
        "errors": [],
    }

    # Step 1: Delete Express Gateway Service
    service_result = await delete_express_gateway_service(service_arn)
    results["service_deletion"] = service_result
    if service_result.get("status") == "failed":
        results["errors"].append(service_result.get("error", "Service deletion failed"))

    # Step 2: Delete ECR Infrastructure
    ecr_result = await delete_ecr_infrastructure(app_name)
    results["ecr_deletion"] = ecr_result
    if ecr_result.get("status") == "failed":
        results["errors"].append(ecr_result.get("error", "ECR deletion failed"))

    # Create summary
    service_status = service_result.get("status", "unknown")
    ecr_status = ecr_result.get("status", "unknown")

    deleted_resources = []
    if service_status == "deleted":
        deleted_resources.append(f"Express Gateway Service: {service_arn}")
    if ecr_status == "deleted":
        deleted_resources.extend(ecr_result.get("deleted_resources", []))

    if len(results["errors"]) == 0:
        results["summary"] = {
            "status": "success",
            "message": f"Successfully deleted Express Mode deployment for {app_name}",
            "deleted_resources": deleted_resources,
        }
        logger.info(f"✅ Successfully deleted all resources for {app_name}")
    else:
        results["summary"] = {
            "status": "partial"
            if (
                service_status in ["deleted", "not_found"] or ecr_status in ["deleted", "not_found"]
            )
            else "failed",
            "message": f"Deletion completed with {len(results['errors'])} error(s)",
            "service_status": service_status,
            "ecr_status": ecr_status,
            "deleted_resources": deleted_resources,
        }
        logger.warning(f"⚠️  Deletion completed with errors for {app_name}")

    return results


async def wait_for_service_ready(
    cluster: str, service_name: str, timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    Waits for ECS tasks in a service to reach RUNNING status.

    Polls every 10 seconds until at least one task is running or timeout is reached.

    Args:
        cluster: ECS cluster name
        service_name: ECS service name
        timeout_seconds: Maximum time to wait in seconds (default: 300)

    Returns:
        Dictionary with status ("success", "timeout", or "failed") and message
    """
    logger.info(f"Waiting for service {service_name} in cluster {cluster} to be ready")

    poll_interval = 10
    start_time = time.time()
    attempts = 0

    try:
        ecs_client = await get_aws_client("ecs")

        while time.time() - start_time < timeout_seconds:
            attempts += 1
            elapsed = int(time.time() - start_time)

            logger.info(f"Checking service status (attempt {attempts}, {elapsed}s elapsed)")

            try:
                tasks_response = ecs_client.list_tasks(cluster=cluster, serviceName=service_name)

                if tasks_response.get("taskArns"):
                    describe_response = ecs_client.describe_tasks(
                        cluster=cluster, tasks=tasks_response["taskArns"]
                    )

                    running_count = sum(
                        1
                        for task in describe_response.get("tasks", [])
                        if task.get("lastStatus") == "RUNNING"
                    )

                    if running_count > 0:
                        logger.info(f"✅ Service ready with {running_count} running task(s)")
                        return {
                            "status": "success",
                            "message": f"Service is ready with {running_count} running task(s)",
                        }

            except Exception as e:
                logger.warning(f"Polling error: {str(e)}")

            if time.time() - start_time < timeout_seconds:
                await asyncio.sleep(poll_interval)

        # Timeout
        elapsed = int(time.time() - start_time)
        return {
            "status": "timeout",
            "message": f"Timeout after {elapsed}s - service not ready",
        }

    except Exception as e:
        return {
            "status": "failed",
            "message": f"Error: {str(e)}",
        }
