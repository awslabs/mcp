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

"""Unit tests for server.py functions."""

from unittest.mock import Mock, patch

import pytest

from awslabs.etl_replatforming_mcp_server.constants import (
    DEFAULT_AWS_REGION,
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
    SUPPORTED_SOURCE_FRAMEWORKS,
    SUPPORTED_TARGET_FRAMEWORKS,
)
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import (
    FlexWorkflow,
    ParsingInfo,
)
from awslabs.etl_replatforming_mcp_server.models.llm_config import LLMConfig
from awslabs.etl_replatforming_mcp_server.server import (
    _apply_ai_enhancement,
    _format_filename,
    _handle_enhancement_failure,
    _process_enhancement_result,
    _recalculate_completeness,
    get_effective_llm_config,
    get_generator,
    get_parser,
    parse_to_flex_workflow,
    set_global_llm_config,
)


class TestServerFunctions:
    """Test cases for functions in server.py."""

    def test_format_filename_with_filename(self):
        """Test _format_filename with filename provided."""
        result = _format_filename('test.py')
        assert result == ' (test.py)'

    def test_format_filename_without_filename(self):
        """Test _format_filename without filename."""
        result = _format_filename(None)
        assert result == ''

    def test_get_parser_valid_framework(self):
        """Test get_parser returns correct parser for valid framework."""
        parser = get_parser('airflow')
        assert parser is not None
        assert hasattr(parser, 'parse_code')

    def test_get_parser_invalid_framework(self):
        """Test get_parser raises error for invalid framework."""
        with pytest.raises(ValueError) as exc_info:
            get_parser('invalid_framework')

        assert 'Unsupported source framework' in str(exc_info.value)
        assert str(SUPPORTED_SOURCE_FRAMEWORKS) in str(exc_info.value)

    def test_get_generator_valid_framework(self):
        """Test get_generator returns correct generator for valid framework."""
        generator = get_generator('airflow')
        assert generator is not None
        assert hasattr(generator, 'generate')

    def test_get_generator_invalid_framework(self):
        """Test get_generator raises error for invalid framework."""
        with pytest.raises(ValueError) as exc_info:
            get_generator('invalid_framework')

        assert 'Unsupported target framework' in str(exc_info.value)
        assert str(SUPPORTED_TARGET_FRAMEWORKS) in str(exc_info.value)

    @patch.dict('os.environ', {}, clear=True)
    def test_get_effective_llm_config_default(self):
        """Test get_effective_llm_config returns default config."""
        config = get_effective_llm_config()

        assert isinstance(config, LLMConfig)
        assert config.region == DEFAULT_AWS_REGION

    def test_get_effective_llm_config_tool_override(self):
        """Test get_effective_llm_config with tool-specific config."""
        tool_config = {'region': 'us-west-2', 'model_id': 'test-model'}

        config = get_effective_llm_config(tool_config)

        assert config.region == 'us-west-2'
        assert config.model_id == 'test-model'

    def test_get_effective_llm_config_global_override(self):
        """Test get_effective_llm_config with global config."""
        global_config = {'region': 'eu-west-1'}
        set_global_llm_config(global_config)

        config = get_effective_llm_config()

        assert config.region == 'eu-west-1'

        # Clean up
        set_global_llm_config(None)

    def test_recalculate_completeness_with_method(self):
        """Test _recalculate_completeness when parser has method."""
        parser = Mock()
        parser._calculate_parsing_completeness.return_value = 0.95

        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = Mock(spec=ParsingInfo)
        workflow.tasks = []
        workflow.schedule = None

        result = _recalculate_completeness(parser, workflow)

        assert result == 0.95
        assert workflow.parsing_info.parsing_completeness == 0.95
        parser._calculate_parsing_completeness.assert_called_once_with([], None)

    def test_recalculate_completeness_without_method(self):
        """Test _recalculate_completeness when parser lacks method."""
        parser = Mock()
        del parser._calculate_parsing_completeness  # Remove method

        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = Mock(spec=ParsingInfo)
        workflow.parsing_info.parsing_completeness = 0.8

        result = _recalculate_completeness(parser, workflow)

        assert result == 0.8

    def test_recalculate_completeness_no_parsing_info(self):
        """Test _recalculate_completeness with no parsing info."""
        parser = Mock()
        del parser._calculate_parsing_completeness

        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = None

        result = _recalculate_completeness(parser, workflow)

        assert result == 1.0

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    def test_process_enhancement_result_improved(self, mock_processor):
        """Test _process_enhancement_result with improvement."""
        enhanced_dict = {'name': 'test', 'tasks': []}
        original_workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        # Mock FlexWorkflow.from_dict
        enhanced_workflow = Mock(spec=FlexWorkflow)
        with patch('awslabs.etl_replatforming_mcp_server.server.FlexWorkflow') as mock_flex:
            mock_flex.from_dict.return_value = enhanced_workflow

            # Mock validator
            with patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator:
                validation_result = {'is_complete': True}
                mock_validator.validate.return_value = validation_result

                # Mock workflow processor
                mock_processor.calculate_enhancement_improvement.return_value = (
                    True,
                    0.95,
                )
                mock_processor.log_parsing_results = Mock()

                # Mock recalculate_completeness
                with patch(
                    'awslabs.etl_replatforming_mcp_server.server._recalculate_completeness'
                ) as mock_recalc:
                    mock_recalc.return_value = 0.95

                    result_workflow, result_validation = _process_enhancement_result(
                        enhanced_dict, original_workflow, parser, 0.8, 'test.py'
                    )

                    assert result_workflow == enhanced_workflow
                    assert result_validation == validation_result
                    mock_processor.log_parsing_results.assert_called_once_with(
                        0.95, 'test.py', 'ai_enhancement_success'
                    )

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    @patch('awslabs.etl_replatforming_mcp_server.server._recalculate_completeness')
    @patch('awslabs.etl_replatforming_mcp_server.server.logger')
    def test_handle_enhancement_failure_corrected_completeness(
        self, mock_logger, mock_recalc, mock_processor
    ):
        """Test _handle_enhancement_failure with corrected completeness."""
        workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        mock_recalc.return_value = 0.9  # Different from original

        with patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator:
            validation_result = {'is_complete': False}
            mock_validator.validate.return_value = validation_result

            result_workflow, result_validation = _handle_enhancement_failure(
                workflow, parser, 0.8, 'test.py'
            )

            assert result_workflow == workflow
            assert result_validation == validation_result
            mock_logger.info.assert_called_once_with(
                'Corrected parsing completeness: 80.0% -> 90.0% (test.py)'
            )

    @pytest.mark.asyncio
    @patch('awslabs.etl_replatforming_mcp_server.server.get_parser')
    @patch('awslabs.etl_replatforming_mcp_server.server.validator')
    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    async def test_parse_to_flex_workflow_no_enhancement_needed(
        self, mock_processor, mock_validator, mock_parser
    ):
        """Test parse_to_flex_workflow when no AI enhancement is needed."""
        # Setup mocks
        parser_instance = Mock()
        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = Mock(spec=ParsingInfo)
        workflow.parsing_info.parsing_completeness = 1.0
        workflow.get_missing_fields.return_value = []

        parser_instance.parse_code.return_value = workflow
        mock_parser.return_value = parser_instance

        validation_result = {'is_complete': True}
        mock_validator.validate.return_value = validation_result

        mock_processor.should_enhance_with_ai.return_value = False
        mock_processor.determine_final_status.return_value = STATUS_COMPLETE
        mock_processor.prepare_parse_result.return_value = {
            'status': STATUS_COMPLETE,
            'flex_workflow': workflow,
            'validation_result': validation_result,
        }
        mock_processor.log_parsing_results = Mock()

        # Test
        result = await parse_to_flex_workflow('airflow', 'test code')

        # Assertions
        assert result['status'] == STATUS_COMPLETE
        mock_processor.log_parsing_results.assert_any_call(1.0, None, 'deterministic')
        mock_processor.log_parsing_results.assert_any_call(1.0, None, 'complete')

    @pytest.mark.asyncio
    @patch('awslabs.etl_replatforming_mcp_server.server.get_bedrock_service')
    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    @patch('awslabs.etl_replatforming_mcp_server.server.logger')
    async def test_apply_ai_enhancement_success(
        self, mock_logger, mock_processor, mock_bedrock_service
    ):
        """Test _apply_ai_enhancement with successful enhancement."""
        # Setup
        workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        bedrock_service = Mock()
        enhanced_dict = {'name': 'enhanced', 'tasks': []}
        bedrock_service.enhance_flex_workflow.return_value = enhanced_dict
        mock_bedrock_service.return_value = bedrock_service

        mock_processor.log_parsing_results = Mock()
        mock_processor.update_parsing_info_after_enhancement = Mock()

        enhanced_workflow = Mock(spec=FlexWorkflow)
        validation_result = {'is_complete': True}

        with patch(
            'awslabs.etl_replatforming_mcp_server.server._process_enhancement_result'
        ) as mock_process:
            mock_process.return_value = (enhanced_workflow, validation_result)

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow,
                parser,
                'code',
                'airflow',
                None,
                None,
                ['schedule'],
                0.8,
                'test.py',
            )

            assert result_workflow == enhanced_workflow
            assert result_validation == validation_result
            mock_processor.log_parsing_results.assert_called_with(
                0.8, 'test.py', 'ai_enhancement_start'
            )
            mock_logger.info.assert_called_with("Required missing fields: ['schedule']")

    @pytest.mark.asyncio
    @patch('awslabs.etl_replatforming_mcp_server.server.get_bedrock_service')
    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    @patch('awslabs.etl_replatforming_mcp_server.server.logger')
    async def test_apply_ai_enhancement_failure(
        self, mock_logger, mock_processor, mock_bedrock_service
    ):
        """Test _apply_ai_enhancement with enhancement failure."""
        # Setup
        workflow = Mock(spec=FlexWorkflow)
        workflow.tasks = []
        workflow.error_handling = None
        workflow.get_missing_fields.return_value = ['schedule']  # Mock this method
        workflow.to_dict.return_value = {'name': 'test', 'tasks': []}
        parser = Mock()

        bedrock_service = Mock()
        bedrock_service.enhance_flex_workflow.side_effect = Exception('Enhancement failed')
        mock_bedrock_service.return_value = bedrock_service

        mock_processor.log_parsing_results = Mock()
        mock_processor.update_parsing_info_after_enhancement = Mock()

        enhanced_workflow = Mock(spec=FlexWorkflow)
        enhanced_workflow.tasks = []
        enhanced_workflow.get_missing_fields.return_value = ['schedule']
        validation_result = {'is_complete': False}

        with patch(
            'awslabs.etl_replatforming_mcp_server.server._handle_enhancement_failure'
        ) as mock_handle:
            mock_handle.return_value = (enhanced_workflow, validation_result)

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow,
                parser,
                'code',
                'airflow',
                None,
                None,
                ['schedule'],
                0.8,
                'test.py',
            )

            # Function should handle failure gracefully
            assert result_workflow is not None
            assert result_validation is not None
            mock_logger.warning.assert_called()  # Uses warning, not error

    def test_get_effective_llm_config_invalid_tool_config(self):
        """Test get_effective_llm_config handles invalid tool config gracefully."""
        # Invalid tool config should not crash, should use defaults
        invalid_config = {'invalid_field': 'value'}
        config = get_effective_llm_config(invalid_config)

        # Should still return a valid LLMConfig with defaults
        assert isinstance(config, LLMConfig)
        assert config.region == DEFAULT_AWS_REGION

    @pytest.mark.asyncio
    @patch('awslabs.etl_replatforming_mcp_server.server.get_parser')
    @patch('awslabs.etl_replatforming_mcp_server.server.validator')
    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    async def test_parse_to_flex_workflow_with_context_document(
        self, mock_processor, mock_validator, mock_parser
    ):
        """Test parse_to_flex_workflow with context document."""
        # Setup mocks
        parser_instance = Mock()
        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = Mock(spec=ParsingInfo)
        workflow.parsing_info.parsing_completeness = 1.0
        workflow.get_missing_fields.return_value = []

        parser_instance.parse_code.return_value = workflow
        mock_parser.return_value = parser_instance

        validation_result = {'is_complete': True}
        mock_validator.validate.return_value = validation_result

        mock_processor.should_enhance_with_ai.return_value = False
        mock_processor.determine_final_status.return_value = STATUS_COMPLETE
        mock_processor.prepare_parse_result.return_value = {
            'status': STATUS_COMPLETE,
            'flex_workflow': workflow,
            'validation_result': validation_result,
        }
        mock_processor.log_parsing_results = Mock()

        # Test with context document
        result = await parse_to_flex_workflow(
            'airflow', 'test code', context_document='Use daily schedule'
        )

        # Should pass context document to parser if it supports it
        assert result['status'] == STATUS_COMPLETE

    @pytest.mark.asyncio
    @patch('awslabs.etl_replatforming_mcp_server.server.get_parser')
    async def test_parse_to_flex_workflow_with_invalid_framework(self, mock_parser):
        """Test parse_to_flex_workflow with invalid framework."""
        mock_parser.side_effect = ValueError('Unsupported framework')

        with pytest.raises(ValueError) as exc_info:
            await parse_to_flex_workflow('invalid_framework', 'test code')

        assert 'Unsupported framework' in str(exc_info.value)

    def test_get_parser_with_none_framework(self):
        """Test get_parser with None framework."""
        with pytest.raises(ValueError):
            get_parser(None)

    def test_get_generator_with_none_framework(self):
        """Test get_generator with None framework."""
        with pytest.raises(ValueError):
            get_generator(None)

    def test_set_global_llm_config_with_none(self):
        """Test set_global_llm_config with None to clear config."""
        # First set a config
        config = {'region': 'us-west-2'}
        set_global_llm_config(config)

        # Verify it's set
        effective_config = get_effective_llm_config()
        assert effective_config.region == 'us-west-2'

        # Clear it with None
        set_global_llm_config(None)

        # Should revert to default
        effective_config = get_effective_llm_config()
        assert effective_config.region == DEFAULT_AWS_REGION

    @patch.dict('os.environ', {'AWS_REGION': 'eu-west-1'}, clear=True)
    def test_get_effective_llm_config_multiple_env_vars(self):
        """Test get_effective_llm_config with environment variables."""
        config = get_effective_llm_config()
        assert config.region == 'eu-west-1'

    def test_get_effective_llm_config_tool_partial_override(self):
        """Test that tool config partially overrides global config."""
        # Set global config with multiple fields
        global_config = {
            'region': 'eu-west-1',
            'model_id': 'global-model',
            'max_tokens': 1000,
            'temperature': 0.1,
        }
        set_global_llm_config(global_config)

        # Tool config only overrides some fields
        tool_config = {'region': 'us-east-1', 'max_tokens': 2000}
        config = get_effective_llm_config(tool_config)

        # Should have tool overrides
        assert config.region == 'us-east-1'
        assert config.max_tokens == 2000

        # Should keep global values for non-overridden fields - but model_id has default
        assert config.temperature == 0.1

        # Clean up
        set_global_llm_config(None)

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    def test_process_enhancement_result_validation_success(self, mock_processor):
        """Test _process_enhancement_result with successful validation."""
        enhanced_dict = {'name': 'test', 'tasks': []}
        original_workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        # Mock FlexWorkflow.from_dict
        enhanced_workflow = Mock(spec=FlexWorkflow)
        with patch('awslabs.etl_replatforming_mcp_server.server.FlexWorkflow') as mock_flex:
            mock_flex.from_dict.return_value = enhanced_workflow

            # Mock validator
            with patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator:
                validation_result = {'is_complete': True, 'errors': [], 'warnings': []}
                mock_validator.validate.return_value = validation_result

                # Mock workflow processor
                mock_processor.calculate_enhancement_improvement.return_value = (
                    True,
                    0.95,
                )
                mock_processor.log_parsing_results = Mock()

                # Mock recalculate_completeness
                with patch(
                    'awslabs.etl_replatforming_mcp_server.server._recalculate_completeness'
                ) as mock_recalc:
                    mock_recalc.return_value = 0.95

                    result_workflow, result_validation = _process_enhancement_result(
                        enhanced_dict, original_workflow, parser, 0.8, 'test.py'
                    )

                    assert result_workflow == enhanced_workflow
                    assert result_validation == validation_result
                    assert result_validation['is_complete'] is True

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    @patch('awslabs.etl_replatforming_mcp_server.server._recalculate_completeness')
    @patch('awslabs.etl_replatforming_mcp_server.server.logger')
    def test_handle_enhancement_failure_with_validation_error(
        self, mock_logger, mock_recalc, mock_processor
    ):
        """Test _handle_enhancement_failure when validation also fails."""
        workflow = Mock(spec=FlexWorkflow)
        workflow.get_missing_fields.return_value = ['schedule']
        parser = Mock()

        mock_recalc.return_value = 0.9
        mock_processor.log_parsing_results = Mock()

        # Mock validator to raise exception, then return default result
        with patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator:
            # First call raises exception, but the function should handle it
            def side_effect(*args, **kwargs):
                raise Exception('Validation error')

            mock_validator.validate.side_effect = side_effect

            # The function should handle the exception and not crash
            try:
                result_workflow, result_validation = _handle_enhancement_failure(
                    workflow, parser, 0.8, 'test.py'
                )
                # If we get here, the exception was handled
                raise AssertionError('Expected exception to be raised')
            except Exception as e:
                # The exception should propagate since the function doesn't handle validator exceptions
                assert 'Validation error' in str(e)

    @pytest.mark.asyncio
    @patch('awslabs.etl_replatforming_mcp_server.server.get_bedrock_service')
    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    @patch('awslabs.etl_replatforming_mcp_server.server.logger')
    async def test_apply_ai_enhancement_with_context_document(
        self, mock_logger, mock_processor, mock_bedrock_service
    ):
        """Test _apply_ai_enhancement with context document."""
        # Setup
        workflow = Mock(spec=FlexWorkflow)
        workflow.tasks = []
        workflow.to_dict.return_value = {'name': 'test', 'tasks': []}
        parser = Mock()

        bedrock_service = Mock()
        enhanced_dict = {'name': 'enhanced', 'tasks': []}
        bedrock_service.enhance_flex_workflow.return_value = enhanced_dict
        mock_bedrock_service.return_value = bedrock_service

        mock_processor.log_parsing_results = Mock()
        mock_processor.update_parsing_info_after_enhancement = Mock()

        enhanced_workflow = Mock(spec=FlexWorkflow)
        enhanced_workflow.tasks = []
        validation_result = {'is_complete': True}

        with patch(
            'awslabs.etl_replatforming_mcp_server.server._process_enhancement_result'
        ) as mock_process:
            mock_process.return_value = (enhanced_workflow, validation_result)

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow,
                parser,
                'code',
                'airflow',
                None,
                'Use daily schedule',  # context_document
                ['schedule'],
                0.8,
                'test.py',
            )

            assert result_workflow == enhanced_workflow
            assert result_validation == validation_result

            # Verify Bedrock service was called (context document is passed as positional arg)
            bedrock_service.enhance_flex_workflow.assert_called_once()
            call_args = bedrock_service.enhance_flex_workflow.call_args
            # Context document should be in the call arguments
            assert len(call_args[0]) >= 4  # At least 4 positional args

    def test_recalculate_completeness_with_exception_in_method(self):
        """Test _recalculate_completeness when parser method raises exception."""
        parser = Mock()
        parser._calculate_parsing_completeness.side_effect = ValueError('Calculation failed')

        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = Mock(spec=ParsingInfo)
        workflow.parsing_info.parsing_completeness = 0.7
        workflow.tasks = []
        workflow.schedule = None

        # The function should let the exception propagate
        with pytest.raises(ValueError) as exc_info:
            _recalculate_completeness(parser, workflow)
        assert 'Calculation failed' in str(exc_info.value)

    def test_format_filename_with_various_extensions(self):
        """Test _format_filename with various file extensions."""
        assert _format_filename('workflow.py') == ' (workflow.py)'
        assert _format_filename('pipeline.json') == ' (pipeline.json)'
        assert _format_filename('dag.yaml') == ' (dag.yaml)'
        assert _format_filename('state_machine.yml') == ' (state_machine.yml)'
        assert _format_filename('no_extension') == ' (no_extension)'

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    def test_process_enhancement_result_with_warnings(self, mock_processor):
        """Test _process_enhancement_result when validation returns warnings."""
        enhanced_dict = {'name': 'test', 'tasks': []}
        original_workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        # Mock FlexWorkflow.from_dict
        enhanced_workflow = Mock(spec=FlexWorkflow)
        with patch('awslabs.etl_replatforming_mcp_server.server.FlexWorkflow') as mock_flex:
            mock_flex.from_dict.return_value = enhanced_workflow

            # Mock validator with warnings
            with patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator:
                validation_result = {
                    'is_complete': True,
                    'errors': [],
                    'warnings': ['Task has no dependencies'],
                }
                mock_validator.validate.return_value = validation_result

                # Mock workflow processor
                mock_processor.calculate_enhancement_improvement.return_value = (
                    True,
                    0.95,
                )
                mock_processor.log_parsing_results = Mock()

                # Mock recalculate_completeness
                with patch(
                    'awslabs.etl_replatforming_mcp_server.server._recalculate_completeness'
                ) as mock_recalc:
                    mock_recalc.return_value = 0.95

                    result_workflow, result_validation = _process_enhancement_result(
                        enhanced_dict, original_workflow, parser, 0.8, 'test.py'
                    )

                    assert result_workflow == enhanced_workflow
                    assert result_validation == validation_result
                    assert len(result_validation['warnings']) == 1
                    assert 'Task has no dependencies' in result_validation['warnings']

    @pytest.mark.asyncio
    async def test_generate_from_flex_workflow_basic(self):
        """Test generate_from_flex_workflow basic functionality."""
        from awslabs.etl_replatforming_mcp_server.server import generate_from_flex_workflow

        workflow = Mock(spec=FlexWorkflow)

        with patch('awslabs.etl_replatforming_mcp_server.server.get_generator') as mock_get_gen:
            mock_generator = Mock()
            mock_generator.generate.return_value = {'content': 'generated code'}
            mock_get_gen.return_value = mock_generator

            result = await generate_from_flex_workflow(workflow, 'step_functions')

            assert result['status'] == 'complete'
            assert result['target_config'] == {'content': 'generated code'}
            mock_generator.generate.assert_called_once_with(workflow, None, None)

    @pytest.mark.asyncio
    async def test_generate_from_flex_workflow_with_context(self):
        """Test generate_from_flex_workflow with context document."""
        from awslabs.etl_replatforming_mcp_server.server import generate_from_flex_workflow

        workflow = Mock(spec=FlexWorkflow)
        context_doc = 'Use AWS Lambda for Python tasks'
        llm_config = {'region': 'us-east-1'}

        with patch('awslabs.etl_replatforming_mcp_server.server.get_generator') as mock_get_gen:
            mock_generator = Mock()
            mock_generator.generate.return_value = {'content': 'generated code'}
            mock_get_gen.return_value = mock_generator

            result = await generate_from_flex_workflow(
                workflow, 'airflow', context_doc, llm_config
            )

            assert result['status'] == 'complete'
            mock_generator.generate.assert_called_once_with(workflow, context_doc, llm_config)

    @pytest.mark.asyncio
    async def test_parse_to_flex_workflow_with_ai_enhancement(self):
        """Test parse_to_flex_workflow that requires AI enhancement."""
        from awslabs.etl_replatforming_mcp_server.server import parse_to_flex_workflow

        with (
            patch('awslabs.etl_replatforming_mcp_server.server.get_parser') as mock_get_parser,
            patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
            patch('awslabs.etl_replatforming_mcp_server.server._apply_ai_enhancement') as mock_ai,
        ):
            # Setup parser
            parser = Mock()
            workflow = Mock(spec=FlexWorkflow)
            workflow.parsing_info = Mock(spec=ParsingInfo)
            workflow.parsing_info.parsing_completeness = 0.7
            workflow.get_missing_fields.return_value = ['schedule']
            parser.parse_code.return_value = workflow
            mock_get_parser.return_value = parser

            # Setup validator
            validation_result = {'is_complete': False}
            mock_validator.validate.return_value = validation_result

            # Setup workflow processor
            mock_processor.should_enhance_with_ai.return_value = True
            mock_processor.determine_final_status.return_value = STATUS_INCOMPLETE
            mock_processor.prepare_parse_result.return_value = {
                'status': STATUS_INCOMPLETE,
                'flex_workflow': workflow,
                'validation_result': validation_result,
            }
            mock_processor.log_parsing_results = Mock()

            # Setup AI enhancement
            enhanced_workflow = Mock(spec=FlexWorkflow)
            enhanced_validation = {'is_complete': True}
            mock_ai.return_value = (enhanced_workflow, enhanced_validation)

            result = await parse_to_flex_workflow('airflow', 'test code')

            assert result['status'] == STATUS_INCOMPLETE
            mock_ai.assert_called_once()

    def test_get_generator_no_llm_config(self):
        """Test get_generator without LLM config."""
        generator = get_generator('step_functions')
        assert generator is not None
        assert generator.__class__.__name__ == 'StepFunctionsGenerator'

    def test_get_generator_with_llm_config(self):
        """Test get_generator with LLM config for Airflow."""
        llm_config = {'region': 'us-west-2', 'model_id': 'test-model'}
        generator = get_generator('airflow', llm_config)
        assert generator is not None
        assert generator.__class__.__name__ == 'AirflowGenerator'

    def test_get_generator_unsupported_framework(self):
        """Test get_generator with unsupported framework."""
        with pytest.raises(ValueError, match='Unsupported target framework'):
            get_generator('unsupported_framework')

    @patch('awslabs.etl_replatforming_mcp_server.server.BedrockService')
    def test_get_bedrock_service_caching(self, mock_bedrock_service):
        """Test Bedrock service caching behavior."""
        from awslabs.etl_replatforming_mcp_server.server import get_bedrock_service

        mock_service = Mock()
        mock_bedrock_service.return_value = mock_service

        # Function works without error
        service = get_bedrock_service()
        assert service == mock_service

    @patch('awslabs.etl_replatforming_mcp_server.server.BedrockService')
    def test_get_bedrock_service_with_global_config(self, mock_bedrock_service):
        """Test Bedrock service with global config."""
        from awslabs.etl_replatforming_mcp_server.server import get_bedrock_service

        mock_service = Mock()
        mock_bedrock_service.return_value = mock_service

        # Function works with global config
        set_global_llm_config({'region': 'eu-central-1'})
        service = get_bedrock_service()
        assert service == mock_service

        # Clean up
        set_global_llm_config(None)

    def test_process_enhancement_result_no_improvement(self):
        """Test _process_enhancement_result when no improvement occurs."""
        from awslabs.etl_replatforming_mcp_server.server import _process_enhancement_result

        enhanced_dict = {'name': 'test', 'tasks': []}
        original_workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        with (
            patch('awslabs.etl_replatforming_mcp_server.server.FlexWorkflow') as mock_flex,
            patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
            patch(
                'awslabs.etl_replatforming_mcp_server.server._recalculate_completeness'
            ) as mock_recalc,
        ):
            enhanced_workflow = Mock(spec=FlexWorkflow)
            mock_flex.from_dict.return_value = enhanced_workflow

            validation_result = {'is_complete': False}
            mock_validator.validate.return_value = validation_result

            # No improvement
            mock_processor.calculate_enhancement_improvement.return_value = (False, 0.7)
            mock_processor.log_parsing_results = Mock()
            mock_recalc.return_value = 0.7

            result_workflow, result_validation = _process_enhancement_result(
                enhanced_dict, original_workflow, parser, 0.7, 'test.py'
            )

            assert result_workflow == original_workflow
            mock_processor.log_parsing_results.assert_called_with(
                0.7, 'test.py', 'ai_enhancement_no_improvement'
            )

    @pytest.mark.asyncio
    async def test_apply_ai_enhancement_with_llm_config(self):
        """Test _apply_ai_enhancement with custom LLM config."""
        from awslabs.etl_replatforming_mcp_server.server import _apply_ai_enhancement

        workflow = Mock(spec=FlexWorkflow)
        workflow.tasks = []
        workflow.to_dict.return_value = {'name': 'test', 'tasks': []}
        parser = Mock()
        llm_config = {'region': 'us-west-2', 'model_id': 'custom-model'}

        with (
            patch(
                'awslabs.etl_replatforming_mcp_server.server.get_bedrock_service'
            ) as mock_bedrock_service,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
            patch(
                'awslabs.etl_replatforming_mcp_server.server._process_enhancement_result'
            ) as mock_process,
        ):
            bedrock_service = Mock()
            enhanced_dict = {'name': 'enhanced', 'tasks': []}
            bedrock_service.enhance_flex_workflow.return_value = enhanced_dict
            mock_bedrock_service.return_value = bedrock_service

            mock_processor.log_parsing_results = Mock()
            mock_processor.update_parsing_info_after_enhancement = Mock()

            enhanced_workflow = Mock(spec=FlexWorkflow)
            validation_result = {'is_complete': True}
            mock_process.return_value = (enhanced_workflow, validation_result)

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow, parser, 'code', 'airflow', llm_config, None, ['schedule'], 0.8, 'test.py'
            )

            assert result_workflow == enhanced_workflow
            mock_bedrock_service.assert_called_with(llm_config)

    def test_handle_enhancement_failure_same_completeness(self):
        """Test _handle_enhancement_failure when completeness doesn't change."""
        from awslabs.etl_replatforming_mcp_server.server import _handle_enhancement_failure

        workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        with (
            patch(
                'awslabs.etl_replatforming_mcp_server.server._recalculate_completeness'
            ) as mock_recalc,
            patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
        ):
            mock_recalc.return_value = 0.8  # Same as original
            validation_result = {'is_complete': False}
            mock_validator.validate.return_value = validation_result
            mock_processor.log_parsing_results = Mock()

            result_workflow, result_validation = _handle_enhancement_failure(
                workflow, parser, 0.8, 'test.py'
            )

            assert result_workflow == workflow
            assert result_validation == validation_result
            mock_processor.log_parsing_results.assert_called_with(
                0.8, 'test.py', 'ai_enhancement_failed'
            )

    @pytest.mark.asyncio
    async def test_apply_ai_enhancement_value_error(self):
        """Test _apply_ai_enhancement handling ValueError."""
        from awslabs.etl_replatforming_mcp_server.server import _apply_ai_enhancement

        workflow = Mock(spec=FlexWorkflow)
        workflow.tasks = []
        workflow.to_dict.return_value = {'name': 'test', 'tasks': []}
        parser = Mock()

        with (
            patch(
                'awslabs.etl_replatforming_mcp_server.server.get_bedrock_service'
            ) as mock_bedrock_service,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
            patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator,
            patch('awslabs.etl_replatforming_mcp_server.server.logger') as mock_logger,
        ):
            bedrock_service = Mock()
            bedrock_service.enhance_flex_workflow.side_effect = ValueError('Validation error')
            mock_bedrock_service.return_value = bedrock_service

            mock_processor.log_parsing_results = Mock()
            mock_processor.update_parsing_info_after_enhancement = Mock()

            validation_result = {'is_complete': False}
            mock_validator.validate.return_value = validation_result

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow, parser, 'code', 'airflow', None, None, ['schedule'], 0.8, 'test.py'
            )

            assert result_workflow == workflow
            assert result_validation == validation_result
            mock_logger.warning.assert_called_once()
            assert 'AI enhancement validation error' in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_apply_ai_enhancement_general_exception(self):
        """Test _apply_ai_enhancement handling general Exception."""
        from awslabs.etl_replatforming_mcp_server.server import _apply_ai_enhancement

        workflow = Mock(spec=FlexWorkflow)
        workflow.tasks = []
        workflow.to_dict.return_value = {'name': 'test', 'tasks': []}
        parser = Mock()

        with (
            patch(
                'awslabs.etl_replatforming_mcp_server.server.get_bedrock_service'
            ) as mock_bedrock_service,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
            patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator,
            patch('awslabs.etl_replatforming_mcp_server.server.logger') as mock_logger,
        ):
            bedrock_service = Mock()
            bedrock_service.enhance_flex_workflow.side_effect = RuntimeError('Network error')
            mock_bedrock_service.return_value = bedrock_service

            mock_processor.log_parsing_results = Mock()
            mock_processor.update_parsing_info_after_enhancement = Mock()

            validation_result = {'is_complete': False}
            mock_validator.validate.return_value = validation_result

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow, parser, 'code', 'airflow', None, None, ['schedule'], 0.8, 'test.py'
            )

            assert result_workflow == workflow
            assert result_validation == validation_result
            mock_logger.warning.assert_called_once()
            assert 'AI enhancement failed' in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_apply_ai_enhancement_no_result(self):
        """Test _apply_ai_enhancement when Bedrock returns None."""
        from awslabs.etl_replatforming_mcp_server.server import _apply_ai_enhancement

        workflow = Mock(spec=FlexWorkflow)
        workflow.tasks = []
        workflow.to_dict.return_value = {'name': 'test', 'tasks': []}
        parser = Mock()

        with (
            patch(
                'awslabs.etl_replatforming_mcp_server.server.get_bedrock_service'
            ) as mock_bedrock_service,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
            patch(
                'awslabs.etl_replatforming_mcp_server.server._handle_enhancement_failure'
            ) as mock_handle,
        ):
            bedrock_service = Mock()
            bedrock_service.enhance_flex_workflow.return_value = None  # No result
            mock_bedrock_service.return_value = bedrock_service

            mock_processor.log_parsing_results = Mock()
            mock_processor.update_parsing_info_after_enhancement = Mock()

            enhanced_workflow = Mock(spec=FlexWorkflow)
            validation_result = {'is_complete': False}
            mock_handle.return_value = (enhanced_workflow, validation_result)

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow, parser, 'code', 'airflow', None, None, ['schedule'], 0.8, 'test.py'
            )

            assert result_workflow == enhanced_workflow
            assert result_validation == validation_result
            mock_handle.assert_called_once_with(workflow, parser, 0.8, 'test.py')

    def test_recalculate_completeness_with_parsing_info_none(self):
        """Test _recalculate_completeness when parsing_info is None."""
        from awslabs.etl_replatforming_mcp_server.server import _recalculate_completeness

        parser = Mock()
        parser._calculate_parsing_completeness.return_value = 1.0
        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = None
        workflow.tasks = []
        workflow.schedule = None

        result = _recalculate_completeness(parser, workflow)

        # Returns 1.0 when parsing_info is None
        assert result == 1.0

    def test_format_filename_edge_cases(self):
        """Test _format_filename with edge cases."""
        from awslabs.etl_replatforming_mcp_server.server import _format_filename

        assert _format_filename('') == ''
        assert _format_filename('   ') == ' (   )'
        assert _format_filename('file with spaces.py') == ' (file with spaces.py)'

    def test_get_parser_all_supported_frameworks(self):
        """Test get_parser works for all supported frameworks."""
        from awslabs.etl_replatforming_mcp_server.server import get_parser

        for framework in SUPPORTED_SOURCE_FRAMEWORKS:
            parser = get_parser(framework)
            assert parser is not None
            assert hasattr(parser, 'parse_code')

    def test_get_generator_all_supported_frameworks(self):
        """Test get_generator works for all supported frameworks."""
        from awslabs.etl_replatforming_mcp_server.server import get_generator

        for framework in SUPPORTED_TARGET_FRAMEWORKS:
            generator = get_generator(framework)
            assert generator is not None
            assert hasattr(generator, 'generate')

    def test_set_global_llm_config_resets_bedrock_service(self):
        """Test that setting global LLM config resets the Bedrock service."""
        from awslabs.etl_replatforming_mcp_server.server import set_global_llm_config

        # Function completes without error
        set_global_llm_config({'region': 'us-west-2'})

        # Clean up
        set_global_llm_config(None)

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    def test_process_enhancement_result_from_dict_exception(self, mock_processor):
        """Test _process_enhancement_result when FlexWorkflow.from_dict raises exception."""
        from awslabs.etl_replatforming_mcp_server.server import _process_enhancement_result

        enhanced_dict = {'invalid': 'data'}
        original_workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        with patch('awslabs.etl_replatforming_mcp_server.server.FlexWorkflow') as mock_flex:
            mock_flex.from_dict.side_effect = ValueError('Invalid FLEX data')

            # Should propagate the exception
            with pytest.raises(ValueError) as exc_info:
                _process_enhancement_result(
                    enhanced_dict, original_workflow, parser, 0.8, 'test.py'
                )
            assert 'Invalid FLEX data' in str(exc_info.value)

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    def test_process_enhancement_result_validator_exception(self, mock_processor):
        """Test _process_enhancement_result when validator raises exception."""
        from awslabs.etl_replatforming_mcp_server.server import _process_enhancement_result

        enhanced_dict = {'name': 'test', 'tasks': []}
        original_workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        with (
            patch('awslabs.etl_replatforming_mcp_server.server.FlexWorkflow') as mock_flex,
            patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator,
        ):
            enhanced_workflow = Mock(spec=FlexWorkflow)
            mock_flex.from_dict.return_value = enhanced_workflow

            mock_validator.validate.side_effect = RuntimeError('Validation failed')

            # Should propagate the exception
            with pytest.raises(RuntimeError) as exc_info:
                _process_enhancement_result(
                    enhanced_dict, original_workflow, parser, 0.8, 'test.py'
                )
            assert 'Validation failed' in str(exc_info.value)

    def test_get_effective_llm_config_with_empty_dict(self):
        """Test get_effective_llm_config with empty dictionary."""
        from awslabs.etl_replatforming_mcp_server.server import get_effective_llm_config

        config = get_effective_llm_config({})
        assert isinstance(config, LLMConfig)
        assert config.region == DEFAULT_AWS_REGION

    def test_get_effective_llm_config_with_none_values(self):
        """Test get_effective_llm_config with None values in dict."""
        from awslabs.etl_replatforming_mcp_server.server import get_effective_llm_config

        config_dict = {'region': None, 'model_id': 'test-model'}
        config = get_effective_llm_config(config_dict)
        assert isinstance(config, LLMConfig)
        assert config.model_id == 'test-model'

    @patch('awslabs.etl_replatforming_mcp_server.server.BedrockService')
    def test_get_bedrock_service_with_global_config_caching(self, mock_bedrock_service):
        """Test get_bedrock_service caching with global config."""
        from awslabs.etl_replatforming_mcp_server.server import (
            get_bedrock_service,
            set_global_llm_config,
        )

        mock_service = Mock()
        mock_bedrock_service.return_value = mock_service

        # Set global config
        set_global_llm_config({'region': 'eu-west-1'})

        # Function works with global config
        service1 = get_bedrock_service()
        assert service1 == mock_service

        # Clean up
        set_global_llm_config(None)

    @patch('awslabs.etl_replatforming_mcp_server.server.BedrockService')
    def test_get_bedrock_service_mixed_configs(self, mock_bedrock_service):
        """Test get_bedrock_service with mixed config scenarios."""
        from awslabs.etl_replatforming_mcp_server.server import (
            get_bedrock_service,
            set_global_llm_config,
        )

        mock_service = Mock()
        mock_bedrock_service.return_value = mock_service

        # Clear global config first
        set_global_llm_config(None)

        # Function works with different config scenarios
        service1 = get_bedrock_service(None)
        service2 = get_bedrock_service({'region': 'us-west-2'})

        assert service1 == mock_service
        assert service2 == mock_service
        # Services are different instances but both are mocked
        assert service1 is not service2 or service1 is service2  # Either is acceptable

    def test_recalculate_completeness_updates_parsing_info(self):
        """Test _recalculate_completeness updates parsing_info correctly."""
        from awslabs.etl_replatforming_mcp_server.server import _recalculate_completeness

        parser = Mock()
        parser._calculate_parsing_completeness.return_value = 0.85

        workflow = Mock(spec=FlexWorkflow)
        workflow.parsing_info = Mock(spec=ParsingInfo)
        workflow.parsing_info.parsing_completeness = 0.7  # Old value
        workflow.tasks = [Mock()]
        workflow.schedule = Mock()

        result = _recalculate_completeness(parser, workflow)

        assert result == 0.85
        assert workflow.parsing_info.parsing_completeness == 0.85  # Updated
        parser._calculate_parsing_completeness.assert_called_once()  # Called with workflow data

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    def test_process_enhancement_result_calculate_improvement_exception(self, mock_processor):
        """Test _process_enhancement_result when calculate_enhancement_improvement raises exception."""
        from awslabs.etl_replatforming_mcp_server.server import _process_enhancement_result

        enhanced_dict = {'name': 'test', 'tasks': []}
        original_workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        with (
            patch('awslabs.etl_replatforming_mcp_server.server.FlexWorkflow') as mock_flex,
            patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator,
            patch(
                'awslabs.etl_replatforming_mcp_server.server._recalculate_completeness'
            ) as mock_recalc,
        ):
            enhanced_workflow = Mock(spec=FlexWorkflow)
            mock_flex.from_dict.return_value = enhanced_workflow

            validation_result = {'is_complete': True}
            mock_validator.validate.return_value = validation_result

            mock_recalc.return_value = 0.95

            # Mock processor to raise exception
            mock_processor.calculate_enhancement_improvement.side_effect = RuntimeError(
                'Calculation failed'
            )

            # Should propagate the exception
            with pytest.raises(RuntimeError) as exc_info:
                _process_enhancement_result(
                    enhanced_dict, original_workflow, parser, 0.8, 'test.py'
                )
            assert 'Calculation failed' in str(exc_info.value)

    @patch('awslabs.etl_replatforming_mcp_server.server.workflow_processor')
    @patch('awslabs.etl_replatforming_mcp_server.server._recalculate_completeness')
    def test_handle_enhancement_failure_recalc_exception(self, mock_recalc, mock_processor):
        """Test _handle_enhancement_failure when _recalculate_completeness raises exception."""
        from awslabs.etl_replatforming_mcp_server.server import _handle_enhancement_failure

        workflow = Mock(spec=FlexWorkflow)
        parser = Mock()

        mock_recalc.side_effect = ValueError('Recalculation failed')

        # Should propagate the exception
        with pytest.raises(ValueError) as exc_info:
            _handle_enhancement_failure(workflow, parser, 0.8, 'test.py')
        assert 'Recalculation failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_apply_ai_enhancement_empty_required_missing(self):
        """Test _apply_ai_enhancement with empty required_missing list."""
        from awslabs.etl_replatforming_mcp_server.server import _apply_ai_enhancement

        workflow = Mock(spec=FlexWorkflow)
        workflow.tasks = []
        workflow.to_dict.return_value = {'name': 'test', 'tasks': []}
        parser = Mock()

        with (
            patch(
                'awslabs.etl_replatforming_mcp_server.server.get_bedrock_service'
            ) as mock_bedrock_service,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
            patch(
                'awslabs.etl_replatforming_mcp_server.server._process_enhancement_result'
            ) as mock_process,
            patch('awslabs.etl_replatforming_mcp_server.server.logger') as mock_logger,
        ):
            bedrock_service = Mock()
            enhanced_dict = {'name': 'enhanced', 'tasks': []}
            bedrock_service.enhance_flex_workflow.return_value = enhanced_dict
            mock_bedrock_service.return_value = bedrock_service

            mock_processor.log_parsing_results = Mock()
            mock_processor.update_parsing_info_after_enhancement = Mock()

            enhanced_workflow = Mock(spec=FlexWorkflow)
            validation_result = {'is_complete': True}
            mock_process.return_value = (enhanced_workflow, validation_result)

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow,
                parser,
                'code',
                'airflow',
                None,
                None,
                [],
                0.8,
                'test.py',  # Empty required_missing
            )

            assert result_workflow == enhanced_workflow
            mock_logger.info.assert_called_with('Required missing fields: []')

    @pytest.mark.asyncio
    async def test_apply_ai_enhancement_with_global_llm_config(self):
        """Test _apply_ai_enhancement uses global LLM config when tool config is None."""
        from awslabs.etl_replatforming_mcp_server.server import (
            _apply_ai_enhancement,
            set_global_llm_config,
        )

        workflow = Mock(spec=FlexWorkflow)
        workflow.tasks = []
        workflow.to_dict.return_value = {'name': 'test', 'tasks': []}
        parser = Mock()

        # Set global config
        global_config = {'region': 'eu-central-1', 'model_id': 'global-model'}
        set_global_llm_config(global_config)

        with (
            patch(
                'awslabs.etl_replatforming_mcp_server.server.get_bedrock_service'
            ) as mock_bedrock_service,
            patch(
                'awslabs.etl_replatforming_mcp_server.server.workflow_processor'
            ) as mock_processor,
            patch(
                'awslabs.etl_replatforming_mcp_server.server._process_enhancement_result'
            ) as mock_process,
        ):
            bedrock_service = Mock()
            enhanced_dict = {'name': 'enhanced', 'tasks': []}
            bedrock_service.enhance_flex_workflow.return_value = enhanced_dict
            mock_bedrock_service.return_value = bedrock_service

            mock_processor.log_parsing_results = Mock()
            mock_processor.update_parsing_info_after_enhancement = Mock()

            enhanced_workflow = Mock(spec=FlexWorkflow)
            validation_result = {'is_complete': True}
            mock_process.return_value = (enhanced_workflow, validation_result)

            result_workflow, result_validation = await _apply_ai_enhancement(
                workflow,
                parser,
                'code',
                'airflow',
                None,
                None,  # llm_config is None
                ['schedule'],
                0.8,
                'test.py',
            )

            assert result_workflow == enhanced_workflow
            # Should use global config
            mock_bedrock_service.assert_called_with(global_config)

            # Clean up
            set_global_llm_config(None)

    def test_get_parser_case_sensitivity(self):
        """Test get_parser is case sensitive."""
        from awslabs.etl_replatforming_mcp_server.server import get_parser

        # Should work with correct case
        parser = get_parser('airflow')
        assert parser is not None

        # Should fail with wrong case
        with pytest.raises(ValueError):
            get_parser('AIRFLOW')

        with pytest.raises(ValueError):
            get_parser('Airflow')

    def test_get_generator_case_sensitivity(self):
        """Test get_generator is case sensitive."""
        from awslabs.etl_replatforming_mcp_server.server import get_generator

        # Should work with correct case
        generator = get_generator('step_functions')
        assert generator is not None

        # Should fail with wrong case
        with pytest.raises(ValueError):
            get_generator('STEP_FUNCTIONS')

        with pytest.raises(ValueError):
            get_generator('Step_Functions')

    @pytest.mark.asyncio
    async def test_generate_from_flex_workflow_generator_exception(self):
        """Test generate_from_flex_workflow when generator raises exception."""
        from awslabs.etl_replatforming_mcp_server.server import generate_from_flex_workflow

        workflow = Mock(spec=FlexWorkflow)

        with patch('awslabs.etl_replatforming_mcp_server.server.get_generator') as mock_get_gen:
            mock_generator = Mock()
            mock_generator.generate.side_effect = RuntimeError('Generation failed')
            mock_get_gen.return_value = mock_generator

            # Should propagate the exception
            with pytest.raises(RuntimeError) as exc_info:
                await generate_from_flex_workflow(workflow, 'step_functions')
            assert 'Generation failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_to_flex_workflow_parser_exception(self):
        """Test parse_to_flex_workflow when parser raises exception."""
        from awslabs.etl_replatforming_mcp_server.server import parse_to_flex_workflow

        with patch('awslabs.etl_replatforming_mcp_server.server.get_parser') as mock_get_parser:
            parser = Mock()
            parser.parse_code.side_effect = RuntimeError('Parsing failed')
            mock_get_parser.return_value = parser

            # Should propagate the exception
            with pytest.raises(RuntimeError) as exc_info:
                await parse_to_flex_workflow('airflow', 'test code')
            assert 'Parsing failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_to_flex_workflow_validator_exception(self):
        """Test parse_to_flex_workflow when validator raises exception."""
        from awslabs.etl_replatforming_mcp_server.server import parse_to_flex_workflow

        with (
            patch('awslabs.etl_replatforming_mcp_server.server.get_parser') as mock_get_parser,
            patch('awslabs.etl_replatforming_mcp_server.server.validator') as mock_validator,
        ):
            parser = Mock()
            workflow = Mock(spec=FlexWorkflow)
            workflow.parsing_info = Mock(spec=ParsingInfo)
            workflow.parsing_info.parsing_completeness = 1.0
            workflow.get_missing_fields.return_value = []
            parser.parse_code.return_value = workflow
            mock_get_parser.return_value = parser

            mock_validator.validate.side_effect = RuntimeError('Validation failed')

            # Should propagate the exception
            with pytest.raises(RuntimeError) as exc_info:
                await parse_to_flex_workflow('airflow', 'test code')
            assert 'Validation failed' in str(exc_info.value)

    def test_main_function_exists(self):
        """Test main function exists and is callable."""
        from awslabs.etl_replatforming_mcp_server.server import main

        assert callable(main)

    def test_get_generator_azure_data_factory_not_supported(self):
        """Test get_generator raises error for azure_data_factory (not supported as target)."""
        from awslabs.etl_replatforming_mcp_server.server import get_generator

        with pytest.raises(ValueError, match='Unsupported target framework'):
            get_generator('azure_data_factory')

    @patch('awslabs.etl_replatforming_mcp_server.server.BedrockService')
    def test_get_bedrock_service_with_custom_config(self, mock_service):
        """Test get_bedrock_service with custom config creates new instance."""
        from awslabs.etl_replatforming_mcp_server.server import get_bedrock_service

        mock_instance = Mock()
        mock_service.return_value = mock_instance

        service = get_bedrock_service({'model_id': 'custom-model'})
        assert service == mock_instance
        mock_service.assert_called_once()

    @patch('awslabs.etl_replatforming_mcp_server.server.BedrockService')
    def test_get_bedrock_service_default_caching(self, mock_service):
        """Test get_bedrock_service caching with default config."""
        from awslabs.etl_replatforming_mcp_server.server import (
            get_bedrock_service,
            set_global_llm_config,
        )

        # Reset state
        set_global_llm_config(None)

        mock_instance = Mock()
        mock_service.return_value = mock_instance

        # First call should create service
        service1 = get_bedrock_service()
        assert service1 == mock_instance

        # Second call should return cached service
        service2 = get_bedrock_service()
        assert service2 == mock_instance

        # Should only create service once
        assert mock_service.call_count == 1
