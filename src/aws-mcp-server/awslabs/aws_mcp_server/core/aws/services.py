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
from botocore.exceptions import DataNotFoundError
from botocore.model import OperationModel, StringShape
from collections.abc import Set
from loguru import logger
from lxml import html
from typing import Any, NamedTuple


PaginationConfig = dict[str, int]


class ConfigResult(NamedTuple):
    """Result of configuration extraction for AWS operations."""

    parameters: dict[str, Any]
    pagination_config: PaginationConfig


# Explicit list of parameters that are not compatible with pagination
# (service, operation): parameters
PAGINATION_INCOMPATIBLE = {
    ('ec2', 'DescribeInstanceImageMetadata'): ('InstanceIds',),
    ('ec2', 'DescribeCarrierGateways'): ('CarrierGatewayIds',),
    ('ec2', 'DescribeClientVpnEndpoints'): ('ClientVpnEndpointIds',),
    ('ec2', 'DescribeCoipPools'): ('PoolIds',),
    ('ec2', 'DescribeDhcpOptions'): ('DhcpOptionsIds',),
    ('ec2', 'DescribeElasticGpus'): ('ElasticGpuIds',),
    ('ec2', 'DescribeImages'): ('ImageIds',),
    ('ec2', 'DescribeInstanceCreditSpecifications'): ('InstanceIds',),
    ('ec2', 'DescribeInstanceStatus'): ('InstanceIds',),
    ('ec2', 'DescribeInstanceTopology'): ('InstanceIds',),
    ('ec2', 'DescribeInstances'): ('InstanceIds',),
    ('ec2', 'DescribeInternetGateways'): ('InternetGatewayIds',),
    ('ec2', 'DescribeIpamPools'): ('IpamPoolIds',),
    ('ec2', 'DescribeIpamResourceDiscoveries'): ('IpamResourceDiscoveryIds',),
    ('ec2', 'DescribeIpamResourceDiscoveryAssociations'): ('IpamResourceDiscoveryAssociationIds',),
    ('ec2', 'DescribeIpamScopes'): ('IpamScopeIds',),
    ('ec2', 'DescribeIpams'): ('IpamIds',),
    ('ec2', 'DescribeNetworkAcls'): ('NetworkAclIds',),
    ('ec2', 'DescribeNetworkInterfaces'): ('NetworkInterfaceIds',),
    ('ec2', 'DescribeRouteTables'): ('RouteTableIds',),
    ('ec2', 'DescribeSecurityGroupRules'): ('SecurityGroupRuleIds',),
    ('ec2', 'DescribeSecurityGroups'): ('GroupIds', 'GroupNames'),
    ('ec2', 'DescribeSnapshots'): ('SnapshotIds',),
    ('ec2', 'DescribeSpotInstanceRequests'): ('SpotInstanceRequestIds',),
    ('ec2', 'DescribeSubnets'): ('SubnetIds',),
    ('ec2', 'DescribeVerifiedAccessEndpoints'): ('VerifiedAccessEndpointIds',),
    ('ec2', 'DescribeVerifiedAccessGroups'): ('VerifiedAccessGroupIds',),
    ('ec2', 'DescribeVerifiedAccessInstanceLoggingConfigurations'): ('VerifiedAccessInstanceIds',),
    ('ec2', 'DescribeVerifiedAccessInstances'): ('VerifiedAccessInstanceIds',),
    ('ec2', 'DescribeVerifiedAccessTrustProviders'): ('VerifiedAccessTrustProviderIds',),
    ('ec2', 'DescribeVolumeStatus'): ('VolumeIds',),
    ('ec2', 'DescribeVolumes'): ('VolumeIds',),
    ('ec2', 'DescribeVpcs'): ('VpcIds',),
    ('ec2', 'DescribeInstanceTypes'): ('InstanceTypes'),
    ('ec2', 'DescribeVpcPeeringConnections'): ('VpcPeeringConnectionIds'),
    ('elbv2', 'DescribeLoadBalancers'): ('Names',),
}


# Overrides for MaxResults min and max values
# Some services only enforce them server-side
def get_max_result_override(service_name: str, operation_name: str) -> dict[str, int] | None:
    """Return max result override for specific service and operation if applicable."""
    if service_name == 'rds' and operation_name.startswith('Describe'):
        return {
            'min': 20,
            'max': 100,
        }

    return None


PAGE_SIZE = 20
GET_METRIC_DATA_MAX_RESULTS_OVERRIDE = (
    3900  # Maximum number of datapoints to return, limited for better LLM processing
)

filter_query = re.compile(r'^\s+([-a-z0-9_.]+|tag:<key>)\s+')

driver = awscli.clidriver.create_clidriver()
session = driver.session


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


