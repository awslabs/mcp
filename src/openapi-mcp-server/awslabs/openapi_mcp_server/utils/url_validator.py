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
"""URL and path validation to prevent SSRF and path traversal.

Leverages fastmcp.server.auth.ssrf for DNS resolution and IP validation,
extending it with HTTP scheme support and file path restrictions.
"""

import os
from fastmcp.server.auth.ssrf import (
    SSRFError,
    ValidatedURL,
    is_ip_allowed,
    resolve_hostname,
)
from pathlib import Path
from typing import List, Optional, Set
from urllib.parse import urlparse


ALLOWED_SPEC_EXTENSIONS: Set[str] = {'.json', '.yaml', '.yml'}


async def validate_url_for_spec(
    url: str,
    *,
    allow_http: bool = False,
    allow_private_networks: bool = False,
) -> ValidatedURL:
    """Validate a URL for safe server-side fetching of OpenAPI specs.

    Performs DNS resolution and IP validation to prevent SSRF attacks.
    By default, only HTTPS is allowed and private/internal IPs are blocked.

    Args:
        url: URL to validate.
        allow_http: If True, permit http:// scheme in addition to https://.
        allow_private_networks: If True, permit private/loopback/link-local IPs.

    Returns:
        ValidatedURL with resolved IPs suitable for DNS-pinned connections.

    Raises:
        SSRFError: If the URL fails validation.

    """
    try:
        parsed = urlparse(url)
    except (ValueError, AttributeError) as e:
        raise SSRFError(f'Invalid URL: {e}') from e

    allowed_schemes = {'https', 'http'} if allow_http else {'https'}
    if parsed.scheme not in allowed_schemes:
        raise SSRFError(f"URL scheme '{parsed.scheme}' not allowed. Allowed: {allowed_schemes}")

    if not parsed.netloc:
        raise SSRFError('URL must have a host')

    hostname = parsed.hostname or parsed.netloc
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)

    try:
        resolved_ips = await resolve_hostname(hostname, port)
    except SSRFError:
        raise
    except (OSError, UnicodeError) as e:
        raise SSRFError(f'DNS resolution failed for {hostname}: {e}') from e

    if not allow_private_networks:
        blocked = [ip for ip in resolved_ips if not is_ip_allowed(ip)]
        if blocked:
            raise SSRFError(
                f'URL resolves to blocked IP address(es): {blocked}. '
                f'Private, loopback, link-local, and reserved IPs are not allowed. '
                f'Use --allow-private-networks to override.'
            )

    return ValidatedURL(
        original_url=url,
        hostname=hostname,
        port=port,
        path=parsed.path + ('?' + parsed.query if parsed.query else ''),
        resolved_ips=resolved_ips,
    )


def validate_spec_path(
    path: str,
    *,
    allowed_dirs: Optional[List[str]] = None,
) -> str:
    """Validate a file path is safe to read as an OpenAPI spec.

    Resolves symlinks and traversal sequences, then checks the canonical
    path against allowed directories and file extensions.

    Args:
        path: File path to validate.
        allowed_dirs: If provided, path must be within one of these directories.
            If None, only blocks known sensitive system paths.

    Returns:
        The resolved canonical path as a string.

    Raises:
        SSRFError: If the path targets a blocked or disallowed location.
        FileNotFoundError: If the resolved path does not exist.

    """
    resolved = Path(path).resolve()

    if resolved.suffix.lower() not in ALLOWED_SPEC_EXTENSIONS:
        raise SSRFError(
            f'spec_path must point to a spec file ({", ".join(ALLOWED_SPEC_EXTENSIONS)}), '
            f'got: {resolved.suffix}'
        )

    if allowed_dirs is not None:
        resolved_str = str(resolved)
        allowed_resolved = [str(Path(d).resolve()) for d in allowed_dirs]
        if not any(
            resolved_str == d or resolved_str.startswith(d + os.sep) for d in allowed_resolved
        ):
            raise SSRFError(f'Path {resolved} is not within allowed directories: {allowed_dirs}')
    else:
        resolved_str = str(resolved)
        if os.name == 'nt':
            # Windows sensitive directories
            blocked_prefixes = [
                os.environ.get('SYSTEMROOT', r'C:\Windows') + os.sep,
                os.environ.get('SYSTEMROOT', r'C:\Windows') + r'\System32' + os.sep,
                os.path.expanduser('~') + os.sep,
            ]
        else:
            # POSIX sensitive directories
            blocked_prefixes = ['/etc/', '/root/', '/proc/', '/sys/', '/var/run/']
        for prefix in blocked_prefixes:
            if resolved_str.startswith(prefix) or resolved_str.rstrip(os.sep) == prefix.rstrip(
                os.sep
            ):
                raise SSRFError(f'Path resolves to blocked location: {resolved}')

    if not resolved.exists():
        raise FileNotFoundError(f'File not found: {resolved}')

    return str(resolved)
