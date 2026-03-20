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

"""Browser session profile management tools."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client import (
    get_data_plane_client,
    handle_aws_errors,
)
from loguru import logger


@handle_aws_errors('save browser session profile')
def save_browser_session_profile(
    profile_identifier: str,
    session_id: str,
    browser_identifier: str = 'aws.browser.v1',
) -> dict:
    """Save an active browser session's state as a reusable profile.

    Captures cookies, local storage, and session storage. Use the profile_identifier
    with start_browser_session to restore this state in future sessions.

    Args:
        profile_identifier: Unique name for the profile.
        session_id: ID of the active session to capture.
        browser_identifier: Browser tool ID (default: "aws.browser.v1").

    Returns:
        dict with profile_identifier, browser_identifier, session_id, last_updated_at.
    """
    logger.info(f'Saving browser session profile: {profile_identifier} from session {session_id}')
    client = get_data_plane_client()

    response = client.save_browser_session_profile(
        profileIdentifier=profile_identifier,
        browserIdentifier=browser_identifier,
        sessionId=session_id,
    )

    return {
        'profile_identifier': response.get('profileIdentifier'),
        'browser_identifier': response.get('browserIdentifier'),
        'session_id': response.get('sessionId'),
        'last_updated_at': response.get('lastUpdatedAt'),
    }
