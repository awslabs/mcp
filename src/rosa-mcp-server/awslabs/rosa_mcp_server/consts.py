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

"""Constants for the ROSA MCP Server."""

# Resource tags applied by the MCP server
MCP_MANAGED_TAG_KEY = 'rosa-mcp-server:managed'
MCP_MANAGED_TAG_VALUE = 'true'
MCP_CLUSTER_NAME_TAG_KEY = 'rosa-mcp-server:cluster-name'

# ROSA-specific constants
ROSA_CLI_VERSION = '1.2.0'  # Minimum required ROSA CLI version
DEFAULT_OPENSHIFT_VERSION = '4.14.0'
DEFAULT_MACHINE_TYPE = 'm5.xlarge'
DEFAULT_REPLICAS = 2

# ROSA cluster states
ROSA_CLUSTER_READY_STATE = 'ready'
ROSA_CLUSTER_ERROR_STATE = 'error'
ROSA_CLUSTER_INSTALLING_STATE = 'installing'
ROSA_CLUSTER_PENDING_STATE = 'pending'
ROSA_CLUSTER_DELETING_STATE = 'deleting'

# IAM role prefixes
ROSA_ACCOUNT_ROLE_PREFIX = 'ManagedOpenShift'
ROSA_OPERATOR_ROLE_PREFIX = 'openshift'

# Default timeouts (in seconds)
ROSA_CLUSTER_CREATE_TIMEOUT = 3600  # 1 hour
ROSA_CLUSTER_DELETE_TIMEOUT = 1800  # 30 minutes
ROSA_OPERATION_TIMEOUT = 300  # 5 minutes

# Machine pool defaults
DEFAULT_MACHINE_POOL_NAME = 'worker'
MIN_MACHINE_POOL_SIZE = 1
MAX_MACHINE_POOL_SIZE = 180

# Identity provider types
IDP_TYPES = ['github', 'gitlab', 'google', 'ldap', 'openid', 'htpasswd']

# OpenShift API versions
OPENSHIFT_API_VERSIONS = {
    'v1': 'Core API version 1',
    'apps/v1': 'Apps API version 1',
    'batch/v1': 'Batch API version 1',
    'networking.k8s.io/v1': 'Networking API version 1',
    'rbac.authorization.k8s.io/v1': 'RBAC API version 1',
    'autoscaling/v1': 'Autoscaling API version 1',
    'route.openshift.io/v1': 'OpenShift Route API version 1',
    'build.openshift.io/v1': 'OpenShift Build API version 1',
    'image.openshift.io/v1': 'OpenShift Image API version 1',
    'project.openshift.io/v1': 'OpenShift Project API version 1',
    'apps.openshift.io/v1': 'OpenShift Apps API version 1',
}