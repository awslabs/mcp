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

"""Unit tests for models."""

import pytest
from awslabs.aws_healthomics_mcp_server.models import (
    AnalysisResponse,
    AnalysisResult,
    CacheBehavior,
    ContainerRegistryMap,
    ExportType,
    GenomicsFileSearchRequest,
    ImageMapping,
    LogEvent,
    LogResponse,
    RegistryMapping,
    RunListResponse,
    RunStatus,
    RunSummary,
    StorageRequest,
    StorageType,
    TaskListResponse,
    TaskSummary,
    WorkflowListResponse,
    WorkflowSummary,
    WorkflowType,
)
from datetime import datetime, timezone
from pydantic import ValidationError


# Test Enum classes
def test_workflow_type_enum():
    """Test WorkflowType enum values."""
    assert WorkflowType.WDL == 'WDL'
    assert WorkflowType.NEXTFLOW == 'NEXTFLOW'
    assert WorkflowType.CWL == 'CWL'

    # Test enum membership
    assert WorkflowType.WDL in WorkflowType
    assert 'INVALID' not in [e.value for e in WorkflowType]


def test_storage_type_enum():
    """Test StorageType enum values."""
    assert StorageType.STATIC == 'STATIC'
    assert StorageType.DYNAMIC == 'DYNAMIC'

    # Test enum membership
    assert StorageType.STATIC in StorageType
    assert 'INVALID' not in [e.value for e in StorageType]


def test_cache_behavior_enum():
    """Test CacheBehavior enum values."""
    assert CacheBehavior.CACHE_ALWAYS == 'CACHE_ALWAYS'
    assert CacheBehavior.CACHE_ON_FAILURE == 'CACHE_ON_FAILURE'


def test_run_status_enum():
    """Test RunStatus enum values."""
    assert RunStatus.PENDING == 'PENDING'
    assert RunStatus.STARTING == 'STARTING'
    assert RunStatus.RUNNING == 'RUNNING'
    assert RunStatus.COMPLETED == 'COMPLETED'
    assert RunStatus.FAILED == 'FAILED'
    assert RunStatus.CANCELLED == 'CANCELLED'


def test_export_type_enum():
    """Test ExportType enum values."""
    assert ExportType.DEFINITION == 'DEFINITION'
    assert ExportType.PARAMETER_TEMPLATE == 'PARAMETER_TEMPLATE'


# Test Model classes
def test_workflow_summary():
    """Test WorkflowSummary model."""
    creation_time = datetime.now(timezone.utc)

    # Test with all fields
    workflow = WorkflowSummary(
        id='wfl-12345',
        arn='arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        name='test-workflow',
        description='Test workflow',
        status='ACTIVE',
        type='WDL',
        storageType='DYNAMIC',
        storageCapacity=100,
        creationTime=creation_time,
    )

    assert workflow.id == 'wfl-12345'
    assert workflow.name == 'test-workflow'
    assert workflow.creationTime == creation_time

    # Test with minimal fields
    workflow = WorkflowSummary(
        id='wfl-12345',
        arn='arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        status='ACTIVE',
        type='WDL',
        creationTime=creation_time,
    )

    assert workflow.name is None
    assert workflow.description is None
    assert workflow.storageType is None
    assert workflow.storageCapacity is None


def test_workflow_list_response():
    """Test WorkflowListResponse model."""
    creation_time = datetime.now(timezone.utc)
    workflows = [
        WorkflowSummary(
            id='wfl-12345',
            arn='arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
            status='ACTIVE',
            type='WDL',
            creationTime=creation_time,
        ),
        WorkflowSummary(
            id='wfl-67890',
            arn='arn:aws:omics:us-east-1:123456789012:workflow/wfl-67890',
            status='ACTIVE',
            type='CWL',
            creationTime=creation_time,
        ),
    ]

    # Test with next token
    response = WorkflowListResponse(workflows=workflows, nextToken='next-page-token')

    assert len(response.workflows) == 2
    assert response.nextToken == 'next-page-token'

    # Test without next token
    response = WorkflowListResponse(workflows=workflows)
    assert response.nextToken is None


