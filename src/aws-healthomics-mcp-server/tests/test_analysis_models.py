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

"""Unit and property-based tests for analysis data models."""

import pytest
from awslabs.aws_healthomics_mcp_server.models.analysis import (
    AggregatedTaskMetrics,
    CrossRunAggregate,
    RunCostSummary,
    TaskCostMetrics,
    TimeUnit,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


class TestTimeUnitEnum:
    """Test cases for TimeUnit enum."""

    def test_time_unit_values(self):
        """Test TimeUnit enum values."""
        assert TimeUnit.SECONDS == 'sec'
        assert TimeUnit.MINUTES == 'min'
        assert TimeUnit.HOURS == 'hr'
        assert TimeUnit.DAYS == 'day'

    def test_time_unit_membership(self):
        """Test TimeUnit enum membership."""
        assert TimeUnit.SECONDS in TimeUnit
        assert TimeUnit.MINUTES in TimeUnit
        assert TimeUnit.HOURS in TimeUnit
        assert TimeUnit.DAYS in TimeUnit


class TestTaskCostMetrics:
    """Test cases for TaskCostMetrics model."""

    def test_task_cost_metrics_creation(self):
        """Test TaskCostMetrics model creation with all fields."""
        metrics = TaskCostMetrics(
            taskName='alignment-task',
            taskArn='arn:aws:omics:us-east-1:123456789012:task/task-12345',
            instanceType='omics.m.xlarge',
            runningSeconds=3600.0,
            estimatedUSD=1.25,
            recommendedInstanceType='omics.m.large',
            recommendedCpus=4,
            recommendedMemoryGiB=16.0,
            minimumUSD=0.75,
            potentialSavingsUSD=0.50,
            isHighPrioritySaving=True,
        )

        assert metrics.taskName == 'alignment-task'
        assert metrics.taskArn == 'arn:aws:omics:us-east-1:123456789012:task/task-12345'
        assert metrics.instanceType == 'omics.m.xlarge'
        assert metrics.runningSeconds == 3600.0
        assert metrics.estimatedUSD == 1.25
        assert metrics.recommendedInstanceType == 'omics.m.large'
        assert metrics.recommendedCpus == 4
        assert metrics.recommendedMemoryGiB == 16.0
        assert metrics.minimumUSD == 0.75
        assert metrics.potentialSavingsUSD == 0.50
        assert metrics.isHighPrioritySaving is True

    def test_task_cost_metrics_missing_required_fields(self):
        """Test TaskCostMetrics validation with missing required fields."""
        with pytest.raises(ValidationError):
            TaskCostMetrics()  # type: ignore

    def test_task_cost_metrics_is_high_priority_required(self):
        """Test TaskCostMetrics requires isHighPrioritySaving field."""
        # isHighPrioritySaving is a required field (no default value)
        with pytest.raises(ValidationError):
            TaskCostMetrics(  # type: ignore
                taskName='task',
                taskArn='arn',
                instanceType='omics.m.xlarge',
                runningSeconds=100.0,
                estimatedUSD=1.0,
                recommendedInstanceType='omics.m.large',
                recommendedCpus=2,
                recommendedMemoryGiB=8.0,
                minimumUSD=0.5,
                potentialSavingsUSD=0.5,
                # Missing isHighPrioritySaving - intentionally omitted to test validation
            )


class TestRunCostSummary:
    """Test cases for RunCostSummary model."""

    def test_run_cost_summary_creation(self):
        """Test RunCostSummary model creation with all fields."""
        summary = RunCostSummary(
            runId='run-12345',
            runName='alignment-workflow',
            totalEstimatedUSD=25.50,
            taskCostUSD=20.00,
            storageCostUSD=5.50,
            totalPotentialSavingsUSD=8.25,
            peakConcurrentCpus=64.0,
            peakConcurrentMemoryGiB=256.0,
            averageConcurrentCpus=32.0,
            averageConcurrentMemoryGiB=128.0,
        )

        assert summary.runId == 'run-12345'
        assert summary.runName == 'alignment-workflow'
        assert summary.totalEstimatedUSD == 25.50
        assert summary.taskCostUSD == 20.00
        assert summary.storageCostUSD == 5.50
        assert summary.totalPotentialSavingsUSD == 8.25
        assert summary.peakConcurrentCpus == 64.0
        assert summary.peakConcurrentMemoryGiB == 256.0
        assert summary.averageConcurrentCpus == 32.0
        assert summary.averageConcurrentMemoryGiB == 128.0

    def test_run_cost_summary_missing_required_fields(self):
        """Test RunCostSummary validation with missing required fields."""
        with pytest.raises(ValidationError):
            RunCostSummary()  # type: ignore


class TestAggregatedTaskMetrics:
    """Test cases for AggregatedTaskMetrics model."""

    def test_aggregated_task_metrics_creation(self):
        """Test AggregatedTaskMetrics model creation with all fields."""
        metrics = AggregatedTaskMetrics(
            baseTaskName='alignment',
            count=10,
            meanRunningSeconds=1800.0,
            maximumRunningSeconds=3600.0,
            stdDevRunningSeconds=450.0,
            maximumCpuUtilizationRatio=0.95,
            meanCpuUtilizationRatio=0.75,
            maximumMemoryUtilizationRatio=0.85,
            meanMemoryUtilizationRatio=0.65,
            recommendedCpus=8,
            recommendedMemoryGiB=32.0,
            recommendedInstanceType='omics.m.2xlarge',
            totalEstimatedUSD=15.00,
            meanEstimatedUSD=1.50,
            maximumEstimatedUSD=2.50,
        )

        assert metrics.baseTaskName == 'alignment'
        assert metrics.count == 10
        assert metrics.meanRunningSeconds == 1800.0
        assert metrics.maximumRunningSeconds == 3600.0
        assert metrics.stdDevRunningSeconds == 450.0
        assert metrics.maximumCpuUtilizationRatio == 0.95
        assert metrics.meanCpuUtilizationRatio == 0.75
        assert metrics.maximumMemoryUtilizationRatio == 0.85
        assert metrics.meanMemoryUtilizationRatio == 0.65
        assert metrics.recommendedCpus == 8
        assert metrics.recommendedMemoryGiB == 32.0
        assert metrics.recommendedInstanceType == 'omics.m.2xlarge'
        assert metrics.totalEstimatedUSD == 15.00
        assert metrics.meanEstimatedUSD == 1.50
        assert metrics.maximumEstimatedUSD == 2.50

    def test_aggregated_task_metrics_optional_stddev(self):
        """Test AggregatedTaskMetrics with optional stdDevRunningSeconds."""
        metrics = AggregatedTaskMetrics(
            baseTaskName='alignment',
            count=1,
            meanRunningSeconds=1800.0,
            maximumRunningSeconds=1800.0,
            stdDevRunningSeconds=None,  # Optional field
            maximumCpuUtilizationRatio=0.75,
            meanCpuUtilizationRatio=0.75,
            maximumMemoryUtilizationRatio=0.65,
            meanMemoryUtilizationRatio=0.65,
            recommendedCpus=4,
            recommendedMemoryGiB=16.0,
            recommendedInstanceType='omics.m.xlarge',
            totalEstimatedUSD=1.50,
            meanEstimatedUSD=1.50,
            maximumEstimatedUSD=1.50,
        )

        assert metrics.stdDevRunningSeconds is None

    def test_aggregated_task_metrics_missing_required_fields(self):
        """Test AggregatedTaskMetrics validation with missing required fields."""
        with pytest.raises(ValidationError):
            AggregatedTaskMetrics()  # type: ignore


class TestCrossRunAggregate:
    """Test cases for CrossRunAggregate model."""

    def test_cross_run_aggregate_creation(self):
        """Test CrossRunAggregate model creation with all fields."""
        aggregate = CrossRunAggregate(
            baseTaskName='alignment',
            runCount=5,
            totalTaskCount=50,
            meanRunningSeconds=2000.0,
            maximumRunningSeconds=4000.0,
            meanCpuUtilizationRatio=0.70,
            meanMemoryUtilizationRatio=0.60,
            totalEstimatedUSD=75.00,
            recommendedInstanceType='omics.m.2xlarge',
        )

        assert aggregate.baseTaskName == 'alignment'
        assert aggregate.runCount == 5
        assert aggregate.totalTaskCount == 50
        assert aggregate.meanRunningSeconds == 2000.0
        assert aggregate.maximumRunningSeconds == 4000.0
        assert aggregate.meanCpuUtilizationRatio == 0.70
        assert aggregate.meanMemoryUtilizationRatio == 0.60
        assert aggregate.totalEstimatedUSD == 75.00
        assert aggregate.recommendedInstanceType == 'omics.m.2xlarge'

    def test_cross_run_aggregate_missing_required_fields(self):
        """Test CrossRunAggregate validation with missing required fields."""
        with pytest.raises(ValidationError):
            CrossRunAggregate()  # type: ignore


class TestAnalysisModelsPropertyBased:
    """Property-based tests for analysis models using Hypothesis."""

    # Strategies for generating valid model data
    task_name_strategy = st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'), whitelist_characters='-_.'
        ),
    )
    arn_strategy = st.text(min_size=1, max_size=200)
    instance_type_strategy = st.sampled_from(
        [
            'omics.c.large',
            'omics.c.xlarge',
            'omics.c.2xlarge',
            'omics.m.large',
            'omics.m.xlarge',
            'omics.m.2xlarge',
            'omics.r.large',
            'omics.r.xlarge',
            'omics.r.2xlarge',
        ]
    )
    positive_float_strategy = st.floats(
        min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False
    )
    ratio_strategy = st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)
    positive_int_strategy = st.integers(min_value=1, max_value=1000)
    count_strategy = st.integers(min_value=1, max_value=10000)

    @given(
        task_name=task_name_strategy,
        task_arn=arn_strategy,
        instance_type=instance_type_strategy,
        running_seconds=positive_float_strategy,
        estimated_usd=positive_float_strategy,
        recommended_instance=instance_type_strategy,
        recommended_cpus=positive_int_strategy,
        recommended_memory=positive_float_strategy,
        minimum_usd=positive_float_strategy,
        potential_savings=positive_float_strategy,
        is_high_priority=st.booleans(),
    )
    @settings(max_examples=100)
    def test_property_task_cost_metrics_output_completeness(
        self,
        task_name: str,
        task_arn: str,
        instance_type: str,
        running_seconds: float,
        estimated_usd: float,
        recommended_instance: str,
        recommended_cpus: int,
        recommended_memory: float,
        minimum_usd: float,
        potential_savings: float,
        is_high_priority: bool,
    ):
        """Property 12: Output Completeness - TaskCostMetrics.

        For any successful analysis, the TaskCostMetrics output SHALL contain all required fields:
        - estimatedUSD
        - recommendedInstanceType
        - recommendedCpus
        - recommendedMemoryGiB
        - potentialSavingsUSD

        **Validates: Requirements 1.4, 3.4, 4.3**
        **Feature: run-analyzer-enhancement, Property 12: Output Completeness**
        """
        metrics = TaskCostMetrics(
            taskName=task_name,
            taskArn=task_arn,
            instanceType=instance_type,
            runningSeconds=running_seconds,
            estimatedUSD=estimated_usd,
            recommendedInstanceType=recommended_instance,
            recommendedCpus=recommended_cpus,
            recommendedMemoryGiB=recommended_memory,
            minimumUSD=minimum_usd,
            potentialSavingsUSD=potential_savings,
            isHighPrioritySaving=is_high_priority,
        )

        # Property: All required fields are present and accessible
        assert hasattr(metrics, 'estimatedUSD')
        assert hasattr(metrics, 'recommendedInstanceType')
        assert hasattr(metrics, 'recommendedCpus')
        assert hasattr(metrics, 'recommendedMemoryGiB')
        assert hasattr(metrics, 'potentialSavingsUSD')

        # Property: Fields have correct types
        assert isinstance(metrics.estimatedUSD, float)
        assert isinstance(metrics.recommendedInstanceType, str)
        assert isinstance(metrics.recommendedCpus, int)
        assert isinstance(metrics.recommendedMemoryGiB, float)
        assert isinstance(metrics.potentialSavingsUSD, float)

        # Property: Model can be serialized to dict with all fields
        data = metrics.model_dump()
        required_fields = [
            'taskName',
            'taskArn',
            'instanceType',
            'runningSeconds',
            'estimatedUSD',
            'recommendedInstanceType',
            'recommendedCpus',
            'recommendedMemoryGiB',
            'minimumUSD',
            'potentialSavingsUSD',
            'isHighPrioritySaving',
        ]
        for field in required_fields:
            assert field in data, f'Missing required field: {field}'

    @given(
        run_id=st.text(min_size=1, max_size=50),
        run_name=st.text(min_size=1, max_size=100),
        total_estimated=positive_float_strategy,
        task_cost=positive_float_strategy,
        storage_cost=positive_float_strategy,
        total_savings=positive_float_strategy,
        peak_cpus=positive_float_strategy,
        peak_memory=positive_float_strategy,
        avg_cpus=positive_float_strategy,
        avg_memory=positive_float_strategy,
    )
    @settings(max_examples=100)
    def test_property_run_cost_summary_output_completeness(
        self,
        run_id: str,
        run_name: str,
        total_estimated: float,
        task_cost: float,
        storage_cost: float,
        total_savings: float,
        peak_cpus: float,
        peak_memory: float,
        avg_cpus: float,
        avg_memory: float,
    ):
        """Property 12: Output Completeness - RunCostSummary.

        For any successful analysis, the RunCostSummary output SHALL contain all required fields:
        - totalEstimatedUSD
        - taskCostUSD
        - storageCostUSD
        - totalPotentialSavingsUSD
        - peakConcurrentCpus
        - peakConcurrentMemoryGiB
        - averageConcurrentCpus
        - averageConcurrentMemoryGiB

        **Validates: Requirements 2.3, 4.3, 9.4, 11.4**
        **Feature: run-analyzer-enhancement, Property 12: Output Completeness**
        """
        summary = RunCostSummary(
            runId=run_id,
            runName=run_name,
            totalEstimatedUSD=total_estimated,
            taskCostUSD=task_cost,
            storageCostUSD=storage_cost,
            totalPotentialSavingsUSD=total_savings,
            peakConcurrentCpus=peak_cpus,
            peakConcurrentMemoryGiB=peak_memory,
            averageConcurrentCpus=avg_cpus,
            averageConcurrentMemoryGiB=avg_memory,
        )

        # Property: All required fields are present and accessible
        assert hasattr(summary, 'totalEstimatedUSD')
        assert hasattr(summary, 'taskCostUSD')
        assert hasattr(summary, 'storageCostUSD')
        assert hasattr(summary, 'totalPotentialSavingsUSD')
        assert hasattr(summary, 'peakConcurrentCpus')
        assert hasattr(summary, 'peakConcurrentMemoryGiB')
        assert hasattr(summary, 'averageConcurrentCpus')
        assert hasattr(summary, 'averageConcurrentMemoryGiB')

        # Property: Fields have correct types
        assert isinstance(summary.totalEstimatedUSD, float)
        assert isinstance(summary.taskCostUSD, float)
        assert isinstance(summary.storageCostUSD, float)
        assert isinstance(summary.totalPotentialSavingsUSD, float)
        assert isinstance(summary.peakConcurrentCpus, float)
        assert isinstance(summary.peakConcurrentMemoryGiB, float)
        assert isinstance(summary.averageConcurrentCpus, float)
        assert isinstance(summary.averageConcurrentMemoryGiB, float)

        # Property: Model can be serialized to dict with all fields
        data = summary.model_dump()
        required_fields = [
            'runId',
            'runName',
            'totalEstimatedUSD',
            'taskCostUSD',
            'storageCostUSD',
            'totalPotentialSavingsUSD',
            'peakConcurrentCpus',
            'peakConcurrentMemoryGiB',
            'averageConcurrentCpus',
            'averageConcurrentMemoryGiB',
        ]
        for field in required_fields:
            assert field in data, f'Missing required field: {field}'

    @given(
        base_task_name=task_name_strategy,
        run_count=count_strategy,
        total_task_count=count_strategy,
        mean_running=positive_float_strategy,
        max_running=positive_float_strategy,
        mean_cpu_ratio=ratio_strategy,
        mean_memory_ratio=ratio_strategy,
        total_estimated=positive_float_strategy,
        recommended_instance=instance_type_strategy,
    )
    @settings(max_examples=100)
    def test_property_cross_run_aggregate_output_completeness(
        self,
        base_task_name: str,
        run_count: int,
        total_task_count: int,
        mean_running: float,
        max_running: float,
        mean_cpu_ratio: float,
        mean_memory_ratio: float,
        total_estimated: float,
        recommended_instance: str,
    ):
        """Property 12: Output Completeness - CrossRunAggregate.

        For any multi-run analysis, the CrossRunAggregate output SHALL contain all required fields
        when multiple runs are provided.

        **Validates: Requirements 7.3**
        **Feature: run-analyzer-enhancement, Property 12: Output Completeness**
        """
        aggregate = CrossRunAggregate(
            baseTaskName=base_task_name,
            runCount=run_count,
            totalTaskCount=total_task_count,
            meanRunningSeconds=mean_running,
            maximumRunningSeconds=max_running,
            meanCpuUtilizationRatio=mean_cpu_ratio,
            meanMemoryUtilizationRatio=mean_memory_ratio,
            totalEstimatedUSD=total_estimated,
            recommendedInstanceType=recommended_instance,
        )

        # Property: All required fields are present and accessible
        assert hasattr(aggregate, 'baseTaskName')
        assert hasattr(aggregate, 'runCount')
        assert hasattr(aggregate, 'totalTaskCount')
        assert hasattr(aggregate, 'meanRunningSeconds')
        assert hasattr(aggregate, 'maximumRunningSeconds')
        assert hasattr(aggregate, 'meanCpuUtilizationRatio')
        assert hasattr(aggregate, 'meanMemoryUtilizationRatio')
        assert hasattr(aggregate, 'totalEstimatedUSD')
        assert hasattr(aggregate, 'recommendedInstanceType')

        # Property: Model can be serialized to dict with all fields
        data = aggregate.model_dump()
        required_fields = [
            'baseTaskName',
            'runCount',
            'totalTaskCount',
            'meanRunningSeconds',
            'maximumRunningSeconds',
            'meanCpuUtilizationRatio',
            'meanMemoryUtilizationRatio',
            'totalEstimatedUSD',
            'recommendedInstanceType',
        ]
        for field in required_fields:
            assert field in data, f'Missing required field: {field}'


