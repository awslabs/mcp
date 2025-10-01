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

from .command_metadata import CommandMetadata
from typing import Any, Dict, List, Set, Tuple


# Commands that write binary/blob outputs to local files
BINARY_OUTPUT_OPERATIONS: Set[Tuple[str, str]] = {
    ('s3api', 'get-object'),
    ('s3api', 'select-object-content'),
    ('lambda', 'invoke'),
    ('apigateway', 'get-export'),
    ('glacier', 'get-job-output'),
    ('appconfig', 'get-configuration'),
    ('bedrock-runtime', 'invoke-model'),
    ('iotwireless', 'get-position-estimate'),
    ('kms', 'generate-data-key'),
    ('secretsmanager', 'get-secret-value'),
    ('acm', 'export-certificate'),
}

# S3 operations that can download to local files
S3_DOWNLOAD_OPERATIONS: Set[str] = {'cp', 'sync', 'mv'}

# Parameters that are known to be file paths for specific operations
FILE_PATH_PARAMETERS: Dict[Tuple[str, str], Set[str]] = {
    ('s3', 'cp'): {'--paths'},
    ('s3', 'sync'): {'--paths'},
    ('s3', 'mv'): {'--paths'},
    ('cloudformation', 'package'): {'--output-template-file'},
}

# Global parameters that can specify output files
GLOBAL_FILE_PARAMETERS: Set[str] = {
    '--outfile',
    '--cli-input-json',
    '--cli-input-yaml',
}


def get_file_parameters_for_operation(service: str, operation: str) -> Set[str]:
    """Get file parameters for a specific operation."""
    params = set()

    # Add operation-specific parameters
    key = (service, operation)
    if key in FILE_PATH_PARAMETERS:
        params.update(FILE_PATH_PARAMETERS[key])

    # Add global parameters
    params.update(GLOBAL_FILE_PARAMETERS)

    return params


def is_binary_output_operation(command_metadata: CommandMetadata) -> bool:
    """Check if operation produces binary output that requires local file."""
    return (
        command_metadata.service_sdk_name,
        command_metadata.operation_sdk_name,
    ) in BINARY_OUTPUT_OPERATIONS


def is_s3_download_operation(command_metadata: CommandMetadata) -> bool:
    """Check if operation is S3 download that can write local files."""
    return (
        command_metadata.service_sdk_name == 's3'
        and command_metadata.operation_sdk_name in S3_DOWNLOAD_OPERATIONS
    )


def extract_file_paths_from_parameters(
    command_metadata: CommandMetadata, parameters: Dict[str, Any]
) -> List[str]:
    """Extract all potential file paths from command parameters."""
    file_paths = []

    # Get known file parameters for this operation
    file_params = get_file_parameters_for_operation(
        command_metadata.service_sdk_name, command_metadata.operation_sdk_name
    )

    # Check specific file parameters
    for param_name, param_value in parameters.items():
        if param_name in file_params:
            if isinstance(param_value, str) and not _is_remote_path(param_value):
                file_paths.append(param_value)
            elif isinstance(param_value, list):
                file_paths.extend(
                    [
                        item
                        for item in param_value
                        if isinstance(item, str) and not _is_remote_path(item)
                    ]
                )

    # For S3 operations, check --paths parameter for local files
    if command_metadata.service_sdk_name == 's3' and '--paths' in parameters:
        paths = parameters['--paths']
        if isinstance(paths, list):
            for path in paths:
                if isinstance(path, str) and not _is_remote_path(path):
                    file_paths.append(path)

    # For binary output operations, check both parameter names and values for file paths
    if is_binary_output_operation(command_metadata):
        for param_value in parameters.values():
            if (
                isinstance(param_value, str)
                and not _is_remote_path(param_value)
                and _could_be_file_path(param_value)
            ):
                file_paths.append(param_value)

        for param_name in parameters.keys():
            if (
                isinstance(param_name, str)
                and not _is_remote_path(param_name)
                and _could_be_file_path(param_name)
            ):
                file_paths.append(param_name)

    return file_paths


def _is_remote_path(path: str) -> bool:
    """Check if path is remote (S3, HTTP, etc.)."""
    return path.startswith(('s3://', 'http://', 'https://', 'ftp://', 'arn:'))


def _could_be_file_path(value: str) -> bool:
    """Check if value could be a file path."""
    # Skip obvious non-file values
    if value == '-' or len(value) < 2:
        return False

    # Skip AWS resource identifiers (common patterns)
    if value.startswith(('i-', 'sg-', 'vpc-', 'subnet-', 'ami-', 'snap-', 'vol-')):
        return False

    # If it has path separators or extensions, likely a file
    if '/' in value or '\\' in value or '.' in value:
        return True

    return False
