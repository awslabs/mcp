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

"""Tests for the eval framework's Bedrock provider and LLM judge (evals/core)."""

import importlib
import pytest
from evals.core import BedrockLLMProvider, LLMJudgeValidator, ValidationPromptType, eval_config
from evals.core.captor import FINAL_RESPONSE
from unittest.mock import MagicMock


class TestBedrockLLMProvider:
    """Converse request built by BedrockLLMProvider."""

    def test_default_temperature_is_sent(self, monkeypatch):
        """Without MCP_EVAL_TEMPERATURE the default 0.0 is sent, as before."""
        monkeypatch.delenv('MCP_EVAL_TEMPERATURE', raising=False)
        importlib.reload(eval_config)
        client = MagicMock()
        BedrockLLMProvider(bedrock_client=client, model_id='model').converse(messages=[])
        assert client.converse.call_args.kwargs['inferenceConfig'] == {'temperature': 0.0}

    def test_temperature_none_omits_inference_config(self, monkeypatch):
        """MCP_EVAL_TEMPERATURE=none omits the field for models that reject it."""
        monkeypatch.setenv('MCP_EVAL_TEMPERATURE', 'none')
        try:
            importlib.reload(eval_config)
            assert eval_config.TEMPERATURE is None
            client = MagicMock()
            BedrockLLMProvider(bedrock_client=client, model_id='us.openai.gpt-6-sol').converse(
                messages=[]
            )
            assert 'inferenceConfig' not in client.converse.call_args.kwargs
        finally:
            monkeypatch.delenv('MCP_EVAL_TEMPERATURE')
            importlib.reload(eval_config)


class TestLLMJudgeValidator:
    """Parsing of the judge model's Converse reply."""

    @staticmethod
    async def _validate(content):
        provider = MagicMock()
        provider.converse.return_value = {'output': {'message': {'content': content}}}
        validator = LLMJudgeValidator(
            ValidationPromptType.DATA_INTERPRETATION, provider, ['Lists the services']
        )
        return await validator.validate({FINAL_RESPONSE: 'Two services are monitored.'})

    @pytest.mark.asyncio
    async def test_reasoning_block_before_text(self):
        """A reasoningContent block ahead of the verdict text is skipped."""
        result = await self._validate(
            [
                {'reasoningContent': {'redactedContent': b'rsn_example'}},
                {'text': '1. [PASS] Both services are listed.'},
            ]
        )
        assert result.get('overall_pass') is True, result
        assert result.get('criteria_results', [])[0]['status'] == 'PASS'

    @pytest.mark.asyncio
    async def test_reply_without_text_block_fails(self):
        """A reply with only a reasoning block is still a validation error."""
        result = await self._validate([{'reasoningContent': {'redactedContent': b'rsn_example'}}])
        assert result.get('overall_pass') is False
