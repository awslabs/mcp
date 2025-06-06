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
"""Security utilities for the AWS Serverless MCP Server."""

import re
from typing import Any, Dict


class ResponseSanitizer:
    """Sanitizes responses to prevent sensitive information leakage in CloudWatch logs and Lambda outputs."""

    # Patterns for sensitive data commonly found in serverless environments
    PATTERNS = {
        'aws_access_key': r'\b[A-Z0-9]{20}\b',
        'aws_secret_key': r'\b[A-Za-z0-9/+=]{40}\b',
        'password': r'(?i)password\s*[=:]\s*[^\s]+',
        'private_key': r'-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----',
        'aws_account_id': r'\b\d{12}\b',
        'api_key': r'(?i)(api[_-]?key|x-api-key)\s*[:=]\s*[a-zA-Z0-9_/+=:\-]+',
    }

    @classmethod
    def sanitize(cls, response: Any) -> Any:
        """Sanitizes a response to remove sensitive information.

        Args:
            response: The response to sanitize

        Returns:
            Any: The sanitized response
        """
        if isinstance(response, dict):
            return cls._sanitize_dict(response)
        elif isinstance(response, list):
            return [cls.sanitize(item) for item in response]
        elif isinstance(response, str):
            return cls._sanitize_string(response)
        else:
            return response

    @classmethod
    def _sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes a dictionary recursively.

        Args:
            data: The dictionary to sanitize

        Returns:
            Dict[str, Any]: The sanitized dictionary
        """
        result = {}
        for key, value in data.items():
            result[key] = cls.sanitize(value)
        return result

    @classmethod
    def _sanitize_string(cls, text: str) -> str:
        """Sanitizes a string to remove sensitive information.

        Args:
            text: The string to sanitize

        Returns:
            str: The sanitized string
        """
        for pattern_name, pattern in cls.PATTERNS.items():
            text = re.sub(pattern, f'[REDACTED {pattern_name.upper()}]', text)
        return text
