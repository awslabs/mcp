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

"""Shared constants for the RDS Control Plane MCP Server."""

# Version
MCP_SERVER_VERSION = '0.1.0'

# Success messages
SUCCESS_STARTED = '{} has been started successfully.'
SUCCESS_STOPPED = '{} has been stopped successfully.'
SUCCESS_REBOOTED = '{} has been rebooted successfully.'
SUCCESS_CREATED = '{} has been created successfully.'
SUCCESS_MODIFIED = '{} has been modified successfully.'
SUCCESS_DELETED = '{} has been deleted successfully.'

# Engine port mapping
ENGINE_PORT_MAP = {
    'aurora': 3306,
    'aurora-mysql': 3306,
    'aurora-postgresql': 5432,
    'mysql': 3306,
    'postgres': 5432,
    'mariadb': 3306,
    'oracle': 1521,
    'sqlserver': 1433,
}
