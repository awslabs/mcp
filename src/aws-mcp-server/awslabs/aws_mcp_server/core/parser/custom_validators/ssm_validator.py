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

from ...common.errors import (
    ParameterSchemaValidationError,
    ParameterValidationErrorRecord,
)
from collections.abc import Iterable
from re import finditer
from typing import Any


"""
Special filter validations for the aws ssm list-nodes and list-node-summary apis
"""

FILTERS_KEY = 'Filters'
WINDOWS_SERVER_PLATFORM_NAME = 'Windows Server'
WINDOWS_2022_PLATFORM_VERSION = '2022'
MAC_OS_PLATFORM_TYPE = 'MacOs'
MAC_OS_PLATFORM_NAME = 'macOs'
PLATFORM_TYPES = ['linux'.casefold(), 'windows'.casefold(), 'macos'.casefold()]  # Ignore case
PLATFORM_NAME_KEY = 'PlatformName'
PLATFORM_TYPE_KEY = 'PlatformType'
PLATFORM_VERSION_KEY = 'PlatformVersion'
SYNC_NAME_KEY = 'SyncName'
REGION_KEY = 'Region'
VALUES_KEY = 'Values'
TYPE_KEY = 'Type'
KEY_KEY = 'Key'
OPERATIONS_TO_VALIDATE = ['list-nodes', 'list-nodes-summary']


def _get_platform_name_and_platform_version(string: str) -> Iterable[tuple[str, str]]:
    regex_to_match_name_and_version = (
        r'(?P<platformName>[A-Za-z\s\d]*)\s+((?P<platformVersion>[\d.]+))?\s*$'
    )
    matches = finditer(regex_to_match_name_and_version, string)
    for match in matches:
        platform_name = match.group('platformName')
        platform_version = match.group('platformVersion')
        yield platform_name, platform_version


def _validate_platform_name_used_correctly(
    filters: dict[str, dict[str, str]],
) -> list[ParameterValidationErrorRecord]:
    errors = []
    """
    Heuristic:
    1. If PlatformName is in known PLATFORM_TYPES, then PlatformType should be used instead.
    2. If PlatformName has version number as suffix this should only be part of
    PlatformVersion and not of PlatformName
    """
    filter_name = filters.get(PLATFORM_NAME_KEY, {})
    filter_type = filter_name.get(TYPE_KEY, '')
    if not filter_type:
        return [
            ParameterValidationErrorRecord(
                FILTERS_KEY, f'Missing {TYPE_KEY} for key {PLATFORM_NAME_KEY}. '
            )
        ]
    for name in filter_name.get(VALUES_KEY, []):
        # If misclassified as PlatformName when should be PlatformType
        if name.casefold() in PLATFORM_TYPES:
            errors.append(
                ParameterValidationErrorRecord(
                    FILTERS_KEY,
                    f'Incorrect value {name} for key {PLATFORM_NAME_KEY}. '
                    f"Use instead Key={PLATFORM_TYPE_KEY},Values='{name}',Type={filter_type} ",
                )
            )

        # If PlatformName has version suffix,
        # we should split this into PlatformVersion and PlatformName
        if PLATFORM_VERSION_KEY not in filters:
            for platform_name, platform_version in _get_platform_name_and_platform_version(name):
                # Windows Server 2022 should be mapped to Windows Server 2022 Standard PlatformName
                if (
                    WINDOWS_SERVER_PLATFORM_NAME in platform_name
                    and platform_version == WINDOWS_2022_PLATFORM_VERSION
                ):
                    errors.append(
                        ParameterValidationErrorRecord(
                            FILTERS_KEY,
                            f'Incorrect value {name} for key {PLATFORM_NAME_KEY}. '
                            f'Use instead: '
                            f'Key={PLATFORM_NAME_KEY},'
                            f"Values='Microsoft Windows Server 2022 Standard',"
                            f'Type={filter_type} ',
                        )
                    )
                elif platform_name and platform_version:
                    errors.append(
                        ParameterValidationErrorRecord(
                            FILTERS_KEY,
                            f'Incorrect value {name} for key {PLATFORM_NAME_KEY}. '
                            f'Also version suffix {platform_version} should be part of '
                            f'{PLATFORM_VERSION_KEY}. '
                            f'Use instead:'
                            f"Key={PLATFORM_NAME_KEY},Values='{platform_name}',"
                            f'Type={filter_type} '
                            f"Key={PLATFORM_VERSION_KEY},Values='{platform_version}',Type={filter_type}",
                        )
                    )

    return errors


