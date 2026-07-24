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

"""Phase 1 credential-resolution seam tests.

Groups the property-based tests that exercise the ``DefaultCredentialResolver``
seam introduced in ``utils/aws_utils.py``. These tests reuse the boto3/botocore
mocking patterns established in ``tests/test_aws_utils.py``.
"""

import os
from awslabs.aws_healthomics_mcp_server import __version__
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialRequest,
    DefaultCredentialResolver,
    get_agent_value,
    get_aws_session,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import MagicMock, patch


# Region used for the AWS_REGION environment variable so that the "region absent"
# branch (which falls back to get_region()) is deterministic and distinguishable
# from any generated region override.
ENV_REGION = 'eu-central-1'

# Module path prefix for patch targets, matching tests/test_aws_utils.py.
_AWS_UTILS = 'awslabs.aws_healthomics_mcp_server.utils.aws_utils'


# region present (non-empty) or absent (None)
region_inputs = st.one_of(
    st.none(),
    st.text(
        alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
        min_size=1,
        max_size=20,
    ),
)

# profile absent (None), empty/whitespace, or a non-empty named profile
profile_inputs = st.one_of(
    st.none(),
    st.sampled_from(['', ' ', '   ', '\t', '\n', ' \t ']),
    st.text(
        alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
        min_size=1,
        max_size=20,
    ),
)

# AGENT environment value absent or present (arbitrary, possibly needing sanitizing).
# Null bytes and surrogate code points cannot be stored in OS environment variables,
# so they are excluded from the generated values.
agent_inputs = st.one_of(
    st.none(),
    st.text(
        alphabet=st.characters(exclude_characters='\x00', exclude_categories=('Cs',)),
        max_size=20,
    ),
)


def _resolve_both(region_input, profile_input, agent_input):
    """Build sessions via the resolver and via get_aws_session under mocked boto3.

    Returns a tuple of (resolver_kwargs, legacy_kwargs, resolver_user_agent,
    legacy_user_agent) captured from the two mocked ``boto3.Session`` calls.
    """
    env = {'AWS_REGION': ENV_REGION}
    if agent_input is not None:
        env['AGENT'] = agent_input

    with patch.dict(os.environ, env, clear=True):
        with (
            patch(f'{_AWS_UTILS}.boto3.Session') as mock_boto3_session,
            patch(f'{_AWS_UTILS}.botocore.session.Session') as mock_botocore_session,
        ):
            botocore_instances: list = []

            def _make_botocore(*args, **kwargs):
                instance = MagicMock()
                botocore_instances.append(instance)
                return instance

            mock_botocore_session.side_effect = _make_botocore
            mock_boto3_session.return_value = MagicMock()

            # First call: the seam's DefaultCredentialResolver.
            DefaultCredentialResolver().resolve(
                CredentialRequest(region=region_input, profile=profile_input)
            )
            # Second call: the public get_aws_session wrapper (delegates to the seam).
            get_aws_session(region_input, profile_input)

            resolver_kwargs = mock_boto3_session.call_args_list[0].kwargs
            legacy_kwargs = mock_boto3_session.call_args_list[1].kwargs
            resolver_user_agent = botocore_instances[0].user_agent_extra
            legacy_user_agent = botocore_instances[1].user_agent_extra

    return resolver_kwargs, legacy_kwargs, resolver_user_agent, legacy_user_agent


class TestDefaultResolverEquivalence:
    """Property: Default resolver equivalence to get_aws_session.

    Validates: Requirements Credential-resolution seam, Behavior preservation in
    single-tenant mode.
    """

    @given(
        region_input=region_inputs,
        profile_input=profile_inputs,
        agent_input=agent_inputs,
    )
    @settings(max_examples=100)
    def test_default_resolver_matches_get_aws_session(
        self, region_input, profile_input, agent_input
    ):
        """Property: Default resolver equivalence to get_aws_session.

        For any region input (present non-empty or absent) and profile input
        (absent, empty/whitespace, or a named profile), DefaultCredentialResolver
        produces a boto3.Session configured with the same effective region, the
        same credential resolution path (default chain vs named profile), and the
        same user-agent extra string (including the sanitized AGENT suffix) as the
        current get_aws_session implementation.

        Validates: Requirements Credential-resolution seam, Behavior preservation
        in single-tenant mode.
        """
        (
            resolver_kwargs,
            legacy_kwargs,
            resolver_user_agent,
            legacy_user_agent,
        ) = _resolve_both(region_input, profile_input, agent_input)

        # Effective region is identical between the two paths.
        assert resolver_kwargs['region_name'] == legacy_kwargs['region_name']

        # Credential resolution path is identical: profile_name presence and value
        # must match (named profile vs default credential chain).
        assert ('profile_name' in resolver_kwargs) == ('profile_name' in legacy_kwargs)
        assert resolver_kwargs.get('profile_name') == legacy_kwargs.get('profile_name')

        # User-agent extra string is identical, including any sanitized AGENT suffix.
        assert resolver_user_agent == legacy_user_agent

    @given(
        region_input=region_inputs,
        profile_input=profile_inputs,
        agent_input=agent_inputs,
    )
    @settings(max_examples=100)
    def test_default_resolver_effective_configuration(
        self, region_input, profile_input, agent_input
    ):
        """Property: Default resolver equivalence to get_aws_session.

        The resolver's effective region resolves to the request region when
        present, otherwise get_region(); the named profile is supplied only when a
        truthy profile is given (default credential chain otherwise); and the
        user-agent extra always carries the server identifier plus the sanitized,
        lowercased AGENT suffix exactly when AGENT resolves to a non-empty value.

        Validates: Requirements Credential-resolution seam, Behavior preservation
        in single-tenant mode.
        """
        env = {'AWS_REGION': ENV_REGION}
        if agent_input is not None:
            env['AGENT'] = agent_input

        with patch.dict(os.environ, env, clear=True):
            expected_agent = get_agent_value()
            (
                resolver_kwargs,
                _legacy_kwargs,
                resolver_user_agent,
                _legacy_user_agent,
            ) = _resolve_both(region_input, profile_input, agent_input)

        expected_region = region_input if region_input else ENV_REGION
        assert resolver_kwargs['region_name'] == expected_region

        # The resolver applies its profile only when the value is truthy.
        if profile_input:
            assert resolver_kwargs.get('profile_name') == profile_input
        else:
            assert 'profile_name' not in resolver_kwargs

        expected_user_agent = f'md/awslabs#mcp#aws-healthomics-mcp-server#{__version__}'
        if expected_agent:
            expected_user_agent += f' agent/{expected_agent.lower()}'
        assert resolver_user_agent == expected_user_agent
