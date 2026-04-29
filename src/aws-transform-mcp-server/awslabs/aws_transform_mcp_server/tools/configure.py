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

import os
import time
from awslabs.aws_transform_mcp_server import __version__ as SERVER_VERSION
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import (
    build_bearer_config,
    build_cookie_config,
    clear_config,
    derive_fes_endpoint,
    get_config,
    is_configured,
    is_sigv4_fes_available,
    persist_config,
    set_config,
)
from awslabs.aws_transform_mcp_server.fes_client import (
    call_fes_direct_bearer,
    call_fes_direct_cookie,
)
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.oauth import get_scope, run_oauth_flow
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
    text_result,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Optional


class ConfigureHandler:
    """Registers configure-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register configure tools on the MCP server."""
        audited_tool(mcp, 'configure')(self.configure)
        audited_tool(mcp, 'get_status')(self.get_status)

    async def configure(
        self,
        ctx: Context,
        authMode: Annotated[
            str,
            Field(
                description=(
                    'Authentication method: "cookie" for browser session, "sso" for IdC bearer token'
                ),
            ),
        ],
        stage: Annotated[
            str,
            Field(
                description=(
                    'Environment stage (default: prod). Gamma only supports us-east-1 and us-west-2.'
                ),
            ),
        ] = 'prod',
        region: Annotated[
            str,
            Field(
                description=(
                    'AWS region (default: us-east-1). For SSO auth, this must be the region '
                    'where your IAM Identity Center instance is configured.'
                ),
            ),
        ] = 'us-east-1',
        sessionCookie: Annotated[
            Optional[str],
            Field(
                description=(
                    '(cookie mode) The aws-transform-session cookie value from browser DevTools'
                ),
            ),
        ] = None,
        origin: Annotated[
            Optional[str],
            Field(
                description=(
                    '(cookie mode) Your Transform application URL '
                    '(e.g., https://xxx.transform-gamma.us-east-1.on.aws)'
                ),
            ),
        ] = None,
        startUrl: Annotated[
            Optional[str],
            Field(
                description='(sso mode) Your IdC start URL (e.g., https://d-xxx.awsapps.com/start)',
            ),
        ] = None,
        profileName: Annotated[
            Optional[str],
            Field(
                description=(
                    '(sso mode) Profile to connect to when multiple profiles exist. '
                    'Call without this first to see available profiles.'
                ),
            ),
        ] = None,
    ) -> dict:
        """Connect to AWS Transform using a browser session cookie or SSO/IdC bearer token."""
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
                    '(e.g., https://xxx.transform-gamma.us-east-1.on.aws).',
                )

            config = build_cookie_config(origin, sessionCookie, stage, region)

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
                    'stage': config.stage,
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

        scope = get_scope(stage)

        try:
            # Step 1: Run full OAuth flow
            tokens = await run_oauth_flow(start_url=startUrl, idc_region=region, scope=scope)

            # Step 2: Discover profiles via ListAvailableProfiles
            fes_endpoint = derive_fes_endpoint(stage, region)
            profiles_result = await call_fes_direct_bearer(
                fes_endpoint, tokens.access_token, 'ListAvailableProfiles'
            )

            profiles = (
                profiles_result.get('profiles', []) if isinstance(profiles_result, dict) else []
            )

            if len(profiles) == 0:
                return error_result(
                    'NO_PROFILES',
                    'No AWS Transform profiles found for this account.',
                    'You may need to create a profile first.',
                )

            # Step 3: Select profile
            if len(profiles) == 1:
                profile = profiles[0]
            elif profileName:
                match = next((p for p in profiles if p.get('profileName') == profileName), None)
                if not match:
                    return text_result(
                        {
                            'success': False,
                            'error': {
                                'code': 'PROFILE_NOT_FOUND',
                                'message': f'Profile "{profileName}" not found.',
                                'suggestedAction': (
                                    'Re-call configure with authMode "sso" and one of '
                                    'the profile names listed below.'
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
                profile = match
            else:
                return text_result(
                    {
                        'success': False,
                        'error': {
                            'code': 'PROFILE_SELECTION_REQUIRED',
                            'message': 'Multiple profiles found. Please choose one.',
                            'suggestedAction': (
                                'Re-call configure with authMode "sso" and profileName '
                                'set to one of the names below.'
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

            resolved_origin = profile.get('applicationUrl', '').rstrip('/')

            # Step 4: Verify session with selected profile
            session = await call_fes_direct_bearer(
                fes_endpoint, tokens.access_token, 'VerifySession', {}, resolved_origin
            )

            # Step 5: Build and save config
            config = build_bearer_config(
                bearer_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_expiry=int(time.time()) + tokens.expires_in,
                origin=resolved_origin,
                start_url=startUrl,
                stage=stage,
                region=region,
                oidc_client_id=tokens.client_id,
                oidc_client_secret=tokens.client_secret,
                oidc_client_secret_expires_at=tokens.client_secret_expires_at,
            )
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
                'stage': config.stage,
                'region': config.region,
                'origin': config.origin,
                'profile': profile.get('profileName'),
                'tokenExpiresIn': f'{tokens.expires_in}s',
                'session': session,
            }
        )

    async def get_status(self, ctx: Context) -> dict:
        """Check the status of all connections (FES cookie/SSO/SigV4 and TCP SigV4)."""
        status: dict = {'serverVersion': SERVER_VERSION}

        # ── FES status ──────────────────────────────────────────────────
        if not is_configured():
            status['fes'] = {
                'configured': False,
                'message': 'Not connected. Use configure with authMode "cookie" or "sso".',
            }
        else:
            config = get_config()
            if config is None:
                status['fes'] = {
                    'configured': False,
                    'message': 'Not connected. Use configure with authMode "cookie" or "sso".',
                }
                return text_result(status, is_error=False)
            try:
                if config.auth_mode == 'cookie':
                    result = await call_fes_direct_cookie(
                        config.fes_endpoint,
                        config.origin,
                        config.session_cookie or '',
                        'VerifySession',
                    )
                else:
                    result = await call_fes_direct_bearer(
                        config.fes_endpoint,
                        config.bearer_token or '',
                        'VerifySession',
                        {},
                        config.origin,
                    )

                info: dict = {
                    'configured': True,
                    'authMode': config.auth_mode,
                    'stage': config.stage,
                    'region': config.region,
                    'origin': config.origin,
                    'session': result,
                }
                if config.auth_mode == 'bearer' and config.token_expiry:
                    remaining = config.token_expiry - int(time.time())
                    info['tokenExpiresIn'] = f'{remaining}s' if remaining > 0 else 'EXPIRED'
                status['fes'] = info
            except HttpError as error:
                if error.status_code in (401, 403):
                    clear_config()
                    status['fes'] = {
                        'configured': False,
                        'message': (
                            'Session expired or unauthorized. Re-authenticate with configure.'
                        ),
                    }
                else:
                    status['fes'] = {
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
                        'stage': config.stage,
                        'region': config.region,
                    }
            except Exception as error:
                status['fes'] = {
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
                    'stage': config.stage,
                    'region': config.region,
                }

        # ── SigV4 status (auto-detect + STS validation) ────────────────
        try:
            from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper
            from awslabs.aws_transform_mcp_server.config_store import derive_tcp_endpoint

            stage = os.environ.get('ATX_STAGE', 'prod')
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
                tcp_endpoint = derive_tcp_endpoint(stage, region)
                source = f'AWS_PROFILE={profile}' if profile else 'default credential chain'
                status['sigv4'] = {
                    'configured': True,
                    'source': f'auto-detected from {source}',
                    'accountId': identity.get('Account'),
                    'arn': identity.get('Arn'),
                    'stage': stage,
                    'region': region,
                    'tcpEndpoint': tcp_endpoint,
                }
        except ValueError as exc:
            status['sigv4'] = {
                'configured': False,
                'message': f'Region configuration error: {exc}',
            }
        except Exception as exc:
            status['sigv4'] = {
                'configured': False,
                'message': f'AWS credential validation failed: {exc}',
            }

        # ── SigV4 FES status ────────────────────────────────────────────
        status['sigv4Fes'] = {
            'available': is_sigv4_fes_available(),
            'message': (
                'SigV4 FES auth enabled — FES tools work without configure.'
                if is_sigv4_fes_available()
                else 'SigV4 FES auth not available. Use configure for FES tools.'
            ),
        }

        fes_status = status.get('fes', {})
        has_error = 'error' in fes_status
        return text_result(status, is_error=has_error)
