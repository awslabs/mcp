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

"""Property-based tests for run group Pydantic models."""

from awslabs.aws_healthomics_mcp_server.models.core import (
    RunGroupDetail,
    RunGroupListResponse,
    RunGroupSummary,
)
from datetime import datetime, timezone
from hypothesis import given, settings
from hypothesis import strategies as st


# --- Hypothesis Strategies ---

name_strategy = st.text(min_size=1, max_size=128)
resource_limit_strategy = st.integers(min_value=1, max_value=100000)
optional_resource_limit_strategy = st.none() | st.integers(min_value=1, max_value=100000)
tags_strategy = st.dictionaries(
    st.text(min_size=1, max_size=128),
    st.text(max_size=256),
    max_size=10,
)
id_strategy = st.text(min_size=1, max_size=18, alphabet=st.characters(categories=('Nd',)))
arn_strategy = st.text(min_size=1, max_size=200)
datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=st.just(timezone.utc),
)


# Feature: run-group-tools, Property: Pydantic model round-trip serialization
class TestRunGroupModelRoundTrip:
    """Property-based tests for run group model round-trip serialization.

    For any valid run group data, constructing a model, serializing to dict,
    and deserializing back should produce an equivalent model instance.

    Validates: RunGroupSummary, RunGroupDetail, and RunGroupListResponse models
    """

    @given(
        id=id_strategy,
        arn=arn_strategy,
        name=st.none() | name_strategy,
        max_cpus=optional_resource_limit_strategy,
        max_gpus=optional_resource_limit_strategy,
        max_duration=optional_resource_limit_strategy,
        max_runs=optional_resource_limit_strategy,
        creation_time=datetime_strategy,
    )
    @settings(max_examples=100)
    def test_run_group_summary_round_trip(
        self,
        id: str,
        arn: str,
        name,
        max_cpus,
        max_gpus,
        max_duration,
        max_runs,
        creation_time: datetime,
    ):
        """RunGroupSummary round-trip: construct -> model_dump -> model_validate -> equal.

        Validates: RunGroupSummary model definition
        """
        original = RunGroupSummary(
            id=id,
            arn=arn,
            name=name,
            maxCpus=max_cpus,
            maxGpus=max_gpus,
            maxDuration=max_duration,
            maxRuns=max_runs,
            creationTime=creation_time,
        )

        data = original.model_dump()
        restored = RunGroupSummary.model_validate(data)

        assert restored == original
        assert restored.id == original.id
        assert restored.arn == original.arn
        assert restored.name == original.name
        assert restored.maxCpus == original.maxCpus
        assert restored.maxGpus == original.maxGpus
        assert restored.maxDuration == original.maxDuration
        assert restored.maxRuns == original.maxRuns
        assert restored.creationTime == original.creationTime

    @given(
        id=id_strategy,
        arn=arn_strategy,
        name=st.none() | name_strategy,
        max_cpus=optional_resource_limit_strategy,
        max_gpus=optional_resource_limit_strategy,
        max_duration=optional_resource_limit_strategy,
        max_runs=optional_resource_limit_strategy,
        creation_time=datetime_strategy,
        tags=st.none() | tags_strategy,
    )
    @settings(max_examples=100)
    def test_run_group_detail_round_trip(
        self,
        id: str,
        arn: str,
        name,
        max_cpus,
        max_gpus,
        max_duration,
        max_runs,
        creation_time: datetime,
        tags,
    ):
        """RunGroupDetail round-trip: construct -> model_dump -> model_validate -> equal.

        Validates: RunGroupDetail model with tags field
        """
        original = RunGroupDetail(
            id=id,
            arn=arn,
            name=name,
            maxCpus=max_cpus,
            maxGpus=max_gpus,
            maxDuration=max_duration,
            maxRuns=max_runs,
            creationTime=creation_time,
            tags=tags,
        )

        data = original.model_dump()
        restored = RunGroupDetail.model_validate(data)

        assert restored == original
        assert restored.tags == original.tags

    @given(
        num_groups=st.integers(min_value=0, max_value=5),
        next_token=st.none() | st.text(min_size=1, max_size=64),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_run_group_list_response_round_trip(
        self,
        num_groups: int,
        next_token,
        data,
    ):
        """RunGroupListResponse round-trip: construct -> model_dump -> model_validate -> equal.

        Validates: RunGroupListResponse model with list and pagination
        """
        run_groups = []
        for _ in range(num_groups):
            group = RunGroupSummary(
                id=data.draw(id_strategy),
                arn=data.draw(arn_strategy),
                name=data.draw(st.none() | name_strategy),
                maxCpus=data.draw(optional_resource_limit_strategy),
                maxGpus=data.draw(optional_resource_limit_strategy),
                maxDuration=data.draw(optional_resource_limit_strategy),
                maxRuns=data.draw(optional_resource_limit_strategy),
                creationTime=data.draw(datetime_strategy),
            )
            run_groups.append(group)

        original = RunGroupListResponse(
            runGroups=run_groups,
            nextToken=next_token,
        )

        dumped = original.model_dump()
        restored = RunGroupListResponse.model_validate(dumped)

        assert restored == original
        assert len(restored.runGroups) == len(original.runGroups)
        assert restored.nextToken == original.nextToken
