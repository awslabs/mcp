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

"""Tests for guidance_nudge module."""
# ruff: noqa: D101, D102, D103

import pytest
from awslabs.aws_transform_mcp_server.guidance_nudge import (
    _checked_jobs,
    job_needs_check,
    mark_job_checked,
    matches_instruction_label,
    unmark_job,
)


@pytest.fixture(autouse=True)
def reset_checked_jobs():
    """Clear the checked jobs set between tests."""
    _checked_jobs.clear()
    yield
    _checked_jobs.clear()


class TestMarkJobChecked:
    def test_adds_job_id(self):
        mark_job_checked('job-1')
        assert 'job-1' in _checked_jobs

    def test_idempotent(self):
        mark_job_checked('job-1')
        mark_job_checked('job-1')
        assert len(_checked_jobs) == 1


class TestJobNeedsCheck:
    def test_returns_nudge_for_unchecked_job(self):
        result = job_needs_check('job-1')
        assert result is not None
        assert 'load_instructions' in result
        assert 'job-1' in result

    def test_returns_none_for_checked_job(self):
        mark_job_checked('job-1')
        assert job_needs_check('job-1') is None

    def test_returns_none_for_none_job_id(self):
        assert job_needs_check(None) is None

    def test_returns_none_for_empty_string(self):
        assert job_needs_check('') is None


class TestUnmarkJob:
    def test_forgets_checked_job(self):
        mark_job_checked('job-1')
        unmark_job('job-1')
        assert job_needs_check('job-1') is not None

    def test_noop_for_unknown_job(self):
        unmark_job('job-never-seen')
        assert 'job-never-seen' not in _checked_jobs


class TestMatchesInstructionLabel:
    def test_bare_name(self):
        assert matches_instruction_label('JOB_INSTRUCTIONS')

    def test_inside_store_folder(self):
        assert matches_instruction_label('User Uploads/JOB_INSTRUCTIONS')

    def test_deep_store_path(self):
        assert matches_instruction_label(
            'AWSTransform/Workspaces/ws/Jobs/j/User Uploads/JOB_INSTRUCTIONS'
        )

    def test_other_name_no_match(self):
        assert not matches_instruction_label('User Uploads/coding-conventions.md')

    def test_prefix_only_no_match(self):
        assert not matches_instruction_label('JOB_INSTRUCTIONS/other.md')

    def test_empty(self):
        assert not matches_instruction_label('')
