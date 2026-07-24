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

"""Offline guard: the harness container image must not bundle provisioning code.

The deployed AgentCore test container only needs the runtime entrypoint and the shared
header constants. The provisioning modules (``deploy/agentcore``, ``apigateway``, ``cli``,
``iam``, ``cognito``, ``registry``, ``common``) create/delete real AWS infrastructure and
shell out via ``subprocess``; bundling them into a network-reachable container would put
those primitives inside the blast radius of a server compromise. This test parses the
image Dockerfile's ``COPY`` directives and asserts that none of the provisioning modules
(nor the whole ``integration`` tree) is copied into the image, while the required runtime
files are.

Validates: Requirements Harness location and offline isolation.
"""

import re
from pathlib import Path


_DOCKERFILE = Path(__file__).resolve().parents[1] / 'deploy' / 'image' / 'Dockerfile'

# Provisioning / test modules that must never be copied into the deployed container.
_FORBIDDEN = (
    'integration/deploy/agentcore.py',
    'integration/deploy/apigateway.py',
    'integration/deploy/cli.py',
    'integration/deploy/iam.py',
    'integration/deploy/cognito.py',
    'integration/deploy/registry.py',
    'integration/deploy/common.py',
    'integration/harness/inventory.py',
    'integration/harness/tenants.py',
    'integration/harness/isolation.py',
    'integration/harness/mcp_client.py',
    'integration/harness/credential_scan.py',
)

# The runtime glue the entrypoint actually needs.
_REQUIRED = (
    'integration/deploy/image/entrypoint.py',
    'integration/harness/headers.py',
)


def _copy_sources() -> list[str]:
    """Return the source paths referenced by ``COPY`` directives in the image Dockerfile."""
    text = _DOCKERFILE.read_text(encoding='utf-8')
    sources: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('COPY'):
            continue
        # Drop the COPY keyword and any --flag=... options, then take all but the last
        # token (the destination) as sources.
        tokens = [t for t in stripped.split()[1:] if not t.startswith('--')]
        if len(tokens) >= 2:
            sources.extend(tokens[:-1])
    return sources


class TestImageDoesNotBundleProvisioning:
    """The harness image copies only runtime glue, never provisioning/subprocess code.

    Validates: Requirements Harness location and offline isolation.
    """

    def test_no_whole_integration_tree_copy(self) -> None:
        """The Dockerfile must not copy the entire ``integration`` package tree."""
        sources = _copy_sources()
        assert 'integration' not in sources, (
            'The image must not COPY the whole integration/ tree (it would bundle the '
            'provisioning + subprocess code). Copy only the runtime glue.'
        )

    def test_forbidden_provisioning_modules_absent(self) -> None:
        """No provisioning or test module is copied into the image."""
        joined = '\n'.join(_copy_sources())
        for forbidden in _FORBIDDEN:
            assert forbidden not in joined, f'{forbidden} must not be copied into the image'

    def test_required_runtime_files_present(self) -> None:
        """The runtime entrypoint and shared headers are copied into the image."""
        sources = _copy_sources()
        for required in _REQUIRED:
            assert required in sources, f'{required} must be copied into the image'

    def test_entrypoint_only_imports_allowed_integration_modules(self) -> None:
        """The entrypoint imports nothing from integration beyond ``harness.headers``.

        A regression here (e.g. importing ``integration.deploy.agentcore``) would reintroduce
        the provisioning code into the container's runtime import graph.
        """
        entrypoint = (_DOCKERFILE.parent / 'entrypoint.py').read_text(encoding='utf-8')
        integration_imports = re.findall(r'(?:from|import)\s+(integration[\w.]*)', entrypoint)
        for module in integration_imports:
            assert module in ('integration.harness.headers',), (
                f'entrypoint imports {module!r}; only integration.harness.headers is allowed '
                'so the container never pulls in provisioning code'
            )
