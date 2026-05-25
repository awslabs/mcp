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

Why this exists (security rationale)
------------------------------------
Aurora MySQL IAM authentication requires strict TLS, but Python's default
system trust store on most developer machines does not include the Amazon
RDS regional certificate authorities. Connections fail with
CERTIFICATE_VERIFY_FAILED.

To make IAM auth work out of the box, the built wheel ships Amazon's
published global CA bundle at a known path. The runtime verifies that
bundle against a pinned SHA-256 before trusting it.

This hook is deliberate: every build re-downloads the bundle from AWS
and verifies it against the SHA-256 pinned in this file. The verification
is non-negotiable. A hash mismatch fails the build loudly so that an
AWS CA rotation cannot silently change what the package trusts. Updating
the trusted CA chain requires a reviewed commit that bumps the pin.
This is the property that makes the design safer than committing the
PEM directly: the act of trusting a new chain becomes a code-review
event rather than a quiet `git pull`.

We deliberately do NOT commit the PEM to source control:

* Binary blobs muddy code review
* Keeping the PEM out of the repo enforces build-time verification
* Build failure on a hash mismatch guarantees we notice AWS CA rotations
  instead of silently shipping an updated chain we never reviewed

Instead, this hook runs during `uv build`, `hatch build`, `pip wheel`, and
`pip install` from source. It downloads the bundle from AWS's public URL,
verifies it against the pinned hash below, and writes it into the wheel.

When AWS rotates the global bundle
----------------------------------
The build will fail with a clear hash-mismatch error. To update:

1. Read AWS's CA rotation announcement and verify the change is legitimate
   out of band (AWS blog, Trust and Safety advisory, etc.).
2. Run `python hatch_build.py --refresh-hash` to download the new bundle
   and print its SHA-256.
3. Update `_RDS_CA_BUNDLE_SHA256` below to the new value in a commit that
   is reviewed by a second engineer.
4. Rebuild and publish a new package version.

