"""Constants for the Finch MCP server.

This module defines constants used throughout the Finch MCP server.
"""

# Server name
SERVER_NAME = 'finch_mcp_server'

# Log file name
LOG_FILE = 'finch_server.log'

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

# AWS region pattern
REGION_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9-_]*$'

# ECR repository pattern
ECR_REFERENCE_PATTERN = r'(\d{12})\.dkr[-.]ecr(\-fips)?\.([a-zA-Z0-9][a-zA-Z0-9-_]*)\.(on\.aws|amazonaws\.com(\.cn)?|sc2s\.sgov\.gov|c2s\.ic\.gov|cloud\.adc-e\.uk|csp\.hci\.ic\.gov)'

# Configuration file paths
CONFIG_JSON_PATH = '~/.finch/config.json'
FINCH_YAML_PATH = '~/.finch/finch.yaml'
