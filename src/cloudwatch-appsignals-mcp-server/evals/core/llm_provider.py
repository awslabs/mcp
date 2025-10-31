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

"""LLM provider abstraction for pluggable LLM support."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate text from the LLM."""
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
        from .constants import DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE

        model_id = self.model_id or DEFAULT_MODEL_ID
        temperature = self.temperature if self.temperature is not None else DEFAULT_TEMPERATURE

        response = self.bedrock_client.converse(
            modelId=model_id,
            messages=[{'role': 'user', 'content': [{'text': prompt}]}],
            inferenceConfig={'temperature': temperature},
        )

        return response['output']['message']['content'][0]['text']
