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

"""Property-based tests for credential-resolution failure behavior.

Property: Resolution failure suppresses AWS calls
    When the active resolver raises (including a non-empty profile that cannot be
    resolved), the tool surfaces an error and performs NO AWS service call for that
    request.

Validates: Requirements Credential-resolution seam, Tools resolve credentials through
    the seam, Behavior preservation in single-tenant mode
"""

import botocore.exceptions
import pytest
from awslabs.aws_healthomics_mcp_server.utils import aws_utils
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialRequest,
    DefaultCredentialResolver,
    create_aws_client,
    get_account_id,
    get_active_resolver,
    get_aws_session,
    get_codebuild_client,
    get_codeconnections_client,
    get_ecr_client,
    get_iam_client,
    get_logs_client,
    get_omics_client,
    get_partition,
    set_active_resolver,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import MagicMock, patch


class ResolutionFailure(RuntimeError):
    """Sentinel error raised by the failing fake resolver to simulate a resolution failure."""


class RecordingFailingResolver:
    """Fake resolver whose ``resolve`` always raises, recording each invocation.

    Installing this via ``set_active_resolver`` lets us assert that a helper surfaces
    the resolution error before any ``boto3.Session`` (and therefore any AWS service
    call) is constructed.
    """

    def __init__(self, error: Exception) -> None:
        """Store the error to raise and initialize the call recorder.

        Args:
            error: The exception instance to raise from every ``resolve`` call.
        """
        self.error = error
        self.requests: list[CredentialRequest] = []

    def resolve(self, request: CredentialRequest):
        """Record the request and raise the configured error without building a session.

        Args:
            request: The credential resolution inputs (region/profile).

        Raises:
            Exception: Always raises the configured error.
        """
        self.requests.append(request)
        raise self.error


# Each entry takes (region, profile) keyword inputs and routes through the active
# resolver via the credential-resolution seam. ``create_aws_client`` is wrapped to
# supply a service name while keeping the region/profile call shape uniform.
HELPERS = {
    'get_aws_session': lambda region, profile: get_aws_session(
        region_name=region, profile_name=profile
    ),
    'create_aws_client': lambda region, profile: create_aws_client(
        'omics', region_name=region, profile_name=profile
    ),
    'get_omics_client': lambda region, profile: get_omics_client(
        region_name=region, profile_name=profile
    ),
    'get_logs_client': lambda region, profile: get_logs_client(
        region_name=region, profile_name=profile
    ),
    'get_codeconnections_client': lambda region, profile: get_codeconnections_client(
        region_name=region, profile_name=profile
    ),
    'get_ecr_client': lambda region, profile: get_ecr_client(
        region_name=region, profile_name=profile
    ),
    'get_codebuild_client': lambda region, profile: get_codebuild_client(
        region_name=region, profile_name=profile
    ),
    'get_iam_client': lambda region, profile: get_iam_client(
        region_name=region, profile_name=profile
    ),
    'get_account_id': lambda region, profile: get_account_id(
        region_name=region, profile_name=profile
    ),
    'get_partition': lambda region, profile: get_partition(
        region_name=region, profile_name=profile
    ),
}


@pytest.fixture(autouse=True)
def restore_resolver():
    """Save and restore the active resolver and clear the cached partition.

    Ensures each test starts and ends with the default single-tenant resolver and that
    the ``lru_cache`` on ``get_partition`` does not leak state across tests.
    """
    saved = get_active_resolver()
    get_partition.cache_clear()
    try:
        yield
    finally:
        set_active_resolver(saved)
        get_partition.cache_clear()


# Region inputs: absent, empty/whitespace, and named regions.
region_inputs = st.one_of(
    st.none(),
    st.sampled_from(['', '   ', 'us-east-1', 'eu-west-1', 'ap-southeast-2']),
    st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz-0123456789',  # pragma: allowlist secret
        max_size=16,
    ),
)

