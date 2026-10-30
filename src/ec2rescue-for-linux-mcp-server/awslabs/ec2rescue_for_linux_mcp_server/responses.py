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

"""Pydantic response shapes returned by the MCP tools."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class InstanceListResponse(BaseModel):
    """Response shape for the ``list_instances`` tool."""

    instances: list[dict] = Field(
        default_factory=list,
        description='SSM-managed instances reachable from this region.',
    )
    message: Optional[str] = Field(
        default=None,
        description='Human-readable note (e.g. when no instances were found).',
    )


class ModuleResponse(BaseModel):
    """Response shape for every ``run_ec2rescue_linux_<module>`` tool.

    All fields except ``instance_id`` / ``module`` / ``status`` are optional;
    the helpers below populate only the ones that apply to the path taken
    (success vs aborted vs listing vs grep), and ``json.dumps`` with
    ``exclude_none=True`` keeps the wire shape per-path the same as before.
    """

    instance_id: str
    module: str
    status: str  # SSM status: Success / Failed / TimedOut / Cancelled / Aborted
    exit_code: Optional[int] = None
    output_dir: Optional[str] = None
    log_content: str = ''

    # Set when SSM reported Failed but we read the log anyway because the
    # module is in READ_LOG_ON_NONZERO_EXIT_MODULES.
    detected_issue: Optional[bool] = None

    # Failure / abort context.
    stderr: Optional[str] = None
    log_read_error: Optional[str] = None
    raw_stdout: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None

    # software-check precheck context.
    missing_package: Optional[str] = None
    software_check_stdout: Optional[str] = None
    software_check_status: Optional[str] = None

    # Gathered-output flow.
    files: Optional[dict[str, str]] = None
    missing_files: Optional[list[str]] = None
    available_files: Optional[list[str]] = None
    hint: Optional[str] = None

    # grep-keys flow.
    grep_keys: Optional[list[str]] = None

    # tail flow: trailing lines returned per file; absent when full output.
    tail_lines: Optional[int] = None

    def as_json(self) -> str:
        """Serialise to JSON, dropping unset fields to keep wire shape stable."""
        return self.model_dump_json(exclude_none=True)


class InstallResponse(BaseModel):
    """Response shape for the ``install_ec2rescue_linux`` tool."""

    instance_id: str
    status: str  # Success / Failed / TimedOut / Cancelled / Aborted
    automation_execution_id: Optional[str] = None
    outputs: Optional[dict] = None
    failure_message: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None

    def as_json(self) -> str:
        """Serialise to JSON, dropping unset fields."""
        return self.model_dump_json(exclude_none=True)
