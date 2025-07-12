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

# Ignoring the Semgrep finding because the minimum required Python version for AWS API MCP Server is 3.10
# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
import importlib.resources
import json
from ..common.models import (
    ActionType,
    ApiType,
    CommandClassification,
    UnknownClassification,
)
from collections import defaultdict
from functools import lru_cache


# Classification present in the underlying knowledge base
# It contains the plane of the operation (control plane vs data plane)
# as well as if the operation is read-only or a mutation.
CONTROL_PLANE_TYPE = 'ControlPlane'
DATA_PLANE_TYPE = 'DataPlane'
READ_ONLY_ACTION_TYPE = 'ReadOnly'
MUTATING_ACTION_TYPE = 'Mutating'

METADATA_FILE = 'data/api_metadata.json'

# Remove global initialization
_service_knowledge_base = None


@lru_cache(maxsize=1)
def _get_service_knowledge_base():
    """Return the cached service knowledge base, loading it if necessary."""
    global _service_knowledge_base
    if _service_knowledge_base is None:
        _service_knowledge_base = _build_service_metadata()
    return _service_knowledge_base


def classify_operation(service: str, operation: str) -> CommandClassification:
    """Classify a given service operation.

    The classification is done by the type of action (mutation, read-only, etc.)
    and type of API (management/data).
    """
    operations = _get_service_knowledge_base().get(service)
    if not operations:
        return UnknownClassification
    return operations.get(operation) or UnknownClassification


def _build_service_metadata():
    """Build the service metadata dictionary from the API metadata file."""
    services: dict[str, dict[str, CommandClassification]] = defaultdict(dict)

    with (
        importlib.resources.files('awslabs.aws_api_mcp_server.core')
        .joinpath(METADATA_FILE)
        .open() as stream
    ):
        data = json.load(stream)

    for service, operations in data.items():
        for operation in operations:
            operation_type = data.get(service).get(operation).get('type')
            operation_plane = data.get(service).get(operation).get('plane')
            services[service][operation] = generate_classification(operation_plane, operation_type)

    return services


def generate_classification(operation_plane, operation_type):
    """Generate a CommandClassification for the given operation plane and type."""
    if operation_plane == CONTROL_PLANE_TYPE:
        api_type = ApiType.MANAGEMENT
    elif operation_plane == DATA_PLANE_TYPE:
        api_type = ApiType.DATA
    else:
        api_type = ApiType.UNKNOWN

    if operation_type == READ_ONLY_ACTION_TYPE:
        action_types = [ActionType.READ_ONLY]
    elif operation_type == MUTATING_ACTION_TYPE:
        action_types = [ActionType.MUTATING]
    else:
        action_types = [ActionType.UNKNOWN]

    return CommandClassification(action_types=action_types, api_type=api_type)