def test_run_summary():
    """Test RunSummary model."""
    creation_time = datetime.now(timezone.utc)
    start_time = datetime.now(timezone.utc)
    stop_time = datetime.now(timezone.utc)

    # Test with all fields
    run = RunSummary(
        id='run-12345',
        arn='arn:aws:omics:us-east-1:123456789012:run/run-12345',
        name='test-run',
        parameters={'param1': 'value1'},
        status='COMPLETED',
        workflowId='wfl-12345',
        workflowType='WDL',
        creationTime=creation_time,
        startTime=start_time,
        stopTime=stop_time,
    )

    assert run.id == 'run-12345'
    assert run.name == 'test-run'
    assert run.parameters == {'param1': 'value1'}
    assert run.startTime == start_time
    assert run.stopTime == stop_time

    # Test with minimal fields
    run = RunSummary(
        id='run-12345',
        arn='arn:aws:omics:us-east-1:123456789012:run/run-12345',
        status='PENDING',
        workflowId='wfl-12345',
        workflowType='WDL',
        creationTime=creation_time,
    )

    assert run.name is None
    assert run.parameters is None
    assert run.startTime is None
    assert run.stopTime is None


def test_run_list_response():
    """Test RunListResponse model."""
    creation_time = datetime.now(timezone.utc)
    runs = [
        RunSummary(
            id='run-12345',
            arn='arn:aws:omics:us-east-1:123456789012:run/run-12345',
            status='COMPLETED',
            workflowId='wfl-12345',
            workflowType='WDL',
            creationTime=creation_time,
        ),
        RunSummary(
            id='run-67890',
            arn='arn:aws:omics:us-east-1:123456789012:run/run-67890',
            status='RUNNING',
            workflowId='wfl-67890',
            workflowType='CWL',
            creationTime=creation_time,
        ),
    ]

    # Test with next token
    response = RunListResponse(runs=runs, nextToken='next-page-token')

    assert len(response.runs) == 2
    assert response.nextToken == 'next-page-token'

    # Test without next token
    response = RunListResponse(runs=runs)
    assert response.nextToken is None


def test_task_summary():
    """Test TaskSummary model."""
    start_time = datetime.now(timezone.utc)
    stop_time = datetime.now(timezone.utc)

    # Test with all fields
    task = TaskSummary(
        taskId='task-12345',
        status='COMPLETED',
        name='test-task',
        cpus=4,
        memory=16,
        startTime=start_time,
        stopTime=stop_time,
    )

    assert task.taskId == 'task-12345'
    assert task.name == 'test-task'
    assert task.cpus == 4
    assert task.memory == 16
    assert task.startTime == start_time
    assert task.stopTime == stop_time

    # Test with minimal fields
    task = TaskSummary(
        taskId='task-12345',
        status='PENDING',
        name='test-task',
        cpus=2,
        memory=8,
    )

    assert task.startTime is None
    assert task.stopTime is None


def test_task_list_response():
    """Test TaskListResponse model."""
    tasks = [
        TaskSummary(
            taskId='task-12345',
            status='COMPLETED',
            name='test-task-1',
            cpus=4,
            memory=16,
        ),
        TaskSummary(
            taskId='task-67890',
            status='RUNNING',
            name='test-task-2',
            cpus=2,
            memory=8,
        ),
    ]

    # Test with next token
    response = TaskListResponse(tasks=tasks, nextToken='next-page-token')

    assert len(response.tasks) == 2
    assert response.nextToken == 'next-page-token'

    # Test without next token
    response = TaskListResponse(tasks=tasks)
    assert response.nextToken is None


def test_log_event():
    """Test LogEvent model."""
    timestamp = datetime.now(timezone.utc)

    event = LogEvent(timestamp=timestamp, message='Test log message')

    assert event.timestamp == timestamp
    assert event.message == 'Test log message'


def test_log_response():
    """Test LogResponse model."""
    timestamp = datetime.now(timezone.utc)
    events = [
        LogEvent(timestamp=timestamp, message='Log message 1'),
        LogEvent(timestamp=timestamp, message='Log message 2'),
    ]

    # Test with next token
    response = LogResponse(events=events, nextToken='next-page-token')

    assert len(response.events) == 2
    assert response.nextToken == 'next-page-token'

    # Test without next token
    response = LogResponse(events=events)
    assert response.nextToken is None


def test_storage_request():
    """Test StorageRequest model."""
    # Test DYNAMIC storage without capacity
    request = StorageRequest(storageType=StorageType.DYNAMIC)
    assert request.storageType == StorageType.DYNAMIC
    assert request.storageCapacity is None

    # Test STATIC storage with capacity
    request = StorageRequest(storageType=StorageType.STATIC, storageCapacity=100)
    assert request.storageType == StorageType.STATIC
    assert request.storageCapacity == 100

    # Test STATIC storage without capacity (should raise error)
    with pytest.raises(ValidationError) as exc_info:
        StorageRequest(storageType=StorageType.STATIC)

    assert 'Storage capacity is required when using STATIC storage type' in str(exc_info.value)


