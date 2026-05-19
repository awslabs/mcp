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
