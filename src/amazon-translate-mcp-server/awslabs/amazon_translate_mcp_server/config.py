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

"""Configuration management for Amazon Translate MCP Server.

This module handles environment variable configuration, security settings,
and server configuration with validation and defaults.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class ServerConfig:
    """Main server configuration."""

    # AWS Configuration
    aws_profile: Optional[str] = None
    aws_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # Server Configuration
    log_level: str = 'INFO'
    max_text_length: int = 10000
    batch_timeout: int = 3600

    # Feature Flags
    enable_audit_logging: bool = True
    enable_translation_cache: bool = True

    # Cache Configuration
    cache_ttl: int = 3600

    # File Handling
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_extensions: Set[str] = field(default_factory=lambda: {'.csv', '.tmx', '.txt'})

    # Security Patterns
    blocked_patterns: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.log_level not in ['DEBUG', 'INFO', 'WARN', 'ERROR']:
            raise ValueError(f'Invalid log_level: {self.log_level}')

        if self.max_text_length <= 0:
            raise ValueError('max_text_length must be positive')

        if self.batch_timeout <= 0:
            raise ValueError('batch_timeout must be positive')

        if self.cache_ttl < 0:
            raise ValueError('cache_ttl cannot be negative')

        if self.max_file_size <= 0:
            raise ValueError('max_file_size must be positive')


def load_config_from_env() -> ServerConfig:
    """Load configuration from environment variables."""

    # Helper function to parse boolean environment variables
    def parse_bool(value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    # Helper function to parse integer environment variables
    def parse_int(value: Optional[str], default: int) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logging.warning(f"Invalid integer value '{value}', using default {default}")
            return default

    # Helper function to parse set of strings
    def parse_set(value: Optional[str], default: Set[str]) -> Set[str]:
        if value is None:
            return default
        return {ext.strip() for ext in value.split(',') if ext.strip()}

    # Helper function to parse list of strings
    def parse_list(value: Optional[str], default: List[str]) -> List[str]:
        if value is None:
            return default
        return [item.strip() for item in value.split(',') if item.strip()]

    return ServerConfig(
        # AWS Configuration
        aws_profile=os.getenv('AWS_PROFILE'),
        aws_region=os.getenv('AWS_REGION', os.getenv('AWS_DEFAULT_REGION')),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        # Server Configuration
        log_level=os.getenv('FASTMCP_LOG_LEVEL', 'INFO').upper(),
        max_text_length=parse_int(os.getenv('TRANSLATE_MAX_TEXT_LENGTH'), 10000),
        batch_timeout=parse_int(os.getenv('TRANSLATE_BATCH_TIMEOUT'), 3600),
        # Feature Flags
        enable_audit_logging=parse_bool(os.getenv('ENABLE_AUDIT_LOGGING'), True),
        enable_translation_cache=parse_bool(os.getenv('ENABLE_TRANSLATION_CACHE'), True),
        # Cache Configuration
        cache_ttl=parse_int(os.getenv('TRANSLATE_CACHE_TTL'), 3600),
        # File Handling
        max_file_size=parse_int(os.getenv('TRANSLATE_MAX_FILE_SIZE'), 10 * 1024 * 1024),
        allowed_file_extensions=parse_set(
            os.getenv('TRANSLATE_ALLOWED_EXTENSIONS'), {'.csv', '.tmx', '.txt'}
        ),
        # Security Patterns
        blocked_patterns=parse_list(os.getenv('TRANSLATE_BLOCKED_PATTERNS'), []),
    )


def setup_logging(config: ServerConfig):
    """Set up logging configuration based on server config."""
    # Map log levels
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARN': logging.WARNING,
        'ERROR': logging.ERROR,
    }

    log_level = level_map.get(config.log_level, logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Set specific logger levels
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # Security audit logger should always be INFO or higher
    audit_logger = logging.getLogger('audit')
    if config.enable_audit_logging:
        audit_logger.setLevel(logging.INFO)
    else:
        audit_logger.setLevel(logging.CRITICAL)  # Effectively disable

    logger = logging.getLogger(__name__)
    logger.info(f'Logging configured with level: {config.log_level}')
    logger.info(f'Security features - Audit: {config.enable_audit_logging}')


def validate_aws_config(config: ServerConfig) -> bool:
    """Validate AWS configuration."""
    from .security_validators import ALLOWED_AWS_REGIONS, validate_aws_region

    # Check if we have explicit credentials
    has_explicit_creds = config.aws_access_key_id and config.aws_secret_access_key

    # Check if we have profile configuration
    has_profile = config.aws_profile is not None

    # Check if we have environment variables
    has_env_creds = os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')

    # Check if we have IAM role (this will be validated at runtime)
    # For now, we assume it's available if no other credentials are found

    if not (has_explicit_creds or has_profile or has_env_creds):
        logging.warning(
            'No explicit AWS credentials found. Relying on IAM roles or instance metadata.'
        )

    # Validate region with security whitelist
    if not config.aws_region:
        config.aws_region = 'us-east-1'  # Default region
        logging.info(f'No AWS region specified, using default: {config.aws_region}')

    try:
        config.aws_region = validate_aws_region(config.aws_region)
        logging.info(f'AWS region validated: {config.aws_region}')
    except Exception as e:
        logging.error(f'AWS region validation failed: {e}')
        logging.info(f'Allowed regions: {", ".join(sorted(ALLOWED_AWS_REGIONS))}')
        raise

    return True


def validate_startup_configuration() -> ServerConfig:
    """Comprehensive configuration validation for server startup.

    Returns:
        ServerConfig: Validated configuration

    Raises:
        ValueError: If configuration is invalid
        RuntimeError: If AWS services are not accessible

    """
    # Import AWS modules at function level
    import boto3
    from botocore.exceptions import (
        ClientError,
        NoCredentialsError,
        PartialCredentialsError,
    )

    logger = logging.getLogger(__name__)
    logger.info('Starting configuration validation...')

    try:
        # Load configuration
        config = load_config_from_env()
        logger.info('Configuration loaded from environment')

        # Validate AWS configuration
        validate_aws_config(config)
        logger.info('AWS configuration validated')

        # Test AWS connectivity
        try:
            # Create a session with the configured credentials
            session_kwargs = {}
            if config.aws_profile:
                session_kwargs['profile_name'] = config.aws_profile
            if config.aws_region:
                session_kwargs['region_name'] = config.aws_region

            session = boto3.Session(**session_kwargs)

            # Test Amazon Translate connectivity
            translate_client = session.client('translate')

            # Try a lightweight operation to validate credentials and permissions
            try:
                response = translate_client.list_languages()
                logger.info(
                    f'AWS Translate connectivity verified. '
                    f'Supported languages: {len(response.get("Languages", []))}'
                )
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code in ['AccessDenied', 'UnauthorizedOperation']:
                    raise RuntimeError(
                        f'AWS Translate access denied. Please check IAM permissions: {e}'
                    )
                elif error_code == 'InvalidRegion':
                    raise ValueError(
                        f"Invalid AWS region '{config.aws_region}'. "
                        f'Amazon Translate may not be available in this region.'
                    )
                else:
                    logger.warning(f'AWS Translate connectivity check failed: {e}')

            # Test S3 connectivity (needed for batch operations)
            try:
                s3_client = session.client('s3')
                s3_client.list_buckets()
                logger.info('AWS S3 connectivity verified')
            except ClientError as e:
                logger.warning(f'S3 connectivity check failed: {e}')
                logger.warning('Batch translation features may not work properly')

        except (NoCredentialsError, PartialCredentialsError) as e:
            raise RuntimeError(f'AWS credentials not found or incomplete: {e}')
        except Exception as e:
            logger.warning(f'AWS connectivity check failed: {e}')
            logger.warning('Server will start but AWS operations may fail')

        # Log security configuration
        logger.info('Security configuration: Basic security features enabled')

        # Validate file handling configuration
        if config.max_file_size > 100 * 1024 * 1024:  # 100MB
            logger.warning(f'Large max file size configured: {config.max_file_size} bytes')

        # Validate cache configuration
        if config.enable_translation_cache and config.cache_ttl <= 0:
            raise ValueError('Cache TTL must be positive when caching is enabled')

        # Validate blocked patterns (if any)
        if config.blocked_patterns:
            import re

            for pattern in config.blocked_patterns:
                try:
                    re.compile(pattern)
                except re.error as e:
                    raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
            logger.info(f'Validated {len(config.blocked_patterns)} blocked patterns')

        logger.info('Configuration validation completed successfully')
        return config

    except Exception as e:
        logger.error(f'Configuration validation failed: {e}')
        raise


def print_configuration_summary(config: ServerConfig):
    """Print a summary of the current configuration."""
    print('\n' + '=' * 60)
    print('Amazon Translate MCP Server Configuration Summary')
    print('=' * 60)

    print(f'AWS Region: {config.aws_region}')
    print(f'AWS Profile: {config.aws_profile or "Default"}')
    print(f'Log Level: {config.log_level}')

    print('\nFeature Flags:')
    print(f'  Translation Cache: {"Enabled" if config.enable_translation_cache else "Disabled"}')
    print(f'  Audit Logging: {"Enabled" if config.enable_audit_logging else "Disabled"}')

    print('\nLimits:')
    print(f'  Max Text Length: {config.max_text_length:,} characters')
    print(
        f'  Max File Size: {config.max_file_size:,} bytes ({config.max_file_size / (1024 * 1024):.1f} MB)'
    )
    print(f'  Batch Timeout: {config.batch_timeout} seconds')
    print(f'  Cache TTL: {config.cache_ttl} seconds')

    print(f'\nFile Extensions: {", ".join(sorted(config.allowed_file_extensions))}')

    if config.blocked_patterns:
        print(f'Blocked Patterns: {len(config.blocked_patterns)} configured')

    print('=' * 60 + '\n')


# Global configuration instance
_config: Optional[ServerConfig] = None


def get_config() -> ServerConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config_from_env()
        validate_aws_config(_config)
        setup_logging(_config)
    return _config


def set_config(config: ServerConfig):
    """Set the global configuration instance (mainly for testing)."""
    global _config
    _config = config
    setup_logging(config)


def reset_config():
    """Reset the global configuration (mainly for testing)."""
    global _config
    _config = None
