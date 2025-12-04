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

from typing import List


class URLValidationError(Exception):
    """Raised when a URL fails validation."""

    pass


class URLValidator:
    """Validates URLs against a list of allowed domain prefixes."""

    def __init__(self, allowed_domain_prefixes: List[str]):
        """Initialize the URL validator with allowed domain prefixes.

        Args:
            allowed_domain_prefixes: List of allowed domain prefixes
        """
        self.allowed_domain_prefixes = set(allowed_domain_prefixes)

    def is_url_allowed(self, url: str) -> bool:
        """Check if a URL is allowed based on domain prefixes.

        Args:
            url: The URL to validate

        Returns:
            True if the URL is allowed, False otherwise
        """
        if not url or not isinstance(url, str):
            return False

        # Check if URL starts with any of the allowed prefixes
        for allowed_prefix in self.allowed_domain_prefixes:
            if url.startswith(allowed_prefix):
                return True

        return False

    def validate_urls(self, urls) -> List[str]:
        """Validate URLs and return valid ones.

        Args:
            urls: Single URL string or list of URLs to validate

        Returns:
            List of validated URLs (single URL wrapped in list if input was string)

        Raises:
            URLValidationError: If any URL is not allowed
        """
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

    # Convert relative URLs to absolute URLs
    processed_urls = []
    for url in urls:
        if not url.startswith(('http://', 'https://')):
            url = 'https://aws.github.io/bedrock-agentcore-starter-toolkit' + url
        processed_urls.append(url)

    if allowed_domains is None:
        return default_validator.validate_urls(processed_urls)
    else:
        validator = URLValidator(allowed_domains)
        return validator.validate_urls(processed_urls)
