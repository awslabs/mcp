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
"""Constants for the Amazon Keyspaces MCP Server."""

# Server information
SERVER_NAME = 'keyspaces-mcp'
SERVER_VERSION = '0.1.0'

# Logging configuration
DEFAULT_LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Database connection constants
CASSANDRA_DEFAULT_PORT = 9042
KEYSPACES_DEFAULT_PORT = 9142

# Connection timeouts in seconds. Note that these have different types (int and
# float) in the Cassandra driver itself.
CONNECTION_TIMEOUT = 10
CONTROL_CONNECTION_TIMEOUT = 10.0

# Protocol version for Cassandra driver
PROTOCOL_VERSION = 4

# Certificate paths
CERT_FILENAME = 'sf-class2-root.crt'
CERT_DIRECTORY = 'certs'

# Query validation
UNSAFE_OPERATIONS = [
    'insert ',
    'update ',
    'delete ',
    'drop ',
    'truncate ',
    'create ',
    'alter ',
]

# Query display limits
MAX_DISPLAY_ROWS = 20
