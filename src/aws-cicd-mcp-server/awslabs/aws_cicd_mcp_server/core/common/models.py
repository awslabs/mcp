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

"""Pydantic models for AWS CI/CD MCP Server."""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

class PipelineExecution(BaseModel):
    """CodePipeline execution details."""
    pipeline_execution_id: str
    pipeline_name: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class BuildDetails(BaseModel):
    """CodeBuild build details."""
    build_id: str
    project_name: str
    build_status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    logs_location: Optional[str] = None

class DeploymentInfo(BaseModel):
    """CodeDeploy deployment information."""
    deployment_id: str
    application_name: str
    deployment_group_name: str
    status: str
    create_time: Optional[datetime] = None
    complete_time: Optional[datetime] = None
