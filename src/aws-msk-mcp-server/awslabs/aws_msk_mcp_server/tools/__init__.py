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

"""
MSK MCP Server Tools Package

This package contains all the tool modules for the MSK MCP Server.
"""

from awslabs.aws_msk_mcp_server import __version__

# Import register_module functions from each module
from .logs_and_telemetry.register_module import register_module as register_logs_and_telemetry
from .mutate_cluster.register_module import register_module as register_mutate_cluster
from .mutate_config.register_module import register_module as register_mutate_config
from .mutate_vpc.register_module import register_module as register_mutate_vpc
from .read_cluster.register_module import register_module as register_read_cluster
from .read_config.register_module import register_module as register_read_config
from .read_global.register_module import register_module as register_read_global
from .read_vpc.register_module import register_module as register_read_vpc
from .replicator.register_module import register_module as register_replicator
