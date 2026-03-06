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

import os
import re
from .command_metadata import CommandMetadata
from .config import (
    FILE_ACCESS_MODE,
    FILE_ACCESS_MODE_KEY,
    WORKING_DIRECTORY,
    FileAccessMode,
)
from .errors import FilePathValidationError, LocalFileAccessDisabledError
from awscli.arguments import CLIArgument
from awscli.paramfile import get_file
from pathlib import Path
from typing import Any, Dict, List


# Regex pattern for file:// or fileb:// prefixes used in blob arguments
FILE_BLOB_PREFIX_PATTERN = r'^fileb?://'

# Custom operation arguments that accept file paths
# This includes empty entries for all allowed customizations that don't accept file paths
# to make sure that no opearation is overlooked
CUSTOM_FILE_PATH_ARGUMENTS = {
    's3': {
        'ls': [],
        'website': [],
        'sync': ['--paths'],
        'cp': ['--paths'],
        'mv': ['--paths'],
        'rm': [],
        'mb': [],
        'rb': [],
        'presign': [],
    },
    'cloudformation': {
        'package': ['--template-file', '--output-template-file'],
        'deploy': ['--template-file'],
    },
    'cloudfront': {'sign': ['--private-key']},
    'cloudtrail': {
        'validate-logs': [],
    },
    'codeartifact': {'login': []},
    'codecommit': {'credential-helper': []},
    'datapipeline': {'list-runs': [], 'create-default-roles': []},
    'dlm': {'create-default-role': []},
    'ecr': {'get-login': [], 'get-login-password': []},
    'ecr-public': {'get-login-password': []},
    'ecs': {'deploy': ['--task-definition', '--codedeploy-appspec']},
    'eks': {'update-kubeconfig': ['--kubeconfig'], 'get-token': []},
    'emr': {
        'add-instance-groups': [],
        'describe-cluster': [],
        'terminate-clusters': [],
        'modify-cluster-attributes': [],
        'install-applications': [],
        'create-cluster': [],
        'add-steps': [],
        'restore-from-hbase-backup': [],
        'create-hbase-backup': [],
        'schedule-hbase-backup': [],
        'disable-hbase-backups': [],
        'create-default-roles': [],
    },
    'emr-containers': {'update-role-trust-policy': []},
    'gamelift': {'upload-build': ['--build-root'], 'get-game-session-log': ['--save-as']},
    'rds': {'generate-db-auth-token': []},
    'servicecatalog': {'generate': ['--file-path']},
    'deploy': {'push': ['--source'], 'register': [], 'deregister': []},
    'configservice': {'subscribe': [], 'get-status': []},
}

# Custom operation arguments that accept file paths with the file:// or fileb:// prefixes
CUSTOM_BLOB_ARGUMENTS = {
    'emr': {
        'create-cluster': [
            '--configurations',
            '--bootstrap-actions',
            '--ec2-attributes',
            '--instance-groups',
            '--instance-fleets',
            '--kerberos-attributes',
            '--managed-scaling-policy',
            '--placement-group-configs',
            '--auto-termination-policy',
            '--additional-info',
            '--emrfs',
        ],
        'add-steps': [
            '--steps',
        ],
    },
}


def is_streaming_blob_argument(cli_argument: CLIArgument) -> bool:
    """Streaming blob arguments accept only file paths."""
    argument_model = cli_argument.argument_model
    return argument_model.type_name == 'blob' and argument_model.serialization.get('streaming')


def get_file_validated(prefix, path, mode):
    """Validate that a URI path (i.e. file://<path>) is within the allowed working directory."""
    file_path = os.path.expandvars(os.path.expanduser(path[len(prefix) :]))
    validate_file_path(file_path)

    return get_file(prefix, path, mode)


