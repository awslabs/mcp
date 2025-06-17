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
