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
