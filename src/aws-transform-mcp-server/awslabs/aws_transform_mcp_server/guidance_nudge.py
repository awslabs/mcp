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

"""Tracks which jobIds have had load_instructions called.

Any tool receiving a jobId checks this before proceeding. Also owns what
counts as an instruction artifact, shared by discovery (load_instructions)
and upload (upload_artifact).
"""

from typing import Optional, Set


INSTRUCTION_ARTIFACT_LABELS = ['JOB_INSTRUCTIONS']

_checked_jobs: Set[str] = set()


def matches_instruction_label(path: str) -> bool:
    """True if a stored artifact path names an instruction document.

    Customer uploads carry the store folder in their path (e.g.
    'User Uploads/JOB_INSTRUCTIONS'), so match on the path's base name.
    """
    return path.rsplit('/', 1)[-1] in INSTRUCTION_ARTIFACT_LABELS


def mark_job_checked(job_id: str) -> None:
    """Record that load_instructions has been called for this job."""
    _checked_jobs.add(job_id)


def unmark_job(job_id: str) -> None:
    """Forget that a job was checked, so the next job-scoped call nudges a re-load."""
    _checked_jobs.discard(job_id)


def job_needs_check(job_id: Optional[str]) -> Optional[str]:
    """Return a nudge message if load_instructions hasn't been called for this job."""
    if job_id and job_id not in _checked_jobs:
        return (
            f'STOP: Before working on this job, call load_instructions with '
            f'workspaceId and jobId="{job_id}" to check for required workflow instructions.'
        )
    return None
