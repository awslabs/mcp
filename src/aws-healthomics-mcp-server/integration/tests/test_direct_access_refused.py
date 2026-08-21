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


"""Sole-ingress / direct-access refusal integration test.

This opt-in integration test asserts that a direct connection to the Server -- one
that bypasses the deployment's Fronting_Layer -- is refused, proving the Fronting_Layer
is the sole network-reachable ingress.

For the AgentCore deployment the container port is not otherwise exposed, so any
connection attempt that does not traverse AgentCore Runtime fails to establish
("AgentCore deployment demonstration"). For the API Gateway deployment the Server is
bound to the loopback address ``127.0.0.1`` and is therefore not reachable off-box, so
a direct connection that does not traverse API Gateway is refused ("API Gateway
deployment demonstration").

The test is gated behind the Opt_In_Signal (``RUN_REMOTE_INTEGRATION_TESTS``) by the
collection hook in ``integration/conftest.py`` and is skipped by default. When the
signal is present it resolves the direct (bypass) target from the environment via the
``require_inputs`` fixture and skips -- rather than fails -- when that input is absent.
"""

import pytest
import socket
from collections.abc import Callable, Mapping
from urllib.parse import urlsplit


# Environment variable naming the direct (bypass) target that must NOT be reachable:
# the address of the Server behind the Fronting_Layer, expressed either as a
# ``host:port`` pair or as a URL (e.g. ``http://10.0.1.5:8080``). When absent, the test
# is skipped (not failed) by the ``require_inputs`` fixture.
DIRECT_TARGET_ENV = 'AHO_ITEST_DIRECT_TARGET'

# A short connect timeout: a direct connection to a sole-ingress deployment should be
# refused promptly (RST) or, for a filtered/unroutable target, time out. Either outcome
# proves the target is not directly reachable.
_CONNECT_TIMEOUT_SECONDS = 5.0

# The default port assumed when the target is a bare host with no explicit port and no
# URL scheme from which a port can be inferred.
_DEFAULT_PORT = 80

# Connection errors that all count as "the direct connection was refused / did not
# establish". A refused connection (RST), an unreachable host, a DNS failure, or a
# connect timeout each demonstrate the Server is not directly reachable.
_REFUSED_ERRORS: tuple[type[BaseException], ...] = (
    ConnectionRefusedError,
    ConnectionError,
    socket.timeout,
    socket.gaierror,
    TimeoutError,
    OSError,
)


def _parse_host_port(target: str) -> tuple[str, int]:
    """Parse ``target`` into a ``(host, port)`` pair.

    Accepts either a URL (``scheme://host:port/...``) or a bare ``host:port`` pair. When
    no explicit port is present, falls back to the URL scheme's port or ``_DEFAULT_PORT``.
    """
    text = target.strip()
    if '://' in text:
        parts = urlsplit(text)
        host = parts.hostname
        if not host:
            raise ValueError(f'no host in direct target URL: {target!r}')
        port = parts.port
        if port is None:
            port = 443 if parts.scheme == 'https' else _DEFAULT_PORT
        return host, port

    if text.startswith('[') and ']' in text:
        # Bracketed IPv6 literal, optionally with a trailing ``:port``.
        host, _, rest = text[1:].partition(']')
        port = int(rest.lstrip(':')) if rest.lstrip(':') else _DEFAULT_PORT
        return host, port

    host, sep, port_text = text.rpartition(':')
    if not sep:
        return text, _DEFAULT_PORT
    return host, int(port_text)


def _attempt_direct_connection(host: str, port: int, timeout_s: float) -> None:
    """Attempt a raw TCP connection to ``host:port``.

    Returns ``None`` if the connection unexpectedly establishes (a sole-ingress
    violation), and raises one of ``_REFUSED_ERRORS`` when the connection is refused or
    does not establish (the expected, passing outcome).
    """
    with socket.create_connection((host, port), timeout=timeout_s) as conn:
        # If we get here the Server is directly reachable -- record and let the caller
        # fail the test. Close happens via the context manager.
        conn.settimeout(timeout_s)


@pytest.mark.integration
def test_direct_connection_to_server_is_refused(
    require_inputs: Callable[[list[str]], Mapping[str, str]],
) -> None:
    """A direct connection bypassing the Fronting_Layer must be refused.

    Validates: Requirements AgentCore deployment demonstration (AgentCore is the sole
    ingress; the container port is not otherwise exposed) and API Gateway deployment
    demonstration (the Server binds to loopback and is not reachable off-box). Attempts a
    raw TCP connect to the direct (bypass) target and asserts it does NOT establish --
    the Fronting_Layer is the sole ingress.
    """
    inputs = require_inputs([DIRECT_TARGET_ENV])
    host, port = _parse_host_port(inputs[DIRECT_TARGET_ENV])

    try:
        _attempt_direct_connection(host, port, _CONNECT_TIMEOUT_SECONDS)
    except _REFUSED_ERRORS:
        # Expected: the direct connection was refused or did not establish, proving the
        # Server is reachable only through its Fronting_Layer.
        return

    pytest.fail(
        f'direct connection to {host}:{port} unexpectedly succeeded; the Server is '
        'directly reachable, violating sole-ingress (the Fronting_Layer must be the '
        'only network-reachable entry point)'
    )
