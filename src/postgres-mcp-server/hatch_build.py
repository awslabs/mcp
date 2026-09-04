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
"""Hatchling build hook: assemble the AWS CA trust bundle at wheel build time.

Why this exists
---------------
The psycopg (PG Wire) connection path sends real credentials on the wire --
IAM auth tokens and Secrets Manager passwords. To prevent a silent plaintext
downgrade or a MITM presenting a spoofed certificate, connections use
``sslmode=verify-full`` by default, which requires a trusted CA to verify the
server certificate. Python's default system trust store on many hosts (and in
minimal containers) does not reliably include the certificate authorities AWS
uses, so verification would fail with CERTIFICATE_VERIFY_FAILED.

Aurora / RDS PostgreSQL endpoints present certificates from *two* different
Amazon PKIs, both documented:

  * The Amazon RDS private CAs (``rds-ca-rsa2048-g1`` / ``rds-ca-rsa4096-g1`` /
    ``rds-ca-ecc384-g1``), used by direct DB instance / cluster endpoints.
    Distributed in Amazon's RDS ``global-bundle.pem``.
    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.SSL.html
  * The public Amazon Trust Services roots (``Amazon Root CA 1``..``4``), used by
    endpoints whose certificate comes from AWS Certificate Manager (ACM) -- e.g.
    RDS Proxy and Aurora Serverless v1. Published at amazontrust.com.

To make strict TLS work out of the box across all of these, the built wheel
ships the *union* of both -- the RDS global bundle concatenated with the public
Amazon roots -- at a known path inside the package. libpq's ``sslrootcert``
takes a single file, so shipping one combined PEM covers both cert families.
Only root CAs are included (never intermediates), so automatic RDS server
certificate rotation is unaffected.

The PEM is not committed to source control to keep binary blobs out of code
review. The hook fetches its inputs over HTTPS on every build and writes the
combined file into the wheel; AWS CA rotations are picked up automatically on
the next build. Operators who target self-hosted PostgreSQL or maintain their
own trust store can override the bundle at runtime with ``--ca_bundle <path>``.

Running standalone
------------------
``python hatch_build.py`` assembles the bundle without building a wheel. Useful
for local development after a fresh checkout, since tests that load the bundle
expect the PEM to be present on disk.
"""

import argparse
import os
import sys
import urllib.request


# Amazon's always-current RDS global CA bundle (the RDS *private* CAs). AWS
# publishes this at a stable path and updates it when they rotate regional CAs.
_RDS_CA_BUNDLE_URL = 'https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem'

# The public Amazon Trust Services root CAs. ACM-issued certificates (RDS Proxy,
# Aurora Serverless v1, and other publicly-trusted AWS endpoints) chain to these.
# Stable, published URLs (referenced by AWS's own connection docs).
_AMAZON_ROOT_CA_URLS = (
    'https://www.amazontrust.com/repository/AmazonRootCA1.pem',
    'https://www.amazontrust.com/repository/AmazonRootCA2.pem',
    'https://www.amazontrust.com/repository/AmazonRootCA3.pem',
    'https://www.amazontrust.com/repository/AmazonRootCA4.pem',
)

# Every URL fetched by this hook, in the order they are concatenated into the
# combined bundle. RDS private CAs first, then the public Amazon roots.
_BUNDLE_SOURCE_URLS = (_RDS_CA_BUNDLE_URL, *_AMAZON_ROOT_CA_URLS)

# Where the combined bundle is written. Relative to the package root so the same
# path works in both the source tree (for local dev) and the built wheel.
_OUTPUT_PATH = os.path.join(
    'awslabs', 'postgres_mcp_server', 'connection', 'aws_ca_bundle.pem'
)


def _ssl_context_for_aws_endpoint():
    """Build an SSL context that can validate the AWS download endpoints.

    Prefer certifi's bundled CA store when available (the canonical
    public-internet trust list); fall back to the default context otherwise.
    """
    import ssl

    try:
        import certifi  # type: ignore[import-not-found]

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _fetch_url(url: str, ctx) -> bytes:
    """Fetch a single https:// URL and return its bytes.

    Each URL passed here is a hard-coded module-level constant
    (``_BUNDLE_SOURCE_URLS``); none is derived from user input or function
    arguments. The explicit https:// guard rules out the file:// / ftp://
    schemes the scanners warn about, so a malicious actor cannot redirect this
    to read arbitrary local files. Both findings (Bandit B310, Semgrep
    dynamic-urllib-use) are audited and suppressed on that basis; the scheme
    guard also protects against future edits to the constants.
    """
    if not url.startswith('https://'):
        raise RuntimeError(f'CA bundle source URL must use https://, got: {url!r}')
    with urllib.request.urlopen(  # nosec B310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        url, timeout=30, context=ctx
    ) as resp:
        return resp.read()


def fetch(output_path: str = _OUTPUT_PATH) -> str:
    """Assemble the combined AWS CA bundle and write it to disk.

    Concatenates the Amazon RDS global bundle (private CAs) with the public
    Amazon Trust Services root CAs, so the single file verifies both the
    private-CA (direct instance/cluster) and public-CA (ACM: RDS Proxy /
    Serverless) certificate families.

    Returns the absolute path to the written file. Idempotent: if the file is
    already on disk, returns immediately without making a network call.
    """
    abs_path = os.path.abspath(output_path)
    if os.path.exists(abs_path):
        return abs_path

    ctx = _ssl_context_for_aws_endpoint()
    chunks = []
    for url in _BUNDLE_SOURCE_URLS:
        try:
            chunks.append(_fetch_url(url, ctx))
        except Exception as exc:
            raise RuntimeError(
                f'Failed to fetch CA bundle source {url}: {exc}\n\n'
                'Build machine needs HTTPS access to truststore.pki.rds.amazonaws.com '
                'and www.amazontrust.com.\n'
                'If the machine is offline, fetch each source manually on a connected '
                'host and concatenate them into:\n\n'
                f'    {abs_path}\n\n'
                'Sources (in order):\n'
                + '\n'.join(f'    {u}' for u in _BUNDLE_SOURCE_URLS)
                + '\n\nand rerun the build.'
            ) from exc

    # Join with a newline so a source that does not end in one cannot glue two
    # PEM blocks together (``-----END-----\n-----BEGIN-----``).
    content = b'\n'.join(chunk.rstrip() + b'\n' for chunk in chunks)

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
        """Ensures the combined AWS CA bundle is present before the wheel is packed."""

        PLUGIN_NAME = 'rds_ca_bundle'

        def initialize(self, version: str, build_data: dict) -> None:
            """Assemble the bundle and force-include it in the wheel."""
            abs_path = fetch()
            wheel_path = _OUTPUT_PATH.replace(os.sep, '/')
            build_data.setdefault('force_include', {})[abs_path] = wheel_path
            self.app.display_info(f'Wrote AWS CA bundle to {abs_path}')


# ---------------------------------------------------------------------------
# CLI entry point for local dev
# ---------------------------------------------------------------------------
def _main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        description='Assemble the AWS CA bundle for the Postgres MCP server package.'
    )
    parser.parse_args(argv)
    path = fetch()
    print(f'Wrote AWS CA bundle to {path}')
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
