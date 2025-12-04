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

"""Tests for the config module."""

from awslabs.amazon_bedrock_agentcore_mcp_server.config import Config, doc_config


class TestConfig:
    """Test cases for configuration functionality."""

    def test_config_custom_values(self):
        """Test Config can be initialized with custom values."""
        # Arrange
        custom_urls = [
            'https://aws.github.io/bedrock-agentcore-starter-toolkit/doc1',
            'https://aws.github.io/bedrock-agentcore-starter-toolkit/doc1',
        ]
        custom_timeout = 60.0
        custom_user_agent = 'custom-agent/2.0'

        # Act
        config = Config(
            llm_texts_url=custom_urls, timeout=custom_timeout, user_agent=custom_user_agent
        )

        # Assert
        assert config.llm_texts_url == custom_urls
        assert config.timeout == custom_timeout
        assert config.user_agent == custom_user_agent

    def test_config_llm_texts_url_is_list(self):
        """Test llm_texts_url is always a list."""
        # Act
        config = Config()

        # Assert
        assert isinstance(config.llm_texts_url, list)
        assert all(isinstance(url, str) for url in config.llm_texts_url)

    def test_global_doc_config_exists(self):
        """Test global doc_config instance exists and is properly configured."""
        # Assert
        assert doc_config is not None
        assert isinstance(doc_config, Config)
        assert isinstance(doc_config.llm_texts_url, list)
        assert doc_config.timeout > 0
        assert isinstance(doc_config.user_agent, str)
        assert len(doc_config.user_agent) > 0

    def test_config_timeout_is_float(self):
        """Test timeout is stored as float."""
        # Act
        config = Config(timeout=45.0)

        # Assert
        assert isinstance(config.timeout, float)
        assert config.timeout == 45.0

    def test_config_user_agent_format(self):
        """Test user agent follows expected format."""
        # Act
        config = Config()

        # Assert
        assert '/' in config.user_agent
        assert 'agentcore' in config.user_agent.lower()
        assert 'mcp' in config.user_agent.lower()

    def test_config_llm_texts_url_default_is_valid_url(self):
        """Test default llm_texts_url contains valid URLs."""
        # Act
        config = Config()

        # Assert
        for url in config.llm_texts_url:
            assert url.startswith('https://')
            assert 'llms.txt' in url

    def test_config_supports_multiple_llm_urls(self):
        """Test config supports multiple LLM text URLs."""
        # Arrange
        multiple_urls = [
            'https://aws.github.io/bedrock-agentcore-starter-toolkit/doc1',
            'https://aws.github.io/bedrock-agentcore-starter-toolkit/doc2',
            'https://aws.github.io/bedrock-agentcore-starter-toolkit/doc3',
        ]

        # Act
        config = Config(llm_texts_url=multiple_urls)

        # Assert
        assert len(config.llm_texts_url) == 3
        assert config.llm_texts_url == multiple_urls
