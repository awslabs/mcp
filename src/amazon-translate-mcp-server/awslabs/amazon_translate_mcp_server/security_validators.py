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

"""Security validators for Amazon Translate MCP Server.

This module provides comprehensive input validation and security checks
to prevent SSRF, DoS, cost amplification, and other security risks.
"""

import re
from .exceptions import SecurityError, ValidationError
from typing import List, Optional, Set
from urllib.parse import urlparse


# AWS region whitelist - only allow standard AWS regions
ALLOWED_AWS_REGIONS: Set[str] = {
    'us-east-1',
    'us-east-2',
    'us-west-1',
    'us-west-2',
    'af-south-1',
    'ap-east-1',
    'ap-south-1',
    'ap-south-2',
    'ap-northeast-1',
    'ap-northeast-2',
    'ap-northeast-3',
    'ap-southeast-1',
    'ap-southeast-2',
    'ap-southeast-3',
    'ap-southeast-4',
    'ca-central-1',
    'eu-central-1',
    'eu-central-2',
    'eu-west-1',
    'eu-west-2',
    'eu-west-3',
    'eu-south-1',
    'eu-south-2',
    'eu-north-1',
    'me-south-1',
    'me-central-1',
    'sa-east-1',
    'us-gov-east-1',
    'us-gov-west-1',
}

# Supported language codes for Amazon Translate
SUPPORTED_LANGUAGE_CODES: Set[str] = {
    'af',
    'sq',
    'am',
    'ar',
    'hy',
    'az',
    'bn',
    'bs',
    'bg',
    'ca',
    'zh',
    'zh-TW',
    'hr',
    'cs',
    'da',
    'fa-AF',
    'nl',
    'en',
    'et',
    'fa',
    'tl',
    'fi',
    'fr',
    'fr-CA',
    'ka',
    'de',
    'el',
    'gu',
    'ht',
    'ha',
    'he',
    'hi',
    'hu',
    'is',
    'id',
    'ga',
    'it',
    'ja',
    'kn',
    'kk',
    'ko',
    'lv',
    'lt',
    'mk',
    'ms',
    'ml',
    'mt',
    'mr',
    'mn',
    'no',
    'ps',
    'pl',
    'pt',
    'pt-PT',
    'pa',
    'ro',
    'ru',
    'sr',
    'si',
    'sk',
    'sl',
    'so',
    'es',
    'es-MX',
    'sw',
    'sv',
    'ta',
    'te',
    'th',
    'tr',
    'uk',
    'ur',
    'uz',
    'vi',
    'cy',
}

# Maximum limits
MAX_TEXT_LENGTH = 100000  # 100KB of text
MAX_BATCH_SIZE = 1000  # Maximum number of items in a batch
MAX_S3_PREFIX_LENGTH = 1024
MAX_JOB_NAME_LENGTH = 256
MAX_TERMINOLOGY_NAME_LENGTH = 256


def validate_aws_region(region: Optional[str]) -> str:
    """Validate AWS region against whitelist.

    Args:
        region: AWS region to validate

    Returns:
        Validated region string

    Raises:
        SecurityError: If region is not in whitelist

    """
    if not region:
        raise ValidationError(
            'AWS region is required', field_errors={'region': 'Region cannot be empty'}
        )

    if region not in ALLOWED_AWS_REGIONS:
        raise SecurityError(
            f'Invalid or unsupported AWS region: {region}',
            security_type='region_validation',
            details={'provided_region': region, 'allowed_regions': list(ALLOWED_AWS_REGIONS)},
        )

    return region


def validate_language_code(language_code: str, field_name: str = 'language_code') -> str:
    """Validate language code against supported languages.

    Args:
        language_code: Language code to validate
        field_name: Name of the field for error reporting

    Returns:
        Validated language code

    Raises:
        ValidationError: If language code is invalid

    """
    if not language_code:
        raise ValidationError(
            f'{field_name} is required', field_errors={field_name: 'Language code cannot be empty'}
        )

    # Normalize to lowercase for comparison
    normalized_code = language_code.strip().lower()

    # Check against supported codes (case-insensitive)
    if normalized_code not in {code.lower() for code in SUPPORTED_LANGUAGE_CODES}:
        raise ValidationError(
            f'Unsupported language code: {language_code}',
            field_errors={
                field_name: 'Language code must be one of the supported codes',
                'provided_code': language_code,
            },
        )

    return language_code.strip()


