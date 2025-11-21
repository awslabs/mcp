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

"""Shared fixtures for integration tests using testcontainers."""

import pytest
from unittest.mock import patch


@pytest.fixture(scope='session')
def valkey_container():
    """Start a valkey-bundle container for the test session.

    Uses testcontainers RedisContainer with the valkey/valkey-bundle image,
    which includes FT.* search and JSON modules.
    """
    from testcontainers.redis import RedisContainer

    with RedisContainer(image='valkey/valkey-bundle:unstable') as container:
        yield container


@pytest.fixture()
def valkey_connection(valkey_container):
    """Patch get_client to return a GLIDE client connected to the testcontainer.

    Returns the mock client for direct use in tests.
    """
    from glide import GlideClient, GlideClientConfiguration, NodeAddress

    host = valkey_container.get_container_host_ip()
    port = int(valkey_container.get_exposed_port(6379))

    _client = None

    async def _get_client():
        nonlocal _client
        if _client is None:
            config = GlideClientConfiguration(
                addresses=[NodeAddress(host, port)],
                request_timeout=5000,
            )
            _client = await GlideClient.create(config)
        return _client

    with patch(
        'awslabs.valkey_mcp_server.common.connection.get_client',
        side_effect=_get_client,
    ):
        yield _get_client
