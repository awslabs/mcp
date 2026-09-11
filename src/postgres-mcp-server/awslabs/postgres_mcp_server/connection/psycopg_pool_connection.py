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

"""Psycopg connector for postgres MCP Server.

This connector provides direct connection to PostgreSQL databases using psycopg.
It supports both Aurora PostgreSQL and RDS PostgreSQL instances via direct connection
parameters (host, port, database, user, password) or via AWS Secrets Manager.
"""

import asyncio
import boto3
import json
import os
from aiorwlock import RWLock
from awslabs.postgres_mcp_server import __user_agent__
from awslabs.postgres_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from awslabs.postgres_mcp_server.named_params import to_psycopg_placeholders
from botocore.config import Config
from datetime import datetime, timedelta
from loguru import logger
from psycopg.conninfo import make_conninfo
from psycopg_pool import AsyncConnectionPool
from typing import Any, Dict, List, Optional, Tuple


# Path to the combined AWS CA bundle shipped inside the wheel by hatch_build.py.
# It contains BOTH families of CA that Aurora/RDS PostgreSQL endpoints present:
# the Amazon RDS private CAs (rds-ca-*-g1, used by direct instance/cluster
# endpoints) and the public Amazon Trust Services roots (Amazon Root CA 1..4,
# used by ACM-issued certs on RDS Proxy / Aurora Serverless v1). This lets the
# psycopg (PG Wire) path verify the server certificate against any of them out
# of the box. The PEM is gitignored and assembled at build time; operators can
# override it at runtime with --ca_bundle (e.g. self-hosted PostgreSQL with a
# private CA).
_AWS_CA_BUNDLE_PATH = os.path.join(os.path.dirname(__file__), 'aws_ca_bundle.pem')

# Permitted libpq sslmode values. Deliberately restricted to modes that
# guarantee the connection is encrypted -- ``disable``/``allow``/``prefer`` are
# excluded so credentials (IAM token / Secrets Manager password) are never sent
# in cleartext. Within this set the operator tunes certificate validation:
#   require      -> encrypt only; do NOT validate the server certificate
#   verify-ca    -> encrypt + validate the cert chains to a trusted CA (no host)
#   verify-full  -> encrypt + validate CA chain AND hostname (most strict)
#
# The default is ``verify-full``, matching AWS's production guidance: the
# connection is encrypted (closing the reported cleartext-credential gap) and
# both the CA chain and the hostname are verified. The bundled combined CA
# covers both the RDS private CAs and the public Amazon roots, and Aurora/RDS
# server certificates carry the endpoint in their CN/SAN, so verify-full
# connects to direct instances, cluster endpoints, and RDS Proxy alike.
# Operators connecting via an IP/tunnel/CNAME that won't match the certificate
# can opt down to ``verify-ca`` (skip hostname) or ``require`` (skip verification).
DEFAULT_SSLMODE = 'verify-full'
ALLOWED_SSLMODES = ('require', 'verify-ca', 'verify-full')
# The modes that verify the server certificate and therefore need a CA
# (sslrootcert). ``require`` performs no verification, so no CA is attached.
_CA_VERIFYING_SSLMODES = frozenset({'verify-ca', 'verify-full'})
# Sentinel accepted for --ca_bundle to select libpq's system trust store.
_SYSTEM_TRUST_STORE = 'system'

# libpq only recognizes the special ``sslrootcert=system`` value from v16. On
# older libpq it is treated as a *filename*, so it fails with a misleading
# 'could not open certificate file "system"'. Guard the sentinel on this.
_MIN_LIBPQ_VERSION_FOR_SYSTEM = 160000


def _bundled_ca_file() -> Optional[str]:
    """Return the bundled AWS CA path if present on disk, else None.

    Returns None (with a logged error) if the bundle is missing -- the package
    was built without the hook, or is running from a source tree where
    ``python hatch_build.py`` has not been run. The caller fails closed rather
    than silently falling back to the system trust store, which cannot verify
    the RDS private CAs that direct Aurora/RDS endpoints present.
    """
    if not os.path.isfile(_AWS_CA_BUNDLE_PATH):
        logger.error(
            f'Bundled AWS CA bundle is missing at {_AWS_CA_BUNDLE_PATH}. The build '
            'hook should assemble it during package build; rebuild the package, run '
            '`python hatch_build.py`, or pass --ca_bundle <path> to override.'
        )
        return None
    return _AWS_CA_BUNDLE_PATH


