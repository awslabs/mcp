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

"""AWS IoT SiteWise parameter validation utilities."""

import html
import re
from .validation_utils import validate_asset_or_model_id
from datetime import datetime
from typing import Any, Dict, List, Union


COMPUTATION_MODEL_NAME_DESCRIPTION_PATTERN = re.compile(r'^[a-zA-Z0-9 _\-#$*!@]+$')


class ValidationError(Exception):
    """Custom exception for parameter validation errors."""

    pass


def validate_asset_id(asset_id: str) -> None:
    """Validate asset ID format - accepts UUID or external ID format."""
    try:
        validate_asset_or_model_id(asset_id, 'assetId')
    except ValueError as e:
        raise ValidationError(str(e))


def validate_asset_model_id(asset_model_id: str) -> None:
    """Validate asset model ID format - accepts UUID or external ID format."""
    try:
        validate_asset_or_model_id(asset_model_id, 'assetModelId')
    except ValueError as e:
        raise ValidationError(str(e))


def validate_computation_model_name(computation_model_name: str) -> None:
    """Validate computation model name constraints."""
    if not computation_model_name:
        raise ValidationError('Computation model name cannot be empty')
    if len(computation_model_name) > 256:
        raise ValidationError('Computation model name cannot exceed 256 characters')
    if not COMPUTATION_MODEL_NAME_DESCRIPTION_PATTERN.match(computation_model_name):
        raise ValidationError(
            'Computation model name must match pattern: ^[a-zA-Z0-9 _\\-#$*!@]+$'
        )


def validate_computation_model_description(computation_model_description: str) -> None:
    """Validate computation model description constraints."""
    if not computation_model_description:
        raise ValidationError('Computation model description cannot be empty')
    if len(computation_model_description) > 2048:
        raise ValidationError('Computation model description cannot exceed 2048 characters')
    if not COMPUTATION_MODEL_NAME_DESCRIPTION_PATTERN.match(computation_model_description):
        raise ValidationError(
            'Computation model description must match pattern: ^[a-zA-Z0-9 _\\-#$*!@]+$'
        )


def validate_asset_name(asset_name: str) -> None:
    """Validate asset name format."""
    if not asset_name:
        raise ValidationError('Asset name cannot be empty')
    if len(asset_name) > 256:
        raise ValidationError('Asset name cannot exceed 256 characters')
    # Check for injection attempts
    validate_string_for_injection(asset_name, 'Asset name')
    # Asset names have specific character restrictions
    if not re.match(r'^[a-zA-Z0-9_\-\s\.]+$', asset_name):
        raise ValidationError('Asset name contains invalid characters')


def validate_property_alias(property_alias: str) -> None:
    """Validate property alias format."""
    if not property_alias:
        raise ValidationError('Property alias cannot be empty')
    if len(property_alias) > 2048:
        raise ValidationError('Property alias cannot exceed 2048 characters')
    # Property aliases must start with '/'
    if not property_alias.startswith('/'):
        raise ValidationError("Property alias must start with '/'")
    # Validate alias path format
    if not re.match(r'^/[a-zA-Z0-9_\-/]+$', property_alias):
        raise ValidationError('Property alias contains invalid characters')


def validate_region(region: str) -> None:
    """Validate AWS region format."""
    if not region:
        raise ValidationError('Region cannot be empty')
    # AWS region format validation
    if not re.match(r'^[a-z0-9-]+$', region):
        raise ValidationError('Invalid AWS region format')
    # Common AWS regions (not exhaustive, but covers most cases)
    valid_regions = [
        'us-east-1',
        'us-east-2',
        'us-west-1',
        'us-west-2',
        'eu-west-1',
        'eu-west-2',
        'eu-west-3',
        'eu-central-1',
        'ap-southeast-1',
        'ap-southeast-2',
        'ap-northeast-1',
        'ap-northeast-2',
        'ap-south-1',
        'ca-central-1',
        'sa-east-1',
    ]
    if region not in valid_regions:
        # Don't fail for unknown regions, just warn
        pass