def test_analysis_result():
    """Test AnalysisResult model."""
    result = AnalysisResult(
        taskName='test-task',
        count=10,
        meanRunningSeconds=120.5,
        maximumRunningSeconds=180.0,
        stdDevRunningSeconds=15.2,
        maximumCpuUtilizationRatio=0.85,
        meanCpuUtilizationRatio=0.65,
        maximumMemoryUtilizationRatio=0.75,
        meanMemoryUtilizationRatio=0.55,
        recommendedCpus=4,
        recommendedMemoryGiB=16.0,
        recommendedInstanceType='t3.xlarge',
        maximumEstimatedUSD=1.25,
        meanEstimatedUSD=0.95,
    )

    assert result.taskName == 'test-task'
    assert result.count == 10
    assert result.meanRunningSeconds == 120.5
    assert result.maximumRunningSeconds == 180.0
    assert result.stdDevRunningSeconds == 15.2
    assert result.maximumCpuUtilizationRatio == 0.85
    assert result.meanCpuUtilizationRatio == 0.65
    assert result.maximumMemoryUtilizationRatio == 0.75
    assert result.meanMemoryUtilizationRatio == 0.55
    assert result.recommendedCpus == 4
    assert result.recommendedMemoryGiB == 16.0
    assert result.recommendedInstanceType == 't3.xlarge'
    assert result.maximumEstimatedUSD == 1.25
    assert result.meanEstimatedUSD == 0.95


def test_analysis_response():
    """Test AnalysisResponse model."""
    results = [
        AnalysisResult(
            taskName='test-task-1',
            count=10,
            meanRunningSeconds=120.5,
            maximumRunningSeconds=180.0,
            stdDevRunningSeconds=15.2,
            maximumCpuUtilizationRatio=0.85,
            meanCpuUtilizationRatio=0.65,
            maximumMemoryUtilizationRatio=0.75,
            meanMemoryUtilizationRatio=0.55,
            recommendedCpus=4,
            recommendedMemoryGiB=16.0,
            recommendedInstanceType='t3.xlarge',
            maximumEstimatedUSD=1.25,
            meanEstimatedUSD=0.95,
        ),
        AnalysisResult(
            taskName='test-task-2',
            count=5,
            meanRunningSeconds=90.0,
            maximumRunningSeconds=120.0,
            stdDevRunningSeconds=10.5,
            maximumCpuUtilizationRatio=0.75,
            meanCpuUtilizationRatio=0.55,
            maximumMemoryUtilizationRatio=0.65,
            meanMemoryUtilizationRatio=0.45,
            recommendedCpus=2,
            recommendedMemoryGiB=8.0,
            recommendedInstanceType='t3.large',
            maximumEstimatedUSD=0.75,
            meanEstimatedUSD=0.55,
        ),
    ]

    response = AnalysisResponse(results=results)
    assert len(response.results) == 2
    assert response.results[0].taskName == 'test-task-1'
    assert response.results[1].taskName == 'test-task-2'


# Test edge cases and validation
def test_workflow_summary_validation():
    """Test WorkflowSummary validation."""
    # Test missing required fields
    with pytest.raises(ValidationError):
        WorkflowSummary(  # type: ignore
            # Missing required fields: id, arn, status, type, creationTime
        )

    # Test with invalid datetime
    with pytest.raises(ValidationError):
        WorkflowSummary(
            id='wfl-12345',
            arn='arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
            status='ACTIVE',
            type='PRIVATE',
            creationTime='invalid-datetime',  # type: ignore
        )


def test_run_summary_validation():
    """Test RunSummary validation."""
    creation_time = datetime.now(timezone.utc)

    # Test missing required fields
    with pytest.raises(ValidationError):
        RunSummary(  # type: ignore
            # Missing required fields: id, arn, status, workflowId, workflowType, creationTime
        )

    # Test with all required fields
    run = RunSummary(
        id='run-12345',
        arn='arn:aws:omics:us-east-1:123456789012:run/run-12345',
        status='PENDING',
        workflowId='wfl-12345',
        workflowType='WDL',
        creationTime=creation_time,
    )
    assert run.id == 'run-12345'