def find_operation_max_results_key(service_name: str, operation_name: str) -> str | None:
    """Find a given operation's max results key if the number of results can be bounded."""
    try:
        paginator = session.get_paginator_model(service_name)
    except DataNotFoundError:
        return None

    paginator_config = paginator._paginator_config
    op_config = paginator_config.get(operation_name)
    if not op_config:
        return None

    return op_config.get('limit_key')


def is_pagination_compatible(
    parameters: dict[str, Any],
    service_name: str,
    operation_name: str,
) -> bool:
    """Check if the operation is compatible with pagination."""
    incompatible_keys = PAGINATION_INCOMPATIBLE.get((service_name, operation_name))
    if incompatible_keys is not None and any(key in incompatible_keys for key in parameters):
        return False

    max_results_key = find_operation_max_results_key(
        service_name=service_name, operation_name=operation_name
    )
    if max_results_key is None:
        return False

    return True


def update_parameters_with_max_results(
    parameters: dict[str, Any],
    service_name: str,
    operation_name: str,
    max_results: str | int | None = None,
) -> dict[str, Any]:
    """Update parameters with max results for pagination."""
    if (
        is_pagination_compatible(parameters, service_name, operation_name)
        and max_results is not None
    ):
        max_results_key = find_operation_max_results_key(
            service_name=service_name, operation_name=operation_name
        )
        if max_results_key is not None:
            max_results_shape = (
                session.get_service_model(service_name)
                .operation_model(operation_name)
                .input_shape.members.get(max_results_key)  # type: ignore[attr-defined]
            )

            # Some operations accept strings for max_results
            if isinstance(max_results_shape, StringShape):
                max_results = str(max_results)

            parameters.update(**{max_results_key: max_results})

    return parameters


def extract_pagination_config(
    parameters: dict[str, Any],
    service_name: str,
    operation_name: str,
    max_results: int | None = None,
) -> ConfigResult:
    """Extract pagination configuration from parameters."""
    # Some APIs like the EC2 operations allow specifying extra pagination options like max-results
    cli_max_results = parameters.pop('MaxResults', None)
    if cli_max_results is not None and max_results is not None:
        max_results = min(int(cli_max_results), max_results)
    elif cli_max_results is not None:
        max_results = int(cli_max_results)

    pagination_config = parameters.pop('PaginationConfig', {})
    pagination_config_max_results = pagination_config.pop('MaxItems', None)

    if 'PageSize' not in pagination_config and is_pagination_compatible(
        parameters, service_name, operation_name
    ):
        pagination_config['PageSize'] = PAGE_SIZE

    max_results = pagination_config_max_results or max_results
    if max_results is None:
        # Unbounded call so nothing to do here
        return ConfigResult(parameters, pagination_config)

    max_results_key = find_operation_max_results_key(
        service_name=service_name, operation_name=operation_name
    )
    if max_results_key is None:
        # Return the parameters unmodified, this operation *might* not support pagination
        return ConfigResult(parameters, pagination_config)

    max_results_shape = (
        session.get_service_model(service_name)
        .operation_model(operation_name)
        .input_shape.members.get(max_results_key)  # type: ignore[attr-defined]
    )

    # Override MaxResults bounds with server side limits if available
    max_result_bounds = get_max_result_override(service_name, operation_name)
    if not max_result_bounds:
        max_result_bounds = max_results_shape.metadata  # type: ignore[attr-defined]

    # Apply custom limits
    max_results_value = int(max_results)

    if max_result_bounds:
        max_results_value = max(
            max_results_value, int(max_result_bounds.get('min', max_results_value))
        )
        max_results_value = min(
            max_results_value, int(max_result_bounds.get('max', max_results_value))
        )

    if limit := _get_max_results_limit(service_name, operation_name):
        max_results = min(max_results_value, limit)
    else:
        max_results = max_results_value

    pagination_config['MaxItems'] = max_results
    return ConfigResult(parameters, pagination_config)


endpoint_resolver = session._internal_components.get_component('endpoint_resolver')
partitions = endpoint_resolver._endpoint_data['partitions']


def check_service_has_default_region(service: str, region: str):
    """Check if the service has a default region configured."""
    for partition in partitions:
        endpoint_config = endpoint_resolver._endpoint_for_partition(
            partition, service, region, use_dualstack_endpoint=False, use_fips_endpoint=False
        )
        if not endpoint_config:
            continue

        credentials_scope = endpoint_config.get('credentialScope')
        if credentials_scope and credentials_scope['region'] != region:
            return True

    return False


def _get_max_results_limit(service_name: str, operation_name: str) -> int | None:
    if service_name == 'cloudwatch' and operation_name == 'GetMetricData':
        return GET_METRIC_DATA_MAX_RESULTS_OVERRIDE

    return None