def validate_max_results(max_results: int, min_val: int = 1, max_val: int = 250) -> None:
    """Validate max results parameter."""
    if max_results < min_val:
        raise ValidationError(f'Max results must be at least {min_val}')
    if max_results > max_val:
        raise ValidationError(f'Max results cannot exceed {max_val}')


def validate_timestamp(timestamp: Union[int, str, datetime]) -> None:
    """Validate timestamp format."""
    if isinstance(timestamp, str):
        try:
            # Try to parse ISO format
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError('Invalid timestamp format. Use ISO 8601 format.')
    elif isinstance(timestamp, int):
        # Unix timestamp validation
        if timestamp < 0:
            raise ValidationError('Timestamp cannot be negative')
        if timestamp > 2147483647:  # Year 2038 problem
            raise ValidationError('Timestamp too large')


def validate_data_type(data_type: str) -> None:
    """Validate IoT SiteWise data type."""
    valid_types = ['STRING', 'INTEGER', 'DOUBLE', 'BOOLEAN', 'STRUCT']
    if data_type not in valid_types:
        raise ValidationError(f'Invalid data type. Must be one of: {", ".join(valid_types)}')


def validate_quality(quality: str) -> None:
    """Validate data quality indicator."""
    valid_qualities = ['GOOD', 'BAD', 'UNCERTAIN']
    if quality not in valid_qualities:
        raise ValidationError(f'Invalid quality. Must be one of: {", ".join(valid_qualities)}')


def validate_aggregate_types(aggregate_types: List[str]) -> None:
    """Validate aggregate types."""
    valid_types = [
        'AVERAGE',
        'COUNT',
        'MAXIMUM',
        'MINIMUM',
        'SUM',
        'STANDARD_DEVIATION',
    ]
    for agg_type in aggregate_types:
        if agg_type not in valid_types:
            raise ValidationError(
                f'Invalid aggregate type: {agg_type}. Must be one of: {", ".join(valid_types)}'
            )


def validate_time_ordering(time_ordering: str) -> None:
    """Validate time ordering parameter."""
    valid_orderings = ['ASCENDING', 'DESCENDING']
    if time_ordering not in valid_orderings:
        raise ValidationError(
            f'Invalid time ordering. Must be one of: {", ".join(valid_orderings)}'
        )


def validate_asset_model_properties(properties: List[Dict[str, Any]]) -> None:
    """Validate asset model properties structure."""
    if len(properties) > 200:
        raise ValidationError('Cannot have more than 200 properties per asset model')

    for prop in properties:
        if 'name' not in prop:
            raise ValidationError('Property must have a name')
        if 'dataType' not in prop:
            raise ValidationError('Property must have a dataType')
        if 'type' not in prop:
            raise ValidationError('Property must have a type')

        # Validate property name
        prop_name = prop['name']
        if not prop_name or len(prop_name) > 256:
            raise ValidationError('Property name must be 1-256 characters')

        # Check for injection attempts in property name
        validate_string_for_injection(prop_name, 'Property name')

        # Validate data type
        validate_data_type(prop['dataType'])

        # Validate property type structure
        prop_type = prop['type']
        valid_prop_types = ['measurement', 'attribute', 'transform', 'metric']
        if not any(pt in prop_type for pt in valid_prop_types):
            raise ValidationError(
                f'Property type must contain one of: {", ".join(valid_prop_types)}'
            )


def validate_batch_entries(entries: List[Dict[str, Any]], max_entries: int = 10) -> None:
    """Validate batch operation entries."""
    if not entries:
        raise ValidationError('Batch entries cannot be empty')
    if len(entries) > max_entries:
        raise ValidationError(
            f'Cannot process more than {max_entries} entries in a single \
                batch'
        )

    for i, entry in enumerate(entries):
        if 'entryId' not in entry:
            raise ValidationError(f"Entry {i} missing required 'entryId'")

        entry_id = entry['entryId']
        if not entry_id or len(entry_id) > 64:
            raise ValidationError(f'Entry ID must be 1-64 characters: {entry_id}')


