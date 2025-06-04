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
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import json
import requests
from loguru import logger
from typing import Any, Dict, Optional


def fetch_github_content(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Fetch content from GitHub API.

    Args:
        url: GitHub API URL
        headers: Optional additional headers

    Returns:
        Dict: GitHub API response
    """
    default_headers = {'Accept': 'application/vnd.github+json'}
    if headers:
        default_headers.update(headers)

    try:
        logger.info(f'Fetching GitHub content from {url}')
        response = requests.get(url, headers=default_headers, timeout=30)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.error(f'Error fetching or decoding GitHub content: {str(e)}')
        raise ValueError(f'Failed to fetch or decode GitHub content: {str(e)}')