def validate_file_path(file_path: str) -> str:
    """Validate that a file path is within the allowed working directory.

    Args:
        file_path: The file path to validate

    Returns:
        The validated absolute path

    Raises:
        LocalFileAccessDisabledError: If local file access is disabled
        FilePathValidationError: If the path is outside the working directory and unrestricted access is not allowed
    """
    if FILE_ACCESS_MODE == FileAccessMode.NO_ACCESS:
        # Reject local file paths
        raise LocalFileAccessDisabledError(file_path)

    if FILE_ACCESS_MODE == FileAccessMode.UNRESTRICTED:
        return file_path

    # Reject unexpanded tilde paths (e.g., ~invalid_user/path)
    if file_path.startswith('~') and not os.path.isabs(os.path.expanduser(file_path)):
        raise FilePathValidationError(
            file_path, 'contains unexpanded tilde (~) which is not allowed'
        )

    # Relative paths resolve against WORKING_DIRECTORY via os.chdir() in server initialization
    absolute_path = os.path.abspath(file_path)
    working_directory = os.path.abspath(WORKING_DIRECTORY)

    # Check if the path is within the working directory
    try:
        Path(absolute_path).resolve().relative_to(Path(working_directory).resolve())
    except ValueError:
        reason = (
            f"is outside the allowed working directory '{WORKING_DIRECTORY}'. "
            f'Set {FILE_ACCESS_MODE_KEY}=unrestricted to allow unrestricted file access.'
        )
        raise FilePathValidationError(file_path, reason)

    return absolute_path


def extract_file_paths_from_parameters(
    command_metadata: CommandMetadata, parameters: Dict[str, Any]
) -> List[str]:
    """Extract all potential file paths from custom command parameters.

    NOTE: this function only handles AWS CLI customizations (e.g. aws s3 cp, aws cloudformation package).
    Regular service operations are handled separately.

    This function extracts file paths from both regular file path arguments and blob arguments
    (with file:// or fileb:// prefixes). For blob arguments, the prefixes are removed.

    Args:
        command_metadata: Metadata about the command being executed
        parameters: Dictionary of command parameters

    Returns:
        List of file paths (with file:// and fileb:// prefixes removed)
    """
    file_paths = []
    service = command_metadata.service_sdk_name
    operation = command_metadata.operation_sdk_name

    # Get file path arguments for this service/operation
    file_path_args = set()
    if service in CUSTOM_FILE_PATH_ARGUMENTS and operation in CUSTOM_FILE_PATH_ARGUMENTS[service]:
        file_path_args = set(CUSTOM_FILE_PATH_ARGUMENTS[service][operation])

    # Get blob arguments for this service/operation
    blob_args = set()
    if service in CUSTOM_BLOB_ARGUMENTS and operation in CUSTOM_BLOB_ARGUMENTS[service]:
        blob_args = set(CUSTOM_BLOB_ARGUMENTS[service][operation])

    # Extract file paths from parameters
    for param_name, param_value in parameters.items():
        # Check if this is a file path argument
        if param_name in file_path_args:
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

        # Check if this is a blob argument (may have file:// or fileb:// prefix)
        elif param_name in blob_args:
            if isinstance(param_value, str):
                # Remove file:// or fileb:// prefix if present
                if re.match(FILE_BLOB_PREFIX_PATTERN, param_value):
                    cleaned_path = re.sub(FILE_BLOB_PREFIX_PATTERN, '', param_value)
                    file_paths.append(cleaned_path)
            elif isinstance(param_value, list):
                file_paths.extend(
                    [
                        re.sub(FILE_BLOB_PREFIX_PATTERN, '', item)
                        for item in param_value
                        if isinstance(item, str) and re.match(FILE_BLOB_PREFIX_PATTERN, item)
                    ]
                )

    return file_paths


def _is_remote_path(path: str) -> bool:
    """Check if path is remote (S3, HTTP, etc.)."""
    return path.startswith(('s3://', 'http://', 'https://', 'ftp://', 'arn:'))