Running standalone
------------------
`python hatch_build.py` fetches and verifies the bundle without building
a wheel. Useful for local development after a fresh checkout, since tests
that load the bundle expect the PEM to be present on disk.
"""

import argparse
import hashlib
import os
import sys
import urllib.request


# URL for Amazon's always-current RDS global CA bundle. AWS publishes this
# file at a stable path and updates it whenever they rotate regional CAs.
_RDS_CA_BUNDLE_URL = 'https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem'

# Pinned SHA-256 of the bundle content. SECURITY-CRITICAL: changing this
# value implicitly changes which CA chain the package trusts. Every update
# MUST be a reviewed commit. The build (and the runtime loader) refuse any
# bundle that does not match this hash, so an AWS CA rotation will fail
# the build until a human verifies the new chain and bumps the pin.
# See module docstring for the rotation process.
_RDS_CA_BUNDLE_SHA256 = 'e5bb2084ccf45087bda1c9bffdea0eb15ee67f0b91646106e466714f9de3c7e3'

# Where the verified bundle is written. Relative to the package root so the
# same path works in both the source tree (for local dev) and the built
# wheel (for released packages).
_OUTPUT_PATH = os.path.join('awslabs', 'mysql_mcp_server', 'connection', 'rds_global_bundle.pem')


def _verify_existing(path: str) -> bool:
    """Return True if `path` already holds the pinned-hash CA bundle.

    Lets the hook short-circuit when a previous successful build already
    produced the verified file. Important for two reasons:

    1. Avoids redundant network round-trips on every editable install.
    2. Allows builds to succeed on machines whose Python cannot validate
       the AWS truststore endpoint (a common dev-host quirk where the
       system trust store and Python's bundled CA list disagree). On
       those machines the developer can place the verified PEM manually
       once and subsequent builds will trust it via SHA-256.
    """
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'rb') as fh:
            existing = fh.read()
    except OSError:
        return False
    return hashlib.sha256(existing).hexdigest() == _RDS_CA_BUNDLE_SHA256


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


def fetch_and_verify(output_path: str = _OUTPUT_PATH) -> str:
    """Download the RDS CA bundle, verify its hash, write it to disk.

    Returns the absolute path to the written file.

    Raises RuntimeError if the downloaded content does not match the pinned
    hash. This intentionally fails loud: a hash mismatch means either AWS
    rotated the bundle (expected, requires a pin bump + review) or the
    download was tampered with (serious, must be investigated).

    Idempotent: if the file at `output_path` already matches the pinned
    SHA-256, returns immediately without making a network call.
    """
    abs_path = os.path.abspath(output_path)
    if _verify_existing(abs_path):
        return abs_path

    try:
        ctx = _ssl_context_for_aws_endpoint()
        with urllib.request.urlopen(_RDS_CA_BUNDLE_URL, timeout=30, context=ctx) as resp:
            content = resp.read()
    except Exception as exc:
        raise RuntimeError(
            f'Failed to fetch RDS CA bundle from {_RDS_CA_BUNDLE_URL}: {exc}\n\n'
            'Build machine needs HTTPS access to truststore.pki.rds.amazonaws.com.\n'
            'If the machine is offline, fetch the bundle manually on a connected '
            f'host with:\n\n    curl -sSL {_RDS_CA_BUNDLE_URL} -o {abs_path}\n\n'
            'and rerun the build. The hook will SHA-256-verify the placed file.'
        ) from exc

    digest = hashlib.sha256(content).hexdigest()
    if digest != _RDS_CA_BUNDLE_SHA256:
        raise RuntimeError(
            f'RDS CA bundle hash mismatch.\n'
            f'  Downloaded: {digest}\n'
            f'  Pinned:     {_RDS_CA_BUNDLE_SHA256}\n'
            f'  Source:     {_RDS_CA_BUNDLE_URL}\n\n'
            'AWS may have rotated the bundle. Verify the new content is legitimate '
            'out of band, then update _RDS_CA_BUNDLE_SHA256 in hatch_build.py to '
            f'{digest} in a reviewed commit.'
        )

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
        """Ensures the verified RDS CA bundle is present before the wheel is packed."""

        PLUGIN_NAME = 'rds_ca_bundle'

        def initialize(self, version: str, build_data: dict) -> None:
            """Called by hatchling before the wheel is built.

            Fetches and verifies the bundle, then registers it via
            ``build_data['force_include']`` so hatchling packs it into the
            wheel alongside the Python modules. Without the force_include
            registration, hatchling's default wheel builder only picks up
            ``.py`` files in the declared packages.
            """
            abs_path = fetch_and_verify()
            wheel_path = _OUTPUT_PATH.replace(os.sep, '/')
            build_data.setdefault('force_include', {})[abs_path] = wheel_path
            self.app.display_info(f'Wrote verified RDS CA bundle to {abs_path}')


# ---------------------------------------------------------------------------
# CLI entry point for local dev
# ---------------------------------------------------------------------------


def _main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        description=(
            'Fetch and verify the Amazon RDS global CA bundle for the MySQL MCP server package.'
        )
    )
    parser.add_argument(
        '--refresh-hash',
        action='store_true',
        help=(
            'Download the current bundle and print its SHA-256 without '
            'verifying against the pinned hash. Use this when AWS rotates '
            'the bundle and you need the new hash to update the pin.'
        ),
    )
    args = parser.parse_args(argv)

    if args.refresh_hash:
        ctx = _ssl_context_for_aws_endpoint()
        with urllib.request.urlopen(_RDS_CA_BUNDLE_URL, timeout=30, context=ctx) as resp:
            content = resp.read()
        digest = hashlib.sha256(content).hexdigest()
        print(f'Current bundle SHA-256: {digest}')
        print(f'Source: {_RDS_CA_BUNDLE_URL}')
        print(f'Size:   {len(content)} bytes')
        return 0

    path = fetch_and_verify()
    print(f'Wrote verified RDS CA bundle to {path}')
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
