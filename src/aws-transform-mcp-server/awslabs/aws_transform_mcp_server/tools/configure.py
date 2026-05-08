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

"""Configure tool handlers for AWS Transform MCP server."""

import asyncio
import os
import time
from awslabs.aws_transform_mcp_server import __version__ as SERVER_VERSION
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import (
    build_bearer_config,
    build_cookie_config,
    clear_config,
    derive_transform_api_endpoint,
    extract_region_from_origin,
    get_config,
    get_sigv4_region,
    get_sigv4_regions,
    is_configured,
    is_sigv4_fes_available,
    persist_config,
    set_config,
    set_sigv4_region,
)
from awslabs.aws_transform_mcp_server.consts import (
    FES_REGIONS,
    OAUTH_SCOPE,
    PROFILE_DISCOVERY_TIMEOUT_SECONDS,
)
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.oauth import run_oauth_flow
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
    text_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import (
    call_fes_direct_bearer,
    call_fes_direct_cookie,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field
from typing import Annotated, Any, Dict, List, Optional


async def _discover_profiles(
    access_token: str,
) -> List[Dict[str, Any]]:
    """Fan out ListAvailableProfiles across all FES regions.

    Each region gets a 5-second timeout. Profiles are tagged with ``_region``
    (extracted from applicationUrl) so the caller knows which FES to use.

    Returns all discovered profiles, or an empty list if none found.
    """

    async def _call_region(region: str) -> List[Dict[str, Any]]:
        try:
            endpoint = derive_transform_api_endpoint(region)
            result = await asyncio.wait_for(
                call_fes_direct_bearer(endpoint, access_token, 'ListAvailableProfiles'),
                timeout=PROFILE_DISCOVERY_TIMEOUT_SECONDS,
            )
            profiles = result.get('profiles', []) if isinstance(result, dict) else []
            return [{**p, '_region': region} for p in profiles]
        except Exception as exc:
            logger.debug('Profile discovery failed for {}: {}', region, exc)
            return []

    results = await asyncio.gather(*[_call_region(r) for r in FES_REGIONS])
    all_profiles: List[Dict[str, Any]] = []
    for region_profiles in results:
        all_profiles.extend(region_profiles)
    return all_profiles


async def _select_profile(
    ctx: Context,
    profiles: List[Dict[str, Any]],
    profile_name: Optional[str],
) -> Dict[str, Any] | dict:
    """Select a profile from the discovered list.

    If only one profile exists, auto-selects it. If ``profile_name`` is given,
    matches it. Otherwise, tries MCP elicitation; falls back to returning
    PROFILE_SELECTION_REQUIRED for re-call.

    Returns the selected profile dict, or an error response dict (with 'content' key).
    """
    if len(profiles) == 1:
        return profiles[0]

    if profile_name:
        match = next((p for p in profiles if p.get('profileName') == profile_name), None)
        if match:
            return match
        return text_result(
            {
                'success': False,
                'error': {
                    'code': 'PROFILE_NOT_FOUND',
                    'message': f'Profile "{profile_name}" not found.',
                    'suggestedAction': (
                        'Re-call configure with profileName set to one of the names below.'
                    ),
                },
                'availableProfiles': [
                    {
                        'profileName': p.get('profileName'),
                        'applicationUrl': p.get('applicationUrl'),
                    }
                    for p in profiles
                ],
            },
            is_error=True,
        )

    # Try elicitation
    try:
        from mcp.server.elicitation import elicit_with_validation
        from mcp.types import ClientCapabilities, ElicitationCapability
    except ImportError:
        pass
    else:
        try:
            session = ctx.session
            has_elicitation = session.check_client_capability(
                ClientCapabilities(elicitation=ElicitationCapability())
            )

            if has_elicitation:
                display_names = [
                    f'{p.get("profileName", "")} ({p.get("_region", "unknown")})' for p in profiles
                ]

                schema_extra: Dict[str, Any] = {'enum': display_names}

                class ProfileSelection(BaseModel):
                    profile: str = Field(
                        ...,
                        json_schema_extra=schema_extra,
                    )

                result = await elicit_with_validation(
                    session,
                    'Which Transform profile do you want to connect to?',
                    ProfileSelection,
                )

                if result.action == 'accept':
                    selected_display = result.data.profile
                    match = next(
                        (
                            p
                            for p, dn in zip(profiles, display_names, strict=True)
                            if dn == selected_display
                        ),
                        None,
                    )
                    if match:
                        return match

                return error_result('CANCELLED', 'Profile selection was cancelled or declined.')
        except Exception as exc:
            logger.debug('Elicitation failed, falling back to profile list: {}', exc)

    # Fallback: return list for re-call with profileName
    return text_result(
        {
            'success': False,
            'error': {
                'code': 'PROFILE_SELECTION_REQUIRED',
                'message': 'Multiple profiles found. Please choose one.',
                'suggestedAction': (
                    'Re-call configure with profileName set to one of the names below.'
                ),
            },
            'availableProfiles': [
                {'profileName': p.get('profileName'), 'applicationUrl': p.get('applicationUrl')}
                for p in profiles
            ],
        },
        is_error=True,
    )


class ConfigureHandler:
    """Registers configure-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register configure tools on the MCP server."""
        audited_tool(mcp, 'configure')(self.configure)
        audited_tool(mcp, 'get_status')(self.get_status)
        audited_tool(mcp, 'switch_profile')(self.switch_profile)

    async def configure(
        self,
        ctx: Context,
        authMode: Annotated[
            str,
            Field(
                description=(
                    'Authentication method. '
                    '"cookie" — requires: origin, sessionCookie. '
                    '"sso" — requires: startUrl, idcRegion. Opens a browser for login.'
                ),
            ),
        ],
        # ── Cookie mode parameters ─────────────────────────────────────
        origin: Annotated[
            Optional[str],
            Field(
                description=(
                    '(cookie mode, required) Your Transform application URL from the '
                    'browser address bar (e.g., https://abc123.transform.us-east-1.on.aws).'
                ),
            ),
        ] = None,
        sessionCookie: Annotated[
            Optional[str],
            Field(
                description=(
                    '(cookie mode, required) The aws-transform-session cookie value. '
                    'Get it from browser DevTools > Application > Cookies.'
                ),
            ),
        ] = None,
        # ── SSO mode parameters ────────────────────────────────────────
        startUrl: Annotated[
            Optional[str],
            Field(
                description=(
                    '(sso mode, required) Your IAM Identity Center start URL '
                    '(e.g., https://d-xxxxxxxxxx.awsapps.com/start).'
                ),
            ),
        ] = None,
        idcRegion: Annotated[
            Optional[str],
            Field(
                description=(
                    '(sso mode, required) The AWS region where your IAM Identity Center '
                    'instance is configured (e.g., us-east-1, us-west-2).'
                ),
            ),
        ] = None,
        profileName: Annotated[
            Optional[str],
            Field(
                description=(
                    '(sso mode, optional) Profile name when multiple profiles exist. '
                    'Omit to be prompted or to see available profiles.'
                ),
            ),
        ] = None,
    ) -> dict:
        """Authenticate and connect to AWS Transform.

        Use when the user needs to set up or re-establish a connection. Two modes:
        - "cookie": immediate — validates the session cookie against the Transform API.
        Required params: origin, sessionCookie.
        - "sso": interactive — opens a browser for IAM Identity Center login (OAuth PKCE),
        discovers available profiles across all regions, and establishes a bearer token session.
        Required params: startUrl, idcRegion.

        Do NOT use this tool to check connection status — use get_status instead.
        Do NOT call this if get_status already shows a valid connection.

        [CRITICAL] SSO mode opens the user's default browser. Ensure the user expects this.
        """
        # ── Cookie auth ─────────────────────────────────────────────────
        if authMode == 'cookie':
            if not sessionCookie:
                return error_result(
                    'VALIDATION_ERROR',
                    'sessionCookie is required for cookie auth mode.',
                    'Provide the aws-transform-session cookie value from browser DevTools.',
                )
            if not origin:
                return error_result(
                    'VALIDATION_ERROR',
                    'origin is required for cookie auth mode.',
                    'Provide your Transform application URL '
                    '(e.g., https://xxx.transform.us-east-1.on.aws).',
                )

            cookie_region = extract_region_from_origin(origin)
            if not cookie_region:
                return error_result(
                    'INVALID_APPLICATION_URL',
                    f'Could not extract region from origin: {origin}',
                    'Expected format: https://{{id}}.transform.{{region}}.on.aws',
                )

            config = build_cookie_config(origin, sessionCookie, cookie_region)

            try:
                result = await call_fes_direct_cookie(
                    config.fes_endpoint,
                    config.origin,
                    config.session_cookie or '',
                    'VerifySession',
                )
                set_config(config)
                persist_config()
            except Exception as error:
                return failure_result(
                    error, 'Check that your session cookie is valid and not expired.'
                )

            return success_result(
                {
                    'message': 'Connected to AWS Transform (cookie auth)',
                    'authMode': 'cookie',
                    'region': config.region,
                    'origin': config.origin,
                    'session': result,
                }
            )

        # ── SSO / Bearer auth ───────────────────────────────────────────
        if not startUrl:
            return error_result(
                'VALIDATION_ERROR',
                'startUrl is required for sso auth mode.',
                'Provide your IdC start URL (e.g., https://d-xxx.awsapps.com/start).',
            )
        if not idcRegion:
            return error_result(
                'VALIDATION_ERROR',
                'idcRegion is required for sso auth mode.',
                'Provide the AWS region where your IAM Identity Center is configured.',
            )

        try:
            # Step 1: Run full OAuth flow
            scope = os.environ.get('AWS_TRANSFORM_OAUTH_SCOPE', OAUTH_SCOPE)
            tokens = await run_oauth_flow(start_url=startUrl, idc_region=idcRegion, scope=scope)

            # Step 2: Fan out ListAvailableProfiles across all regions
            profiles = await _discover_profiles(tokens.access_token)

            if len(profiles) == 0:
                return error_result(
                    'NO_PROFILES',
                    'No AWS Transform profiles found for this account in any region.',
                    'You may need to create a profile first.',
                )

            # Step 3: Select profile (elicitation or fallback)
            selected = await _select_profile(ctx, profiles, profileName)
            if 'content' in selected:
                return selected

            resolved_origin = selected.get('applicationUrl', '').rstrip('/')
            service_region = extract_region_from_origin(resolved_origin) or selected.get(
                '_region', 'us-east-1'
            )

            # Step 4: Verify session with selected profile
            service_fes_endpoint = derive_transform_api_endpoint(service_region)
            session = await call_fes_direct_bearer(
                service_fes_endpoint, tokens.access_token, 'VerifySession', {}, resolved_origin
            )

            # Step 5: Build and save config
            config = build_bearer_config(
                bearer_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_expiry=int(time.time()) + tokens.expires_in,
                origin=resolved_origin,
                start_url=startUrl,
                region=service_region,
                oidc_client_id=tokens.client_id,
                oidc_client_secret=tokens.client_secret,
                oidc_client_secret_expires_at=tokens.client_secret_expires_at,
                idc_region=idcRegion,
            )
            config.profile_name = selected.get('profileName')
            set_config(config)
            persist_config()
        except Exception as error:
            return failure_result(
                error,
                'Ensure your IdC start URL is correct and you have access to AWS Transform.',
            )

        return success_result(
            {
                'message': 'Connected to AWS Transform (bearer auth)',
                'authMode': 'bearer',
                'region': config.region,
                'origin': config.origin,
                'profile': selected.get('profileName'),
                'session': session,
            }
        )

    async def switch_profile(
        self,
        ctx: Context,
        region: Annotated[
            Optional[str],
            Field(
                description=(
                    '(AWS credential mode, optional) Region to switch to. '
                    'Use a value from availableRegions in the PROFILE_SELECTION_REQUIRED response. '
                    'If omitted, prompts for selection or returns available regions.'
                ),
            ),
        ] = None,
    ) -> dict:
        """Switch to a different Transform profile (region).

        For AWS credential auth: selects which region to use. Pass region directly (e.g. "us-east-1")
        or omit to be prompted. Use when get_status or a tool returns PROFILE_SELECTION_REQUIRED.
        For SSO: re-uses existing bearer token to discover and select a new profile.
        """
        config = get_config()

        if config is None:
            if is_sigv4_fes_available():
                return await self._switch_sigv4_region(ctx, region)
            return error_result(
                'NOT_CONFIGURED',
                'No active session. Connect via SSO (configure with authMode "sso") '
                'or AWS credentials (set AWS_PROFILE in MCP client env and restart).',
            )

        if config.auth_mode != 'bearer' or not config.bearer_token:
            return error_result(
                'NOT_CONFIGURED',
                'Profile switching requires an active SSO session. '
                'Run configure with authMode "sso" first.',
            )

        if config.token_expiry and int(time.time()) >= config.token_expiry:
            return error_result(
                'TOKEN_EXPIRED',
                'Your SSO session has expired.',
                'Run configure with authMode "sso" to re-authenticate.',
            )

        # Fan out to discover all profiles
        profiles = await _discover_profiles(config.bearer_token)

        if len(profiles) == 0:
            return error_result(
                'NO_PROFILES',
                'No AWS Transform profiles found for this account in any region. '
                'If your session recently expired, re-authenticate with configure.',
            )

        # Select profile (elicitation or fallback)
        selected = await _select_profile(ctx, profiles, None)
        if 'content' in selected:
            return selected

        resolved_origin = selected.get('applicationUrl', '').rstrip('/')
        service_region = extract_region_from_origin(resolved_origin) or selected.get(
            '_region', 'us-east-1'
        )

        # Verify session with selected profile
        service_fes_endpoint = derive_transform_api_endpoint(service_region)
        try:
            session = await call_fes_direct_bearer(
                service_fes_endpoint, config.bearer_token, 'VerifySession', {}, resolved_origin
            )
        except Exception as error:
            return failure_result(
                error,
                'Failed to verify session with the selected profile. '
                'You may need to re-authenticate with configure.',
            )

        # Update config with new profile
        config.origin = resolved_origin
        config.region = service_region
        config.fes_endpoint = service_fes_endpoint
        config.profile_name = selected.get('profileName')
        set_config(config)
        persist_config()

        return success_result(
            {
                'message': 'Switched to new profile',
                'profile': selected.get('profileName'),
                'region': service_region,
                'origin': resolved_origin,
                'session': session,
            }
        )

    async def _switch_sigv4_region(self, ctx: Context, region: Optional[str] = None) -> dict:
        """Handle region selection for SigV4 callers."""
        regions = get_sigv4_regions()
        current = get_sigv4_region()

        if not regions and not current:
            return error_result(
                'NO_REGIONS',
                'No regions discovered. Restart the server to re-probe.',
            )

        available = regions or ([current] if current else [])

        # If region was provided directly, validate and select it
        if region:
            if region in available:
                set_sigv4_region(region)
                return success_result(
                    {
                        'message': f'Switched to region {region}',
                        'region': region,
                    }
                )
            return error_result(
                'INVALID_REGION',
                f'Region "{region}" is not available.',
                f'Available regions: {", ".join(available)}',
            )

        if len(available) == 1:
            set_sigv4_region(available[0])
            return success_result(
                {
                    'message': f'Only one region available, already selected: {available[0]}',
                    'region': available[0],
                }
            )

        # Try elicitation
        try:
            schema_extra: Dict[str, Any] = {'enum': available}

            class RegionSelection(BaseModel):
                region: str = Field(
                    ...,
                    json_schema_extra=schema_extra,
                )

            result = await ctx.elicit(
                'Which region do you want to use?',
                RegionSelection,
            )

            if result.action == 'accept':
                selected_region = result.data.region
                set_sigv4_region(selected_region)
                return success_result(
                    {
                        'message': f'Switched to region {selected_region}',
                        'region': selected_region,
                    }
                )

            return error_result('CANCELLED', 'Region selection was cancelled.')
        except Exception as exc:
            logger.debug('Elicitation failed for SigV4 region switch: {}', exc)

        # Fallback: return list for LLM to present
        return text_result(
            {
                'success': False,
                'error': {
                    'code': 'REGION_SELECTION_REQUIRED',
                    'message': 'Multiple regions available. Please choose one.',
                    'suggestedAction': (
                        'Ask the user which region they want, then call '
                        'switch_profile with the region parameter.'
                    ),
                },
                'availableRegions': [
                    {'region': r, 'endpoint': derive_transform_api_endpoint(r)} for r in available
                ],
            },
            is_error=True,
        )

    async def get_status(self, ctx: Context) -> dict:
        """Check the status of all connections (Transform API cookie/SSO/AWS credentials and TCP)."""
        status: dict = {'serverVersion': SERVER_VERSION}

        # ── FES status ──────────────────────────────────────────────────
        if not is_configured():
            if is_sigv4_fes_available():
                status['connection'] = {
                    'configured': True,
                    'authMode': 'sigv4',
                    'message': 'Connected via AWS credentials (auto-detected).',
                }
            else:
                status['connection'] = {
                    'configured': False,
                    'message': 'Not connected to AWS Transform. Options: (1) configure with authMode "sso" '
                    '(opens browser for IAM Identity Center login), (2) configure with '
                    'authMode "cookie" (uses existing browser session), or (3) set '
                    'AWS_PROFILE in the MCP client env block and restart for automatic '
                    'credential detection.',
                }
        else:
            config = get_config()
            if config is None:
                status['connection'] = {
                    'configured': False,
                    'message': 'Not connected to AWS Transform. Options: (1) configure with authMode "sso" '
                    '(opens browser for IAM Identity Center login), (2) configure with '
                    'authMode "cookie" (uses existing browser session), or (3) set '
                    'AWS_PROFILE in the MCP client env block and restart for automatic '
                    'credential detection.',
                }
                return text_result(status, is_error=False)
            fes_endpoint = derive_transform_api_endpoint(config.region or 'us-east-1')
            try:
                if config.auth_mode == 'cookie':
                    result = await call_fes_direct_cookie(
                        fes_endpoint,
                        config.origin,
                        config.session_cookie or '',
                        'VerifySession',
                    )
                else:
                    result = await call_fes_direct_bearer(
                        fes_endpoint,
                        config.bearer_token or '',
                        'VerifySession',
                        {},
                        config.origin,
                    )

                info: dict = {
                    'configured': True,
                    'authMode': config.auth_mode,
                    'region': config.region,
                    'origin': config.origin,
                    'session': result,
                }
                if config.profile_name:
                    info['profile'] = config.profile_name
                if config.auth_mode == 'bearer' and config.token_expiry:
                    remaining = config.token_expiry - int(time.time())
                    info['tokenExpiresIn'] = f'{remaining}s' if remaining > 0 else 'EXPIRED'
                status['connection'] = info
            except HttpError as error:
                if error.status_code in (401, 403):
                    clear_config()
                    status['connection'] = {
                        'configured': False,
                        'message': (
                            'SSO session expired. Re-authenticate with configure '
                            '(authMode "sso"), or set AWS_PROFILE in the MCP client '
                            'env block and restart for automatic credential detection.'
                        ),
                    }
                else:
                    status['connection'] = {
                        'configured': True,
                        'error': {
                            'code': 'SESSION_CHECK_FAILED',
                            'message': f'Session verification failed: {error}',
                        },
                        'suggestedAction': (
                            'This may be a transient error. Try again, or re-authenticate '
                            'if the problem persists.'
                        ),
                        'authMode': config.auth_mode,
                        'region': config.region,
                    }
            except Exception as error:
                status['connection'] = {
                    'configured': True,
                    'error': {
                        'code': 'SESSION_CHECK_FAILED',
                        'message': f'Session verification failed: {error}',
                    },
                    'suggestedAction': (
                        'This may be a transient error. Try again, or re-authenticate '
                        'if the problem persists.'
                    ),
                    'authMode': config.auth_mode,
                    'region': config.region,
                }

        # ── SigV4 status (auto-detect + STS validation) ────────────────
        try:
            from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper
            from awslabs.aws_transform_mcp_server.config_store import derive_tcp_endpoint

            session = AwsHelper.create_session()
            region = AwsHelper.resolve_region(session)
            profile = os.environ.get('AWS_PROFILE')
            resolved = session.get_credentials()
            if resolved is None:
                status['sigv4'] = {
                    'configured': False,
                    'message': (
                        'No AWS credentials detected. '
                        'Set AWS_PROFILE in your MCP client config env block, '
                        'or configure via aws configure / environment variables.'
                    ),
                }
            else:
                sts_client = AwsHelper.create_boto3_client('sts', region_name=region)
                identity = sts_client.get_caller_identity()
                tcp_endpoint = derive_tcp_endpoint(region)
                source = f'AWS_PROFILE={profile}' if profile else 'default credential chain'
                status['sigv4'] = {
                    'configured': True,
                    'source': f'auto-detected from {source}',
                    'accountId': identity.get('Account'),
                    'arn': identity.get('Arn'),
                    'region': region,
                    'tcpEndpoint': tcp_endpoint,
                }
        except ValueError as exc:
            status['sigv4'] = {
                'configured': False,
                'message': (
                    f'AWS region not configured: {exc}. '
                    'Set AWS_REGION in the MCP client env block, or ensure your '
                    'AWS profile has a region configured in ~/.aws/config.'
                ),
            }
        except Exception as exc:
            status['sigv4'] = {
                'configured': False,
                'message': (
                    f'AWS credentials not available: {exc}. '
                    'Set AWS_PROFILE in the MCP client env block and ensure '
                    'credentials are valid (run aws sts get-caller-identity to test).'
                ),
            }

        # ── AWS credential API status ──────────────────────────────────
        status['sigv4AwsTransformAPI'] = {
            'available': is_sigv4_fes_available(),
            'message': (
                'AWS credential auth enabled — all API tools work without configure.'
                if is_sigv4_fes_available()
                else 'AWS credential auth not available. Use configure to connect.'
            ),
        }

        fes_status = status.get('connection', {})
        has_error = 'error' in fes_status
        return text_result(status, is_error=has_error)
