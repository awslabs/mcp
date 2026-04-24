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

from typing import Dict, Set


# ── FES (Front End Service) targets ──────────────────────────────────────
FES_TARGET_COOKIE = 'ElasticGumbyFrontEndService'
FES_TARGET_BEARER = 'com.amazon.elasticgumbyfrontendservice.ElasticGumbyFrontEndService'

# ── TCP (Transform Control Plane) ────────────────────────────────────────
TCP_SERVICE = 'transform'
TCP_TARGET_PREFIX = 'ElasticGumbyTransformControlPlane'

# ── Client identity ───────────────────────────────────────────────────────
HEADER_CLIENT_APP_ID = 'x-amzn-atx-clientAppId'
CLIENT_APP_ID = 'atx-mcp'

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

# ── OAuth scopes per stage ───────────────────────────────────────────────
STAGE_SCOPES: Dict[str, str] = {
    'gamma': 'transform_test:read_write',
    'prod': 'transform:read_write',
}

# ── Region to airport-code mapping (used for non-prod TCP endpoints) ─────
REGION_AIRPORT_CODES: Dict[str, str] = {
    'us-east-1': 'iad',
    'us-east-2': 'cmh',
    'us-west-1': 'sfo',
    'us-west-2': 'pdx',
    'eu-west-1': 'dub',
    'eu-west-2': 'lhr',
    'eu-central-1': 'fra',
    'ap-northeast-1': 'nrt',
    'ap-southeast-1': 'sin',
    'ap-southeast-2': 'syd',
    'ap-south-1': 'bom',
    'sa-east-1': 'gru',
    'ca-central-1': 'yul',
}
