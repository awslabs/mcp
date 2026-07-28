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
        ]
        validator = URLValidator(allowed_domains)

        assert validator.is_url_allowed('https://docs.aws.amazon.com/bedrock/agentcore/')
        assert validator.is_url_allowed('https://github.com/awslabs/mcp/blob/main/README.md')

        assert not validator.is_url_allowed('https://example.com/page')
        assert not validator.is_url_allowed('https://malicious-site.com/evil')

    def test_is_url_allowed_rejects_http(self):
        """http:// scheme must be rejected even if the domain matches."""
        validator = URLValidator(['https://docs.aws.amazon.com'])
        assert not validator.is_url_allowed('http://docs.aws.amazon.com/bedrock/')

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

        with pytest.raises(URLValidationError) as e:
            validate_urls(urls)
        assert 'https://example.com/page' in str(e.value)

    def test_validate_urls_empty_list(self):
        """Test validate_urls with empty list."""
        validator = URLValidator(['https://docs.aws.amazon.com'])
        result = validator.validate_urls([])
        assert result == []

    # --- Bypass vector tests (P415493054) ---

    def test_rejects_relative_url_path_traversal(self):
        """PoC vector 1: /../../attacker-path must be rejected as a relative URL."""
        with pytest.raises(URLValidationError, match='Relative URLs are not allowed'):
            validate_urls('/../../attacker-path')

    def test_rejects_domain_suffix_attack(self):
        """PoC vector 2: prefix match must not approve a longer hostname."""
        with pytest.raises(URLValidationError):
            validate_urls('https://aws.github.io/bedrock-agentcore-starter-toolkit.evil.com/steal')

    def test_rejects_relative_url_with_query(self):
        """PoC vector 3: /evil?test=1 must be rejected as a relative URL."""
        with pytest.raises(URLValidationError, match='Relative URLs are not allowed'):
            validate_urls('/evil?test=1')

    def test_rejects_path_traversal_in_absolute_url(self):
        """Path traversal via .. in an absolute URL must not escape the allowed path prefix."""
        with pytest.raises(URLValidationError):
            validate_urls(
                'https://aws.github.io/bedrock-agentcore-starter-toolkit/../../other-repo/secrets'
            )

    def test_rejects_plain_relative_path(self):
        """Any relative URL must be rejected outright."""
        for path in ['/foo', 'bar', '../up', './here']:
            with pytest.raises(URLValidationError, match='Relative URLs are not allowed'):
                validate_urls(path)

    def test_rejects_non_https_scheme(self):
        """Only https is permitted."""
        with pytest.raises(URLValidationError):
            validate_urls('http://docs.aws.amazon.com/something')

        with pytest.raises(URLValidationError):
            validate_urls('file:///etc/passwd')

        with pytest.raises(URLValidationError):
            validate_urls('ftp://docs.aws.amazon.com/')

    def test_allows_valid_default_domain_urls(self):
        """Legitimate URLs for all default allowed domains must still pass."""
        valid = [
            'https://aws.github.io/bedrock-agentcore-starter-toolkit/quickstart',
            'https://aws.github.io/bedrock-agentcore-starter-toolkit/docs/guide.html',
            'https://strandsagents.com/latest/user-guide/',
            'https://docs.aws.amazon.com/bedrock/latest/userguide/',
            'https://boto3.amazonaws.com/v1/documentation/api/latest/index.html',
        ]
        result = validate_urls(valid)
        assert result == valid

    def test_path_boundary_enforcement(self):
        """Allowed path prefix must match on / boundaries, not arbitrary substrings."""
        validator = URLValidator(['https://example.com/app'])

        assert validator.is_url_allowed('https://example.com/app')
        assert validator.is_url_allowed('https://example.com/app/')
        assert validator.is_url_allowed('https://example.com/app/sub/page')
        assert not validator.is_url_allowed('https://example.com/application')
        assert not validator.is_url_allowed('https://example.com/app-extra')

    def test_hostname_exact_match(self):
        """Hostname must match exactly, not as a prefix/suffix."""
        validator = URLValidator(['https://docs.aws.amazon.com'])

        assert validator.is_url_allowed('https://docs.aws.amazon.com/page')
        assert not validator.is_url_allowed('https://docs.aws.amazon.com.evil.com/page')
        assert not validator.is_url_allowed('https://evil-docs.aws.amazon.com/page')

    def test_validate_urls_with_custom_allowed_domains(self):
        """Custom allowed_domains parameter must override defaults."""
        custom = ['https://internal.example.com/docs']
        result = validate_urls('https://internal.example.com/docs/page', allowed_domains=custom)
        assert result == ['https://internal.example.com/docs/page']

        with pytest.raises(URLValidationError):
            validate_urls('https://docs.aws.amazon.com/', allowed_domains=custom)

    def test_string_input_wrapped_in_list(self):
        """A single string URL input should be treated as a one-element list."""
        result = validate_urls('https://docs.aws.amazon.com/test')
        assert result == ['https://docs.aws.amazon.com/test']

    def test_rejects_control_characters(self):
        """URLs with control characters (CRLF injection) must be rejected."""
        validator = URLValidator(['https://docs.aws.amazon.com'])
        assert not validator.is_url_allowed('https://docs.aws.amazon.com/\r\ninjection')
        assert not validator.is_url_allowed('https://docs.aws.amazon.com/\x00null')

    def test_rejects_userinfo_in_url(self):
        """URLs with userinfo (user@host) must be rejected."""
        validator = URLValidator(['https://docs.aws.amazon.com'])
        assert not validator.is_url_allowed('https://attacker.com@docs.aws.amazon.com/page')

    def test_empty_and_none_urls(self):
        """Empty/None values must be rejected."""
        validator = URLValidator(['https://docs.aws.amazon.com'])
        assert not validator.is_url_allowed('')
        assert not validator.is_url_allowed(None)
