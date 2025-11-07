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

from ..core.common.config import ALLOWED_HOSTS, ALLOWED_ORIGINS
from fastmcp.exceptions import ClientError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from loguru import logger


class HTTPHeaderValidationMiddleware(Middleware):
    """Validates incoming HTTP headers."""

    async def on_request(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        """Validates any incoming request."""
        headers = get_http_headers(include_all=True)
        logger.info(headers)

        if host := headers.get('host'):
            host = host.split(':')[0]  # Strip port if present
            allowed_hosts = ALLOWED_HOSTS.split(',')

            if '*' not in allowed_hosts and host not in allowed_hosts:
                error_msg = f'Host header validation failed: {host} not in {allowed_hosts}'
                logger.error(error_msg)
                raise ClientError(error_msg)

        if origin := headers.get('origin'):
            origin = origin.split(':')[0]  # Strip port if present
            allowed_origins = ALLOWED_ORIGINS.split(',')

            if '*' not in allowed_origins and origin not in allowed_origins:
                error_msg = (
                    f'Origin header validation failed: {origin} is not in {allowed_origins}'
                )
                logger.error(error_msg)
                raise ClientError(error_msg)

        # Continue to the next middleware or handler
        return await call_next(context)