def test_task_summary_validation():
    """Test TaskSummary validation."""
    # Test missing required fields
    with pytest.raises(ValidationError):
        TaskSummary(  # type: ignore
            # Missing required fields: taskId, status, name, cpus, memory
        )

    # Test with all required fields
    task = TaskSummary(
        taskId='task-12345',
        status='PENDING',
        name='test-task',
        cpus=2,
        memory=8,
    )
    assert task.taskId == 'task-12345'


def test_log_event_validation():
    """Test LogEvent validation."""
    timestamp = datetime.now(timezone.utc)

    # Test missing required fields
    with pytest.raises(ValidationError):
        LogEvent(  # type: ignore
            # Missing required fields: timestamp, message
        )

    # Test with all required fields
    event = LogEvent(timestamp=timestamp, message='Test message')
    assert event.message == 'Test message'


def test_storage_request_edge_cases():
    """Test StorageRequest edge cases."""
    # Test DYNAMIC with capacity (should be allowed)
    request = StorageRequest(storageType=StorageType.DYNAMIC, storageCapacity=100)
    assert request.storageCapacity == 100

    # Test STATIC with zero capacity (should raise error)
    with pytest.raises(ValidationError):
        StorageRequest(storageType=StorageType.STATIC, storageCapacity=None)


def test_analysis_result_validation():
    """Test AnalysisResult validation."""
    # Test missing required fields
    with pytest.raises(ValidationError):
        AnalysisResult(  # type: ignore
            # Missing required fields: taskName, count, meanRunningSeconds, maximumRunningSeconds,
            # stdDevRunningSeconds, maximumCpuUtilizationRatio, meanCpuUtilizationRatio,
            # maximumMemoryUtilizationRatio, meanMemoryUtilizationRatio, recommendedCpus,
            # recommendedMemoryGiB, recommendedInstanceType, maximumEstimatedUSD, meanEstimatedUSD
        )

    # Test with negative values (should be allowed as no constraints defined)
    result = AnalysisResult(
        taskName='test-task',
        count=0,
        meanRunningSeconds=0.0,
        maximumRunningSeconds=0.0,
        stdDevRunningSeconds=0.0,
        maximumCpuUtilizationRatio=0.0,
        meanCpuUtilizationRatio=0.0,
        maximumMemoryUtilizationRatio=0.0,
        meanMemoryUtilizationRatio=0.0,
        recommendedCpus=0,
        recommendedMemoryGiB=0.0,
        recommendedInstanceType='',
        maximumEstimatedUSD=0.0,
        meanEstimatedUSD=0.0,
    )
    assert result.count == 0


def test_empty_lists():
    """Test models with empty lists."""
    # Test empty workflow list
    response = WorkflowListResponse(workflows=[])
    assert len(response.workflows) == 0

    # Test empty run list
    response = RunListResponse(runs=[])
    assert len(response.runs) == 0

    # Test empty task list
    response = TaskListResponse(tasks=[])
    assert len(response.tasks) == 0

    # Test empty log events
    response = LogResponse(events=[])
    assert len(response.events) == 0

    # Test empty analysis results
    response = AnalysisResponse(results=[])
    assert len(response.results) == 0


def test_model_serialization():
    """Test model serialization to dict."""
    creation_time = datetime.now(timezone.utc)

    workflow = WorkflowSummary(
        id='wfl-12345',
        arn='arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        name='test-workflow',
        status='ACTIVE',
        type='WDL',
        creationTime=creation_time,
    )

    # Test model_dump
    data = workflow.model_dump()
    assert data['id'] == 'wfl-12345'
    assert data['name'] == 'test-workflow'
    assert isinstance(data['creationTime'], datetime)

    # Test model_dump with exclude_none
    workflow_minimal = WorkflowSummary(
        id='wfl-12345',
        arn='arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        status='ACTIVE',
        type='WDL',
        creationTime=creation_time,
    )

    data = workflow_minimal.model_dump(exclude_none=True)
    assert 'name' not in data
    assert 'description' not in data
    assert data['id'] == 'wfl-12345'


def test_model_json_serialization():
    """Test model JSON serialization."""
    creation_time = datetime.now(timezone.utc)

    workflow = WorkflowSummary(
        id='wfl-12345',
        arn='arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        name='test-workflow',
        status='ACTIVE',
        type='WDL',
        creationTime=creation_time,
    )

    # Test JSON serialization
    json_str = workflow.model_dump_json()
    assert isinstance(json_str, str)
    assert 'wfl-12345' in json_str
    assert 'test-workflow' in json_str


