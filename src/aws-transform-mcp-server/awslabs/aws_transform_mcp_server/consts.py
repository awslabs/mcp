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

"""Constants for aws-transform-mcp-server."""

from typing import List, Set


# ── FES (Front End Service) targets ──────────────────────────────────────
FES_TARGET_COOKIE = 'ElasticGumbyFrontEndService'
FES_TARGET_BEARER = 'com.amazon.elasticgumbyfrontendservice.ElasticGumbyFrontEndService'

# ── TCP (Transform Control Plane) ────────────────────────────────────────
TCP_SERVICE = 'transform'
TCP_TARGET_PREFIX = 'ElasticGumbyTransformControlPlane'

# ── Client identity ───────────────────────────────────────────────────────
HEADER_CLIENT_APP_ID = 'x-amzn-atx-clientAppId'
CLIENT_APP_ID = 'atx-mcp'

# ── FES SigV4 ───────────────────────────────────────────────────────────
FES_SERVICE = 'elasticgumbyfrontendservice'

# ── HTTP retry / timeout ─────────────────────────────────────────────────
TIMEOUT_SECONDS: float = 60.0
STARTUP_TIMEOUT_SECONDS: float = 5.0
STARTUP_MAX_RETRIES: int = 0
MAX_RETRIES: int = 3
RETRYABLE_STATUSES: Set[int] = {429, 500, 502, 503, 504}

# ── Token refresh ────────────────────────────────────────────────────────
TOKEN_REFRESH_BUFFER_SECS: int = 300  # refresh if < 5 min left

# ── Persisted config path ────────────────────────────────────────────────
CONFIG_PATH: str = '~/.aws-transform-mcp/config.json'

# ── OAuth scope ──────────────────────────────────────────────────────────
OAUTH_SCOPE: str = 'transform:read_write'

# ── FES deployed regions (for profile discovery fan-out) ─────────────────
FES_REGIONS: List[str] = [
    'us-east-1',
    'eu-central-1',
    'ap-southeast-2',
    'ap-northeast-1',
    'eu-west-2',
    'ap-northeast-2',
    'sa-east-1',
    'ap-south-1',
    'ca-central-1',
]

# ── Fan-out timeout for profile discovery (seconds per region) ──────────
PROFILE_DISCOVERY_TIMEOUT_SECONDS: float = 5.0
