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

from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration settings for the MCP server.

    Attributes:
        llm_texts_url: List of llms.txt URLs to index for documentation
        timeout: HTTP request timeout in seconds
        user_agent: User agent string for HTTP requests
    """

    llm_texts_url: list[str] = field(
        default_factory=lambda: [
            'https://gist.githubusercontent.com/ryanycoleman/d22cdd6c37ea261b055dc9504e08d1de/raw/5fa9facbd500dcc87dc940e1a43e825e2b3824b1/agentcore-llms-txt.md'
        ]  # TODO: Update this url after finalizing llm.txt location
    )  # Curated list of llms.txt files to index at startup
    timeout: float = 30.0  # HTTP request timeout in seconds
    # User agent for HTTP requests
    user_agent: str = 'agentcore-mcp-docs/1.0'


# Global configuration instance
doc_config = Config()
