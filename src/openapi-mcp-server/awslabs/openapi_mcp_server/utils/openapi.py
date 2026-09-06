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
"""Utilities for working with OpenAPI specifications."""

import asyncio
import httpx
import json
import tempfile
import time
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.utils.cache_provider import cached
from awslabs.openapi_mcp_server.utils.openapi_validator import validate_openapi_spec
from fastmcp.server.auth.ssrf import (
    SSRFError,
    SSRFFetchError,
    ValidatedURL,
    format_ip_for_url,
)
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


# Upper bound on a fetched spec body. The old loader read response bodies
# unbounded; a 10 MiB cap comfortably fits real-world OpenAPI documents while
# preventing a hostile endpoint from exhausting memory.
MAX_SPEC_BYTES = 10 * 1024 * 1024


def extract_api_name_from_spec(spec: Dict[str, Any]) -> Optional[str]:
    """Extract the API name from an OpenAPI specification.

    Args:
        spec: The OpenAPI specification dictionary

    Returns:
        Optional[str]: The API name extracted from the specification, or None if not found

    """
    if not spec or not isinstance(spec, dict):
        logger.warning('Invalid OpenAPI spec format')
        return None

    # Extract from info.title
    if 'info' in spec and isinstance(spec['info'], dict) and 'title' in spec['info']:
        return spec['info']['title']

    logger.debug('No API name found in OpenAPI spec')
    return None


# Import yaml conditionally to avoid errors if it's not installed
try:
    import yaml
except ImportError:
    yaml = None  # type: Optional[Any]


# Try to import prance, but don't fail if it's not installed
try:
    from prance import ResolvingParser
    from prance.util.resolver import RESOLVE_INTERNAL

    PRANCE_AVAILABLE = True
except ImportError:
    PRANCE_AVAILABLE = False
    logger.warning('Prance library not found. Reference resolution will be limited.')


def _reject_external_refs(node: Any) -> None:
    """Reject any non-internal ``$ref`` before the spec reaches prance.

    prance's default resolver (and its validation backend) dereferences
    ``http(s)://`` and ``file://`` ``$ref`` targets using its own fetcher, which
    bypasses the DNS-pinned, SSRF-validated fetch used for the root document.
    A hostile spec served from a validation-passing host could therefore embed a
    ``$ref`` pointing at internal services or cloud metadata (SSRF) or a local
    file (LFI) and exfiltrate the resolved content. We refuse to resolve any
    reference that is not a local, in-document reference (i.e. one that does not
    start with ``#``), so no external network or filesystem access is ever
    triggered by reference resolution.

    Args:
        node: A parsed spec fragment (dict, list, or scalar) to walk recursively.

    Raises:
        SSRFError: If an external (non-``#``) ``$ref`` is present anywhere.

    """
    if isinstance(node, dict):
        ref = node.get('$ref')
        if isinstance(ref, str) and not ref.startswith('#'):
            raise SSRFError(
                f'Refusing to resolve external $ref {ref!r} in OpenAPI spec; only '
                'internal references (starting with "#") are allowed. External '
                'http(s)://, file://, and relative-path references are blocked to '
                'prevent SSRF and local file disclosure.'
            )
        for value in node.values():
            _reject_external_refs(value)
    elif isinstance(node, list):
        for item in node:
            _reject_external_refs(item)


