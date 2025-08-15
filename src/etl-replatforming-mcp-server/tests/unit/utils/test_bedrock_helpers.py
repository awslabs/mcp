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

"""Unit tests for BedrockHelpers."""

from awslabs.etl_replatforming_mcp_server.constants import (
    BASE_CONFIDENCE,
    CLAUDE_3_5_SONNET_INFERENCE_PROFILE,
    CLAUDE_3_5_SONNET_MODEL_ID,
    CLAUDE_SONNET_4_INFERENCE_PROFILE,
    CLAUDE_SONNET_4_MODEL_ID,
    CONFIDENCE_BONUS_COMPLETE_RESPONSE,
    CONFIDENCE_BONUS_DYNAMIC_DETECTION,
    CONFIDENCE_BONUS_FIELD_SPECIFIC,
    MAX_CONFIDENCE,
    TASK_TYPE_FOR_EACH,
)
from awslabs.etl_replatforming_mcp_server.utils.bedrock_helpers import BedrockHelpers


class TestBedrockHelpers:
    """Test cases for BedrockHelpers."""

    def test_get_inference_profile_model_id_claude_sonnet_4(self):
        """Test inference profile mapping for Claude Sonnet 4."""
        result = BedrockHelpers.get_inference_profile_model_id(CLAUDE_SONNET_4_MODEL_ID)
        assert result == CLAUDE_SONNET_4_INFERENCE_PROFILE

    def test_get_inference_profile_model_id_claude_3_5_sonnet(self):
        """Test inference profile mapping for Claude 3.5 Sonnet."""
        result = BedrockHelpers.get_inference_profile_model_id(CLAUDE_3_5_SONNET_MODEL_ID)
        assert result == CLAUDE_3_5_SONNET_INFERENCE_PROFILE

    def test_get_inference_profile_model_id_unknown_model(self):
        """Test inference profile mapping for unknown model returns original."""
        unknown_model = 'anthropic.claude-unknown-model'
        result = BedrockHelpers.get_inference_profile_model_id(unknown_model)
        assert result == unknown_model

    def test_create_field_prompts_basic(self):
        """Test create_field_prompts generates correct prompts."""
        source_framework = 'airflow'
        input_code = 'from airflow import DAG'

        prompts = BedrockHelpers.create_field_prompts(source_framework, input_code)

        assert 'schedule' in prompts
        assert 'error_handling' in prompts
        assert 'parameters' in prompts
        assert 'task_commands' in prompts

        # Check that framework and code are included
        assert source_framework in prompts['schedule']
        assert input_code in prompts['schedule']

    def test_create_field_prompts_with_context(self):
        """Test create_field_prompts includes context document."""
        source_framework = 'step_functions'
        input_code = '{"Comment": "Test"}'
        context_document = 'Use UTC timezone for all schedules'

        prompts = BedrockHelpers.create_field_prompts(
            source_framework, input_code, context_document
        )

        # Check context is included in prompts
        assert context_document in prompts['schedule']
        assert 'Organizational Context' in prompts['schedule']

    def test_calculate_field_confidence_schedule_complete(self):
        """Test confidence calculation for complete schedule field."""
        response = 'Here is the schedule: {"type": "cron", "expression": "0 9 * * *"}'
        field_value = {'type': 'cron', 'expression': '0 9 * * *'}

        confidence = BedrockHelpers.calculate_field_confidence(response, 'schedule', field_value)

        expected = (
            BASE_CONFIDENCE + CONFIDENCE_BONUS_COMPLETE_RESPONSE + CONFIDENCE_BONUS_FIELD_SPECIFIC
        )
        assert confidence == expected

    def test_calculate_field_confidence_schedule_incomplete(self):
        """Test confidence calculation for incomplete schedule field."""
        response = 'Short response'
        field_value = {'type': 'cron'}  # Missing expression

        confidence = BedrockHelpers.calculate_field_confidence(response, 'schedule', field_value)

        assert confidence == BASE_CONFIDENCE

    def test_calculate_field_confidence_error_handling(self):
        """Test confidence calculation for error_handling field."""
        response = 'Error handling configuration with detailed failure actions'
        field_value = {'on_failure': 'retry'}

        confidence = BedrockHelpers.calculate_field_confidence(
            response, 'error_handling', field_value
        )

        expected = (
            BASE_CONFIDENCE + CONFIDENCE_BONUS_COMPLETE_RESPONSE + CONFIDENCE_BONUS_FIELD_SPECIFIC
        )
        assert confidence == expected

    def test_calculate_field_confidence_parameters(self):
        """Test confidence calculation for parameters field."""
        response = 'Parameters extracted from workflow with environment variables'
        field_value = {'env': 'prod', 'region': 'us-east-1'}

        confidence = BedrockHelpers.calculate_field_confidence(response, 'parameters', field_value)

        expected = (
            BASE_CONFIDENCE + CONFIDENCE_BONUS_COMPLETE_RESPONSE + CONFIDENCE_BONUS_FIELD_SPECIFIC
        )
        assert confidence == expected

    def test_calculate_field_confidence_task_commands_with_dynamic(self):
        """Test confidence calculation for task_commands with dynamic detection."""
        response = 'Enhanced tasks with dynamic pattern detection and loop structures'
        field_value = {
            'enhanced_tasks': [
                {'task_id': 'task1', 'command': 'echo hello'},
                {
                    'task_id': 'dynamic_tasks',
                    'type': TASK_TYPE_FOR_EACH,
                    'command': 'process_batch',
                },
            ]
        }

        confidence = BedrockHelpers.calculate_field_confidence(
            response, 'task_commands', field_value
        )

        expected = min(
            BASE_CONFIDENCE
            + CONFIDENCE_BONUS_COMPLETE_RESPONSE
            + CONFIDENCE_BONUS_FIELD_SPECIFIC
            + CONFIDENCE_BONUS_DYNAMIC_DETECTION,
            MAX_CONFIDENCE,
        )
        assert confidence == expected

    def test_calculate_field_confidence_task_commands_no_dynamic(self):
        """Test confidence calculation for task_commands without dynamic detection."""
        response = 'Enhanced tasks with improved commands'
        field_value = {
            'enhanced_tasks': [
                {'task_id': 'task1', 'command': 'echo hello'},
                {'task_id': 'task2', 'command': 'echo world'},
            ]
        }

        confidence = BedrockHelpers.calculate_field_confidence(
            response, 'task_commands', field_value
        )

        # Should be BASE_CONFIDENCE + CONFIDENCE_BONUS_FIELD_SPECIFIC = 0.8 + 0.1 = 0.9
        # (response is too short for complete response bonus)
        expected = BASE_CONFIDENCE + CONFIDENCE_BONUS_FIELD_SPECIFIC
        assert confidence == expected

    def test_calculate_field_confidence_max_limit(self):
        """Test confidence calculation respects maximum limit."""
        response = 'Very detailed response with comprehensive analysis and complete information'
        field_value = {
            'enhanced_tasks': [
                {
                    'task_id': 'dynamic_tasks',
                    'type': TASK_TYPE_FOR_EACH,
                    'command': 'process',
                }
            ]
        }

        confidence = BedrockHelpers.calculate_field_confidence(
            response, 'task_commands', field_value
        )

        assert confidence <= MAX_CONFIDENCE

    def test_calculate_field_confidence_unknown_field(self):
        """Test confidence calculation for unknown field type."""
        response = 'Some response'
        field_value = {'unknown': 'value'}

        confidence = BedrockHelpers.calculate_field_confidence(
            response, 'unknown_field', field_value
        )

        assert confidence == BASE_CONFIDENCE
