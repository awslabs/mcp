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

"""Configuration classes for S3 Tables MCP Server."""

from pydantic import BaseModel
from typing import Optional


class AthenaConfig(BaseModel):
    """Configuration for Athena connection."""

    output_location: str  # The S3 location where Athena query results will be stored (required)
    workgroup: Optional[str] = None  # The Athena workgroup to use for queries
    region: Optional[str] = None  # The AWS region where Athena is running
    database: Optional[str] = None  # The Athena database to use
    catalog: Optional[str] = None  # The Athena catalog to use
