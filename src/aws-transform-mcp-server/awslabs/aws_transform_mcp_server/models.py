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

"""Pydantic models for connection and authentication configuration."""

from pydantic import BaseModel
from typing import Literal, Optional


class ConnectionConfig(BaseModel):
    """FES (Front End Service) authentication configuration."""

    auth_mode: Literal['cookie', 'bearer']
    region: str
    fes_endpoint: str
    origin: str
    # Cookie auth
    session_cookie: Optional[str] = None
    # Bearer auth
    bearer_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[int] = None  # unix timestamp (seconds)
    start_url: Optional[str] = None
    idc_region: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_client_secret_expires_at: Optional[int] = None  # unix timestamp (seconds)
    profile_name: Optional[str] = None


class OAuthTokens(BaseModel):
    """Result of a full OAuth Authorization Code + PKCE flow."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 0
    client_id: str
    client_secret: str
    client_secret_expires_at: int


class RefreshedTokens(BaseModel):
    """Result of a token refresh via the refresh_token grant."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 0
