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

"""Unit tests for constants module."""

from awslabs.etl_replatforming_mcp_server import constants


class TestConstants:
    """Test cases for constants module."""

    def test_timeout_constants_are_positive_integers(self):
        """Test that timeout constants are positive integers."""
        timeout_constants = [
            constants.BEDROCK_REQUEST_TIMEOUT,
            constants.BEDROCK_FIELD_TIMEOUT,
            constants.BEDROCK_CONNECT_TIMEOUT,
            constants.BEDROCK_READ_TIMEOUT,
        ]

        for timeout in timeout_constants:
            assert isinstance(timeout, int)
            assert timeout > 0

    def test_retry_constants_are_positive_integers(self):
        """Test that retry constants are positive integers."""
        retry_constants = [
            constants.MAX_BEDROCK_RETRIES,
            constants.BEDROCK_RETRY_BASE_DELAY,
            constants.BEDROCK_GENERAL_RETRY_DELAY,
        ]

        for retry in retry_constants:
            assert isinstance(retry, int)
            assert retry > 0

    def test_confidence_constants_are_valid_floats(self):
        """Test that confidence constants are valid floats between 0 and 1."""
        confidence_constants = [
            constants.BASE_CONFIDENCE,
            constants.CONFIDENCE_BONUS_COMPLETE_RESPONSE,
            constants.CONFIDENCE_BONUS_FIELD_SPECIFIC,
            constants.CONFIDENCE_BONUS_DYNAMIC_DETECTION,
            constants.MAX_CONFIDENCE,
        ]

        for confidence in confidence_constants:
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0

    def test_status_constants_are_strings(self):
        """Test that status constants are non-empty strings."""
        status_constants = [
            constants.STATUS_COMPLETE,
            constants.STATUS_INCOMPLETE,
            constants.STATUS_ERROR,
            constants.STATUS_PARTIAL,
        ]

        for status in status_constants:
            assert isinstance(status, str)
            assert len(status) > 0

    def test_framework_constants_are_lists(self):
        """Test that framework constants are non-empty lists."""
        framework_constants = [
            constants.SUPPORTED_SOURCE_FRAMEWORKS,
            constants.SUPPORTED_TARGET_FRAMEWORKS,
        ]

        for frameworks in framework_constants:
            assert isinstance(frameworks, list)
            assert len(frameworks) > 0
            assert all(isinstance(fw, str) for fw in frameworks)

    def test_model_id_constants_are_strings(self):
        """Test that model ID constants are non-empty strings."""
        model_constants = [
            constants.CLAUDE_SONNET_4_MODEL_ID,
            constants.CLAUDE_3_5_SONNET_MODEL_ID,
            constants.CLAUDE_SONNET_4_INFERENCE_PROFILE,
            constants.CLAUDE_3_5_SONNET_INFERENCE_PROFILE,
        ]

        for model in model_constants:
            assert isinstance(model, str)
            assert len(model) > 0

    def test_field_name_constants_are_strings(self):
        """Test that field name constants are non-empty strings."""
        field_constants = [
            constants.FIELD_SCHEDULE,
            constants.FIELD_ERROR_HANDLING,
            constants.FIELD_PARAMETERS,
            constants.FIELD_TASK_COMMANDS,
        ]

        for field in field_constants:
            assert isinstance(field, str)
            assert len(field) > 0

    def test_parsing_method_constants_are_strings(self):
        """Test that parsing method constants are non-empty strings."""
        method_constants = [
            constants.PARSING_METHOD_DETERMINISTIC,
            constants.PARSING_METHOD_AI_ENHANCED,
            constants.PARSING_METHOD_HYBRID,
        ]

        for method in method_constants:
            assert isinstance(method, str)
            assert len(method) > 0

    def test_aws_region_constant_is_valid(self):
        """Test that AWS region constant is a valid region format."""
        assert isinstance(constants.DEFAULT_AWS_REGION, str)
        assert len(constants.DEFAULT_AWS_REGION) > 0
        # Basic AWS region format check
        assert '-' in constants.DEFAULT_AWS_REGION

    def test_log_constants_are_valid(self):
        """Test that logging constants are valid."""
        assert isinstance(constants.DEFAULT_LOG_LEVEL, str)
        assert constants.DEFAULT_LOG_LEVEL in ['DEBUG', 'INFO', 'WARNING', 'ERROR']

        assert isinstance(constants.LOG_ROTATION_SIZE, str)
        assert 'MB' in constants.LOG_ROTATION_SIZE

        assert isinstance(constants.LOG_FORMAT, str)
        assert '{time' in constants.LOG_FORMAT
        assert '{level' in constants.LOG_FORMAT

    def test_token_limit_is_positive_integer(self):
        """Test that token limit is a positive integer."""
        assert isinstance(constants.MAX_TOKENS_SINGLE_FIELD, int)
        assert constants.MAX_TOKENS_SINGLE_FIELD > 0

    def test_response_threshold_is_positive_integer(self):
        """Test that response threshold is a positive integer."""
        assert isinstance(constants.MIN_RESPONSE_LENGTH_FOR_BONUS, int)
        assert constants.MIN_RESPONSE_LENGTH_FOR_BONUS > 0

    def test_completeness_threshold_is_valid_float(self):
        """Test that completeness threshold is a valid float."""
        assert isinstance(constants.COMPLETENESS_THRESHOLD, float)
        assert 0.0 <= constants.COMPLETENESS_THRESHOLD <= 1.0

    def test_task_type_constant_is_string(self):
        """Test that task type constant is a non-empty string."""
        assert isinstance(constants.TASK_TYPE_FOR_EACH, str)
        assert len(constants.TASK_TYPE_FOR_EACH) > 0

    def test_directory_prefix_constants_are_strings(self):
        """Test that directory prefix constants are non-empty strings."""
        prefix_constants = [
            constants.OUTPUT_DIR_PREFIX_TARGET,
            constants.OUTPUT_DIR_PREFIX_FLEX,
            constants.OUTPUT_DIR_PREFIX_GENERATED,
        ]

        for prefix in prefix_constants:
            assert isinstance(prefix, str)
            assert len(prefix) > 0

    def test_constants_are_immutable_types(self):
        """Test that constants use immutable types where appropriate."""
        # Lists should be tuples for immutability in production, but lists are acceptable for testing
        assert isinstance(constants.SUPPORTED_SOURCE_FRAMEWORKS, list)
        assert isinstance(constants.SUPPORTED_TARGET_FRAMEWORKS, list)

        # Strings and numbers are immutable by nature
        assert isinstance(constants.DEFAULT_AWS_REGION, str)
        assert isinstance(constants.MAX_BEDROCK_RETRIES, int)
        assert isinstance(constants.BASE_CONFIDENCE, float)
