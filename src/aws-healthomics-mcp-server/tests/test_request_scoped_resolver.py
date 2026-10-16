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

"""Phase 2 request-scoped credential resolver isolation tests.

Property-based tests for the ``RequestScopedCredentialResolver`` introduced in
``utils/aws_utils.py``. This module is dedicated to Property 11 (Request-scoped
resolver uses only its own context); sibling resolver properties live in separate
modules to avoid file conflicts.

The boto3/botocore mocking patterns mirror those established in
``tests/test_credential_resolver.py`` and ``tests/test_aws_utils.py``.
"""

import asyncio
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialRequest,
    RequestScopedCredentialResolver,
    reset_credential_context,
    set_credential_context,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from typing import Any, cast
from unittest.mock import MagicMock, patch


# Module path prefix for patch targets, matching tests/test_credential_resolver.py.
_AWS_UTILS = 'awslabs.aws_healthomics_mcp_server.utils.aws_utils'


# Distinct identity strings for concurrent contexts. Using printable, non-space
# ASCII keeps the derived access key ids readable and unambiguous; ``unique=True``
# guarantees each worker carries a distinct identity (and therefore a distinct
# access key id), which is what makes cross-context leakage observable.
identity_lists = st.lists(
    st.text(
        alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
        min_size=1,
        max_size=10,
    ),
    unique=True,
    min_size=2,
    max_size=5,
)


def _access_key_id_for(identity: str) -> str:
    """Derive a distinct, recognizable access key id for an identity."""
    return f'AKIA-{identity}'


class TestRequestScopedResolverUsesOwnContext:
    """Property: Request-scoped resolver uses only its own context.

    Validates: Requirements Request-scoped credential resolution, Per-request
    credential freshness.
    """

    @given(identities=identity_lists)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_resolver_uses_only_its_own_context(self, identities):
        """Property: Request-scoped resolver uses only its own context.

        Concurrent execution contexts, each carrying a distinct
        ``CredentialContext`` (distinct ``identity_key`` and distinct
        ``access_key_id``), are interleaved via ``asyncio.gather``. Each worker
        sets its own context, yields control to force interleaving, then resolves
        a session through ``RequestScopedCredentialResolver``. The session a worker
        receives must be built from that worker's own credentials and never from
        another concurrent context's credentials.

        Validates: Requirements Request-scoped credential resolution, Per-request
        credential freshness.
        """

        def _make_session(*args, **kwargs):
            # Return a recordable sentinel keyed by the access key id this call
            # was built with, so each worker can assert it received a session for
            # its own identity rather than a neighbor's.
            sentinel = MagicMock()
            sentinel.recorded_access_key_id = kwargs.get('aws_access_key_id')
            sentinel.recorded_secret_access_key = kwargs.get('aws_secret_access_key')
            sentinel.recorded_session_token = kwargs.get('aws_session_token')
            return sentinel

        async def _worker(identity: str):
            access_key_id = _access_key_id_for(identity)
            context = CredentialContext(
                identity_key=identity,
                access_key_id=access_key_id,
                secret_access_key=f'secret-{identity}',
                session_token=f'token-{identity}',
                source='explicit',
            )
            # contextvars are copied per asyncio task, so setting/resetting inside
            # the worker coroutine confines this context to this task alone.
            token = set_credential_context(context)
            try:
                # Force interleaving so that, if the resolver leaked process-level
                # or neighbor state, a concurrent worker could overwrite it.
                await asyncio.sleep(0)
                session = RequestScopedCredentialResolver().resolve(CredentialRequest())
                await asyncio.sleep(0)
                return identity, access_key_id, session
            finally:
                reset_credential_context(token)

        async def _run_all():
            return await asyncio.gather(*(_worker(identity) for identity in identities))

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', side_effect=_make_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            results = asyncio.run(_run_all())

        for identity, access_key_id, session in results:
            # ``session`` is the recordable sentinel returned by the patched
            # boto3.Session; cast to Any so the static type checker permits reading
            # the credentials the resolver actually built the session with.
            recorded = cast(Any, session)
            assert recorded.recorded_access_key_id == access_key_id
            assert recorded.recorded_secret_access_key == f'secret-{identity}'
            assert recorded.recorded_session_token == f'token-{identity}'