def _assert_system_trust_store_supported() -> None:
    """Raise if the loaded libpq is too old to understand ``sslrootcert=system``.

    Fails fast with an actionable message instead of letting libpq < 16 treat
    ``system`` as a filename and emit a phantom
    'could not open certificate file "system"'.
    """
    from psycopg import pq

    version = pq.version()
    if version < _MIN_LIBPQ_VERSION_FOR_SYSTEM:
        raise ValueError(
            f'sslrootcert=system requires libpq 16+, but the loaded libpq is {version}. '
            'Pass --ca_bundle <path> to an explicit CA PEM file, or use a build with '
            'libpq >= 16 (e.g. psycopg[binary]).'
        )


# Substrings of the TLS failures an operator can resolve with a flag. libpq
# surfaces these as ordinary connection errors, so without a hint the operator
# sees only raw OpenSSL/libpq text and no signal that --sslmode / --ca_bundle
# exist. Because the default is verify-full, the hostname case in particular is
# the expected outcome for an IP, tunnel, or CNAME endpoint that previously
# connected under libpq's unverified 'prefer' default.
_TLS_HOSTNAME_MARKERS = (
    'does not match host name',
    'does not match certificate',
)
_TLS_UNTRUSTED_MARKERS = (
    'certificate verify failed',
    'unable to get local issuer certificate',
    'self-signed certificate',
    'self signed certificate',
)
_TLS_CA_FILE_MARKERS = (
    'root certificate file',
    'could not open certificate file',
)
# Bound the exception-chain walk; a conninfo failure nests only a few levels and
# a cycle would otherwise be possible via __context__.
_MAX_EXC_CHAIN_DEPTH = 8


def _exception_chain_text(exc: BaseException) -> str:
    """Return the lower-cased text of ``exc`` and its causes, for marker matching.

    libpq's TLS detail is often on a wrapped cause rather than the outermost
    exception, so matching only ``str(exc)`` misses it.

    Args:
        exc: The exception to flatten.

    Returns:
        str: Lower-cased concatenation of the chain's messages.
    """
    parts: List[str] = []
    seen: set[int] = set()
    current: Optional[BaseException] = exc
    while current is not None and len(parts) < _MAX_EXC_CHAIN_DEPTH:
        if id(current) in seen:
            break
        seen.add(id(current))
        parts.append(str(current))
        current = current.__cause__ or current.__context__
    return ' '.join(parts).lower()


def _tls_remediation_hint(exc: BaseException, sslmode: str) -> Optional[str]:
    """Return operator remediation for a fixable TLS failure, else None.

    Only certificate *verification* failures are actionable via a flag, so this
    returns None for ``require`` (which verifies nothing) and for any error whose
    text carries no TLS marker -- an unreachable host or a bad password must not
    be answered with "relax your TLS settings".

    Args:
        exc: The exception raised while opening the pool.
        sslmode: The libpq sslmode in effect for this connection.

    Returns:
        Optional[str]: A remediation message, or None when not TLS-related.
    """
    if sslmode not in _CA_VERIFYING_SSLMODES:
        return None

    text = _exception_chain_text(exc)

    if any(marker in text for marker in _TLS_HOSTNAME_MARKERS):
        return (
            f'TLS hostname verification failed (sslmode={sslmode}): the server certificate '
            'does not cover the name being connected to. This is expected when connecting '
            'via an IP address, an SSH tunnel or port-forward, or a CNAME that differs from '
            'the endpoint on the certificate. Pass --sslmode=verify-ca to keep '
            'certificate-chain verification without the hostname check. The connection stays '
            'encrypted in every supported mode.'
        )

    if any(marker in text for marker in _TLS_UNTRUSTED_MARKERS):
        return (
            f'TLS certificate verification failed (sslmode={sslmode}): the server '
            'certificate could not be chained to a trusted CA. Pass --ca_bundle <path> to a '
            'PEM containing the issuing CA (self-hosted PostgreSQL or a private trust '
            'store), or --ca_bundle system to use the OS trust store (libpq 16+). '
            '--sslmode=require keeps the connection encrypted but skips certificate '
            'verification entirely; prefer supplying the correct CA.'
        )

    if any(marker in text for marker in _TLS_CA_FILE_MARKERS):
        return (
            f'TLS verification could not read the configured CA file (sslmode={sslmode}). '
            'Check the --ca_bundle path, or pass --ca_bundle system to use the OS trust '
            'store (libpq 16+).'
        )

    return None


