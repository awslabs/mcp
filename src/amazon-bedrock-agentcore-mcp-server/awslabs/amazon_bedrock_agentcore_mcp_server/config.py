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

from .utils.url_validator import URLValidationError, validate_urls
from pydantic import BaseModel, Field, field_validator
from typing import List


class Config(BaseModel):
    """Configuration settings for the MCP server.

    Attributes:
        llm_texts_url: List of llms.txt URLs to index for documentation
        timeout: HTTP request timeout in seconds
        user_agent: User agent string for HTTP requests
    """

    llm_texts_url: List[str] = Field(
        default_factory=lambda: [
            'https://aws.github.io/bedrock-agentcore-starter-toolkit/llms.txt'
        ]
    )  # Curated list of llms.txt files to index at startup
    timeout: float = Field(default=30.0)  # HTTP request timeout in seconds
    user_agent: str = Field(default='agentcore-mcp-docs/1.0')  # User agent for HTTP requests

    @field_validator('llm_texts_url')
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        """Validate URLs after initialization."""
        try:
            return validate_urls(v)
        except URLValidationError as e:
            raise ValueError(f'Invalid URLs in configuration: {e}') from e


# Global configuration instance
doc_config = Config()
