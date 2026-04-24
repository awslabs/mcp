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

"""Shared fixtures for live integration tests."""

from __future__ import annotations

import asyncio
import os
import pytest


@pytest.fixture()
async def client():
    """Create a GLIDE client connected to $VALKEY_HOST. One per test.

    Skips the test if VALKEY_HOST is not set.
    """
    if not os.environ.get('VALKEY_HOST'):
        pytest.skip('VALKEY_HOST not set')
    from glide import GlideClient, GlideClientConfiguration, NodeAddress

    host = os.environ['VALKEY_HOST']
    port = int(os.environ.get('VALKEY_PORT', '6379'))
    config = GlideClientConfiguration(
        addresses=[NodeAddress(host, port)],
        request_timeout=5000,
    )
    c = await asyncio.wait_for(GlideClient.create(config), timeout=10)
    yield c
    await c.close()