def validate_text_input(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Validate text input for length and content.

    Args:
        text: Text to validate
        max_length: Maximum allowed text length

    Returns:
        Validated text

    Raises:
        ValidationError: If text is invalid or too long

    """
    if not text:
        raise ValidationError(
            'Text input is required', field_errors={'text': 'Text cannot be empty'}
        )

    if len(text) > max_length:
        raise ValidationError(
            f'Text exceeds maximum length of {max_length} characters',
            field_errors={
                'text': f'Text length {len(text)} exceeds maximum {max_length}',
                'current_length': str(len(text)),
                'max_length': str(max_length),
            },
        )

    return text


def validate_s3_uri(s3_uri: str, field_name: str = 's3_uri') -> str:
    """Validate S3 URI format and prevent SSRF attacks.

    Args:
        s3_uri: S3 URI to validate
        field_name: Name of the field for error reporting

    Returns:
        Validated S3 URI

    Raises:
        SecurityError: If S3 URI is malformed or potentially malicious

    """
    if not s3_uri:
        raise ValidationError(
            f'{field_name} is required', field_errors={field_name: 'S3 URI cannot be empty'}
        )

    # Check URI length
    if len(s3_uri) > MAX_S3_PREFIX_LENGTH:
        raise ValidationError(
            f'S3 URI exceeds maximum length of {MAX_S3_PREFIX_LENGTH}',
            field_errors={field_name: f'URI length {len(s3_uri)} exceeds maximum'},
        )

    # Parse and validate S3 URI format
    if not s3_uri.startswith('s3://'):
        raise SecurityError(
            'Invalid S3 URI format: must start with s3://',
            security_type='s3_uri_validation',
            details={field_name: s3_uri},
        )

    try:
        parsed = urlparse(s3_uri)

        # Validate scheme
        if parsed.scheme != 's3':
            raise SecurityError(
                f'Invalid S3 URI scheme: {parsed.scheme}',
                security_type='s3_uri_validation',
                details={field_name: s3_uri, 'scheme': parsed.scheme},
            )

        # Validate bucket name
        bucket_name = parsed.netloc
        if not bucket_name:
            raise SecurityError(
                'S3 URI must include bucket name',
                security_type='s3_uri_validation',
                details={field_name: s3_uri},
            )

        # Validate bucket name format (basic check)
        if not re.match(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$', bucket_name):
            raise SecurityError(
                f'Invalid S3 bucket name format: {bucket_name}',
                security_type='s3_uri_validation',
                details={field_name: s3_uri, 'bucket': bucket_name},
            )

        # Check for suspicious patterns that might indicate SSRF attempts
        suspicious_patterns = [
            r'localhost',
            r'127\.0\.0\.1',
            r'169\.254\.169\.254',  # AWS metadata service
            r'0\.0\.0\.0',
            r'::1',
            r'metadata',
        ]

        full_uri_lower = s3_uri.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, full_uri_lower):
                raise SecurityError(
                    f'S3 URI contains suspicious pattern: {pattern}',
                    security_type='ssrf_prevention',
                    details={field_name: s3_uri, 'pattern': pattern},
                )

    except SecurityError:
        raise
    except Exception as e:
        raise SecurityError(
            f'Failed to parse S3 URI: {str(e)}',
            security_type='s3_uri_validation',
            details={field_name: s3_uri, 'error': str(e)},
        )

    return s3_uri


def validate_iam_role_arn(role_arn: str) -> str:
    """Validate IAM role ARN format.

    Args:
        role_arn: IAM role ARN to validate

    Returns:
        Validated role ARN

    Raises:
        ValidationError: If role ARN is invalid

    """
    if not role_arn:
        raise ValidationError(
            'IAM role ARN is required', field_errors={'role_arn': 'Role ARN cannot be empty'}
        )

    # Validate ARN format - allow paths in role name
    arn_pattern = r'^arn:aws:iam::\d{12}:role/[\w+=,.@/-]+$'
    if not re.match(arn_pattern, role_arn):
        raise ValidationError(
            f'Invalid IAM role ARN format: {role_arn}',
            field_errors={
                'role_arn': 'ARN must match format: arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME',
                'provided_arn': role_arn,
            },
        )

    return role_arn


def validate_job_name(job_name: str) -> str:
    """Validate batch job name.

    Args:
        job_name: Job name to validate

    Returns:
        Validated job name

    Raises:
        ValidationError: If job name is invalid

    """
    if not job_name:
        raise ValidationError(
            'Job name is required', field_errors={'job_name': 'Job name cannot be empty'}
        )

    if len(job_name) > MAX_JOB_NAME_LENGTH:
        raise ValidationError(
            f'Job name exceeds maximum length of {MAX_JOB_NAME_LENGTH}',
            field_errors={'job_name': f'Length {len(job_name)} exceeds maximum'},
        )

    # Validate job name format (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', job_name):
        raise ValidationError(
            'Job name must contain only alphanumeric characters, hyphens, and underscores',
            field_errors={'job_name': job_name},
        )

    return job_name


def validate_terminology_name(name: str) -> str:
    """Validate terminology name.

    Args:
        name: Terminology name to validate

    Returns:
        Validated terminology name

    Raises:
        ValidationError: If terminology name is invalid

    """
    if not name:
        raise ValidationError(
            'Terminology name is required',
            field_errors={'name': 'Terminology name cannot be empty'},
        )

    if len(name) > MAX_TERMINOLOGY_NAME_LENGTH:
        raise ValidationError(
            f'Terminology name exceeds maximum length of {MAX_TERMINOLOGY_NAME_LENGTH}',
            field_errors={'name': f'Length {len(name)} exceeds maximum'},
        )

    # Validate terminology name format
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValidationError(
            'Terminology name must contain only alphanumeric characters, hyphens, and underscores',
            field_errors={'name': name},
        )

    return name


def validate_batch_size(size: int, max_size: int = MAX_BATCH_SIZE) -> int:
    """Validate batch operation size.

    Args:
        size: Batch size to validate
        max_size: Maximum allowed batch size

    Returns:
        Validated batch size

    Raises:
        ValidationError: If batch size exceeds limits

    """
    if size <= 0:
        raise ValidationError(
            'Batch size must be positive',
            field_errors={'batch_size': f'Size {size} is not positive'},
        )

    if size > max_size:
        raise ValidationError(
            f'Batch size {size} exceeds maximum allowed size of {max_size}',
            field_errors={
                'batch_size': f'Size {size} exceeds maximum {max_size}',
                'current_size': str(size),
                'max_size': str(max_size),
            },
        )

    return size


def validate_target_languages(target_languages: List[str]) -> List[str]:
    """Validate list of target languages.

    Args:
        target_languages: List of target language codes

    Returns:
        Validated list of language codes

    Raises:
        ValidationError: If any language code is invalid

    """
    if not target_languages:
        raise ValidationError(
            'At least one target language is required',
            field_errors={'target_languages': 'List cannot be empty'},
        )

    # Validate batch size
    validate_batch_size(len(target_languages), max_size=10)  # Limit to 10 target languages

    # Validate each language code
    validated_languages = []
    for i, lang_code in enumerate(target_languages):
        try:
            validated_lang = validate_language_code(lang_code, f'target_languages[{i}]')
            validated_languages.append(validated_lang)
        except ValidationError as e:
            raise ValidationError(
                f'Invalid target language at index {i}: {lang_code}',
                field_errors={f'target_languages[{i}]': str(e)},
            )

    return validated_languages