def _validate_platform_type_used_correctly(
    filters: dict[str, dict[str, str]],
) -> list[ParameterValidationErrorRecord]:
    """Heuristic.

    1. If PlatformType is not in PLATFORM_TYPES, then PlatformName should be used instead.
    2. If PlatformName should be used also check if PlatformVersion should be used.
    """
    errors = []
    platform_type = filters.get(PLATFORM_TYPE_KEY, {})
    platform_type_type = platform_type.get(TYPE_KEY, '')
    if not platform_type_type:
        return [
            ParameterValidationErrorRecord(
                FILTERS_KEY, f'Missing Type for key {PLATFORM_TYPE_KEY}. '
            )
        ]

    for value in platform_type.get(VALUES_KEY, []):
        if value.casefold() in PLATFORM_TYPES:
            continue
        names_and_versions = list(_get_platform_name_and_platform_version(value))
        if names_and_versions:
            for platform_name, platform_version in names_and_versions:
                # Handle case where entry incorrectly mapped as PlatformType
                # and the value also contain a version number
                errors.append(
                    ParameterValidationErrorRecord(
                        FILTERS_KEY,
                        f'Incorrect value {value} for key {PLATFORM_TYPE_KEY} '
                        f'Accepted values: {PLATFORM_TYPES} also '
                        f'version suffix should be part of {PLATFORM_VERSION_KEY}.'
                        f'Use instead: '
                        f"Key={PLATFORM_NAME_KEY},Values='{platform_name}',"
                        f'Type={platform_type_type} '
                        f"Key={PLATFORM_VERSION_KEY},Values='{platform_version}',"
                        f'Type={platform_type_type}',
                    )
                )
        else:
            # Handle case when entry incorrectly mapped as PlatformType without version suffix
            errors.append(
                ParameterValidationErrorRecord(
                    FILTERS_KEY,
                    f'Incorrect value {value} for key {PLATFORM_TYPE_KEY}, '
                    f'accepted values are: {PLATFORM_TYPES}. '
                    f'Use instead: '
                    f"Key={PLATFORM_NAME_KEY},Values='{value}',Type={platform_type_type}",
                )
            )
    return errors


def _validate_filters(filters: list[dict[str, Any]]):
    errors = []
    # filters i.e.
    # [
    #   {'Key': 'PlatformName', 'Type': 'Equal', 'Values': ['Microsoft Windows Server 2008']},
    #   {'Key': 'Region', 'Type': 'Equal', 'Values': ['eu-central-1']}
    # ]

    indexed_filters = {filter_set[KEY_KEY]: filter_set for filter_set in filters}

    for filter_set in filters:
        key = filter_set[KEY_KEY]
        if key == PLATFORM_NAME_KEY:
            new_errors = _validate_platform_name_used_correctly(indexed_filters)
            errors.extend(new_errors)
        elif key == PLATFORM_TYPE_KEY:
            new_errors = _validate_platform_type_used_correctly(indexed_filters)
            errors.extend(new_errors)
    return errors


def _validate_syncname(parameters, filters):
    errors = []
    if SYNC_NAME_KEY not in parameters and ('Aggregators' in parameters or filters):
        should_include_sync_name = False
        if filters:
            for filter_set in filters:
                key = filter_set[KEY_KEY]
                if key == 'Region' or key == 'AccountId' or 'Organization' in key:
                    should_include_sync_name = True
        if REGION_KEY in parameters:
            for filter_set in parameters['Aggregators']:
                if filter_set['AttributeName'] == 'Region':
                    should_include_sync_name = True
        if should_include_sync_name:
            errors.append(
                ParameterValidationErrorRecord(
                    SYNC_NAME_KEY,
                    'the parameter and value --sync-name AWS-QuickSetup-ManagedNode is '
                    'required for this command.',
                )
            )
    return errors


def perform_ssm_validations(operation: str, parameters: dict[str, Any]):
    """Perform custom SSM parameter validations for the given operation and parameters."""
    if operation not in OPERATIONS_TO_VALIDATE:
        return
    errors = []
    filters = parameters.get(FILTERS_KEY)
    if filters:
        filter_errors = _validate_filters(filters)
        errors.extend(filter_errors)
    sync_name_errors = _validate_syncname(parameters, filters)
    errors.extend(sync_name_errors)

    if errors:
        raise ParameterSchemaValidationError(errors)
