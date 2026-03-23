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

"""Pydantic response models for Code Interpreter MCP tools."""

from pydantic import BaseModel, ConfigDict, Field


class CodeInterpreterSessionResponse(BaseModel):
    """Response from session start/get operations.

    Attributes:
        session_id: Unique identifier for the session.
        status: Session status (e.g. READY, TERMINATED).
        code_interpreter_identifier: The code interpreter identifier used.
        message: Human-readable status message.
    """

    session_id: str = Field(description='Unique identifier for the session')
    status: str = Field(description='Session status (e.g. READY, TERMINATED)')
    code_interpreter_identifier: str = Field(description='Code interpreter identifier')
    message: str = Field(default='', description='Human-readable status message')

    model_config = ConfigDict(extra='allow')


class CodeInterpreterSessionSummary(BaseModel):
    """Summary of a session in list responses.

    Attributes:
        session_id: Unique identifier for the session.
        status: Session status.
        name: Optional session name.
    """

    session_id: str = Field(description='Unique identifier for the session')
    status: str = Field(description='Session status')
    name: str | None = Field(default=None, description='Optional session name')

    model_config = ConfigDict(extra='allow')


class SessionListResponse(BaseModel):
    """Response from list sessions operation.

    Attributes:
        sessions: List of session summaries.
        next_token: Pagination token for next page, if available.
        message: Human-readable status message.
    """

    sessions: list[CodeInterpreterSessionSummary] = Field(
        default_factory=list, description='List of session summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token for next page')
    message: str = Field(default='', description='Human-readable status message')


class ExecutionResult(BaseModel):
    """Response from code/command execution operations.

    Attributes:
        stdout: Standard output from execution.
        stderr: Standard error from execution.
        exit_code: Process exit code (0 = success).
        is_error: Whether the execution encountered an error.
        content: Additional content or result data.
        message: Human-readable status message.
    """

    stdout: str = Field(default='', description='Standard output from execution')
    stderr: str = Field(default='', description='Standard error from execution')
    exit_code: int | None = Field(default=None, description='Process exit code (0 = success)')
    is_error: bool = Field(default=False, description='Whether execution encountered an error')
    content: str = Field(default='', description='Additional content or result data')
    message: str = Field(default='', description='Human-readable status message')

    model_config = ConfigDict(extra='allow')


class FileOperationResult(BaseModel):
    """Response from file upload/download operations.

    Attributes:
        path: File path in the sandbox.
        content: File content (for downloads).
        message: Human-readable status message.
    """

    path: str = Field(description='File path in the sandbox')
    content: str | None = Field(default=None, description='File content (for downloads)')
    message: str = Field(default='', description='Human-readable status message')