# Test Container Registry Map models
def test_registry_mapping():
    """Test RegistryMapping model."""
    mapping = RegistryMapping(
        upstreamRegistryUrl='docker.io',
        ecrRepositoryPrefix='my-prefix',
        upstreamRepositoryPrefix='library',
        ecrAccountId='123456789012',
    )

    assert mapping.upstreamRegistryUrl == 'docker.io'
    assert mapping.ecrRepositoryPrefix == 'my-prefix'
    assert mapping.upstreamRepositoryPrefix == 'library'
    assert mapping.ecrAccountId == '123456789012'


def test_registry_mapping_validation():
    """Test RegistryMapping validation."""
    # Test missing required fields
    with pytest.raises(ValidationError):
        RegistryMapping(  # type: ignore
            # Missing required fields
        )

    # Test with all required fields
    mapping = RegistryMapping(
        upstreamRegistryUrl='docker.io',
        ecrRepositoryPrefix='my-prefix',
        upstreamRepositoryPrefix='library',
        ecrAccountId='123456789012',
    )
    assert mapping.upstreamRegistryUrl == 'docker.io'


def test_image_mapping():
    """Test ImageMapping model."""
    mapping = ImageMapping(
        sourceImage='nginx:latest',
        destinationImage='123456789012.dkr.ecr.us-east-1.amazonaws.com/nginx:latest',
    )

    assert mapping.sourceImage == 'nginx:latest'
    assert mapping.destinationImage == '123456789012.dkr.ecr.us-east-1.amazonaws.com/nginx:latest'


def test_image_mapping_validation():
    """Test ImageMapping validation."""
    # Test missing required fields
    with pytest.raises(ValidationError):
        ImageMapping(  # type: ignore
            # Missing required fields
        )

    # Test with all required fields
    mapping = ImageMapping(
        sourceImage='nginx:latest',
        destinationImage='123456789012.dkr.ecr.us-east-1.amazonaws.com/nginx:latest',
    )
    assert mapping.sourceImage == 'nginx:latest'


def test_container_registry_map():
    """Test ContainerRegistryMap model."""
    # Test with empty lists (defaults)
    registry_map = ContainerRegistryMap()
    assert registry_map.registryMappings == []
    assert registry_map.imageMappings == []

    # Test with data
    registry_mappings = [
        RegistryMapping(
            upstreamRegistryUrl='docker.io',
            ecrRepositoryPrefix='my-prefix',
            upstreamRepositoryPrefix='library',
            ecrAccountId='123456789012',
        )
    ]
    image_mappings = [
        ImageMapping(
            sourceImage='nginx:latest',
            destinationImage='123456789012.dkr.ecr.us-east-1.amazonaws.com/nginx:latest',
        )
    ]

    registry_map = ContainerRegistryMap(
        registryMappings=registry_mappings,  # type: ignore[arg-type]
        imageMappings=image_mappings,  # type: ignore[arg-type]
    )

    assert len(registry_map.registryMappings) == 1
    assert len(registry_map.imageMappings) == 1
    assert registry_map.registryMappings[0].upstreamRegistryUrl == 'docker.io'
    assert registry_map.imageMappings[0].sourceImage == 'nginx:latest'


def test_container_registry_map_none_conversion():
    """Test ContainerRegistryMap None value conversion."""
    # Test None values are converted to empty lists
    registry_map = ContainerRegistryMap(
        registryMappings=None,  # type: ignore[arg-type]
        imageMappings=None,  # type: ignore[arg-type]
    )

    assert registry_map.registryMappings == []
    assert registry_map.imageMappings == []
    assert isinstance(registry_map.registryMappings, list)
    assert isinstance(registry_map.imageMappings, list)


def test_container_registry_map_dict_creation():
    """Test ContainerRegistryMap creation from dictionary."""
    # Test with dictionary input (as would come from API)
    data = {
        'registryMappings': [
            {
                'upstreamRegistryUrl': 'docker.io',
                'ecrRepositoryPrefix': 'my-prefix',
                'upstreamRepositoryPrefix': 'library',
                'ecrAccountId': '123456789012',
            }
        ],
        'imageMappings': [
            {
                'sourceImage': 'nginx:latest',
                'destinationImage': '123456789012.dkr.ecr.us-east-1.amazonaws.com/nginx:latest',
            }
        ],
    }

    registry_map = ContainerRegistryMap(**data)  # type: ignore[arg-type]
    assert len(registry_map.registryMappings) == 1
    assert len(registry_map.imageMappings) == 1
    assert registry_map.registryMappings[0].upstreamRegistryUrl == 'docker.io'
    assert registry_map.imageMappings[0].sourceImage == 'nginx:latest'


