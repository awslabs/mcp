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

import awscli.clidriver
import re
from ..common.config import get_user_agent_extra
from ..common.file_system_controls import get_file_validated
from ..common.models import Credentials
from awscli.paramfile import URIArgumentHandler
from botocore.model import OperationModel
from collections.abc import Set
from loguru import logger
from lxml import html
from typing import Any, NamedTuple


def _deny_remote_prefix(prefix, _uri):
    raise ValueError(f'{prefix} prefix is not allowed')


RESTRICTED_URI_HANDLER = URIArgumentHandler(
    prefixes={
        'file://': (get_file_validated, {'mode': 'r'}),
        'fileb://': (get_file_validated, {'mode': 'rb'}),
        'http://': (_deny_remote_prefix, {}),
        'https://': (_deny_remote_prefix, {}),
    }
)


PaginationConfig = dict[str, int]


class ConfigResult(NamedTuple):
    """Result of configuration extraction for AWS operations."""

    parameters: dict[str, Any]
    pagination_config: PaginationConfig


filter_query = re.compile(r'^\s+([-a-z0-9_.]+|tag:<key>)\s+')


def get_awscli_driver(credentials: Credentials | None = None) -> awscli.clidriver.CLIDriver:
    """Create a AWS CLI driver to execute aws commands."""
    driver = awscli.clidriver.create_clidriver()
    session = driver.session
    session.register('load-cli-arg', RESTRICTED_URI_HANDLER)

    # append user agent to session for aws cli customizations
    session.user_agent_extra += ' ' + get_user_agent_extra() + ' cli-customizations'
    if credentials:
        session.set_credentials(
            access_key=credentials.access_key_id,
            secret_key=credentials.secret_access_key,
            token=credentials.session_token,
        )
    return driver


class OperationFilters:
    """Represents filters for an AWS operation."""

    def __init__(self, filter_keys: Set[str], filter_set: Set[str], allows_tag_key: bool):
        """Initialize OperationFilters with filter keys, filter set, and tag key allowance."""
        self._filter_keys = frozenset(filter_keys)
        self._filter_set = frozenset(filter_set)
        self._allows_tag_key = allows_tag_key

    @property
    def filter_keys(self) -> frozenset[str]:
        """Return the set of filter keys."""
        return self._filter_keys

    def allows_filter(self, filter_name: str) -> bool:
        """Check if the given filter name is allowed."""
        if not self._filter_set:
            # Bypassing validation if filter names are not known
            return True
        return (
            filter_name in self._filter_set
            or self._allows_tag_key
            and filter_name.startswith('tag:')
        )


ALLOWED_SSM_LIST_NODES_FILTERS = {
    'AgentType',
    'AgentVersion',
    'ComputerName',
    'InstanceId',
    'InstanceStatus',
    'IpAddress',
    'ManagedStatus',
    'PlatformName',
    'PlatformType',
    'PlatformVersion',
    'ResourceType',
    'OrganizationalUnitId',
    'OrganizationalUnitPath',
    'Region',
    'AccountId',
}

# The documentation for ssm:ListDocuments doesn't list the filters
# Using the list from https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_DocumentKeyValuesFilter.html
# and an undocumented key SearchKeyword
ALLOWED_SSM_LIST_DOCUMENTS_FILTERS = {
    'DocumentType',
    'Name',
    'Owner',
    'PlatformTypes',
    'SearchKeyword',
}

CUSTOM_OPERATION_FILTERS = {
    ('ssm', 'ListDocuments'): OperationFilters(
        filter_keys={'Key', 'Values'},
        filter_set=ALLOWED_SSM_LIST_DOCUMENTS_FILTERS,
        allows_tag_key=True,
    ),
    ('ssm', 'ListNodes'): OperationFilters(
        filter_keys={'Key', 'Values', 'Type'},
        filter_set=ALLOWED_SSM_LIST_NODES_FILTERS,
        allows_tag_key=True,
    ),
    ('ssm', 'ListNodesSummary'): OperationFilters(
        filter_keys={'Key', 'Values', 'Type'},
        filter_set=ALLOWED_SSM_LIST_NODES_FILTERS,
        allows_tag_key=True,
    ),
}


def get_operation_filters(operation: OperationModel) -> OperationFilters:
    """Given an operation, find all its filters."""
    filters = operation.input_shape._shape_model.get('members', {}).get('Filters')  # type: ignore[attr-defined]

    if not filters or 'documentation' not in filters:
        return OperationFilters(filter_keys=set(), filter_set=set(), allows_tag_key=False)

    if (operation.service_model.service_name, operation.name) in CUSTOM_OPERATION_FILTERS:
        return CUSTOM_OPERATION_FILTERS[
            (str(operation.service_model.service_name), str(operation.name))
        ]

    filter_keys = set()
    filters_shape = operation.service_model.shape_for(filters['shape'])
    # Single (non-list) filter validation isn't implemented right now
    if filters_shape.type_name == 'list':
        filters_shape_member = filters_shape.member
        if filters_shape_member.type_name == 'structure':
            filter_keys = set(filters_shape_member.members)  # type: ignore[attr-defined]

    # Filters are not exposed as their own field in the boto3 model, but they are
    # part of the documentation.
    filter_documentation = filters['documentation']
    filter_set = set()
    allows_tag_key = False
    for list_item in html.fromstring(filter_documentation).xpath('ul/li'):
        matched = filter_query.search(list_item.text_content())
        if matched is not None:
            filter_name = matched.group(1)
            if filter_name == 'tag:<key>':
                allows_tag_key = True
            else:
                filter_set.add(filter_name)
    if not filter_set:
        logger.warning(
            f'Empty filter set for {operation.service_model.service_name}:{operation.name}. '
            'Filter validation is likely to fail'
        )
    return OperationFilters(filter_keys, filter_set, allows_tag_key)


def extract_pagination_config(
    parameters: dict[str, Any],
    max_results: int | None = None,
) -> ConfigResult:
    """Extract pagination configuration from parameters."""
    pagination_config = parameters.pop('PaginationConfig', {})

    if max_results is None:
        return ConfigResult(parameters, pagination_config)

    max_items = pagination_config.pop('MaxItems', None)

    if max_items is not None:
        max_items = min(int(max_items), max_results)
    else:
        max_items = max_results

    pagination_config['MaxItems'] = max_items
    return ConfigResult(parameters, pagination_config)
