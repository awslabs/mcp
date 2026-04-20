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

"""Response models for Lake Formation operations."""

from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class PermissionSummary(BaseModel):
    """Summary of a Lake Formation permission."""

    principal: str
    resource: Dict[str, Any]
    permissions: List[str]
    permissions_with_grant_option: Optional[List[str]] = None


class DataLakeSettingsSummary(BaseModel):
    """Summary of Lake Formation data lake settings."""

    data_lake_admins: List[str]
    create_database_default_permissions: Optional[List[Dict[str, Any]]] = None
    create_table_default_permissions: Optional[List[Dict[str, Any]]] = None
    allow_external_data_filtering: bool = False


class ResourceSummary(BaseModel):
    """Summary of a Lake Formation registered resource."""

    resource_arn: str
    role_arn: Optional[str] = None
    use_service_linked_role: bool = True
    with_federation: bool = False
    last_modified: Optional[str] = None


class EffectivePermissionSummary(BaseModel):
    """Summary of an effective Lake Formation permission for a resource path."""

    principal: str
    resource: Dict[str, Any]
    permissions: List[str]
    permissions_with_grant_option: Optional[List[str]] = None


class ListPermissionsData(BaseModel):
    """Data model for listing Lake Formation permissions."""

    permissions: List[PermissionSummary]
    operation: str = 'list-permissions'


class GetDataLakeSettingsData(BaseModel):
    """Data model for getting data lake settings."""

    settings: DataLakeSettingsSummary
    operation: str = 'get-data-lake-settings'


class ListResourcesData(BaseModel):
    """Data model for listing Lake Formation resources."""

    resources: List[ResourceSummary]
    operation: str = 'list-resources'


class DescribeResourceData(BaseModel):
    """Data model for describing a Lake Formation resource."""

    resource: ResourceSummary
    operation: str = 'describe-resource'


class GetEffectivePermissionsData(BaseModel):
    """Data model for batch get effective permissions for path."""

    effective_permissions: List[EffectivePermissionSummary]
    operation: str = 'batch-get-effective-permissions-for-path'
