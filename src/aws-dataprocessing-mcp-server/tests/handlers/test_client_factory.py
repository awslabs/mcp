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

"""Tests for caller-provided AWS client factories."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_data_catalog_handler import (
    AthenaDataCatalogHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_query_handler import (
    AthenaQueryHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_workgroup_handler import (
    AthenaWorkGroupHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.commons.common_resource_handler import (
    CommonResourceHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_cluster_handler import (
    EMREc2ClusterHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_instance_handler import (
    EMREc2InstanceHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_steps_handler import (
    EMREc2StepsHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_application_handler import (
    EMRServerlessApplicationHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_job_run_handler import (
    EMRServerlessJobRunHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler import CrawlerHandler
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler import (
    GlueDataCatalogHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_commons_handler import (
    GlueCommonsHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_etl_handler import GlueEtlJobsHandler
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.interactive_sessions_handler import (
    GlueInteractiveSessionsHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.worklows_handler import (
    GlueWorkflowAndTriggerHandler,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from unittest.mock import MagicMock, call, patch


@pytest.mark.parametrize(
    ('handler_type', 'service_name', 'client_attribute'),
    [
        (AthenaQueryHandler, 'athena', 'athena_client'),
        (AthenaDataCatalogHandler, 'athena', 'athena_client'),
        (AthenaWorkGroupHandler, 'athena', 'athena_client'),
        (CrawlerHandler, 'glue', 'glue_client'),
        (GlueCommonsHandler, 'glue', 'glue_client'),
        (GlueEtlJobsHandler, 'glue', 'glue_client'),
        (GlueInteractiveSessionsHandler, 'glue', 'glue_client'),
        (GlueWorkflowAndTriggerHandler, 'glue', 'glue_client'),
        (EMREc2ClusterHandler, 'emr', 'emr_client'),
        (EMREc2InstanceHandler, 'emr', 'emr_client'),
        (EMREc2StepsHandler, 'emr', 'emr_client'),
        (EMRServerlessApplicationHandler, 'emr-serverless', 'emr_serverless_client'),
        (EMRServerlessJobRunHandler, 'emr-serverless', 'emr_serverless_client'),
    ],
)
def test_handler_uses_supplied_client_factory(handler_type, service_name, client_attribute):
    """AWS-backed handlers request their service client from the supplied factory."""
    client = MagicMock()
    client_factory = MagicMock(return_value=client)

    handler = handler_type(MagicMock(), client_factory=client_factory)

    assert getattr(handler, client_attribute) is client
    assert handler._provided_client_factory is client_factory
    client_factory.assert_called_once_with(service_name)


@pytest.mark.asyncio
async def test_default_handler_identity_uses_ambient_cache(monkeypatch):
    """Default handler identity preserves the ambient account cache and aws partition."""
    glue_client = MagicMock()
    glue_client.get_crawler.return_value = {'Crawler': {'Parameters': {'mcp:managed': 'true'}}}
    monkeypatch.setattr(AwsHelper, '_aws_account_id', '111111111111')
    monkeypatch.setattr(AwsHelper, '_aws_partition', 'aws-us-gov')

    with (
        patch.object(AwsHelper, 'create_boto3_client', return_value=glue_client),
        patch.object(AwsHelper, 'get_or_default_aws_region', return_value='us-east-1'),
        patch.object(AwsHelper, 'is_resource_mcp_managed', return_value=True) as is_managed,
        patch('boto3.client') as ambient_boto3_client,
    ):
        handler = CrawlerHandler(MagicMock(), allow_write=True)
        result = await handler.manage_aws_glue_crawlers(
            MagicMock(), operation='delete-crawler', crawler_name='test-crawler'
        )

    assert result.is_error is False
    assert handler._provided_client_factory is None
    ambient_boto3_client.assert_not_called()
    is_managed.assert_called_once_with(
        glue_client,
        'arn:aws:glue:us-east-1:111111111111:crawler/test-crawler',
        {'mcp:managed': 'true'},
    )


@pytest.mark.parametrize(
    ('handler_type', 'method_name', 'operation_kwargs', 'resource_suffix'),
    [
        (
            CrawlerHandler,
            'manage_aws_glue_crawlers',
            {'operation': 'delete-crawler', 'crawler_name': 'test-crawler'},
            'crawler/test-crawler',
        ),
        (
            GlueEtlJobsHandler,
            'manage_aws_glue_jobs',
            {'operation': 'delete-job', 'job_name': 'test-job'},
            'job/test-job',
        ),
        (
            GlueInteractiveSessionsHandler,
            'manage_aws_glue_sessions',
            {'operation': 'delete-session', 'session_id': 'test-session'},
            'session/test-session',
        ),
        (
            GlueCommonsHandler,
            'manage_aws_glue_usage_profiles',
            {'operation': 'delete-profile', 'profile_name': 'test-profile'},
            'usageProfile/test-profile',
        ),
        (
            GlueWorkflowAndTriggerHandler,
            'manage_aws_glue_workflows',
            {'operation': 'delete-workflow', 'workflow_name': 'test-workflow'},
            'workflow/test-workflow',
        ),
        (
            GlueWorkflowAndTriggerHandler,
            'manage_aws_glue_triggers',
            {'operation': 'delete-trigger', 'trigger_name': 'test-trigger'},
            'trigger/test-trigger',
        ),
    ],
)
@pytest.mark.asyncio
async def test_injected_glue_handler_arns_use_factory_partition(
    monkeypatch, handler_type, method_name, operation_kwargs, resource_suffix
):
    """Injected Glue handler ARNs use factory account and partition identity."""
    glue_client = MagicMock()
    sts_client = MagicMock()
    sts_client.get_caller_identity.return_value = {
        'Account': '222222222222',
        'Arn': 'arn:aws-us-gov:sts::222222222222:assumed-role/test/session',
    }
    clients = {'glue': glue_client, 'sts': sts_client}
    client_factory = MagicMock(side_effect=lambda service_name: clients[service_name])
    monkeypatch.setattr(AwsHelper, '_aws_account_id', '111111111111')
    monkeypatch.setattr(AwsHelper, '_aws_partition', 'aws')

    with (
        patch.object(AwsHelper, 'get_or_default_aws_region', return_value='us-gov-west-1'),
        patch.object(AwsHelper, 'is_resource_mcp_managed', return_value=True) as is_managed,
        patch('boto3.client') as ambient_boto3_client,
    ):
        handler = handler_type(MagicMock(), allow_write=True, client_factory=client_factory)
        result = await getattr(handler, method_name)(MagicMock(), **operation_kwargs)

    assert result.is_error is False
    assert AwsHelper._aws_account_id == '111111111111'
    assert AwsHelper._aws_partition == 'aws'
    ambient_boto3_client.assert_not_called()
    assert client_factory.call_args_list == [call('glue'), call('sts'), call('sts')]
    assert is_managed.call_args.args[1] == (
        f'arn:aws-us-gov:glue:us-gov-west-1:222222222222:{resource_suffix}'
    )


def test_glue_data_catalog_passes_factory_to_each_manager():
    """The Glue Data Catalog wrapper preserves one Glue client creation per manager."""
    glue_client = MagicMock()
    client_factory = MagicMock(return_value=glue_client)

    handler = GlueDataCatalogHandler(MagicMock(), client_factory=client_factory)

    assert handler.data_catalog_database_manager.glue_client is glue_client
    assert handler.data_catalog_table_manager.glue_client is glue_client
    assert handler.data_catalog_manager.glue_client is glue_client
    assert client_factory.call_args_list == [call('glue'), call('glue'), call('glue')]


@pytest.mark.asyncio
async def test_common_resource_handler_uses_factory_for_lazy_service_clients():
    """Common resource analysis uses the supplied factory for all lazily created clients."""
    clients = {
        'iam': MagicMock(),
        's3': MagicMock(),
        'glue': MagicMock(),
        'athena': MagicMock(),
        'emr': MagicMock(),
    }
    clients['s3'].list_buckets.return_value = {'Buckets': []}
    client_factory = MagicMock(side_effect=lambda service_name: clients[service_name])
    handler = CommonResourceHandler(MagicMock(), client_factory=client_factory)

    result = await handler.analyze_s3_usage_for_data_processing(MagicMock())

    assert result.is_error is False
    assert client_factory.call_args_list == [
        call('iam'),
        call('s3'),
        call('glue'),
        call('athena'),
        call('emr'),
    ]
