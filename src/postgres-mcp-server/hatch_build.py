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
review. It is a build artifact, so the build hook always fetches fresh inputs
over HTTPS and rewrites the combined file (``force_refresh=True``); this is what
picks up AWS CA rotations for every release. Integrity is checked before the
file is accepted: each Amazon Trust Services root is pinned to a SHA-256 checked
into this file, every source must parse as PEM, and the assembled bundle must
contain at least ``_MIN_CERTS_IN_BUNDLE`` certificates. The file is written
atomically (temp file + ``os.replace``), so an interrupted build never leaves a
truncated bundle behind. If the network is unavailable the build falls back to
an existing on-disk bundle ONLY when that file itself passes validation -- a
missing, truncated, or corrupt file is never silently shipped. Operators who
target self-hosted PostgreSQL or maintain their own trust store can override the
bundle at runtime with ``--ca_bundle <path>``.

The RDS ``global-bundle.pem`` is deliberately NOT checksum-pinned: AWS rotates
its regional CAs, so a fixed hash would break every build on the next rotation.
Its integrity rests on the HTTPS fetch plus the PEM-validity / cert-count
checks. The Amazon roots essentially never change, so pinning them is free
supply-chain protection.

Running standalone
------------------
``python hatch_build.py`` assembles the bundle without building a wheel. Useful
for local development after a fresh checkout, since tests that load the bundle
expect the PEM to be present on disk.
"""

import argparse
import hashlib
import os
import sys
import tempfile
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

# SHA-256 of each Amazon Trust Services root PEM *file* (raw downloaded bytes).
# These roots are valid into 2037-2040 and do not rotate, so pinning them costs
# nothing and detects tampering or an unexpected substitution at build time. The
# RDS global bundle is intentionally absent (it rotates -- see module docstring).
# To regenerate if AWS ever re-publishes a root: download each URL and take
# ``hashlib.sha256(bytes).hexdigest()``.
_AMAZON_ROOT_CA_SHA256 = {
    'https://www.amazontrust.com/repository/AmazonRootCA1.pem': (
        '2c43952ee9e000ff2acc4e2ed0897c0a72ad5fa72c3d934e81741cbd54f05bd1'  # pragma: allowlist secret
    ),
    'https://www.amazontrust.com/repository/AmazonRootCA2.pem': (
        'a3a7fe25439d9a9b50f60af43684444d798a4c869305bf615881e5c84a44c1a2'  # pragma: allowlist secret
    ),
    'https://www.amazontrust.com/repository/AmazonRootCA3.pem': (
        '3eb7c3258f4af9222033dc1bb3dd2c7cfa0982b98e39fb8e9dc095cfeb38126c'  # pragma: allowlist secret
    ),
    'https://www.amazontrust.com/repository/AmazonRootCA4.pem': (
        'b0b7961120481e33670315b2f843e643c42f693c7a1010eb9555e06ddc730214'  # pragma: allowlist secret
    ),
}

# PEM certificate delimiter used for counting certs in validation.
_CERT_MARKER = b'-----BEGIN CERTIFICATE-----'

# Minimum certificate count for an assembled bundle to be considered valid. The
# real bundle has ~112 (RDS global bundle ~108 + 4 Amazon roots), so this floor
# decisively rejects an empty / truncated / non-PEM file while leaving wide
# headroom for the RDS bundle to shrink as AWS retires regional CAs.
_MIN_CERTS_IN_BUNDLE = 10

# Where the combined bundle is written. Relative to the package root so the same
# path works in both the source tree (for local dev) and the built wheel.
_OUTPUT_PATH = os.path.join('awslabs', 'postgres_mcp_server', 'connection', 'aws_ca_bundle.pem')


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


class BundleIntegrityError(RuntimeError):
    """Raised when fetched bundle data fails an integrity check.

    Distinct from a network failure: an integrity failure (checksum mismatch,
    non-PEM data, too few certificates) means the bytes we got are wrong, so it
    is never masked by falling back to a pre-existing file -- the build fails
    loudly instead.
    """


def _count_certs(pem_bytes: bytes) -> int:
    """Return the number of PEM certificate blocks in ``pem_bytes``."""
    return pem_bytes.count(_CERT_MARKER)


def _is_valid_bundle(path: str) -> bool:
    """Return True if ``path`` holds a plausible CA bundle (enough PEM certs).

    A cheap structural check -- not full X.509 validation -- whose job is to
    reject an empty, truncated, or non-PEM file left at the output path, so such
    a file is never reused or shipped.
    """
    try:
        with open(path, 'rb') as fh:
            return _count_certs(fh.read()) >= _MIN_CERTS_IN_BUNDLE
    except OSError:
        return False


def _verify_source(url: str, chunk: bytes) -> None:
    """Validate a freshly-fetched source: PEM shape and, for roots, pinned hash.

    Raises:
        BundleIntegrityError: If the source returned no PEM certificate, or a
            pinned Amazon root's SHA-256 does not match.
    """
    if _count_certs(chunk) < 1:
        raise BundleIntegrityError(
            f'source did not return PEM certificate data: {url} '
            f'({len(chunk)} bytes) -- possibly a captive portal or error page'
        )
    pinned = _AMAZON_ROOT_CA_SHA256.get(url)
    if pinned is not None:
        actual = hashlib.sha256(chunk).hexdigest()
        if actual != pinned:
            raise BundleIntegrityError(
                f'SHA-256 mismatch for pinned root {url}: expected {pinned}, got {actual}. '
                'If AWS legitimately re-published this root, update _AMAZON_ROOT_CA_SHA256.'
            )


def _assemble_bundle(ctx) -> bytes:
    """Fetch every source, validate each, and return the combined PEM bytes.

    Raises:
        BundleIntegrityError: If a source or the assembled bundle fails validation.
        Exception: Network / URL errors from :func:`_fetch_url` propagate as-is
            (the caller distinguishes these from integrity errors).
    """
    chunks = []
    for url in _BUNDLE_SOURCE_URLS:
        chunk = _fetch_url(url, ctx)
        _verify_source(url, chunk)
        chunks.append(chunk)

    # Join with a newline so a source that does not end in one cannot glue two
    # PEM blocks together (``-----END-----\n-----BEGIN-----``).
    content = b'\n'.join(chunk.rstrip() + b'\n' for chunk in chunks)

    n = _count_certs(content)
    if n < _MIN_CERTS_IN_BUNDLE:
        raise BundleIntegrityError(
            f'assembled CA bundle has too few certificates ({n} < {_MIN_CERTS_IN_BUNDLE})'
        )
    return content


def _atomic_write(abs_path: str, content: bytes) -> None:
    """Write ``content`` to ``abs_path`` atomically (temp file + os.replace).

    A crash between the write and the replace leaves the original file (or no
    file) intact -- never a partially-written bundle at the real path.
    """
    directory = os.path.dirname(abs_path)
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.aws_ca_bundle.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, abs_path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            # Best-effort cleanup only: if unlink fails, preserve and re-raise
            # the original exception from the write/replace path.
            pass
        raise


def fetch(output_path: str = _OUTPUT_PATH, force_refresh: bool = False) -> str:
    """Assemble the combined AWS CA bundle and write it to disk.

    Concatenates the Amazon RDS global bundle (private CAs) with the public
    Amazon Trust Services root CAs, so the single file verifies both the
    private-CA (direct instance/cluster) and public-CA (ACM: RDS Proxy /
    Serverless) certificate families.

    The output is fetched fresh, integrity-checked, and written atomically. A
    pre-existing file is trusted only when ``force_refresh`` is False AND it
    passes validation (:func:`_is_valid_bundle`) -- so a stale/truncated file is
    never silently reused. When ``force_refresh`` is True (the release build
    hook) the bundle is always re-fetched; a valid pre-existing file is reused
    only as an offline fallback when the network fetch fails.

    Args:
        output_path: Destination path for the combined PEM.
        force_refresh: Always re-fetch rather than reuse a valid on-disk file.

    Returns:
        The absolute path to the written (or validated existing) file.

    Raises:
        BundleIntegrityError: A fetched source failed an integrity check.
        RuntimeError: The fetch failed and no valid existing file is available.
    """
    abs_path = os.path.abspath(output_path)
    have_valid_existing = _is_valid_bundle(abs_path)

    # Local dev / tests: reuse a valid on-disk bundle without a network call.
    # A missing or invalid file falls through to a fresh fetch.
    if not force_refresh and have_valid_existing:
        return abs_path

    ctx = _ssl_context_for_aws_endpoint()
    try:
        content = _assemble_bundle(ctx)
    except BundleIntegrityError:
        # Integrity failures are never masked by an old file -- fail loudly.
        raise
    except Exception as exc:
        # Network / fetch failure. Fall back to a valid existing file (keeps
        # offline builds working) but never accept a missing/corrupt one.
        if have_valid_existing:
            print(
                f'WARNING: could not fetch fresh AWS CA bundle ({exc}); '
                f'reusing the existing valid bundle at {abs_path}.',
                file=sys.stderr,
            )
            return abs_path
        raise RuntimeError(
            f'Failed to fetch the AWS CA bundle: {exc}\n\n'
            'Build machine needs HTTPS access to truststore.pki.rds.amazonaws.com '
            'and www.amazontrust.com.\n'
            'If the machine is offline, fetch each source manually on a connected '
            'host and concatenate them (in order) into:\n\n'
            f'    {abs_path}\n\n'
            'Sources (in order):\n'
            + '\n'.join(f'    {u}' for u in _BUNDLE_SOURCE_URLS)
            + '\n\nand rerun the build.'
        ) from exc

    _atomic_write(abs_path, content)
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
            """Assemble the bundle and force-include it in the wheel.

            Always re-fetches (``force_refresh=True``) so a release ships a
            fresh, integrity-checked trust store and never a stale/leftover file.
            """
            abs_path = fetch(force_refresh=True)
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
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Always re-fetch even if a valid bundle is already on disk.',
    )
    args = parser.parse_args(argv)
    path = fetch(force_refresh=args.force_refresh)
    print(f'Wrote AWS CA bundle to {path}')
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
