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
"""Pydantic models for the Finch MCP server.

This module defines the data models used for request and response validation
in the Finch MCP server tools.
"""

from pydantic import BaseModel, Field


class Result(BaseModel):
    """Base model for operation results.

    This model only includes status and message fields, regardless of what additional
    fields might be present in the input dictionary. This ensures that only these two
    fields are returned to the user.
    """

    status: str = Field(..., description="Status of the operation ('success', 'error', etc.)")
    message: str = Field(..., description='Descriptive message about the result of the operation')
