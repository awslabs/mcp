# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Decorators for AWS CI/CD MCP Server."""

from functools import wraps
from typing import Any, Callable
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger


def handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle AWS exceptions with specific error messages."""
    
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        try:
            return await func(*args, **kwargs)
        except NoCredentialsError:
            error_msg = "AWS credentials not found. Configure using 'aws configure' or set environment variables."
            logger.error(error_msg)
            return {"error": error_msg}
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            # Provide specific guidance for common errors
            if error_code == 'AccessDenied':
                guidance = "Check IAM permissions for CodePipeline, CodeBuild, or CodeDeploy services."
            elif error_code == 'ResourceNotFound':
                guidance = "Verify the resource name and region are correct."
            elif error_code == 'ValidationException':
                guidance = "Check parameter values and formats."
            else:
                guidance = f"AWS Error: {error_code}"
            
            full_error = f"{error_msg}. {guidance}"
            logger.error(f"AWS API Error: {full_error}")
            return {"error": full_error}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": str(e)}
    
    return wrapper
