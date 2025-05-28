"""Configuration utilities for the OpenAPI MCP Server."""

import os


# Metrics configuration
METRICS_MAX_HISTORY = int(os.environ.get('METRICS_MAX_HISTORY', '100'))
USE_PROMETHEUS = os.environ.get('ENABLE_PROMETHEUS', 'false').lower() == 'true'
PROMETHEUS_PORT = int(os.environ.get('PROMETHEUS_PORT', '9090'))

# Operation prompts configuration
ENABLE_OPERATION_PROMPTS = os.environ.get('ENABLE_OPERATION_PROMPTS', 'true').lower() == 'true'

# HTTP client configuration
HTTP_MAX_CONNECTIONS = int(os.environ.get('HTTP_MAX_CONNECTIONS', '100'))
HTTP_MAX_KEEPALIVE = int(os.environ.get('HTTP_MAX_KEEPALIVE', '20'))
USE_TENACITY = os.environ.get('USE_TENACITY', 'true').lower() == 'true'

# Cache configuration
CACHE_MAXSIZE = int(os.environ.get('CACHE_MAXSIZE', '1000'))
CACHE_TTL = int(os.environ.get('CACHE_TTL', '3600'))  # 1 hour default
USE_CACHETOOLS = os.environ.get('USE_CACHETOOLS', 'true').lower() == 'true'