def validate_access_policy_permission(permission: str) -> None:
    """Validate access policy permission level."""
    valid_permissions = ['ADMINISTRATOR', 'VIEWER']
    if permission not in valid_permissions:
        raise ValidationError(
            f'Invalid permission level. Must be one of: {", ".join(valid_permissions)}'
        )


def validate_encryption_type(encryption_type: str) -> None:
    """Validate encryption type."""
    valid_types = ['SITEWISE_DEFAULT_ENCRYPTION', 'KMS_BASED_ENCRYPTION']
    if encryption_type not in valid_types:
        raise ValidationError(f'Invalid encryption type. Must be one of: {", ".join(valid_types)}')


def validate_storage_type(storage_type: str) -> None:
    """Validate storage type."""
    valid_types = ['SITEWISE_DEFAULT_STORAGE', 'MULTI_LAYER_STORAGE']
    if storage_type not in valid_types:
        raise ValidationError(f'Invalid storage type. Must be one of: {", ".join(valid_types)}')


def validate_gateway_platform(platform: Dict[str, Any]) -> None:
    """Validate gateway platform configuration."""
    if not platform:
        raise ValidationError('Gateway platform configuration cannot be empty')

    # Must have either greengrass or greengrassV2
    if 'greengrass' not in platform and 'greengrassV2' not in platform:
        raise ValidationError(
            "Gateway platform must specify either 'greengrass' or \
                'greengrassV2'"
        )

    # Validate Greengrass configuration
    if 'greengrass' in platform:
        gg_config = platform['greengrass']
        if 'groupArn' not in gg_config:
            raise ValidationError("Greengrass configuration must include 'groupArn'")

    if 'greengrassV2' in platform:
        gg2_config = platform['greengrassV2']
        if 'coreDeviceThingName' not in gg2_config:
            raise ValidationError(
                "Greengrass V2 configuration must include \
                    'coreDeviceThingName'"
            )


# Service quota constants (as of 2024)
class SiteWiseQuotas:
    """AWS IoT SiteWise service quotas and limits."""

    MAX_ASSETS_PER_ACCOUNT = 100000
    MAX_ASSET_MODELS_PER_ACCOUNT = 10000
    MAX_PROPERTIES_PER_ASSET_MODEL = 200
    MAX_HIERARCHIES_PER_ASSET_MODEL = 10
    MAX_COMPOSITE_MODELS_PER_ASSET_MODEL = 10

    MAX_BATCH_PUT_ENTRIES = 10
    MAX_BATCH_GET_ENTRIES = 16
    MAX_PROPERTY_VALUES_PER_ENTRY = 10

    MAX_GATEWAYS_PER_ACCOUNT = 1000
    MAX_TIME_SERIES_PER_ACCOUNT = 1000000

    # API rate limits (requests per second)
    CONTROL_PLANE_RPS = 10
    DATA_PLANE_RPS = 1000
    QUERY_RPS = 10


def validate_service_quotas(operation: str, current_count: int = 0) -> None:
    """Validate against service quotas where applicable."""
    quotas = {
        'create_asset': SiteWiseQuotas.MAX_ASSETS_PER_ACCOUNT,
        'create_asset_model': SiteWiseQuotas.MAX_ASSET_MODELS_PER_ACCOUNT,
        'create_gateway': SiteWiseQuotas.MAX_GATEWAYS_PER_ACCOUNT,
    }

    if operation in quotas and current_count >= quotas[operation]:
        raise ValidationError(f'Service quota exceeded for {operation}: {quotas[operation]}')


