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

"""Data scrubbing utilities for removing sensitive information from AWS configurations."""

import re
from typing import Any, Dict


class DataScrubber:
    """Utility class for scrubbing sensitive data from AWS configurations and responses."""

    # Patterns for sensitive data that should be redacted
    SENSITIVE_PATTERNS = {
        # AWS Account IDs (12 digits)
        'account_id': re.compile(r'\b\d{12}\b'),
        # AWS Access Keys (starts with AKIA, ASIA, etc.)
        'access_key': re.compile(
            r'\b(AKIA|ASIA|AROA|AIDA|AGPA|AIPA|ANPA|ANVA|APKA)[A-Z0-9]{16}\b'
        ),
        # AWS Secret Keys (base64-like strings of 40 chars)
        'secret_key': re.compile(r'\b[A-Za-z0-9+/]{40}\b'),
        # AWS Session Tokens (longer base64-like strings)
        'session_token': re.compile(r'\b[A-Za-z0-9+/=]{100,}\b'),
        # IP Addresses (private and public)
        'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
        # Email addresses
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        # Phone numbers (various formats)
        'phone': re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
        # URLs with credentials
        'url_with_creds': re.compile(r'https?://[^:]+:[^@]+@[^\s]+'),
        # Database connection strings
        'db_connection': re.compile(r'(mysql|postgresql|mongodb)://[^:]+:[^@]+@[^\s]+'),
        # JWT tokens
        'jwt_token': re.compile(r'\beyJ[A-Za-z0-9+/=]+\.[A-Za-z0-9+/=]+\.[A-Za-z0-9+/=]*\b'),
    }

    # AWS-specific sensitive field names
    SENSITIVE_FIELD_NAMES = {
        'password',
        'secret',
        'key',
        'token',
        'credential',
        'auth',
        'AccessKeyId',
        'SecretAccessKey',
        'SessionToken',
        'DBPassword',
        'MasterUserPassword',
        'AdminPassword',
        'ApiKey',
        'AuthToken',
        'BearerToken',
        'PrivateKey',
        'CertificateBody',
        'CertificateChain',
        'PrivateKeyBody',
        'UserData',
        'Environment',
        'EnvironmentVariables',
    }

    # Replacement patterns for different types of sensitive data
    REPLACEMENTS = {
        'account_id': '************',
        'access_key': 'AKIA****************',
        'secret_key': '****************************************',
        'session_token': '[REDACTED_SESSION_TOKEN]',
        'ip_address': 'XXX.XXX.XXX.XXX',
        'email': '[REDACTED_EMAIL]',
        'phone': '[REDACTED_PHONE]',
        'url_with_creds': '[REDACTED_URL_WITH_CREDENTIALS]',
        'db_connection': '[REDACTED_DB_CONNECTION]',
        'jwt_token': '[REDACTED_JWT_TOKEN]',
        'generic': '[REDACTED]',
    }

    @classmethod
    def scrub_text(cls, text: Any) -> Any:
        """Scrub sensitive data from a text string.

        Args:
            text: The text to scrub

        Returns:
            The scrubbed text with sensitive data replaced
        """
        if not isinstance(text, str):
            return text

        scrubbed = text

        # Apply pattern-based scrubbing in specific order
        # More specific patterns first to avoid conflicts
        pattern_order = [
            'url_with_creds',  # URLs with credentials first
            'db_connection',  # DB connections second
            'jwt_token',  # JWT tokens
            'session_token',  # Session tokens
            'secret_key',  # Secret keys
            'access_key',  # Access keys
            'account_id',  # Account IDs
            'email',  # Email addresses (after URL/DB patterns)
            'phone',  # Phone numbers
            'ip_address',  # IP addresses
        ]

        for pattern_name in pattern_order:
            if pattern_name in cls.SENSITIVE_PATTERNS:
                pattern = cls.SENSITIVE_PATTERNS[pattern_name]
                replacement = cls.REPLACEMENTS.get(pattern_name, cls.REPLACEMENTS['generic'])
                scrubbed = pattern.sub(replacement, scrubbed)

        return scrubbed

    @classmethod
    def scrub_dict(cls, data: Any, deep_copy: bool = True) -> Any:
        """Scrub sensitive data from a dictionary.

        Args:
            data: The dictionary to scrub
            deep_copy: Whether to create a deep copy (default: True)

        Returns:
            The scrubbed dictionary
        """
        if not isinstance(data, dict):
            return data

        if deep_copy:
            import copy

            scrubbed = copy.deepcopy(data)
        else:
            scrubbed = data.copy()

        return cls._scrub_dict_recursive(scrubbed)

    @classmethod
    def _scrub_dict_recursive(cls, data: Any) -> Any:
        """Recursively scrub sensitive data from nested structures.

        Args:
            data: The data structure to scrub

        Returns:
            The scrubbed data structure
        """
        if isinstance(data, dict):
            scrubbed = {}
            for key, value in data.items():
                # Check if the key name indicates sensitive data
                if cls._is_sensitive_field_name(key):
                    scrubbed[key] = cls.REPLACEMENTS['generic']
                else:
                    scrubbed[key] = cls._scrub_dict_recursive(value)
            return scrubbed

        elif isinstance(data, list):
            return [cls._scrub_dict_recursive(item) for item in data]

        elif isinstance(data, str):
            return cls.scrub_text(data)

        elif isinstance(data, (int, float)):
            # Convert numbers to strings and check if they match sensitive patterns
            str_data = str(data)
            scrubbed_str = cls.scrub_text(str_data)
            # If the string was modified, return the scrubbed string
            if scrubbed_str != str_data:
                return scrubbed_str
            else:
                return data

        else:
            return data

    @classmethod
    def _is_sensitive_field_name(cls, field_name: str) -> bool:
        """Check if a field name indicates sensitive data.

        Args:
            field_name: The field name to check

        Returns:
            True if the field name indicates sensitive data
        """
        field_lower = field_name.lower()

        # Check exact matches first
        if field_lower in {name.lower() for name in cls.SENSITIVE_FIELD_NAMES}:
            return True

        # Check partial matches for common sensitive patterns
        # But be more specific - avoid matching container field names
        sensitive_substrings = ['password', 'secret', 'key', 'token', 'credential', 'auth']

        # Don't treat container/collection field names as sensitive
        # (e.g., "list_with_secrets", "secrets_config", etc.)
        container_indicators = ['list', 'array', 'config', 'settings', 'data', 'info', 'details']

        # If it looks like a container field, don't treat as sensitive
        if any(indicator in field_lower for indicator in container_indicators):
            return False

        return any(substring in field_lower for substring in sensitive_substrings)

    @classmethod
    def scrub_lambda_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub sensitive data from Lambda function configuration.

        Args:
            config: Lambda function configuration

        Returns:
            Scrubbed Lambda configuration
        """
        import copy

        scrubbed = copy.deepcopy(config)

        # Custom scrubbing for Lambda config - don't treat Environment as sensitive
        for key, value in scrubbed.items():
            if key == 'Environment' and isinstance(value, dict):
                # Handle Environment section specially
                if 'Variables' in value and isinstance(value['Variables'], dict):
                    # Scrub environment variables more aggressively
                    env_vars = value['Variables']
                    for env_key, env_value in env_vars.items():
                        if cls._is_sensitive_field_name(env_key):
                            env_vars[env_key] = cls.REPLACEMENTS['generic']
                        else:
                            # Always scrub the value for patterns (this handles sensitive values with specific patterns)
                            env_vars[env_key] = cls.scrub_text(str(env_value))
            elif cls._is_sensitive_field_name(key):
                scrubbed[key] = cls.REPLACEMENTS['generic']
            else:
                scrubbed[key] = cls._scrub_dict_recursive(value)

        return scrubbed

    @classmethod
    def scrub_esm_config(cls, config: Any) -> Dict[str, Any]:
        """Scrub sensitive data from Event Source Mapping configuration.

        Args:
            config: ESM configuration

        Returns:
            Scrubbed ESM configuration
        """
        # Handle FieldInfo objects by returning empty dict
        if not isinstance(config, dict):
            return {}

        scrubbed = cls.scrub_dict(config)

        # ESM-specific scrubbing
        sensitive_esm_fields = [
            'SourceAccessConfigurations',
            'SelfManagedEventSource',
            'AmazonManagedKafkaEventSourceConfig',
            'SelfManagedKafkaEventSourceConfig',
        ]

        for field in sensitive_esm_fields:
            if field in scrubbed:
                # Scrub authentication and connection details
                if isinstance(scrubbed[field], dict):
                    scrubbed[field] = cls._scrub_dict_recursive(scrubbed[field])
                elif isinstance(scrubbed[field], list):
                    scrubbed[field] = [cls._scrub_dict_recursive(item) for item in scrubbed[field]]

        return scrubbed

    @classmethod
    def _looks_like_sensitive_value(cls, value: str) -> bool:
        """Check if a value looks like sensitive data based on patterns.

        Args:
            value: The value to check

        Returns:
            True if the value looks sensitive
        """
        if len(value) < 8:  # Very short values are probably not sensitive
            return False

        # Check against known sensitive patterns
        for pattern in cls.SENSITIVE_PATTERNS.values():
            if pattern.search(value):
                return True

        # Check for high entropy (likely encoded/encrypted data)
        if len(value) > 20 and cls._has_high_entropy(value):
            return True

        return False

    @classmethod
    def _has_high_entropy(cls, value: str) -> bool:
        """Check if a string has high entropy (likely encoded data).

        Args:
            value: The string to check

        Returns:
            True if the string has high entropy
        """
        import math
        from collections import Counter

        if len(value) < 10:
            return False

        # Calculate Shannon entropy
        counter = Counter(value)
        length = len(value)
        entropy = -sum((count / length) * math.log2(count / length) for count in counter.values())

        # High entropy threshold (base64 encoded data typically has entropy > 4.5)
        return entropy > 4.5

    @classmethod
    def scrub_aws_response(cls, response: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub sensitive data from AWS API responses.

        Args:
            response: AWS API response

        Returns:
            Scrubbed AWS response
        """
        scrubbed = cls.scrub_dict(response)

        # Remove AWS metadata that might contain sensitive info
        if 'ResponseMetadata' in scrubbed:
            metadata = scrubbed['ResponseMetadata']
            if 'HTTPHeaders' in metadata:
                # Keep only safe headers
                safe_headers = ['content-type', 'content-length', 'date', 'server']
                metadata['HTTPHeaders'] = {
                    k: v for k, v in metadata['HTTPHeaders'].items() if k.lower() in safe_headers
                }

        return scrubbed
