"""Constants for the Finch MCP server.

This module defines constants used throughout the Finch MCP server.
"""

# Server name
SERVER_NAME = 'finch_image'

# Log file name
LOG_FILE = 'finch_image.log'

# VM states
VM_STATE_RUNNING = 'running'
VM_STATE_STOPPED = 'stopped'
VM_STATE_NONEXISTENT = 'nonexistent'
VM_STATE_UNKNOWN = 'unknown'

# Operation status
STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'
STATUS_WARNING = 'warning'
STATUS_INFO = 'info'

# ECR repository pattern
ECR_REPOSITORY_PATTERN = (
    r'^(\d{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/([a-zA-Z0-9._/-]+)(?::([a-zA-Z0-9._-]+))?$'
)
ECR_REFERENCE_PATTERN = r'(\d{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com'

# Configuration file paths
CONFIG_JSON_PATH = '~/.finch/config.json'
FINCH_YAML_PATH = '~/.finch/finch.yaml'