def validate_string_for_injection(text: str, field_name: str = 'input') -> None:
    """Validate string for potential injection attacks or dangerous patterns.

    Args:
        text: The string to validate
        field_name: Name of the field being validated for error messages

    Raises:
        ValidationError: If dangerous patterns are detected
    """
    if not text:
        return

    # Check for common prompt injection patterns
    prompt_injection_patterns = [
        # Direct instruction attempts
        r'(?i)(ignore|forget|disregard|skip|bypass)\s+(all\s+)?previous\s+(instructions?|rules?|commands?)',
        r'(?i)new\s+instructions?:',
        r'(?i)system\s+prompt:',
        r'(?i)\\u0000|\\x00',  # Null byte injection
        r'(?i)<\s*script\s*>',  # Script tags
        r'(?i)javascript:',  # JavaScript protocol
        r'(?i)on\w+\s*=',  # Event handlers
        # Common prompt manipulation attempts
        r'(?i)(act|pretend|imagine|roleplay)\s+(as|like|you\s+are)',
        r'(?i)you\s+are\s+now',
        r'(?i)from\s+now\s+on',
        r'(?i)new\s+role:',
        r'(?i)switch\s+to\s+\w+\s+mode',
        # Instruction boundary attempts
        r'(?i)###\s*(system|instruction|command)',
        r'(?i)---\s*(end|stop)\s+(of\s+)?(instructions?|rules?)',
        r'(?i)\[\[.*\]\]',  # Common delimiter pattern
        r'(?i){{.*}}',  # Template injection pattern
    ]

    for pattern in prompt_injection_patterns:
        if re.search(pattern, text):
            raise ValidationError(
                f'{field_name} contains potentially dangerous patterns that could be used for injection attacks'
            )

    # Check for command injection patterns first (more specific)
    command_injection_patterns = [
        r'[;&|`](?=.*\b(rm|ls|cat|echo|bash|sh|cmd|powershell|del|dir)\b)',  # Command separators with shell commands
        r'\$\(',  # Command substitution
        r'(?i)\b(sh|bash|cmd|powershell)\s',  # Shell invocation with space
        r'(?i)(>|>>|<|<<)\s*[/\w]',  # Redirections to files
    ]

    for pattern in command_injection_patterns:
        if re.search(pattern, text):
            raise ValidationError(
                f'{field_name} contains patterns that could be used for command injection'
            )

    # Check for SQL injection patterns
    sql_injection_patterns = [
        r'(?i)(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b.*\b(from|into|where|table)\b)',
        r"(?i)('.*'.*=.*'|\".*\".*=.*\")|--.*$|\*/.*\*/|xp_\w+|sp_\w+",  # SQL injection with quotes and comparison
        r'(?i)(\bor\b\s*\d+\s*=\s*\d+|\band\b\s*\d+\s*=\s*\d+)',  # OR 1=1, AND 1=1
        r'(?i);.*\b(drop|delete|truncate|update|insert)\b',  # Semicolon followed by destructive SQL
        r"(?i)'.*;\s*(drop|delete|truncate|update|insert)\b",  # Quote followed by semicolon and SQL
    ]

    for pattern in sql_injection_patterns:
        if re.search(pattern, text):
            raise ValidationError(
                f'{field_name} contains patterns that could be used for SQL injection'
            )

    # Check for excessive special characters that might indicate obfuscation
    special_char_count = len(re.findall(r'[^\w\s\-._/]', text))
    if special_char_count > len(text) * 0.3:  # More than 30% special characters
        raise ValidationError(
            f'{field_name} contains excessive special characters which could indicate an obfuscation attempt'
        )

    # Check for excessive length (potential buffer overflow or DoS)
    if len(text) > 10000:
        raise ValidationError(
            f'{field_name} is excessively long (maximum 10000 characters allowed)'
        )

    # Check for control characters
    if re.search(r'[\x00-\x1F\x7F-\x9F]', text):
        raise ValidationError(f'{field_name} contains control characters which are not allowed')


