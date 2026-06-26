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

"""Tests for the ServiceEvents shared runtime state module.

Module-level globals (``_appsignals_enabled``, ``_service_env_cache``) are reset
between tests by the autouse fixture in conftest.py, so these tests can mutate
them freely.
"""

from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import state
from unittest.mock import MagicMock, patch


# ============================================================================
# AppSignals enabled flag accessors
# ============================================================================


class TestAppSignalsFlag:
    """Tests for the Application Signals availability flag accessors."""

    def test_set_and_get(self):
        """Round-trip the flag through the setter and getter."""
        state.set_appsignals_enabled(True)
        assert state.is_appsignals_enabled() is True

        state.set_appsignals_enabled(False)
        assert state.is_appsignals_enabled() is False


# ============================================================================
# check_appsignals_enabled — boto3 logs probe
# ============================================================================


class TestCheckAppSignalsEnabled:
    """Tests for the log-group probe that detects Application Signals."""

    def test_returns_true_when_log_group_present(self):
        """Return True when the AppSignals data log group exists."""
        logs = MagicMock()
        logs.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/application-signals/data'}]
        }
        fake_boto3 = MagicMock()
        fake_boto3.client.return_value = logs
        with patch.dict('sys.modules', {'boto3': fake_boto3}):
            assert state.check_appsignals_enabled('us-east-1') is True
        fake_boto3.client.assert_called_once_with('logs', region_name='us-east-1')

    def test_returns_false_when_log_group_absent(self):
        """Return False when no matching log group is returned."""
        logs = MagicMock()
        logs.describe_log_groups.return_value = {'logGroups': [{'logGroupName': '/aws/other'}]}
        fake_boto3 = MagicMock()
        fake_boto3.client.return_value = logs
        with patch.dict('sys.modules', {'boto3': fake_boto3}):
            assert state.check_appsignals_enabled('us-west-2') is False

    def test_returns_false_on_empty_response(self):
        """Return False when describe_log_groups returns no groups."""
        logs = MagicMock()
        logs.describe_log_groups.return_value = {}
        fake_boto3 = MagicMock()
        fake_boto3.client.return_value = logs
        with patch.dict('sys.modules', {'boto3': fake_boto3}):
            assert state.check_appsignals_enabled('us-east-1') is False

    def test_returns_false_on_exception(self):
        """Swallow any boto3 error and return False."""
        logs = MagicMock()
        logs.describe_log_groups.side_effect = RuntimeError('boom')
        fake_boto3 = MagicMock()
        fake_boto3.client.return_value = logs
        with patch.dict('sys.modules', {'boto3': fake_boto3}):
            assert state.check_appsignals_enabled('us-east-1') is False


# ============================================================================
# initialize_env_cache — service -> environment cache population
# ============================================================================


class TestInitializeEnvCache:
    """Tests for populating the service-environment cache from list_services."""

    def _patch_client(self, response):
        """Patch get_applicationsignals_client to return a client with list_services -> response."""
        client = MagicMock()
        client.list_services.return_value = response
        return patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients'
            '.get_applicationsignals_client',
            return_value=client,
        )

    def test_populates_cache_with_name_and_env(self):
        """Cache service->env pairs that carry both Name and Environment."""
        response = {
            'ServiceSummaries': [
                {'KeyAttributes': {'Name': 'svc-a', 'Environment': 'prod'}},
                {'KeyAttributes': {'Name': 'svc-b', 'Environment': 'staging'}},
            ]
        }
        with self._patch_client(response):
            count = state.initialize_env_cache()
        assert count == 2
        assert state._service_env_cache == {'svc-a': 'prod', 'svc-b': 'staging'}

    def test_skips_entries_missing_name_or_env(self):
        """Skip summaries that lack a Name or an Environment."""
        response = {
            'ServiceSummaries': [
                {'KeyAttributes': {'Name': 'svc-a', 'Environment': 'prod'}},
                {'KeyAttributes': {'Name': 'no-env'}},
                {'KeyAttributes': {'Environment': 'no-name'}},
                {'KeyAttributes': {}},
            ]
        }
        with self._patch_client(response):
            count = state.initialize_env_cache()
        assert count == 1
        assert state._service_env_cache == {'svc-a': 'prod'}

    def test_empty_summaries(self):
        """Return zero and leave an empty cache when no services are returned."""
        with self._patch_client({}):
            count = state.initialize_env_cache()
        assert count == 0
        assert state._service_env_cache == {}

    def test_exception_returns_zero(self):
        """Swallow errors from list_services and return zero."""
        client = MagicMock()
        client.list_services.side_effect = RuntimeError('api down')
        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients'
            '.get_applicationsignals_client',
            return_value=client,
        ):
            count = state.initialize_env_cache()
        assert count == 0
