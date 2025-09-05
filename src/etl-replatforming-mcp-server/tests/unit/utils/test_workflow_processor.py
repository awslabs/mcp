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

"""Unit tests for WorkflowProcessor."""

from unittest.mock import Mock, patch

import pytest

from awslabs.etl_replatforming_mcp_server.constants import (
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
)
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import (
    FlexWorkflow,
    ParsingInfo,
)
from awslabs.etl_replatforming_mcp_server.utils.workflow_processor import (
    WorkflowProcessor,
)
from awslabs.etl_replatforming_mcp_server.validators.workflow_validator import (
    WorkflowValidator,
)


class TestWorkflowProcessor:
    """Test cases for WorkflowProcessor."""

    @pytest.fixture
    def validator(self):
        """Create mock validator."""
        return Mock(spec=WorkflowValidator)

    @pytest.fixture
    def processor(self, validator):
        """Create WorkflowProcessor instance."""
        return WorkflowProcessor(validator)

    @pytest.fixture
    def mock_workflow(self):
        """Create mock FlexWorkflow."""
        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = Mock(spec=ParsingInfo)
        workflow.parsing_info.parsing_completeness = 0.8
        workflow.get_missing_fields.return_value = ['schedule']
        workflow.should_trigger_ai_enhancement.return_value = True
        return workflow

    def test_should_enhance_with_ai_true(self, processor, mock_workflow):
        """Test should_enhance_with_ai returns True when workflow needs enhancement."""
        mock_workflow.should_trigger_ai_enhancement.return_value = True

        result = processor.should_enhance_with_ai(mock_workflow)

        assert result is True
        mock_workflow.should_trigger_ai_enhancement.assert_called_once()

    def test_should_enhance_with_ai_false(self, processor, mock_workflow):
        """Test should_enhance_with_ai returns False when workflow is complete."""
        mock_workflow.should_trigger_ai_enhancement.return_value = False

        result = processor.should_enhance_with_ai(mock_workflow)

        assert result is False

    def test_calculate_enhancement_improvement_improved(self, processor, mock_workflow):
        """Test calculate_enhancement_improvement detects improvement."""
        original_workflow = Mock(spec=FlexWorkflow)
        original_workflow.get_missing_fields.return_value = [
            'schedule',
            'error_handling',
        ]

        enhanced_workflow = Mock(spec=FlexWorkflow)
        enhanced_workflow.get_missing_fields.return_value = ['schedule']
        enhanced_workflow.parsing_info = Mock(spec=ParsingInfo)
        enhanced_workflow.parsing_info.parsing_completeness = 0.9

        improved, final_completeness = processor.calculate_enhancement_improvement(
            original_workflow, enhanced_workflow, 0.8
        )

        assert improved is True
        assert final_completeness == 0.9

    def test_calculate_enhancement_improvement_no_improvement(self, processor, mock_workflow):
        """Test calculate_enhancement_improvement detects no improvement."""
        original_workflow = Mock(spec=FlexWorkflow)
        original_workflow.get_missing_fields.return_value = ['schedule']

        enhanced_workflow = Mock(spec=FlexWorkflow)
        enhanced_workflow.get_missing_fields.return_value = ['schedule']
        enhanced_workflow.parsing_info = Mock(spec=ParsingInfo)
        enhanced_workflow.parsing_info.parsing_completeness = 0.8

        improved, final_completeness = processor.calculate_enhancement_improvement(
            original_workflow, enhanced_workflow, 0.8
        )

        assert improved is False
        assert final_completeness == 0.8

    @patch('awslabs.etl_replatforming_mcp_server.utils.workflow_processor.logger')
    def test_log_parsing_results_deterministic(self, mock_logger, processor):
        """Test log_parsing_results for deterministic stage."""
        processor.log_parsing_results(0.85, 'test.py', 'deterministic')

        mock_logger.info.assert_called_once_with('Deterministic parsing: 85.0% complete (test.py)')

    @patch('awslabs.etl_replatforming_mcp_server.utils.workflow_processor.logger')
    def test_log_parsing_results_no_filename(self, mock_logger, processor):
        """Test log_parsing_results without filename."""
        processor.log_parsing_results(0.85, None, 'deterministic')

        mock_logger.info.assert_called_once_with('Deterministic parsing: 85.0% complete')

    def test_update_parsing_info_after_enhancement(self, processor, mock_workflow):
        """Test update_parsing_info_after_enhancement sets missing fields."""
        missing_fields = ['schedule', 'error_handling']

        processor.update_parsing_info_after_enhancement(mock_workflow, missing_fields)

        assert mock_workflow.parsing_info.missing_fields == missing_fields

    def test_determine_final_status_complete(self, processor, mock_workflow):
        """Test determine_final_status returns complete when no missing fields."""
        mock_workflow.get_missing_fields.return_value = []

        status = processor.determine_final_status(mock_workflow)

        assert status == STATUS_COMPLETE

    def test_determine_final_status_incomplete(self, processor, mock_workflow):
        """Test determine_final_status returns incomplete when missing fields exist."""
        mock_workflow.get_missing_fields.return_value = ['schedule']

        status = processor.determine_final_status(mock_workflow)

        assert status == STATUS_INCOMPLETE

    def test_prepare_parse_result(self, processor, mock_workflow):
        """Test prepare_parse_result creates correct structure."""
        validation_result = {'is_complete': True}

        result = processor.prepare_parse_result(STATUS_COMPLETE, mock_workflow, validation_result)

        expected = {
            'status': STATUS_COMPLETE,
            'flex_workflow': mock_workflow,
            'validation_result': validation_result,
        }
        assert result == expected

    @patch('awslabs.etl_replatforming_mcp_server.utils.workflow_processor.logger')
    def test_log_parsing_results_ai_enhancement_start(self, mock_logger, processor):
        """Test log_parsing_results for ai_enhancement_start stage."""
        processor.log_parsing_results(0.8, 'test.py', 'ai_enhancement_start')
        mock_logger.info.assert_called_once_with(
            'Deterministic parsing incomplete - invoking Bedrock AI enhancement (test.py)'
        )

    @patch('awslabs.etl_replatforming_mcp_server.utils.workflow_processor.logger')
    def test_log_parsing_results_ai_enhancement_success(self, mock_logger, processor):
        """Test log_parsing_results for ai_enhancement_success stage."""
        processor.log_parsing_results(0.9, 'test.py', 'ai_enhancement_success')
        mock_logger.info.assert_called_once_with('AI enhancement successful (test.py)')

    @patch('awslabs.etl_replatforming_mcp_server.utils.workflow_processor.logger')
    def test_log_parsing_results_ai_enhancement_no_improvement(self, mock_logger, processor):
        """Test log_parsing_results for ai_enhancement_no_improvement stage."""
        processor.log_parsing_results(0.8, 'test.py', 'ai_enhancement_no_improvement')
        mock_logger.warning.assert_called_once_with(
            'AI enhancement showed no improvement (test.py)'
        )

    @patch('awslabs.etl_replatforming_mcp_server.utils.workflow_processor.logger')
    def test_log_parsing_results_ai_enhancement_failed(self, mock_logger, processor):
        """Test log_parsing_results for ai_enhancement_failed stage."""
        processor.log_parsing_results(0.8, 'test.py', 'ai_enhancement_failed')
        mock_logger.warning.assert_called_once_with('AI enhancement failed (test.py)')

    @patch('awslabs.etl_replatforming_mcp_server.utils.workflow_processor.logger')
    def test_log_parsing_results_complete(self, mock_logger, processor):
        """Test log_parsing_results for complete stage."""
        processor.log_parsing_results(1.0, 'test.py', 'complete')
        mock_logger.info.assert_called_once_with(
            'Deterministic parsing complete - no AI enhancement needed (test.py)'
        )
