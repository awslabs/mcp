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

    Provides conversational interface for both simple queries and multi-turn
    interactions with tool calling.
    """

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
        bedrock_client: Optional[Any] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        region_name: Optional[str] = None,
    ):
        """Initialize Bedrock LLM provider.

        Args:
            bedrock_client: Boto3 Bedrock Runtime client (created if not provided)
            model_id: Model ID (defaults to framework default)
            temperature: Temperature (defaults to framework default)
            region_name: AWS region (defaults to framework default, only used if bedrock_client not provided)
        """
        if bedrock_client is None:
            import boto3
            from .eval_config import AWS_REGION

            region = region_name or AWS_REGION
            self.bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=region)
        else:
            self.bedrock_client = bedrock_client
        self.model_id = model_id
        self.temperature = temperature

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
