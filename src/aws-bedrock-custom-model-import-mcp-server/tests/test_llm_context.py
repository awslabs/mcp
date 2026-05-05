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

"""Tests for the llm_context module."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.llm_context import (
    build_bedrock_knowledge,
    build_imported_model_details_context,
    build_list_imported_models_context,
    build_list_model_import_jobs_context,
    build_model_import_job_details_context,
    build_model_import_knowledge,
    dict_to_markdown,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    CustomModelUnits,
    ImportedModel,
    JobStatus,
    ListImportedModelsResponse,
    ListModelImportJobsResponse,
    ModelDataSource,
    ModelImportJob,
    ModelImportJobSummary,
    ModelSummary,
    S3DataSource,
)
from datetime import datetime


class TestLlmContext:
    """Tests for the llm_context module."""

    @pytest.fixture
    def model_import_job(self):
        """Fixture for creating a ModelImportJob instance."""
        return ModelImportJob(
            jobArn='test-job-arn',
            jobName='test-job',
            importedModelName='test-model',
            importedModelArn='test-model-arn',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            status=JobStatus.IN_PROGRESS,
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            lastModifiedTime=datetime(2025, 1, 1, 12, 0, 0),
            failureMessage=None,
            endTime=None,
            vpcConfig=None,
            importedModelKmsKeyArn=None,
        )

    @pytest.fixture
    def imported_model(self):
        """Fixture for creating an ImportedModel instance."""
        return ImportedModel(
            modelArn='test-model-arn',
            modelName='test-model',
            jobName='test-job',
            jobArn='test-job-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            modelArchitecture='llama2',
            instructSupported=True,
            customModelUnits=CustomModelUnits(
                customModelUnitsPerModelCopy=1,
                customModelUnitsVersion='1.0',
            ),
            modelKmsKeyArn=None,
        )

    @pytest.fixture
    def list_model_import_jobs_response(self):
        """Fixture for creating a ListModelImportJobsResponse instance."""
        job_summary = ModelImportJobSummary(
            jobArn='test-job-arn',
            jobName='test-job',
            status=JobStatus.IN_PROGRESS,
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            lastModifiedTime=datetime(2025, 1, 1, 12, 0, 0),
            importedModelName='test-model',
            endTime=None,
            importedModelArn=None,
        )
        return ListModelImportJobsResponse(
            modelImportJobSummaries=[job_summary],
            nextToken=None,
        )

    @pytest.fixture
    def list_imported_models_response(self):
        """Fixture for creating a ListImportedModelsResponse instance."""
        model_summary = ModelSummary(
            modelArn='test-model-arn',
            modelName='test-model',
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            instructSupported=True,
            modelArchitecture='llama2',
        )
        return ListImportedModelsResponse(
            modelSummaries=[model_summary],
            nextToken=None,
        )

    def test_build_bedrock_knowledge(self):
        """Test build_bedrock_knowledge function."""
        # Execute
        result = build_bedrock_knowledge()

        # Verify
        assert isinstance(result, dict)
        assert 'service_description' in result
        assert 'custom_models' in result
        assert 'Amazon Bedrock' in result['service_description']

    def test_build_model_import_knowledge(self):
        """Test build_model_import_knowledge function."""
        # Execute
        result = build_model_import_knowledge()

        # Verify
        assert isinstance(result, dict)
        assert 'import_process' in result
        assert 'supported_formats' in result
        assert 'permissions' in result
        assert 'Importing a model' in result['import_process']

    def test_build_list_model_import_jobs_context(self, list_model_import_jobs_response):
        """Test build_list_model_import_jobs_context function."""
        # Execute
        result = build_list_model_import_jobs_context(list_model_import_jobs_response)

        # Verify
        assert isinstance(result, str)
        assert 'Bedrock Knowledge' in result
        assert 'Model Import Knowledge' in result
        assert 'Job Guidance' in result
        assert 'Job Status' in result
        assert 'Job Naming' in result
        assert 'Job Filtering' in result

    def test_build_list_imported_models_context(self, list_imported_models_response):
        """Test build_list_imported_models_context function."""
        # Execute
        result = build_list_imported_models_context(list_imported_models_response)

        # Verify
        assert isinstance(result, str)
        assert 'Bedrock Knowledge' in result
        assert 'Model Import Knowledge' in result
        assert 'Model Guidance' in result
        assert 'Model Usage' in result
        assert 'Model Architecture' in result
        assert 'Instruct Support' in result

    def test_build_model_import_job_details_context(self, model_import_job):
        """Test build_model_import_job_details_context function."""
        # Execute
        result = build_model_import_job_details_context(model_import_job)

        # Verify
        assert isinstance(result, str)
        assert 'Bedrock Knowledge' in result
        assert 'Model Import Knowledge' in result
        assert 'Job Guidance' in result
        assert 'Status Guidance' in result
        assert 'Monitoring' in result
        assert 'Duration' in result

    def test_build_model_import_job_details_context_completed(self, model_import_job):
        """Test build_model_import_job_details_context function with completed job."""
        # Setup
        model_import_job.status = JobStatus.COMPLETED
        model_import_job.end_time = datetime(2025, 1, 1, 13, 0, 0)

        # Execute
        result = build_model_import_job_details_context(model_import_job)

        # Verify
        assert isinstance(result, str)
        assert 'Status Guidance' in result
        assert 'Next Steps' in result
        assert 'Model Access' in result

    def test_build_model_import_job_details_context_failed(self, model_import_job):
        """Test build_model_import_job_details_context function with failed job."""
        # Setup
        model_import_job.status = JobStatus.FAILED
        model_import_job.failure_message = 'Test failure message'
        model_import_job.end_time = datetime(2025, 1, 1, 13, 0, 0)

        # Execute
        result = build_model_import_job_details_context(model_import_job)

        # Verify
        assert isinstance(result, str)
        assert 'Status Guidance' in result
        assert 'Troubleshooting' in result
        assert 'Common Issues' in result

    def test_build_imported_model_details_context(self, imported_model):
        """Test build_imported_model_details_context function."""
        # Execute
        result = build_imported_model_details_context(imported_model)

        # Verify
        assert isinstance(result, str)
        assert 'Bedrock Knowledge' in result
        assert 'Model Import Knowledge' in result
        assert 'Model Guidance' in result
        assert 'Architecture Guidance' in result
        assert 'Model Usage' in result
        assert 'Model Architecture' in result
        assert 'Instruct Support' in result
        assert 'Billing' in result

    def test_dict_to_markdown(self):
        """Test dict_to_markdown function."""
        # Setup
        test_dict = {
            'section1': 'This is section 1 content.',
            'section2': {
                'subsection1': 'This is subsection 1 content.',
                'subsection2': 'This is subsection 2 content.',
            },
            'section3': ['item1', 'item2', 'item3'],
            'section4': True,
            'section5': [
                {'name': 'item1', 'value': 'value1'},
                {'name': 'item2', 'value': 'value2'},
            ],
        }

        # Execute
        result = dict_to_markdown(test_dict)

        # Verify
        assert isinstance(result, str)
        assert '## Section1' in result
        assert 'This is section 1 content.' in result
        assert '## Section2' in result
        assert '### Subsection1' in result
        assert 'This is subsection 1 content.' in result
        assert '### Subsection2' in result
        assert 'This is subsection 2 content.' in result
        assert '## Section3' in result
        assert '- item1' in result
        assert '- item2' in result
        assert '- item3' in result
        assert '## Section4' in result
        assert 'Yes' in result
        assert '## Section5' in result