class TestModelSerialization:
    """Test model serialization capabilities."""

    def test_task_cost_metrics_json_serialization(self):
        """Test TaskCostMetrics JSON serialization."""
        metrics = TaskCostMetrics(
            taskName='task',
            taskArn='arn',
            instanceType='omics.m.xlarge',
            runningSeconds=100.0,
            estimatedUSD=1.0,
            recommendedInstanceType='omics.m.large',
            recommendedCpus=2,
            recommendedMemoryGiB=8.0,
            minimumUSD=0.5,
            potentialSavingsUSD=0.5,
            isHighPrioritySaving=True,
        )

        json_str = metrics.model_dump_json()
        assert isinstance(json_str, str)
        assert 'task' in json_str
        assert 'omics.m.xlarge' in json_str

    def test_run_cost_summary_json_serialization(self):
        """Test RunCostSummary JSON serialization."""
        summary = RunCostSummary(
            runId='run-123',
            runName='test-run',
            totalEstimatedUSD=10.0,
            taskCostUSD=8.0,
            storageCostUSD=2.0,
            totalPotentialSavingsUSD=3.0,
            peakConcurrentCpus=16.0,
            peakConcurrentMemoryGiB=64.0,
            averageConcurrentCpus=8.0,
            averageConcurrentMemoryGiB=32.0,
        )

        json_str = summary.model_dump_json()
        assert isinstance(json_str, str)
        assert 'run-123' in json_str
        assert 'test-run' in json_str
