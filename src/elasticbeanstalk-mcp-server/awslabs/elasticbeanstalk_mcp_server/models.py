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

"""Pydantic models for the Beanstalk MCP Server."""

from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class EnvironmentTier(BaseModel):
    """Environment tier specification."""

    Name: Optional[str] = None
    Type: Optional[str] = None
    Version: Optional[str] = None


class Tag(BaseModel):
    """Resource tag."""

    Key: str
    Value: str


class OptionSetting(BaseModel):
    """Configuration option setting."""

    Namespace: str
    OptionName: str
    Value: str


class EnvironmentDescription(BaseModel):
    """Environment description."""

    EnvironmentName: Optional[str] = None
    EnvironmentId: Optional[str] = None
    ApplicationName: Optional[str] = None
    VersionLabel: Optional[str] = None
    SolutionStackName: Optional[str] = None
    PlatformArn: Optional[str] = None
    TemplateName: Optional[str] = None
    Description: Optional[str] = None
    EndpointURL: Optional[str] = None
    CNAME: Optional[str] = None
    DateCreated: Optional[str] = None
    DateUpdated: Optional[str] = None
    Status: Optional[str] = None
    AbortableOperationInProgress: Optional[bool] = None
    Health: Optional[str] = None
    HealthStatus: Optional[str] = None
    Resources: Optional[Dict[str, Any]] = None
    Tier: Optional[EnvironmentTier] = None
    EnvironmentLinks: Optional[List[Dict[str, str]]] = None
    EnvironmentArn: Optional[str] = None
    OperationsRole: Optional[str] = None


class ApplicationDescription(BaseModel):
    """Application description."""

    ApplicationName: Optional[str] = None
    Description: Optional[str] = None
    DateCreated: Optional[str] = None
    DateUpdated: Optional[str] = None
    Versions: Optional[List[str]] = None
    ConfigurationTemplates: Optional[List[str]] = None
    ResourceLifecycleConfig: Optional[Dict[str, Any]] = None
    ApplicationArn: Optional[str] = None


class ApplicationVersionDescription(BaseModel):
    """Application version description."""

    ApplicationVersionArn: Optional[str] = None
    ApplicationName: Optional[str] = None
    Description: Optional[str] = None
    VersionLabel: Optional[str] = None
    SourceBuildInformation: Optional[Dict[str, str]] = None
    BuildArn: Optional[str] = None
    SourceBundle: Optional[Dict[str, str]] = None
    DateCreated: Optional[str] = None
    DateUpdated: Optional[str] = None
    Status: Optional[str] = None