# Profile inputs: absent, empty/whitespace, and named profiles (including unresolvable).
profile_inputs = st.one_of(
    st.none(),
    st.sampled_from(['', '   ', 'default', 'bogus', 'does-not-exist']),
    st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz-_0123456789',  # pragma: allowlist secret
        max_size=16,
    ),
)

helper_names = st.sampled_from(sorted(HELPERS.keys()))


@settings(max_examples=100)
@given(
    helper_name=helper_names,
    region=region_inputs,
    profile=profile_inputs,
    error=st.sampled_from(
        [
            ResolutionFailure('credential resolution failed'),
            botocore.exceptions.ProfileNotFound(profile='bogus'),
            RuntimeError('unexpected resolver failure'),
        ]
    ),
)
def test_active_resolver_failure_suppresses_aws_calls(helper_name, region, profile, error):
    """Property: Resolution failure suppresses AWS calls (active-resolver raises).

    When the active resolver raises for a helper invocation, the helper surfaces the
    error and constructs no ``boto3.Session`` (so no AWS service call is made).

    Validates: Requirements Credential-resolution seam, Tools resolve credentials
        through the seam, Behavior preservation in single-tenant mode
    """
    failing = RecordingFailingResolver(error)
    set_active_resolver(failing)
    get_partition.cache_clear()

    helper = HELPERS[helper_name]

    # Patch boto3.Session so we can prove NO session/client was constructed: the failing
    # resolver raises before any AWS service object is created.
    with patch.object(aws_utils.boto3, 'Session') as mock_session:
        with pytest.raises(Exception) as exc_info:
            helper(region, profile)

    # The surfaced error is exactly the one the resolver raised.
    assert exc_info.value is error
    # The resolver was consulted (the seam is the single choke point).
    assert len(failing.requests) >= 1
    # The tool-supplied inputs were forwarded unchanged through the seam.
    assert failing.requests[0].region == region
    assert failing.requests[0].profile == profile
    # No AWS session (and therefore no AWS service call) was constructed.
    mock_session.assert_not_called()


@settings(max_examples=100)
@given(
    helper_name=helper_names,
    region=region_inputs,
    profile=st.text(alphabet='abcdefghijklmnopqrstuvwxyz-_0123456789', min_size=1, max_size=16),
)
def test_named_profile_unresolvable_suppresses_aws_calls(helper_name, region, profile):
    """Property: Resolution failure suppresses AWS calls (named profile unresolvable).

    Using the real DefaultCredentialResolver, a non-empty profile that cannot be
    resolved raises ProfileNotFound and no AWS service call (sts get_caller_identity)
    is performed for that request.

    Validates: Requirements Credential-resolution seam, Tools resolve credentials
        through the seam, Behavior preservation in single-tenant mode
    """
    set_active_resolver(DefaultCredentialResolver())
    get_partition.cache_clear()

    helper = HELPERS[helper_name]

    # botocore.session.Session() is constructed by the default resolver; keep it inert.
    # boto3.Session raises ProfileNotFound when a (non-empty) profile_name is supplied,
    # simulating a named profile that cannot be resolved.
    def session_side_effect(*positional_args, **keyword_args):
        if keyword_args.get('profile_name'):
            raise botocore.exceptions.ProfileNotFound(profile=keyword_args['profile_name'])
        # No profile -> return a session whose client would call AWS; we still assert
        # below that get_caller_identity is never reached because these helpers either
        # raise or short-circuit before a real AWS call in this test's profile-driven path.
        return MagicMock()

    with (
        patch.object(aws_utils.botocore.session, 'Session', return_value=MagicMock()),
        patch.object(aws_utils.boto3, 'Session', side_effect=session_side_effect) as mock_session,
    ):
        with pytest.raises(botocore.exceptions.ProfileNotFound):
            helper(region, profile)

    # boto3.Session was attempted with the unresolvable named profile and raised; no
    # client was returned, so no AWS service call could be made for that request.
    assert mock_session.called
    for call in mock_session.call_args_list:
        assert call.kwargs.get('profile_name') == profile