def get_credentials_from_secret(
    secret_arn: str, region: str, is_test: bool = False
) -> Tuple[str, str]:
    """Fetch database (username, password) from AWS Secrets Manager.

    The secret payload is expected to be JSON with ``username``/``user``/
    ``Username`` and ``password``/``Password`` fields — the standard shape
    RDS-managed secrets produce.

    Module-level so callers (e.g. ``server.internal_create_connection``
    on the IAM-auth path, which only needs the username) can reuse it
    without instantiating a connection pool.

    Args:
        secret_arn: Secrets Manager ARN.
        region: AWS region of the secret.
        is_test: If True, return deterministic test credentials instead of
            hitting AWS. Intended for unit tests only.

    Returns:
        ``(username, password)`` tuple.

    Raises:
        ValueError: If the secret is missing, malformed, or lacks
            username/password fields.
    """
    if is_test:
        return 'test_user', 'test_password'

    try:
        logger.debug(f'Creating Secrets Manager client in region {region}')
        session = boto3.Session()
        client = session.client(service_name='secretsmanager', region_name=region)

        logger.debug(f'Retrieving secret value for {secret_arn}')
        get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
        logger.debug('Successfully retrieved secret value')

        if 'SecretString' not in get_secret_value_response:
            logger.error('Secret does not contain a SecretString')
            raise ValueError('Secret does not contain a SecretString')

        secret = json.loads(get_secret_value_response['SecretString'])
        logger.debug(f'Secret keys: {", ".join(secret.keys())}')

        username = secret.get('username') or secret.get('user') or secret.get('Username')
        password = secret.get('password') or secret.get('Password')

        if not username:
            logger.error(
                f'Username not found in secret. Available keys: {", ".join(secret.keys())}'
            )
            raise ValueError(
                f'Secret does not contain username. Available keys: {", ".join(secret.keys())}'
            )

        if not password:
            logger.error('Password not found in secret')
            raise ValueError(
                f'Secret does not contain password. Available keys: {", ".join(secret.keys())}'
            )

        logger.debug(f'Successfully extracted credentials for user: {username}')
        return username, password
    except Exception as e:
        logger.exception(f'Failed to retrieve credentials from Secrets Manager: {str(e)}')
        raise ValueError(f'Failed to retrieve credentials from Secrets Manager: {str(e)}')