def _basic_parse(content: bytes) -> Any:
    """Parse spec bytes as JSON, then YAML, without resolving any references.

    Returns whatever the parser produces — normally a ``dict`` for an OpenAPI
    document, but JSON/YAML may legally yield a list, scalar, or ``None``; the
    caller (``_reject_external_refs``) handles any node type.

    YAML is parsed with PyYAML when installed, then with ``ruamel-yaml`` (a
    ``prance`` dependency) as a fallback. The ruamel fallback matters for the
    external-``$ref`` prescan: ``prance`` parses YAML via ``ruamel-yaml``, which
    accepts inputs PyYAML rejects (e.g. a tab after a mapping key). Without also
    trying ruamel when PyYAML *fails*, such a document would be treated as
    unparseable here, skip ``_reject_external_refs``, yet still be parsed and
    ``$ref``-resolved by ``prance`` — silently re-opening the SSRF/LFI bypass. So
    the prescan must never parse *less* than prance would.
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError as json_err:
        # Try PyYAML first when present, but fall back to ruamel-yaml if PyYAML
        # is absent OR rejects the document, so the prescan parses whatever
        # prance (which uses ruamel) would. Only surface a parse error when no
        # available YAML parser can read the content.
        if yaml is not None:
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError:
                pass
        try:
            import io
            from ruamel.yaml import YAML
        except ImportError:
            raise json_err
        return YAML(typ='safe').load(io.BytesIO(content))


def _validate_url_sync(
    url: str,
    *,
    allow_http: bool,
    allow_private_networks: bool,
) -> ValidatedURL:
    """Validate + DNS-pin a spec URL from synchronous code.

    ``validate_url_for_spec`` is async, but ``load_openapi_spec`` is synchronous
    and may be invoked either from a plain sync context or from within an
    already-running event loop (e.g. ``create_mcp_server_async``). Calling
    ``asyncio.run`` inside a running loop raises ``RuntimeError``; when a loop is
    already running we drive the coroutine to completion on a short-lived worker
    thread instead of touching the live loop.
    """
    # Imported lazily to avoid a module import cycle at load time.
    from awslabs.openapi_mcp_server.utils.url_validator import validate_url_for_spec

    async def _run() -> ValidatedURL:
        return await validate_url_for_spec(
            url,
            allow_http=allow_http,
            allow_private_networks=allow_private_networks,
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop in this thread: safe to drive one directly.
        return asyncio.run(_run())

    # A loop is already running here; run the coroutine on a separate thread.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(_run())).result()


def _pinned_fetch(
    validated_url: ValidatedURL,
    *,
    allow_http: bool,
    max_size: int = MAX_SPEC_BYTES,
    timeout: float = 10.0,
) -> bytes:
    """Fetch a spec body, connecting ONLY to the IPs validation already pinned.

    This mirrors fastmcp's ``ssrf_safe_fetch`` but consumes the resolved IPs from
    ``validated_url`` rather than re-resolving DNS (so there is no second,
    unchecked ``getaddrinfo`` that a rebinding server could exploit). It also
    supports http:// when the operator explicitly opted in, and caps the body at
    a spec-appropriate size. Redirects are disabled and rejected explicitly.

    Args:
        validated_url: The result of SSRF validation, carrying pinned IPs.
        allow_http: Whether http:// is permitted (mirrors the validation flag).
        max_size: Maximum accepted response body size in bytes.
        timeout: Per-operation timeout in seconds.

    Returns:
        The raw response body as bytes.

    Raises:
        SSRFError: If the scheme is disallowed.
        SSRFFetchError: On redirect, oversized body, or exhausted pinned IPs.
        httpx.HTTPError: On transient network/HTTP errors (retryable upstream).

    """
    scheme = urlparse(validated_url.original_url).scheme or 'https'
    if scheme not in ('https', 'http'):
        raise SSRFError(f"URL scheme '{scheme}' not allowed")
    if scheme == 'http' and not allow_http:
        # Defensive: validation should already have rejected this.
        raise SSRFError('http:// URL requires allow_insecure_http')

    last_error: Optional[Exception] = None
    for pinned_ip in validated_url.resolved_ips:
        pinned_url = (
            f'{scheme}://{format_ip_for_url(pinned_ip)}:{validated_url.port}{validated_url.path}'
        )
        # Keep Host + (for TLS) SNI bound to the validated hostname while we dial
        # the pinned IP directly, so vhost routing and certificate validation
        # still work against the real host.
        headers = {'Host': validated_url.hostname}
        extensions = {'sni_hostname': validated_url.hostname} if scheme == 'https' else {}

        logger.debug(
            f'Fetching spec {validated_url.original_url} pinned to {pinned_ip} ({pinned_url})'
        )
        try:
            with httpx.Client(
                timeout=httpx.Timeout(timeout),
                follow_redirects=False,
                verify=True,
            ) as client:
                with client.stream(
                    'GET', pinned_url, headers=headers, extensions=extensions
                ) as response:
                    # Following a 30x is a classic SSRF bypass (redirect to an
                    # internal host); reject rather than follow.
                    if 300 <= response.status_code < 400:
                        raise SSRFFetchError(
                            f'Refusing to follow redirect (HTTP {response.status_code}) '
                            f'for {validated_url.original_url}'
                        )
                    response.raise_for_status()

                    # Reject oversized bodies up front when advertised...
                    content_length = response.headers.get('content-length')
                    if content_length:
                        try:
                            if int(content_length) > max_size:
                                raise SSRFFetchError(
                                    f'Spec too large: {content_length} bytes (max {max_size})'
                                )
                        except ValueError:
                            # Ignore malformed Content-Length; enforce max_size while streaming below.
                            logger.debug(
                                'Ignoring invalid Content-Length header value: %s',
                                content_length,
                            )

                    # ...and enforce the cap while streaming regardless.
                    chunks = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > max_size:
                            raise SSRFFetchError(f'Spec too large: exceeded {max_size} bytes')
                        chunks.append(chunk)
                    return b''.join(chunks)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            # Transient / per-IP connection error: try the next pinned IP.
            last_error = e
            continue

    if last_error is not None:
        raise last_error
    raise SSRFFetchError(f'No resolved IPs available for {validated_url.original_url}')


def _require_mapping(spec: Any) -> Dict[str, Any]:
    """Return ``spec`` if it is a mapping, else raise a clear ``ValueError``.

    JSON/YAML may legally parse to a list, scalar, or ``None``. Returning such a
    value would make downstream validation (``'openapi' in spec``) raise an
    opaque ``TypeError`` on non-iterable roots; enforcing a mapping here converts
    malformed input into a clear error instead of an unhandled exception.
    """
    if not isinstance(spec, dict):
        raise ValueError(f'OpenAPI spec must be a mapping at its root, got {type(spec).__name__}')
    return spec


def _parse_spec_bytes(content: bytes) -> Dict[str, Any]:
    """Parse fetched spec bytes into a dict.

    Any external ``$ref`` is refused before prance sees the spec (see
    ``_reject_external_refs``), then prance resolves internal references only.
    Falls back to basic JSON (then YAML) parsing when prance is unavailable or
    fails on a spec that has already passed the external-ref check. The returned
    root is always a mapping; a non-mapping document raises ``ValueError``.
    """
    # Refuse external references before any resolver/validator can dereference
    # them. Parse once (best effort) purely for this safety check: if the bytes
    # are not parseable as JSON/YAML there are no references to resolve, so we
    # defer the parse error to prance / the basic fallback below. An SSRFError
    # from the ref check propagates and is never swallowed by the fallback.
    try:
        basic = _basic_parse(content)
    except (MemoryError, RecursionError):
        # Resource-exhaustion failures are not "unparseable content" — let them
        # propagate rather than masking them as a silent prescan skip.
        raise
    except Exception:
        basic = None
    if basic is not None:
        _reject_external_refs(basic)

    if PRANCE_AVAILABLE:
        logger.info('Using prance for reference resolution')
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(content)
        try:
            # RESOLVE_INTERNAL restricts prance to in-document references; combined
            # with the external-ref rejection above, no http(s)://, file://, or
            # relative-path reference is ever fetched.
            parser = ResolvingParser(temp_path, resolve_types=RESOLVE_INTERNAL)
            spec = parser.specification
            Path(temp_path).unlink(missing_ok=True)
            return _require_mapping(spec)
        except (MemoryError, RecursionError):
            # Resource-exhaustion failures are non-recoverable; clean up the temp
            # file and propagate rather than silently falling back to basic parsing.
            Path(temp_path).unlink(missing_ok=True)
            raise
        except Exception as e:
            logger.warning(f'Failed to parse with prance: {e}. Falling back to basic parsing.')
            Path(temp_path).unlink(missing_ok=True)

    # Basic parsing (references already validated as internal-only above).
    return _require_mapping(basic if basic is not None else _basic_parse(content))


@cached(ttl_seconds=3600)  # Cache OpenAPI specs for 1 hour
def load_openapi_spec(
    url: str = '',
    path: str = '',
    validated_url: Optional[ValidatedURL] = None,
    allow_http: bool = False,
    allow_private_networks: bool = False,
) -> Dict[str, Any]:
    """Load an OpenAPI specification from a URL or file path.

    URL fetches are always DNS-pinned: the spec is retrieved by connecting only
    to the IP address(es) that SSRF validation approved, never by re-resolving
    the hostname at fetch time. Callers that have already validated a URL should
    pass the resulting ``validated_url``; a bare ``url`` is validated and pinned
    in-function so there is no code path that fetches a spec un-pinned.

    If prance is available, it will be used to resolve references in the OpenAPI
    spec. Otherwise, falls back to basic JSON/YAML parsing.

    Args:
        url: URL to the OpenAPI specification (validated + pinned in-function).
        path: Path to the OpenAPI specification file.
        validated_url: A pre-validated, DNS-pinned URL from ``validate_url_for_spec``.
        allow_http: Permit http:// when validating a bare ``url``.
        allow_private_networks: Permit private/loopback IPs when validating a bare ``url``.

    Returns:
        Dict[str, Any]: The parsed OpenAPI specification

    Raises:
        ValueError: If neither url/validated_url nor path are provided
        SSRFError: If a bare url fails security validation
        SSRFFetchError: If the pinned fetch is unsafe (redirect, oversized, etc.)
        FileNotFoundError: If the file at path does not exist
        httpx.HTTPError: If there's an HTTP error when fetching the spec
        httpx.TimeoutException: If there's a timeout when fetching the spec

    """
    if not url and not path and validated_url is None:
        logger.error('Neither URL/validated_url nor path provided')
        raise ValueError('Either url/validated_url or path must be provided')

    # Load from URL (DNS-pinned; no re-resolution at fetch time)
    if validated_url is not None or url:
        # If only a raw url was given, validate + pin here so there is NO code
        # path that fetches a spec without SSRF-safe DNS pinning.
        if validated_url is None:
            validated_url = _validate_url_sync(
                url,
                allow_http=allow_http,
                allow_private_networks=allow_private_networks,
            )

        logger.info(f'Fetching OpenAPI spec from URL: {validated_url.original_url}')
        last_exception = None

        # Use retry logic for network resilience
        for attempt in range(3):
            try:
                content = _pinned_fetch(validated_url, allow_http=allow_http)
                spec = _parse_spec_bytes(content)

                # Validate the spec
                if validate_openapi_spec(spec):
                    return spec
                else:
                    logger.error('Invalid OpenAPI specification')
                    raise ValueError('Invalid OpenAPI specification')

            except (SSRFError, SSRFFetchError):
                # Security failures must not be retried away.
                raise
            except (httpx.TimeoutException, httpx.HTTPError) as e:
                last_exception = e
                if attempt < 2:  # Don't log on the last attempt
                    logger.warning(f'Attempt {attempt + 1} failed: {e}. Retrying...')
                    time.sleep(1 * (2**attempt))  # Exponential backoff
                else:
                    # Re-raise the exception on the last attempt
                    logger.error(f'All retry attempts failed: {e}')
                    raise

        # This will only be reached if all retries fail and no exception is raised
        if last_exception:
            raise last_exception
        else:
            raise httpx.HTTPError('All retry attempts failed')

    # Load from file
    if path:
        spec_path = Path(path)
        if not spec_path.exists():
            logger.error(f'OpenAPI spec file not found: {path}')
            raise FileNotFoundError(f'File not found: {path}')

        logger.info(f'Loading OpenAPI spec from file: {path}')
        try:
            # Refuse external references before prance can dereference them. This
            # runs outside the prance try/except below so the SSRFError is never
            # swallowed by the fallback-to-basic-parsing path. The parse here is
            # best effort purely for the safety check: an unparseable file has no
            # references to resolve, so its parse error is left to the existing
            # handling below.
            with open(spec_path, 'rb') as f:
                try:
                    prescan_spec = _basic_parse(f.read())
                except (MemoryError, RecursionError):
                    # Resource-exhaustion failures are not "unparseable content" —
                    # let them propagate rather than masking them as a prescan skip.
                    raise
                except Exception:
                    prescan_spec = None
            if prescan_spec is not None:
                _reject_external_refs(prescan_spec)

            if PRANCE_AVAILABLE:
                logger.info('Using prance for reference resolution')
                # Use prance for reference resolution if available. RESOLVE_INTERNAL
                # restricts prance to in-document references; combined with the
                # external-ref rejection above, no external file/URL is fetched.
                try:
                    parser = ResolvingParser(path, resolve_types=RESOLVE_INTERNAL)
                    spec = parser.specification
                except (MemoryError, RecursionError):
                    # Resource-exhaustion failures are non-recoverable; propagate
                    # rather than silently falling back to basic parsing.
                    raise
                except Exception as e:
                    logger.warning(
                        f'Failed to parse with prance: {e}. Falling back to basic parsing.'
                    )
                    # Fall back to basic parsing
                    with open(spec_path, 'r') as f:
                        content = f.read()
                        try:
                            spec = json.loads(content)
                        except json.JSONDecodeError as json_err:
                            # If it's not JSON, try to parse as YAML
                            try:
                                import yaml

                                spec = yaml.safe_load(content)
                            except ImportError:
                                logger.error('YAML parsing requires pyyaml to be installed')
                                raise ImportError(
                                    "Required dependency 'pyyaml' not installed. Install it with: pip install pyyaml"
                                ) from json_err
                            except Exception as yaml_err:
                                logger.error(f'Failed to parse YAML: {yaml_err}')
                                raise ValueError(f'Invalid YAML: {yaml_err}') from yaml_err
            else:
                # Basic parsing without reference resolution
                with open(spec_path, 'r') as f:
                    content = f.read()
                    try:
                        spec = json.loads(content)
                    except json.JSONDecodeError as json_err:
                        # If it's not JSON, try to parse as YAML
                        try:
                            import yaml

                            spec = yaml.safe_load(content)
                        except ImportError:
                            logger.error('YAML parsing requires pyyaml to be installed')
                            raise ImportError(
                                "Required dependency 'pyyaml' not installed. Install it with: pip install pyyaml"
                            ) from json_err
                        except Exception as yaml_err:
                            logger.error(f'Failed to parse YAML: {yaml_err}')
                            raise ValueError(f'Invalid YAML: {yaml_err}') from yaml_err

            # Enforce a mapping root so validation gets a clear error rather than
            # an opaque TypeError on a non-dict (list/scalar/None) document.
            spec = _require_mapping(spec)

            # Validate the spec
            if validate_openapi_spec(spec):
                return spec
            else:
                raise ValueError('Invalid OpenAPI specification')

        except Exception as e:
            logger.error(f'Failed to load OpenAPI spec from file: {path} - Error: {e}')
            raise

    # All real branches above return or raise; this terminal raise only guards
    # against an implicit None fall-through (satisfies the no-fall-through linter).
    raise ValueError('Either url/validated_url or path must be provided')