def test_container_registry_map_empty_dict():
    """Test ContainerRegistryMap with empty dictionary."""
    # Test with empty dictionary
    data = {}
    registry_map = ContainerRegistryMap(**data)
    assert registry_map.registryMappings == []
    assert registry_map.imageMappings == []

    # Test with None values in dictionary
    data = {'registryMappings': None, 'imageMappings': None}
    registry_map = ContainerRegistryMap(**data)  # type: ignore[arg-type]
    assert registry_map.registryMappings == []
    assert registry_map.imageMappings == []


def test_container_registry_map_validation_errors():
    """Test ContainerRegistryMap validation errors."""
    # Test with invalid registry mapping structure
    with pytest.raises(ValidationError):
        ContainerRegistryMap(
            registryMappings=[  # type: ignore[arg-type]
                {
                    'upstreamRegistryUrl': 'docker.io',
                    # Missing required fields
                }
            ]
        )

    # Test with invalid image mapping structure
    with pytest.raises(ValidationError):
        ContainerRegistryMap(
            imageMappings=[  # type: ignore[arg-type]
                {
                    'sourceImage': 'nginx:latest',
                    # Missing destinationImage
                }
            ]
        )


def test_container_registry_map_serialization():
    """Test ContainerRegistryMap serialization."""
    registry_map = ContainerRegistryMap(
        registryMappings=[
            RegistryMapping(
                upstreamRegistryUrl='registry-url',
                ecrRepositoryPrefix='my-prefix',
                upstreamRepositoryPrefix='library',
                ecrAccountId='123456789012',
            )
        ],
        imageMappings=[
            ImageMapping(
                sourceImage='nginx:latest',
                destinationImage='123456789012.dkr.ecr.us-east-1.amazonaws.com/nginx:latest',
            )
        ],
    )

    # Test model_dump
    data = registry_map.model_dump()
    assert 'registryMappings' in data
    assert 'imageMappings' in data
    assert len(data['registryMappings']) == 1
    assert len(data['imageMappings']) == 1

    # Test JSON serialization
    json_str = registry_map.model_dump_json()
    assert isinstance(json_str, str)
    assert 'registry-url' in json_str
    assert 'nginx:latest' in json_str


def test_genomics_file_search_request_validation():
    """Test GenomicsFileSearchRequest validation."""
    # Test valid request
    request = GenomicsFileSearchRequest(
        file_type='fastq', search_terms=['sample'], max_results=100, pagination_buffer_size=500
    )
    assert request.max_results == 100
    assert request.pagination_buffer_size == 500

    # Test max_results validation - too high
    with pytest.raises(ValidationError) as exc_info:
        GenomicsFileSearchRequest(max_results=15000)
    assert 'max_results cannot exceed 10000' in str(exc_info.value)

    # Test pagination_buffer_size validation - too low
    with pytest.raises(ValidationError) as exc_info:
        GenomicsFileSearchRequest(pagination_buffer_size=50)
    assert 'pagination_buffer_size must be at least 100' in str(exc_info.value)

    # Test pagination_buffer_size validation - too high
    with pytest.raises(ValidationError) as exc_info:
        GenomicsFileSearchRequest(pagination_buffer_size=60000)
    assert 'pagination_buffer_size cannot exceed 50000' in str(exc_info.value)


