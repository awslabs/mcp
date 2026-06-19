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
"""boto3 client factory for the dynamic instrumentation feature.

Loads the bundled private ``application-signals`` service model via a
scoped botocore data loader (no ``AWS_DATA_PATH`` env mutation), pins
the API version to ``2024-04-15``, and lazily caches the resulting
clients so MCP tools can reuse a single configured instance.
"""

import boto3
import botocore.session
import os
from .. import __version__
from botocore.config import Config
from loguru import logger
from pathlib import Path


AWS_DATA_PATH = Path(__file__).parent / 'aws_data'
APPLICATION_SIGNALS_API_VERSION = '2024-04-15'


def _resolve_region() -> str:
    """Resolve AWS region by deferring to the parent package's ``aws_clients``.

    Region resolution (``AWS_REGION`` env var > configured profile's region >
    ``us-east-1``) lives in one place — the parent ``aws_clients.AWS_REGION``.
    This module must use the *same* value: the snapshot tools query CloudWatch
    Logs through the parent package's ``logs_client``, so splitting region
    resolution between the two would route a profile-only caller's clients to
    different regions — instrumentations created in one region while snapshot
    queries run in another, surfacing as a breakpoint that shows ACTIVE but
    whose snapshot searches always come back empty.
    """
    from ..aws_clients import AWS_REGION

    return AWS_REGION


def _build_config() -> Config:
    mcp_source = os.environ.get('MCP_RUN_FROM')
    user_agent_suffix = f'/{mcp_source}' if mcp_source else ''
    return Config(
        user_agent_extra=f'awslabs.cloudwatch-applicationsignals-mcp-server/dynamic-instrumentation/{__version__}{user_agent_suffix}'
    )


def _build_session() -> boto3.Session:
    """Build a boto3 Session with the bundled private model loader prepended."""
    botocore_session = botocore.session.Session()
    botocore_session.get_component('data_loader').search_paths.insert(0, str(AWS_DATA_PATH))
    profile = os.environ.get('AWS_PROFILE')
    return boto3.Session(botocore_session=botocore_session, profile_name=profile)


_application_signals_client = None


def get_application_signals_client():
    """Return a lazily-built ``application-signals`` client pinned to the private model."""
    global _application_signals_client
    if _application_signals_client is not None:
        return _application_signals_client

    region = _resolve_region()

    session = _build_session()
    _application_signals_client = session.client(
        'application-signals',
        api_version=APPLICATION_SIGNALS_API_VERSION,
        region_name=region,
        config=_build_config(),
    )
    logger.debug(
        f'application-signals client initialized (region={region}, '
        f'api_version={APPLICATION_SIGNALS_API_VERSION})'
    )
    return _application_signals_client


def _reset_clients() -> None:
    """Drop the cached client so tests can re-initialize against a fresh stub."""
    global _application_signals_client
    _application_signals_client = None
