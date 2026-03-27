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

"""Browser tools sub-package for the unified AgentCore MCP server.

Provides 25 browser automation tools via Amazon Bedrock AgentCore.
"""

import asyncio
from .connection_manager import BrowserConnectionManager
from .interaction import InteractionTools
from .management import ManagementTools
from .navigation import NavigationTools
from .observation import ObservationTools
from .session import BrowserSessionTools
from .snapshot_manager import SnapshotManager
from loguru import logger


STALE_SESSION_CHECK_INTERVAL_S = 60


async def cleanup_stale_sessions(
    connection_manager: BrowserConnectionManager,
    snapshot_manager: SnapshotManager,
) -> None:
    """Periodically check for stale Playwright connections and prune them."""
    while True:
        await asyncio.sleep(STALE_SESSION_CHECK_INTERVAL_S)
        try:
            for sid in connection_manager.get_session_ids():
                try:
                    browser = connection_manager.get_browser(sid)
                    if not browser.is_connected():
                        logger.info(f'Pruning stale session {sid} (browser disconnected)')
                        await connection_manager.disconnect(sid)
                        snapshot_manager.cleanup_session(sid)
                except ValueError:
                    logger.debug(f'Session {sid} already removed during stale cleanup')
                except Exception as e:
                    logger.warning(f'Error checking session {sid} liveness: {e}')
        except Exception as e:
            logger.warning(f'Stale session cleanup sweep error: {e}')


def register_browser_tools(mcp):
    """Create managers, register all 25 browser tools, return managers for lifecycle use."""
    connection_manager = BrowserConnectionManager()
    snapshot_manager = SnapshotManager()
    groups = [
        ('session', BrowserSessionTools),
        ('navigation', NavigationTools),
        ('interaction', InteractionTools),
        ('observation', ObservationTools),
        ('management', ManagementTools),
    ]
    for name, cls in groups:
        try:
            cls(connection_manager, snapshot_manager).register(mcp)
        except Exception as e:
            raise RuntimeError(f'Failed to register browser {name} tools: {e}') from e
    logger.info('All browser tool groups registered successfully')
    return connection_manager, snapshot_manager