def sanitize_string(text: Union[str, None], max_length: int = 1000) -> Union[str, None]:
    """Sanitize a string by escaping HTML entities and limiting length.

    Args:
        text: The string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if text is None or not text:
        return text

    # Escape HTML entities
    text = html.escape(text)

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]

    # Remove control characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

    return text


def validate_json_string(json_str: str, field_name: str = 'JSON') -> None:
    """Validate JSON strings for injection attempts.

    Args:
        json_str: JSON string to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If dangerous patterns are detected
    """
    if not json_str:
        return

    # Check for basic length limits
    if len(json_str) > 10000:
        raise ValidationError(
            f'{field_name} is excessively long (maximum 10000 characters allowed)'
        )

    # Check for control characters
    if re.search(r'[\x00-\x1F\x7F-\x9F]', json_str):
        raise ValidationError(f'{field_name} contains control characters which are not allowed')

    # Check for prompt injection patterns (more specific for JSON context)
    prompt_injection_patterns = [
        r'(?i)(ignore|forget|disregard|skip|bypass)\s+(all\s+)?previous\s+(instructions?|rules?|commands?)',
        r'(?i)new\s+instructions?:',
        r'(?i)system\s+prompt:',
        r'(?i)(act|pretend|imagine|roleplay)\s+(as|like|you\s+are)',
        r'(?i)you\s+are\s+now',
        r'(?i)from\s+now\s+on',
    ]

    for pattern in prompt_injection_patterns:
        if re.search(pattern, json_str):
            raise ValidationError(
                f'{field_name} contains potentially dangerous patterns that could be used for injection attacks'
            )

    # JSON-specific security checks
    if re.search(r'__proto__|constructor|prototype', json_str):
        raise ValidationError(
            f'{field_name} contains patterns that could be used for prototype pollution'
        )

    # Check for script injection in JSON values
    if re.search(r'(?i)<\s*script\s*>|javascript:|on\w+\s*=', json_str):
        raise ValidationError(
            f'{field_name} contains patterns that could be used for script injection'
        )


def validate_safe_identifier(identifier: str, field_name: str = 'identifier') -> None:
    """Validate that a string is a safe identifier (alphanumeric, underscore, hyphen only).

    Args:
        identifier: The identifier to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If the identifier contains unsafe characters
    """
    if not identifier:
        raise ValidationError(f'{field_name} cannot be empty')

    if not re.match(r'^[a-zA-Z0-9_-]+$', identifier):
        raise ValidationError(
            f'{field_name} must contain only alphanumeric characters, underscores, and hyphens'
        )

    if len(identifier) > 256:
        raise ValidationError(f'{field_name} cannot exceed 256 characters')


def check_storage_configuration_requirements(client, adaptive_ingestion: bool) -> None:
    """Check storage configuration requirements for bulk import jobs.

    For bulk import jobs with adaptive_ingestion=False, either:
    1. Multi-layer storage must be configured, OR
    2. Warm tier must be enabled for default storage

    Args:
        client: IoT SiteWise client
        adaptive_ingestion: Whether adaptive ingestion is enabled

    Raises:
        ValidationError: If storage configuration requirements are not met
    """
    if adaptive_ingestion:
        return

    try:
        response = client.describe_storage_configuration()
        storage_type = response.get('storageType', 'SITEWISE_DEFAULT_STORAGE')

        if storage_type == 'SITEWISE_DEFAULT_STORAGE':
            # Check if warm tier is enabled for default storage
            warm_tier = response.get('warmTier')
            if not warm_tier or warm_tier.get('state') != 'ENABLED':
                raise ValidationError(
                    'For bulk import jobs with adaptive ingestion disabled, either multi-layer storage '
                    'must be configured or warm tier must be enabled. Current configuration has default '
                    'storage without warm tier enabled.'
                    'Ask the user if they can enable adaptive_ingestion if data is within 30 days or they wants to enable cold/warm tier'
                )

        elif storage_type == 'MULTI_LAYER_STORAGE':
            # Verify multi-layer storage is properly configured
            multilayer_storage = response.get('multiLayerStorage', {})
            customer_managed_s3_storage = multilayer_storage.get('customerManagedS3Storage', {})
            if not customer_managed_s3_storage:
                raise ValidationError(
                    'Multi-layer storage is configured but customer managed S3 storage is not properly set up.'
                )

        else:
            raise ValidationError(f'Unknown storage type: {storage_type}')

    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f'Failed to validate storage configuration: {str(e)}')
