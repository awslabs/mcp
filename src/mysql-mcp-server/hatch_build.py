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

"""Hatchling build hook: fetch the Amazon RDS global CA bundle at wheel build time.

Why this exists
---------------
Aurora MySQL IAM authentication requires strict TLS, but Python's default
system trust store on most developer machines does not include the Amazon
RDS regional certificate authorities. Connections fail with
CERTIFICATE_VERIFY_FAILED.

To make IAM auth work out of the box, the built wheel ships Amazon's
published global CA bundle at a known path inside the package. Runtime
TLS validation against that bundle handles cert chain and FQDN matching
the way TLS normally does — including detection of attacker-controlled
endpoints reached via DNS poisoning.

The PEM is not committed to source control to keep binary blobs out of
code review. The hook fetches it from
`https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` on
every build and writes it into the wheel. AWS rotations are picked up
automatically on the next build with no maintainer action required.

Running standalone
------------------
`python hatch_build.py` fetches the bundle without building a wheel.
Useful for local development after a fresh checkout, since tests that
load the bundle expect the PEM to be present on disk.
"""

import argparse
import os
import sys
import urllib.request


# URL for Amazon's always-current RDS global CA bundle. AWS publishes this
# file at a stable path and updates it whenever they rotate regional CAs.
_RDS_CA_BUNDLE_URL = 'https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem'

# Where the bundle is written. Relative to the package root so the same
# path works in both the source tree (for local dev) and the built wheel
# (for released packages).
_OUTPUT_PATH = os.path.join('awslabs', 'mysql_mcp_server', 'connection', 'rds_global_bundle.pem')


def _ssl_context_for_aws_endpoint():
    """Build an SSL context that can validate truststore.pki.rds.amazonaws.com.

    Python's urllib uses the system trust store on Linux, which on some dev
    hosts does not chain to the public CA that signs truststore.pki.rds.
    Prefer certifi's bundled CA store when available (it ships with most
    Python distributions and is the canonical 'public-internet' trust
    list); fall back to the default context otherwise.
    """
    import ssl

    try:
        import certifi  # type: ignore[import-not-found]

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(output_path: str = _OUTPUT_PATH) -> str:
    """Download the RDS CA bundle and write it to disk.

    Returns the absolute path to the written file. Idempotent: if the file
    is already on disk, returns immediately without making a network call.
    """
    abs_path = os.path.abspath(output_path)
    if os.path.exists(abs_path):
        return abs_path

    # Defensive scheme check before urlopen. urllib.request.urlopen accepts
    # any URL scheme, including file:// and ftp://, which static analysers
    # rightly flag (Bandit B310). Guard against future bugs that change
    # _RDS_CA_BUNDLE_URL or pass an attacker-controlled value here.
    if not _RDS_CA_BUNDLE_URL.startswith('https://'):
        raise RuntimeError(f'RDS CA bundle URL must use https://, got: {_RDS_CA_BUNDLE_URL!r}')

    try:
        ctx = _ssl_context_for_aws_endpoint()
        # B310 (audit url open for permitted schemes): scheme is enforced
        # to be https:// by the explicit check above, and the URL is a
        # module-level constant pointing at AWS's public truststore.
        with urllib.request.urlopen(  # nosec B310
            _RDS_CA_BUNDLE_URL, timeout=30, context=ctx
        ) as resp:
            content = resp.read()
    except Exception as exc:
        raise RuntimeError(
            f'Failed to fetch RDS CA bundle from {_RDS_CA_BUNDLE_URL}: {exc}\n\n'
            'Build machine needs HTTPS access to truststore.pki.rds.amazonaws.com.\n'
            'If the machine is offline, fetch the bundle manually on a connected '
            f'host with:\n\n    curl -sSL {_RDS_CA_BUNDLE_URL} -o {abs_path}\n\n'
            'and rerun the build.'
        ) from exc

    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, 'wb') as fh:
        fh.write(content)
    return abs_path


# ---------------------------------------------------------------------------
# Hatchling build hook
# ---------------------------------------------------------------------------

try:
    from hatchling.builders.hooks.plugin.interface import BuildHookInterface
except ImportError:  # pragma: no cover - only happens outside a build env
    BuildHookInterface = None  # type: ignore[assignment, misc]


if BuildHookInterface is not None:

    class RDSCABundleHook(BuildHookInterface):
        """Ensures the RDS CA bundle is present before the wheel is packed."""

        PLUGIN_NAME = 'rds_ca_bundle'

        def initialize(self, version: str, build_data: dict) -> None:
            """Called by hatchling before the wheel is built.

            Fetches the bundle, then registers it via
            ``build_data['force_include']`` so hatchling packs it into the
            wheel alongside the Python modules. Without the force_include
            registration, hatchling's default wheel builder only picks up
            ``.py`` files in the declared packages.
            """
            abs_path = fetch()
            wheel_path = _OUTPUT_PATH.replace(os.sep, '/')
            build_data.setdefault('force_include', {})[abs_path] = wheel_path
            self.app.display_info(f'Wrote RDS CA bundle to {abs_path}')


# ---------------------------------------------------------------------------
# CLI entry point for local dev
# ---------------------------------------------------------------------------


def _main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        description=('Fetch the Amazon RDS global CA bundle for the MySQL MCP server package.')
    )
    parser.parse_args(argv)

    path = fetch()
    print(f'Wrote RDS CA bundle to {path}')
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
