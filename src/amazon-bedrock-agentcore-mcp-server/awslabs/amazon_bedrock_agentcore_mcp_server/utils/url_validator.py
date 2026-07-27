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

"""URL validation for domain restriction."""

import posixpath
from typing import List
from urllib.parse import urlparse


class URLValidationError(Exception):
    """Raised when a URL fails validation."""

    pass


class _AllowedOrigin:
    """Parsed representation of an allowed URL prefix for structural matching."""

    def __init__(self, raw: str):
        parsed = urlparse(raw)
        self.scheme = parsed.scheme
        self.hostname = parsed.hostname or ''
        self.path = parsed.path.rstrip('/')

    def matches(self, scheme: str, hostname: str, normalized_path: str) -> bool:
        if self.scheme != scheme or self.hostname != hostname:
            return False
        if not self.path:
            return True
        return normalized_path == self.path or normalized_path.startswith(self.path + '/')


class URLValidator:
    """Validates URLs against a list of allowed domain prefixes."""

    def __init__(self, allowed_domain_prefixes: List[str]):
        """Initialize the URL validator with allowed domain prefixes."""
        self.allowed_domain_prefixes = set(allowed_domain_prefixes)
        self._allowed_origins = [_AllowedOrigin(p) for p in allowed_domain_prefixes]

    def is_url_allowed(self, url: str | None) -> bool:
        """Check if a URL is allowed based on structural matching against allowed origins."""
        if not url or not isinstance(url, str):
            return False

        if any(c in url for c in '\r\n\x00'):
            return False

        parsed = urlparse(url)

        if parsed.scheme != 'https':
            return False

        if '@' in parsed.netloc:
            return False

        hostname = parsed.hostname or ''
        normalized_path = posixpath.normpath(parsed.path or '/')

        for origin in self._allowed_origins:
            if origin.matches(parsed.scheme, hostname, normalized_path):
                return True

        return False

    def validate_urls(self, urls) -> List[str]:
        """Validate URLs and return valid ones, raising URLValidationError for any disallowed URL."""
        if isinstance(urls, str):
            urls = [urls]

        validated_urls = []
        invalid_urls = []

        for url in urls:
            if self.is_url_allowed(url):
                validated_urls.append(url)
            else:
                invalid_urls.append(url)

        if invalid_urls:
            allowed_domains = ', '.join(sorted(self.allowed_domain_prefixes))
            raise URLValidationError(
                f'URLs not allowed: {", ".join(invalid_urls)}. '
                f'Allowed domain prefixes: {allowed_domains}'
            )

        return validated_urls


DEFAULT_ALLOWED_DOMAINS = [
    'https://aws.github.io/bedrock-agentcore-starter-toolkit',
    'https://strandsagents.com/',
    'https://docs.aws.amazon.com/',
    'https://boto3.amazonaws.com/v1/documentation/',
]

default_validator = URLValidator(DEFAULT_ALLOWED_DOMAINS)


def validate_urls(urls, allowed_domains: list[str] | None = None) -> list[str]:
    """Validate URLs based on allowed domains.

    Args:
        urls: Single URL string or list of URLs to validate
        allowed_domains: Optional list of allowed domain prefixes. If None, uses default allowed domains.

    Returns:
        List of validated URLs

    Raises:
        URLValidationError: If any URL is not allowed
    """
    if isinstance(urls, str):
        urls = [urls]

    for url in urls:
        if not url.startswith(('http://', 'https://')):
            raise URLValidationError(
                f'Relative URLs are not allowed: {url}. '
                f'All URLs must use an absolute https:// scheme.'
            )

    if allowed_domains is None:
        return default_validator.validate_urls(urls)
    else:
        validator = URLValidator(allowed_domains)
        return validator.validate_urls(urls)
