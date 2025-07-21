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

"""Constants for the AWS Secrets Manager MCP server."""

import os

# Default configuration values
DEFAULT_REGION = os.environ.get('AWS_REGION', 'us-east-1')
DEFAULT_MAX_RESULTS = 50
DEFAULT_TIMEOUT = 30  # seconds

# Environment variables
AWS_PROFILE = os.environ.get('AWS_PROFILE')
FASTMCP_LOG_LEVEL = os.environ.get('FASTMCP_LOG_LEVEL', 'WARNING')

# Secret value size limits (AWS Secrets Manager limits)
MAX_SECRET_SIZE = 65536  # 64KB
MAX_SECRET_NAME_LENGTH = 512
MAX_DESCRIPTION_LENGTH = 2048

# Rotation configuration
DEFAULT_ROTATION_DAYS = 30
MIN_ROTATION_DAYS = 1
MAX_ROTATION_DAYS = 365

# Pagination limits
MAX_LIST_RESULTS = 100
DEFAULT_LIST_RESULTS = 20

# Secret name patterns
SECRET_NAME_PATTERN = r'^[a-zA-Z0-9/_+=.@-]+$'

# Common secret types for validation and suggestions
COMMON_SECRET_TYPES = {
    'database': {
        'description': 'Database credentials with username and password',
        'required_keys': ['username', 'password'],
        'optional_keys': ['host', 'port', 'dbname', 'engine']
    },
    'api_key': {
        'description': 'API key for external service integration',
        'required_keys': ['api_key'],
        'optional_keys': ['api_secret', 'endpoint', 'service_name']
    },
    'oauth': {
        'description': 'OAuth credentials for authentication',
        'required_keys': ['client_id', 'client_secret'],
        'optional_keys': ['access_token', 'refresh_token', 'scope', 'token_url']
    },
    'certificate': {
        'description': 'SSL/TLS certificate and private key',
        'required_keys': ['certificate', 'private_key'],
        'optional_keys': ['certificate_chain', 'passphrase']
    },
    'generic': {
        'description': 'Generic secret with custom key-value pairs',
        'required_keys': [],
        'optional_keys': []
    }
}

# Error messages
ERROR_MESSAGES = {
    'secret_not_found': 'Secret not found: {}',
    'invalid_secret_name': 'Invalid secret name: {}. Must match pattern: {}',
    'secret_too_large': 'Secret value exceeds maximum size of {} bytes',
    'invalid_json': 'Secret value is not valid JSON: {}',
    'rotation_not_enabled': 'Automatic rotation is not enabled for secret: {}',
    'invalid_rotation_days': 'Rotation days must be between {} and {}',
    'permission_denied': 'Permission denied for operation on secret: {}',
    'kms_access_denied': 'KMS access denied for secret encryption/decryption: {}',
    'invalid_region': 'Invalid AWS region: {}',
    'no_credentials': 'No AWS credentials found. Please configure AWS credentials.',
}

# Success messages
SUCCESS_MESSAGES = {
    'secret_created': 'Secret created successfully: {}',
    'secret_updated': 'Secret updated successfully: {}',
    'secret_deleted': 'Secret deleted successfully: {}',
    'secret_restored': 'Secret restored successfully: {}',
    'rotation_enabled': 'Automatic rotation enabled for secret: {}',
    'rotation_disabled': 'Automatic rotation disabled for secret: {}',
    'rotation_triggered': 'Manual rotation triggered for secret: {}',
}

# Documentation content for AI instructions
SECRETS_MANAGER_INSTRUCTIONS = """
# AWS Secrets Manager MCP Server

This MCP server provides comprehensive AWS Secrets Manager functionality for secure secret lifecycle management.

## Available Tools

### create-secret
Create a new secret with optional automatic rotation configuration.

### get-secret-value
Retrieve the current value of a secret, with optional version specification.

### update-secret
Update an existing secret's value, description, or KMS key.

### delete-secret
Schedule a secret for deletion with configurable recovery window.

### restore-secret
Restore a secret that was scheduled for deletion.

### list-secrets
List all secrets with optional filtering by name prefix or tags.

### describe-secret
Get detailed metadata about a secret including rotation configuration.

### enable-rotation
Enable automatic rotation for a secret with Lambda function.

### disable-rotation
Disable automatic rotation for a secret.

### rotate-secret
Manually trigger rotation for a secret.

### get-random-password
Generate a cryptographically secure random password.

### tag-resource
Add or update tags on a secret.

### untag-resource
Remove tags from a secret.

### get-resource-policy
Retrieve the resource-based policy for a secret.

### put-resource-policy
Set or update the resource-based policy for a secret.

### delete-resource-policy
Remove the resource-based policy from a secret.

## Best Practices

1. **Secret Naming**: Use descriptive names with forward slashes for organization (e.g., 'prod/database/mysql')
2. **JSON Structure**: Store structured secrets as JSON for easy parsing and updates
3. **Rotation**: Enable automatic rotation for database credentials and API keys
4. **Tagging**: Use consistent tagging for cost allocation and access control
5. **KMS Keys**: Use customer-managed KMS keys for additional security control
6. **Least Privilege**: Apply resource policies to restrict access to secrets

## Security Considerations

- All secret values are encrypted at rest using AWS KMS
- Secret values are encrypted in transit using TLS
- Access is controlled through IAM policies and resource policies
- Audit trail is maintained through AWS CloudTrail
- Automatic rotation reduces exposure window for compromised credentials
"""