def test_genomics_file_search_request_adhoc_s3_buckets_validation():
    """Test GenomicsFileSearchRequest adhoc_s3_buckets validation."""
    # Test valid adhoc buckets
    request = GenomicsFileSearchRequest(
        adhoc_s3_buckets=['s3://test-bucket/', 's3://another-bucket/path/']
    )
    assert request.adhoc_s3_buckets == ['s3://test-bucket/', 's3://another-bucket/path/']

    # Test None value (should be allowed)
    request = GenomicsFileSearchRequest(adhoc_s3_buckets=None)
    assert request.adhoc_s3_buckets is None

    # Test empty list (should be converted to None)
    request = GenomicsFileSearchRequest(adhoc_s3_buckets=[])
    assert request.adhoc_s3_buckets is None

    # Test non-list value (Pydantic type validation)
    with pytest.raises(ValidationError) as exc_info:
        GenomicsFileSearchRequest(adhoc_s3_buckets='s3://test-bucket/')  # type: ignore[arg-type]
    assert 'Input should be a valid list' in str(exc_info.value)

    # Test too many buckets (more than 50)
    too_many_buckets = [f's3://bucket-{i}/' for i in range(51)]
    with pytest.raises(ValidationError) as exc_info:
        GenomicsFileSearchRequest(adhoc_s3_buckets=too_many_buckets)
    assert 'adhoc_s3_buckets cannot contain more than 50 bucket paths' in str(exc_info.value)

    # Test non-string entries (Pydantic will catch this at type level)
    with pytest.raises(ValidationError) as exc_info:
        GenomicsFileSearchRequest(adhoc_s3_buckets=['s3://valid-bucket/', 123])  # type: ignore[list-item]
    # Pydantic validates list item types, so this will be caught before our validator
    assert 'Input should be a valid string' in str(exc_info.value)

    # Test invalid S3 path format
    with pytest.raises(ValidationError) as exc_info:
        GenomicsFileSearchRequest(adhoc_s3_buckets=['invalid-path'])
    assert 'Invalid S3 bucket path "invalid-path"' in str(exc_info.value)

    # Test invalid S3 path format with special characters
    with pytest.raises(ValidationError) as exc_info:
        GenomicsFileSearchRequest(adhoc_s3_buckets=['s3://bucket with spaces/'])
    assert 'Invalid S3 bucket path "s3://bucket with spaces/"' in str(exc_info.value)


def test_genomics_file_search_response():
    """Test GenomicsFileSearchResponse model."""
    from awslabs.aws_healthomics_mcp_server.models.search import GenomicsFileSearchResponse

    # Test basic response
    response = GenomicsFileSearchResponse(
        results=[{'file': 'test.fastq', 'score': 0.9}],
        total_found=1,
        search_duration_ms=150,
        storage_systems_searched=['s3', 'healthomics'],
    )

    assert len(response.results) == 1
    assert response.total_found == 1
    assert response.search_duration_ms == 150
    assert response.storage_systems_searched == ['s3', 'healthomics']
    assert response.enhanced_response is None

    # Test with enhanced response
    enhanced_data = {'pagination': {'has_more': False}, 'stats': {'cache_hits': 5}}
    response_with_enhanced = GenomicsFileSearchResponse(
        results=[],
        total_found=0,
        search_duration_ms=50,
        storage_systems_searched=['s3'],
        enhanced_response=enhanced_data,
    )

    assert response_with_enhanced.enhanced_response == enhanced_data


def test_storage_pagination_request():
    """Test StoragePaginationRequest dataclass."""
    from awslabs.aws_healthomics_mcp_server.models.search import StoragePaginationRequest

    # Test default values
    request = StoragePaginationRequest()
    assert request.max_results == 100
    assert request.continuation_token is None
    assert request.buffer_size == 500

    # Test custom values
    request = StoragePaginationRequest(
        max_results=50, continuation_token='token123', buffer_size=1000
    )
    assert request.max_results == 50
    assert request.continuation_token == 'token123'
    assert request.buffer_size == 1000

    # Test buffer size auto-adjustment when too small (less than max_results)
    request = StoragePaginationRequest(max_results=300, buffer_size=200)
    assert request.buffer_size == 600  # Should be max_results * 2

    # Test buffer size auto-adjustment with minimum when buffer < max_results
    request = StoragePaginationRequest(max_results=100, buffer_size=50)
    assert request.buffer_size == 500  # Should use minimum of 500 (max of max_results * 2 and 500)

    # Test buffer size NOT adjusted when buffer >= max_results
    request = StoragePaginationRequest(max_results=100, buffer_size=150)
    assert request.buffer_size == 150  # Should remain unchanged since 150 >= 100

    # Test validation errors
    with pytest.raises(ValueError, match='max_results must be greater than 0'):
        StoragePaginationRequest(max_results=0)

    with pytest.raises(ValueError, match='max_results cannot exceed 10000'):
        StoragePaginationRequest(max_results=15000)


# Tests for DefinitionRepository model validation


