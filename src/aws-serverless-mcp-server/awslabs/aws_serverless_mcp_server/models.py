# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Models for the AWS Serverless MCP Server."""

from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, Optional


# Serverless WebApp models
class BackendConfiguration(BaseModel):
    """Backend configuration for web application deployment."""

    built_artifacts_path: str = Field(
        ..., description='Absolute path to pre-built backend artifacts'
    )
    framework: Optional[str] = Field(None, description='Backend framework')
    runtime: str = Field(..., description='Lambda runtime (e.g. nodejs22.x, python3.13)')
    startup_script: Optional[str] = Field(
        None,
        description='Startup script that must be executable in Linux environment. Relative to the built_artifacts_path directory.',
    )
    entry_point: Optional[str] = Field(
        None, description='Application entry point file (e.g., app.js, app.py)'
    )
    generate_startup_script: Optional[bool] = Field(
        False, description='Whether to automatically generate a startup script'
    )
    architecture: Optional[Literal['x86_64', 'arm64']] = Field(
        'x86_64', description='Lambda architecture'
    )
    memory_size: Optional[int] = Field(512, description='Lambda memory size')
    timeout: Optional[int] = Field(30, description='Lambda timeout')
    stage: Optional[str] = Field('prod', description='API Gateway stage')
    cors: Optional[bool] = Field(True, description='Enable CORS')
    port: int = Field(..., description='Port on which the web application runs')
    environment: Optional[Dict[str, str]] = Field(None, description='Environment variables')
    database_configuration: Optional[Dict[str, Any]] = Field(
        None, description='Database configuration for creating DynamoDB tables'
    )


class FrontendConfiguration(BaseModel):
    """Frontend configuration for web application deployment."""

    built_assets_path: str = Field(..., description='Absolute path to pre-built frontend assets')
    framework: Optional[str] = Field(None, description='Frontend framework')
    index_document: Optional[str] = Field('index.html', description='Index document')
    error_document: Optional[str] = Field(None, description='Error document')
    custom_domain: Optional[str] = Field(None, description='Custom domain')
    certificate_arn: Optional[str] = Field(None, description='ACM certificate ARN')


class DeployWebAppRequest(BaseModel):
    """Request model for deploying a web application."""

    deployment_type: Literal['backend', 'frontend', 'fullstack'] = Field(
        ..., description='Type of deployment'
    )
    project_name: str = Field(..., description='Project name')
    project_root: str = Field(..., description='Absolute path to the project root directory')
    region: Optional[str] = Field(None, description='AWS Region to deploy to (e.g., us-east-1)')
    backend_configuration: Optional[BackendConfiguration] = Field(
        None, description='Backend configuration'
    )
    frontend_configuration: Optional[FrontendConfiguration] = Field(
        None, description='Frontend configuration'
    )
