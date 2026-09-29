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


"""Opt-in gating for the remote-deployment integration test harness.

The integration suite is opt-in: it only runs against live AWS when an explicit
activation signal is present. This module provides the pure-logic gate used by
``integration/conftest.py`` to decide whether to skip the integration tests and,
when enabled, which required configuration inputs are missing.

The truthy parse mirrors the server's own boolean convention
(``_MULTI_TENANT_ENABLE_VALUES`` in
``awslabs.aws_healthomics_mcp_server.config``) so operators reason about a single
mental model: values are matched case-insensitively after trimming surrounding
whitespace.
"""

from collections.abc import Mapping, Sequence


OPT_IN_ENV = 'RUN_REMOTE_INTEGRATION_TESTS'

# Recognized truthy values for the Opt_In_Signal. This mirrors the server's
# ``_MULTI_TENANT_ENABLE_VALUES`` convention (case-insensitive, whitespace
# trimmed) so the harness and the server share one mental model. Unlike the
# server's strict parser, any value outside this set (including the disable
# values and unrecognized values) is treated as "not enabled" so the gate fails
# safe toward skipping rather than raising.
_ENABLE_VALUES = ('true', '1', 'yes', 'on', 'enabled')


def is_opt_in_enabled(env: Mapping[str, str]) -> bool:
    """Return True iff the Opt_In_Signal is present and truthy.

    The value is matched case-insensitively after trimming surrounding
    whitespace against the recognized enable values (``true``, ``1``, ``yes``,
    ``on``, ``enabled``). An absent, empty, whitespace-only, or otherwise
    unrecognized value yields ``False``.

    Args:
        env: A mapping of environment variables (typically ``os.environ``).

    Returns:
        ``True`` when the integration suite should run against live AWS.
    """
    raw = env.get(OPT_IN_ENV)
    if raw is None:
        return False
    return raw.strip().lower() in _ENABLE_VALUES


def skip_reason() -> str:
    """Return a human-readable skip reason naming the Opt_In_Signal env var.

    Attached to skipped integration items when the Opt_In_Signal is absent so an
    operator can see exactly which variable enables the suite.
    """
    return (
        f'Remote integration tests are opt-in; set {OPT_IN_ENV} to a truthy value '
        f'(e.g. "true") to enable them.'
    )


def missing_required_inputs(required: Sequence[str], provided: Mapping[str, str]) -> list[str]:
    """Return the names of required inputs absent or blank in ``provided``.

    A required name is considered missing when it is not present in ``provided``
    or when its value is ``None``, empty, or whitespace-only. The returned list
    preserves the order of ``required`` and contains each missing name once per
    occurrence in ``required``.

    Args:
        required: The names of the configuration inputs a test depends on.
        provided: A mapping of available inputs (typically resolved from the
            resource inventory and/or the environment).

    Returns:
        The names of the required inputs that are absent or blank.
    """
    missing: list[str] = []
    for name in required:
        value = provided.get(name)
        if value is None or value.strip() == '':
            missing.append(name)
    return missing