class TestDefinitionRepositoryModel:
    """Test cases for DefinitionRepository model validation."""

    def test_definition_repository_valid(self):
        """Test DefinitionRepository with valid data."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            DefinitionRepository,
            SourceReference,
            SourceReferenceType,
        )

        repo = DefinitionRepository(
            connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123',
            full_repository_id='owner/repo',
            source_reference=SourceReference(type=SourceReferenceType.BRANCH, value='main'),
        )

        assert (
            repo.connection_arn
            == 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123'
        )
        assert repo.full_repository_id == 'owner/repo'
        assert repo.source_reference.type.value == 'BRANCH'
        assert repo.source_reference.value == 'main'

    def test_definition_repository_empty_full_repository_id(self):
        """Test DefinitionRepository rejects empty full_repository_id."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            DefinitionRepository,
            SourceReference,
            SourceReferenceType,
        )

        with pytest.raises(ValidationError) as exc_info:
            DefinitionRepository(
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123',
                full_repository_id='',  # Empty string
                source_reference=SourceReference(type=SourceReferenceType.BRANCH, value='main'),
            )

        assert 'full_repository_id cannot be empty' in str(exc_info.value)

    def test_definition_repository_whitespace_full_repository_id(self):
        """Test DefinitionRepository rejects whitespace-only full_repository_id."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            DefinitionRepository,
            SourceReference,
            SourceReferenceType,
        )

        with pytest.raises(ValidationError) as exc_info:
            DefinitionRepository(
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123',
                full_repository_id='   ',  # Whitespace only
                source_reference=SourceReference(type=SourceReferenceType.BRANCH, value='main'),
            )

        assert 'full_repository_id cannot be empty' in str(exc_info.value)

    def test_definition_repository_invalid_connection_arn(self):
        """Test DefinitionRepository rejects invalid connection_arn."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            DefinitionRepository,
            SourceReference,
            SourceReferenceType,
        )

        with pytest.raises(ValidationError) as exc_info:
            DefinitionRepository(
                connection_arn='invalid-arn',  # Invalid ARN format
                full_repository_id='owner/repo',
                source_reference=SourceReference(type=SourceReferenceType.BRANCH, value='main'),
            )

        assert 'connection_arn must be a valid AWS CodeConnection ARN' in str(exc_info.value)

    def test_definition_repository_with_exclude_patterns(self):
        """Test DefinitionRepository with exclude_file_patterns."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            DefinitionRepository,
            SourceReference,
            SourceReferenceType,
        )

        repo = DefinitionRepository(
            connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123',
            full_repository_id='owner/repo',
            source_reference=SourceReference(type=SourceReferenceType.TAG, value='v1.0.0'),
            exclude_file_patterns=['*.md', 'tests/*', '.github/*'],
        )

        assert repo.exclude_file_patterns == ['*.md', 'tests/*', '.github/*']


class TestSourceReferenceModel:
    """Test cases for SourceReference model validation."""

    def test_source_reference_valid_branch(self):
        """Test SourceReference with valid BRANCH type."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            SourceReference,
            SourceReferenceType,
        )

        ref = SourceReference(type=SourceReferenceType.BRANCH, value='main')
        assert ref.type.value == 'BRANCH'
        assert ref.value == 'main'

    def test_source_reference_valid_tag(self):
        """Test SourceReference with valid TAG type."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            SourceReference,
            SourceReferenceType,
        )

        ref = SourceReference(type=SourceReferenceType.TAG, value='v1.0.0')
        assert ref.type.value == 'TAG'
        assert ref.value == 'v1.0.0'

    def test_source_reference_valid_commit_id(self):
        """Test SourceReference with valid COMMIT_ID type."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            SourceReference,
            SourceReferenceType,
        )

        ref = SourceReference(type=SourceReferenceType.COMMIT_ID, value='abc')
        assert ref.type.value == 'COMMIT_ID'
        assert ref.value == 'abc'

    def test_source_reference_empty_value(self):
        """Test SourceReference rejects empty value."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            SourceReference,
            SourceReferenceType,
        )

        with pytest.raises(ValidationError) as exc_info:
            SourceReference(type=SourceReferenceType.BRANCH, value='')

        assert 'source_reference.value cannot be empty' in str(exc_info.value)

    def test_source_reference_whitespace_value(self):
        """Test SourceReference rejects whitespace-only value."""
        from awslabs.aws_healthomics_mcp_server.models.core import (
            SourceReference,
            SourceReferenceType,
        )

        with pytest.raises(ValidationError) as exc_info:
            SourceReference(type=SourceReferenceType.TAG, value='   ')

        assert 'source_reference.value cannot be empty' in str(exc_info.value)

    def test_source_reference_invalid_type(self):
        """Test SourceReference rejects invalid type."""
        from awslabs.aws_healthomics_mcp_server.models.core import SourceReference

        with pytest.raises(ValidationError):
            SourceReference(type='INVALID_TYPE', value='main')  # type: ignore[arg-type]
