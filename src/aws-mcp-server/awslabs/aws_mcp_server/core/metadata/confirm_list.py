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

import argparse
import importlib_resources
import json
import sys
from awslabs.aws_mcp_server.core.common.models import ActionType, ApiType
from awslabs.aws_mcp_server.core.parser.classifier import generate_classification
from loguru import logger


METADATA_FILE = 'data/api_metadata.json'
CONFIRM_LIST_FILE = 'data/confirm_list.json'

DEFAULT_CONFIRM_LIST_OUT = 'confirm_list.json'

CONFIRM_LIST_VERSION = '1.0'
ACTION_TYPE_TO_CONFIRM = frozenset([ActionType.MUTATING, ActionType.UNKNOWN])


class ConfirmList(dict):
    """Dictionary-like object to store operations that require explicit user confirmation."""

    def __init__(self, *args, **kwargs):
        """Initialize ConfirmList with optional metadata."""
        super().__init__(*args, **kwargs)
        self._metadata = self.get('metadata', {})
        self._version = self._metadata.get('version', None)

    @property
    def version(self):
        """Return the version of the confirm list."""
        return self._version

    def has(self, service, operation) -> bool:
        """Check if the given service and operation require confirmation.

        Args:
            service: The AWS service name.
            operation: The operation name.

        Returns:
            True if the operation requires confirmation, False otherwise.
        """
        logger.info(f'checking in confirm list : {service} - {operation}')
        return service in self and operation in self[service]


def get_confirm_list():
    """Load and return the ConfirmList from the metadata file."""
    try:
        with (
            importlib_resources.files('awslabs.aws_mcp_server.core')
            .joinpath(CONFIRM_LIST_FILE)
            .open() as stream
        ):
            data = json.load(stream)
        return ConfirmList(data)
    except Exception as e:
        logger.error(f'failed to load confirm list : {e}')

    return ConfirmList({})


def main(output_path=None):
    """Generate the confirm list and write it to the specified output path."""
    output_file = output_path if output_path else DEFAULT_CONFIRM_LIST_OUT

    with (
        importlib_resources.files('awslabs.aws_mcp_server.core')
        .joinpath(METADATA_FILE)
        .open() as stream
    ):
        data = json.load(stream)

    confirm_list = ConfirmList({'metadata': {'version': CONFIRM_LIST_VERSION}})
    for service, operations in data.items():
        confirm_list[service] = []
        for operation in operations:
            operation_type = operations.get(operation).get('type')
            operation_plane = operations.get(operation).get('plane')
            classification = generate_classification(operation_plane, operation_type)

            if (
                ACTION_TYPE_TO_CONFIRM.intersection(set(classification.action_types))
                or classification.api_type == ApiType.UNKNOWN
            ):
                confirm_list[service].append(operation)

        if not confirm_list[service]:
            confirm_list.pop(service, None)

    with open(output_file, 'w') as fp:
        json.dump(confirm_list, fp, indent=2, sort_keys=True)
        fp.write('\n')


if __name__ == '__main__':
    # Configure Loguru logging
    logger.remove()
    logger.add(sys.stderr)

    parser = argparse.ArgumentParser(description='Generate confirmation list for API operations')
    parser.add_argument(
        '--output', '-o', help='Output file path', default=DEFAULT_CONFIRM_LIST_OUT
    )
    args = parser.parse_args()
    main(args.output)
