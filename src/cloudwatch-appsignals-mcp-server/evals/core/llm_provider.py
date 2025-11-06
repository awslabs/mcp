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

"""LLM provider abstraction for unified agent and judge support.

This module provides a unified interface for LLM interactions used by both
the agent loop (with tool calling) and the LLM judge (simple text generation).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Supports both simple text generation (for judge) and conversational
    interactions with tool calling (for agent).
    """

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate text from a simple prompt.

        Used by LLM judge for validation.

        Args:
            prompt: Text prompt for generation

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def converse(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Conduct a conversation with optional tool calling.

        Used by agent loop for multi-turn conversations with tool support.

        Args:
            messages: List of conversation messages
            tools: Optional list of tool definitions
            **kwargs: Additional provider-specific parameters

        Returns:
            Response dictionary from the LLM
        """
        pass


class BedrockLLMProvider(LLMProvider):
    """AWS Bedrock LLM provider implementation."""

    def __init__(
        self,
        bedrock_client: Any,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """Initialize Bedrock LLM provider.

        Args:
            bedrock_client: Boto3 Bedrock Runtime client
            model_id: Model ID (defaults to framework default)
            temperature: Temperature (defaults to framework default)
        """
        self.bedrock_client = bedrock_client
        self.model_id = model_id
        self.temperature = temperature

    async def generate(self, prompt: str) -> str:
        """Generate text using AWS Bedrock."""
        from .eval_config import MODEL_ID, TEMPERATURE

        model_id = self.model_id or MODEL_ID
        temperature = self.temperature if self.temperature is not None else TEMPERATURE

        response = self.bedrock_client.converse(
            modelId=model_id,
            messages=[{'role': 'user', 'content': [{'text': prompt}]}],
            inferenceConfig={'temperature': temperature},
        )

        return response['output']['message']['content'][0]['text']

    def converse(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Conduct conversation using AWS Bedrock."""
        from .eval_config import MODEL_ID, TEMPERATURE

        model_id = self.model_id or MODEL_ID
        temperature = self.temperature if self.temperature is not None else TEMPERATURE

        converse_params = {
            'modelId': model_id,
            'messages': messages,
            'inferenceConfig': {'temperature': temperature},
        }

        if tools:
            converse_params['toolConfig'] = {'tools': tools}

        # Allow overriding with additional kwargs
        converse_params.update(kwargs)

        return self.bedrock_client.converse(**converse_params)