class PsycopgPoolConnection(AbstractDBConnection):
    """Class that wraps DB connection using psycopg connection pool.

    This class can connect directly to any PostgreSQL database, including:
    - Aurora PostgreSQL (using the cluster endpoint)
    - RDS PostgreSQL (using the instance endpoint)
    - Self-hosted PostgreSQL

    It uses AWS Secrets Manager (secret_arn and region) for authentication.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        readonly: bool,
        secret_arn: str,
        db_user: str,
        region: str,
        is_iam_auth: bool = False,
        pool_expiry_min: int = 30,
        min_size: int = 1,
        max_size: int = 10,
        is_test: bool = False,
        ca_bundle_path: Optional[str] = None,
        sslmode: str = DEFAULT_SSLMODE,
    ):
        """Initialize a new DB connection pool.

        Args:
            host: Database host (Aurora cluster endpoint or RDS instance endpoint)
            port: Database port
            database: Database name
            readonly: Whether connections should be read-only
            secret_arn: ARN of the secret containing credentials
            db_user: Database username
            region: AWS region for Secrets Manager
            is_iam_auth: Whether to use IAM authentication
            pool_expiry_min: Pool expiry time in minutes
            min_size: Minimum number of connections in the pool
            max_size: Maximum number of connections in the pool
            is_test: Whether this is a test connection
            ca_bundle_path: Optional path to an alternate CA bundle (PEM) used for
                certificate verification, overriding the bundled AWS CA bundle.
                The sentinel ``'system'`` selects libpq's system trust store.
            sslmode: libpq SSL mode; one of ALLOWED_SSLMODES (default verify-full).
                The connection is always encrypted; this tunes certificate
                verification.
        """
        super().__init__(readonly)
        self.host = host
        self.port = port
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.region = region
        self.is_iam_auth = is_iam_auth
        self.user = db_user
        self.pool_expiry_min = pool_expiry_min
        self.secret_arn = secret_arn
        self.is_test = is_test
        self.ca_bundle_path = ca_bundle_path
        self.sslmode = sslmode
        self.pool: Optional['AsyncConnectionPool[Any]'] = None
        self.rw_lock = RWLock()
        self.created_time = datetime.now()

        if is_iam_auth:
            # if db_user is set, then it is IAM auth scenario and iam_auth_token must be set
            if not db_user:
                raise ValueError('db_user must be set when is_iam_auth is True')

            # set pool expiry before IAM auth token expiry of 15 minutes
            self.pool_expiry_min = 14
            logger.debug(f'Use IAM auth for user: {db_user}')

    def _build_conninfo(self, password: str) -> str:
        """Build the libpq conninfo string, always encrypting the connection.

        Credentials always go on the wire for this connector (an IAM auth token
        or a Secrets Manager password), so the connection is always encrypted:
        ``sslmode`` is restricted to ALLOWED_SSLMODES (no plaintext fallback).
        The operator tunes *certificate verification* via ``sslmode``:

          * ``require``     -- encrypt only; the server certificate is not
            verified, so no CA is attached.
          * ``verify-ca``   -- verify the certificate chains to a trusted CA
            (hostname not checked).
          * ``verify-full`` -- verify the CA chain and the hostname (default).

        For the verifying modes the trust anchor (sslrootcert) is chosen as:

          1. ``--ca_bundle`` override, if supplied (a PEM path, or the sentinel
             ``'system'`` for the OS trust store; ``'system'`` requires libpq
             >= 16), else
          2. the bundled combined AWS CA bundle shipped in the wheel (RDS private
             CAs + public Amazon roots), else
          3. fail fast with a remediation message. There is deliberately no
             silent fallback to the system trust store: it does not contain the
             RDS private CAs that direct Aurora/RDS endpoints present, so it
             would guarantee a connection failure disguised as a soft degrade.

        ``make_conninfo`` escapes values, so passwords containing spaces or
        special characters are handled correctly.

        Raises:
            ValueError: if ``sslmode`` is unsupported, if a verifying mode has no
                usable CA (missing bundle and no override), or if ``--ca_bundle
                system`` is selected on libpq < 16.
        """
        if self.sslmode not in ALLOWED_SSLMODES:
            # Fail closed: never silently fall through to an insecure mode.
            raise ValueError(
                f'Unsupported sslmode {self.sslmode!r}; allowed: {", ".join(ALLOWED_SSLMODES)}'
            )

        params: Dict[str, Any] = {
            'host': self.host,
            'port': self.port,
            'dbname': self.database,
            'user': self.user,
            'password': password,
            'sslmode': self.sslmode,
        }

        # Attach a CA only for the modes that actually verify the certificate.
        # ``require`` performs no verification, so sslrootcert is irrelevant.
        if self.sslmode in _CA_VERIFYING_SSLMODES:
            if self.ca_bundle_path == _SYSTEM_TRUST_STORE:
                # Operator explicitly chose the OS trust store. Gate on libpq
                # version so a pre-16 build fails with a real message instead of
                # a phantom 'could not open certificate file "system"'.
                _assert_system_trust_store_supported()
                params['sslrootcert'] = _SYSTEM_TRUST_STORE
            elif self.ca_bundle_path:
                params['sslrootcert'] = self.ca_bundle_path
            else:
                cafile = _bundled_ca_file()
                if cafile:
                    params['sslrootcert'] = cafile
                else:
                    # Fail fast. The primary topology (direct Aurora/RDS instance
                    # and cluster endpoints) presents the Amazon RDS private CAs
                    # (rds-ca-*-g1), which are NOT in any OS trust store -- that
                    # is exactly why the build hook assembles a combined bundle.
                    # Silently using the system store here is a guaranteed
                    # connection failure dressed up as a soft degrade: libpq >= 16
                    # fails every query with CERTIFICATE_VERIFY_FAILED, and
                    # libpq < 16 reports a phantom missing file "system". Raise now
                    # with the remediation instead of deferring to that per-query
                    # error.
                    raise ValueError(
                        f'No CA bundle available for TLS verification (sslmode={self.sslmode}) '
                        f'and no --ca_bundle override supplied. The bundled Amazon RDS CA is '
                        f'missing at {_AWS_CA_BUNDLE_PATH}. Reinstall the built wheel (which '
                        'ships the bundle), run `python hatch_build.py` in a source checkout, '
                        'or pass --ca_bundle <path> to an explicit CA PEM. Use --ca_bundle '
                        'system only for ACM/public-CA endpoints (e.g. RDS Proxy); it cannot '
                        'verify direct instance/cluster endpoints.'
                    )
        return make_conninfo(**params)

    def _log_tls_posture(self) -> None:
        """Log the TLS validation posture and auth mode for this connection.

        Emitted at pool initialization *before* the pool is opened, so the
        record is present in the logs even when the connection subsequently
        fails with an SSL or authentication error -- it answers "what SSL
        validation and auth were we attempting?" for troubleshooting. The
        password/IAM token is never logged; only the sslmode and the resolved
        trust anchor (sslrootcert) are surfaced.
        """
        from psycopg.conninfo import conninfo_to_dict

        try:
            info = conninfo_to_dict(self.conninfo)
        except Exception:
            info = {}
        sslmode = info.get('sslmode', self.sslmode)
        sslrootcert = info.get('sslrootcert')
        if self.sslmode == 'require':
            trust = 'none (require: certificate not verified)'
        elif sslrootcert == _SYSTEM_TRUST_STORE:
            trust = 'system trust store'
        elif sslrootcert == _AWS_CA_BUNDLE_PATH:
            trust = f'bundled AWS CA (RDS private + public Amazon roots): {sslrootcert}'
        elif sslrootcert:
            trust = f'operator-supplied CA: {sslrootcert}'
        else:
            trust = '(none)'
        logger.info(
            f'TLS posture: sslmode={sslmode}, trust_anchor={trust}, '
            f'auth={"iam" if self.is_iam_auth else "secrets_manager"}, '
            f'user={self.user}, endpoint={self.host}:{self.port}, db={self.database}'
        )

    async def initialize_pool(self):
        """Initialize the connection pool."""
        async with self.rw_lock.reader_lock:
            if self.pool is not None:
                return

        async with self.rw_lock.writer_lock:
            if self.pool is not None:
                return

            logger.debug(
                f'initialize_pool:\n'
                f'endpoint:{self.host}\n'
                f'port:{self.port}\n'
                f'region:{self.region}\n'
                f'db:{self.database}\n'
                f'user:{self.user}\n'
                f'is_iam_auth:{self.is_iam_auth}\n'
            )

            # These are synchronous boto3 HTTP calls. Run them in a worker thread
            # so a credential refresh (triggered every ``pool_expiry_min`` minutes
            # by ``check_expiry``) does not block the event loop and stall the MCP
            # stdio transport while the AWS round-trip is in flight.
            if self.is_iam_auth:
                logger.debug(f'Retrieving IAM auth token for {self.user}')
                password = await asyncio.to_thread(self.get_iam_auth_token)
            else:
                logger.debug(f'Retrieving credentials from Secrets Manager: {self.secret_arn}')
                self.user, password = await asyncio.to_thread(
                    self._get_credentials_from_secret,
                    self.secret_arn,
                    self.region,
                    self.is_test,
                )

            self.created_time = datetime.now()
            self.conninfo = self._build_conninfo(password)
            self._log_tls_posture()
            self.pool = AsyncConnectionPool(
                self.conninfo, min_size=self.min_size, max_size=self.max_size, open=False
            )

            # wait up to 30 seconds to fill the pool with connections
            try:
                await self.pool.open(True, 30)
            except Exception as e:
                # Pool failed to open — psycopg marks it as closed internally.
                # Set self.pool to None so callers don't try to use a closed pool.
                logger.exception('Failed to open connection pool')
                # A TLS verification failure is fixable by a flag, unlike an
                # unreachable host, so surface the remediation instead of leaving
                # the operator with raw OpenSSL text. Logged, not raised: the
                # original exception's type and traceback are preserved for
                # callers (and psycopg_pool's own semantics) untouched.
                tls_hint = _tls_remediation_hint(e, self.sslmode)
                if tls_hint:
                    logger.error(tls_hint)
                self.pool = None
                raise
            pool_name = getattr(self.pool, 'name', 'unknown')
            logger.info(
                f'Connection pool {pool_name} initialized at {self.created_time.isoformat()}, '
                f'host={self.host}, db={self.database}, is_iam={self.is_iam_auth}, '
                f'expiry_min={self.pool_expiry_min}'
            )

    async def _get_connection(self):
        """Get a database connection from the pool."""
        await self.check_expiry()

        async with self.rw_lock.reader_lock:
            if self.pool is None:
                raise ValueError('Failed to initialize connection pool')
            return self.pool.connection(timeout=15.0)

    async def check_expiry(self):
        """Check and handle pool expiry."""
        async with self.rw_lock.reader_lock:
            if self.pool and datetime.now() - self.created_time < timedelta(
                minutes=self.pool_expiry_min
            ):
                return

        pool_name = getattr(self.pool, 'name', 'None') if self.pool else 'None'
        age_seconds = (datetime.now() - self.created_time).total_seconds()
        logger.debug(
            f'check_expiry: pool {pool_name} expired or None. '
            f'age={age_seconds:.1f}s, expiry={self.pool_expiry_min * 60}s, '
            f'host={self.host}, db={self.database}'
        )
        await self.close()
        await self.initialize_pool()

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query using async connection."""
        try:
            async with await self._get_connection() as conn:
                async with conn.transaction():
                    if self.readonly_query:
                        logger.debug('SET TRANSACTION READ ONLY')
                        await conn.execute('SET TRANSACTION READ ONLY')

                    # Create a cursor for better control
                    async with conn.cursor() as cursor:
                        # Execute the query
                        if parameters:
                            converted_sql = self._convert_sql_for_psycopg(sql)
                            converted_params = self._convert_parameters(parameters)
                            await cursor.execute(converted_sql, converted_params)
                        else:
                            await cursor.execute(sql)

                        # Check if there are results to fetch by examining the cursor's description
                        if cursor.description:
                            # Get column names
                            columns = [desc[0] for desc in cursor.description]

                            # Fetch all rows
                            rows = await cursor.fetchall()

                            # Structure the response to match the interface contract required by server.py
                            column_metadata = [{'name': col} for col in columns]
                            records = []

                            # Convert each row to the expected format
                            for row in rows:
                                record = []
                                for value in row:
                                    if value is None:
                                        record.append({'isNull': True})
                                    elif isinstance(value, str):
                                        record.append({'stringValue': value})
                                    elif isinstance(value, bool):
                                        record.append({'booleanValue': value})
                                    elif isinstance(value, int):
                                        record.append({'longValue': value})
                                    elif isinstance(value, float):
                                        record.append({'doubleValue': value})
                                    elif isinstance(value, bytes):
                                        record.append({'blobValue': value})
                                    else:
                                        # Convert other types to string
                                        record.append({'stringValue': str(value)})
                                records.append(record)

                            return {'columnMetadata': column_metadata, 'records': records}
                        else:
                            # No results (e.g., for INSERT, UPDATE, etc.)
                            return {'columnMetadata': [], 'records': []}

        except Exception as e:
            logger.exception(f'Database connection error: {str(e)}')
            raise

    def _convert_parameters(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform structured parameter format to psycopg's native parameter format."""
        result = {}
        for param in parameters:
            name = param.get('name')
            value = param.get('value', {})

            # Extract the value based on its type
            if 'stringValue' in value:
                result[name] = value['stringValue']
            elif 'longValue' in value:
                result[name] = value['longValue']
            elif 'doubleValue' in value:
                result[name] = value['doubleValue']
            elif 'booleanValue' in value:
                result[name] = value['booleanValue']
            elif 'blobValue' in value:
                result[name] = value['blobValue']
            elif 'isNull' in value and value['isNull']:
                result[name] = None

        return result

    def _convert_sql_for_psycopg(self, sql: str) -> str:
        """Convert Aurora-style :name placeholders to psycopg %(name)s style.

        Delegates the *matching* rule to :mod:`named_params`, which the SQL policy
        guard uses as well. Both layers must treat the same colons as
        placeholders: when this method had its own looser rule it rewrote the
        array slice in ``SELECT tags[1:limit_idx] FROM items`` -- which the guard
        correctly leaves alone -- into the unparseable
        ``SELECT tags[1%(limit_idx)s] FROM items``, failing a query the guard had
        already approved.

        Examples:
            :table_name         →  %(table_name)s
            column::text        →  column::text            (cast unchanged)
            tags[1:limit_idx]   →  tags[1:limit_idx]       (array slice unchanged)
        """
        return to_psycopg_placeholders(sql)

    def _get_credentials_from_secret(
        self, secret_arn: str, region: str, is_test: bool = False
    ) -> Tuple[str, str]:
        """Get database credentials from AWS Secrets Manager.

        Instance-method wrapper around the module-level
        :func:`get_credentials_from_secret` helper, kept for backward
        compatibility with existing tests.
        """
        return get_credentials_from_secret(secret_arn, region, is_test)

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self.rw_lock.writer_lock:
            if self.pool is not None:
                pool_name = getattr(self.pool, 'name', 'unknown')
                logger.info(f'Closing connection pool {pool_name} at {datetime.now().isoformat()}')
                await self.pool.close()
                self.pool = None
                logger.info(f'Connection pool {pool_name} closed successfully')

    async def check_connection_health(self) -> bool:
        """Check if the connection is healthy."""
        try:
            result = await self.execute_query('SELECT 1')
            return len(result.get('records', [])) > 0
        except Exception as e:
            logger.exception(f'Connection health check failed: {str(e)}')
            return False

    async def get_pool_stats(self) -> Dict[str, int]:
        """Get current connection pool statistics."""
        async with self.rw_lock.reader_lock:
            if not hasattr(self, 'pool') or self.pool is None:
                return {'size': 0, 'min_size': self.min_size, 'max_size': self.max_size, 'idle': 0}

            # Access pool attributes safely
            size = getattr(self.pool, 'size', 0)
            min_size = getattr(self.pool, 'min_size', self.min_size)
            max_size = getattr(self.pool, 'max_size', self.max_size)
            idle = getattr(self.pool, 'idle', 0)

            return {'size': size, 'min_size': min_size, 'max_size': max_size, 'idle': idle}

    def get_iam_auth_token(self) -> str:
        """Generate an IAM authentication token for RDS database access."""
        rds_client = boto3.client(
            'rds', region_name=self.region, config=Config(user_agent_extra=__user_agent__)
        )
        return rds_client.generate_db_auth_token(
            DBHostname=self.host, Port=self.port, DBUsername=self.user, Region=self.region
        )
