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

"""Base class for embeddings providers."""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingsProvider(ABC):
    """Abstract base class for embeddings providers.

    All embeddings providers must implement this interface to ensure
    compatibility with the Valkey MCP Server semantic search tools.
    """

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector from text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """Get the dimensionality of embeddings produced by this provider.

        Returns:
            Number of dimensions in the embedding vectors
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this embeddings provider.

        Returns:
            Provider name (e.g., "OpenAI", "Bedrock", "Ollama")
        """
        pass
