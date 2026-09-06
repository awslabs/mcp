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

"""Shared runtime state and Application Signals detection for ServiceEvents tools.

The ServiceEvents tools and the server entry point share a small amount of
module-level state that is established at startup (whether Application Signals
is available, and a service -> environment cache). Keeping it here, behind
accessor functions, gives a single source of truth that both ``server.py`` and
the tool handlers read through.
"""

import logging
from datetime import datetime, timedelta, timezone


logger = logging.getLogger(__name__)

# Cloud-related resource attribute keys for output filtering
CLOUD_ATTR_KEYS = {
    'cloud.provider',
    'cloud.platform',
    'cloud.region',
    'cloud.account.id',
    'cloud.availability_zone',
}

# Module-level flag for Application Signals availability
_appsignals_enabled = False

# Service name -> environment cache (populated from AppSignals list_services at startup)
_service_env_cache = {}


def is_appsignals_enabled() -> bool:
    """Return whether Application Signals was detected at startup."""
    return _appsignals_enabled


def set_appsignals_enabled(value: bool) -> None:
    """Set the Application Signals availability flag."""
    global _appsignals_enabled
    _appsignals_enabled = value


def check_appsignals_enabled(region: str) -> bool:
    """Check if Application Signals is enabled by verifying log group exists."""
    try:
        import boto3

        logs = boto3.client('logs', region_name=region)
        resp = logs.describe_log_groups(
            logGroupNamePrefix='/aws/application-signals/data', limit=1
        )
        return any(
            lg.get('logGroupName') == '/aws/application-signals/data'
            for lg in resp.get('logGroups', [])
        )
    except Exception:
        return False


def initialize_env_cache() -> int:
    """Initialize the service-environment cache from AppSignals list_monitored_services.

    Called during startup when AppSignals is enabled. Populates a module-level
    cache so that Environment can be auto-populated on API calls.

    Returns:
        Number of service-environment pairs cached.
    """
    global _service_env_cache
    try:
        from ..aws_clients import get_applicationsignals_client

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        response = get_applicationsignals_client().list_services(
            StartTime=start_time, EndTime=end_time, MaxResults=100
        )
        services = response.get('ServiceSummaries', [])
        new_cache = {}
        for svc in services:
            key_attrs = svc.get('KeyAttributes', {})
            name = key_attrs.get('Name')
            env = key_attrs.get('Environment')
            if name and env:
                new_cache[name] = env
        _service_env_cache = new_cache
        logger.info(f'Service-environment cache initialized: {len(new_cache)} pairs')
        return len(new_cache)
    except Exception as e:
        logger.warning(f'Failed to initialize service-environment cache: {e}')
        return 0
