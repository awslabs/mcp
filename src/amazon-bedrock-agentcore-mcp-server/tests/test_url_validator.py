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

"""Tests for URL validation functionality."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.utils.url_validator import (
    URLValidationError,
    URLValidator,
    validate_urls,
)


class TestURLValidator:
    """Test cases for URLValidator class."""

    def test_init_with_domain_prefixes(self):
        """Test URLValidator initialization with domain prefixes."""
        allowed_domains = ['https://docs.aws.amazon.com', 'https://github.com']
        validator = URLValidator(allowed_domains)
        assert validator.allowed_domain_prefixes == {
            'https://docs.aws.amazon.com',
            'https://github.com',
        }

    def test_is_url_allowed(self):
        """Test is_url_allowed with valid URLs."""
        allowed_domains = [
            'https://docs.aws.amazon.com',
            'https://github.com',
            'http://docs.aws.amazon.com',
        ]
        validator = URLValidator(allowed_domains)

        assert validator.is_url_allowed('https://docs.aws.amazon.com/bedrock/agentcore/')
        assert validator.is_url_allowed('https://github.com/awslabs/mcp/blob/main/README.md')
        assert validator.is_url_allowed('http://docs.aws.amazon.com/bedrock/')

        assert not validator.is_url_allowed('https://example.com/page')
        assert not validator.is_url_allowed('https://malicious-site.com/evil')

    def test_validate_urls_all_valid(self):
        """Test validate_urls with all valid URLs."""
        allowed_domains = ['https://docs.aws.amazon.com', 'https://github.com']
        validator = URLValidator(allowed_domains)

        urls = ['https://docs.aws.amazon.com/bedrock/', 'https://github.com/awslabs/mcp']
        result = validator.validate_urls(urls)
        assert result == urls

        default_urls = ['https://docs.aws.amazon.com/bedrock/', 'https://strandsagents.com/']
        result = validate_urls(default_urls)
        assert result == default_urls

    def test_validate_urls_some_invalid(self):
        """Test validate_urls with some invalid URLs."""
        allowed_domains = ['https://docs.aws.amazon.com']
        validator = URLValidator(allowed_domains)

        urls = ['https://docs.aws.amazon.com/bedrock/', 'https://example.com/page']

        with pytest.raises(URLValidationError) as e:
            validator.validate_urls(urls)
        assert 'https://example.com/page' in str(e.value)

        # Default validator
        with pytest.raises(URLValidationError) as e:
            validate_urls(urls)
        assert 'https://example.com/page' in str(e.value)

    def test_validate_urls_empty_list(self):
        """Test validate_urls with empty list."""
        validator = URLValidator(['https://docs.aws.amazon.com'])
        result = validator.validate_urls([])
        assert result == []
