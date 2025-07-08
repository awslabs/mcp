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
S3 Storage Lens Query Module for AWS FinOps MCP Server.

This module provides functionality to query S3 Storage Lens metrics data
using Athena. Since there are no direct boto3 methods to query Storage Lens
metrics, this tool leverages the exported data in S3 and Athena to run SQL
queries against it.
"""

from .manifest_handler import ManifestHandler
from .athena_handler import AthenaHandler
from .query_tool import StorageLensQueryTool

__all__ = ['StorageLensQueryTool', 'ManifestHandler', 'AthenaHandler']
