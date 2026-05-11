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

"""OCM (OpenShift Cluster Manager) REST API client.

Provides async HTTP access to the OCM API for managing ROSA clusters,
machine pools, identity providers, upgrades, and ingresses.

Authentication uses an offline token exchanged for a short-lived access token
via Red Hat SSO.

Environment Variables:
    OCM_TOKEN: Red Hat offline token (from console.redhat.com/openshift/token)
    OCM_API_URL: OCM API base URL (default: https://api.openshift.com)
"""

import httpx
import os
import time
from loguru import logger


OCM_API_URL = 'https://api.openshift.com'
OCM_SSO_TOKEN_URL = (
    'https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token'
)
OCM_CLIENT_ID_DEFAULT = 'cloud-services'
API_PATH = '/api/clusters_mgmt/v1'

# Token refresh buffer — refresh 60s before expiry
_TOKEN_REFRESH_BUFFER = 60


class OCMClient:
    """Async client for the OpenShift Cluster Manager REST API.

    Handles token lifecycle (exchange, refresh) and provides typed methods
    for all ROSA resource operations.
    """

    def __init__(
        self,
        offline_token: str | None = None,
        api_url: str | None = None,
        client_id: str | None = None,
    ) -> None:
        """Initialize the OCM client.

        Args:
            offline_token: Red Hat offline token. Falls back to OCM_TOKEN env var,
                          then to ~/.config/ocm/ocm.json or ~/Library/Application Support/ocm/ocm.json.
            api_url: OCM API base URL. Falls back to OCM_API_URL env var or default.
            client_id: OAuth client ID for token exchange. Falls back to OCM_CLIENT_ID env var,
                      OCM config file, or 'cloud-services' default.
        """
        self._offline_token = offline_token or os.environ.get('OCM_TOKEN', '')
        self._client_id = client_id or os.environ.get('OCM_CLIENT_ID', '')

        # Try loading from OCM config file if not provided via env/args
        if not self._offline_token or not self._client_id:
            ocm_config = self._load_ocm_config()
            if not self._offline_token:
                self._offline_token = ocm_config.get('refresh_token', '')
            if not self._client_id:
                self._client_id = ocm_config.get('client_id', '')

        if not self._offline_token:
            raise ValueError(
                'OCM offline token required. Set OCM_TOKEN env var, pass offline_token, '
                'or login with: ocm login --use-device-code'
            )
        if not self._client_id:
            self._client_id = OCM_CLIENT_ID_DEFAULT

        self._api_url = (api_url or os.environ.get('OCM_API_URL', '') or OCM_API_URL).rstrip('/')
        self._access_token: str | None = None
        self._token_expiry: float = 0
        self._http: httpx.AsyncClient | None = None

    @staticmethod
    def _load_ocm_config() -> dict:
        """Load OCM config from standard locations."""
        import json
        import pathlib
        import platform

        candidates = []
        if platform.system() == 'Darwin':
            candidates.append(
                pathlib.Path.home() / 'Library' / 'Application Support' / 'ocm' / 'ocm.json'
            )
        candidates.append(pathlib.Path.home() / '.config' / 'ocm' / 'ocm.json')

        for path in candidates:
            if path.exists():
                try:
                    return json.loads(path.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
        return {}

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=60.0)
        return self._http

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None

    async def _ensure_token(self) -> str:
        """Ensure we have a valid access token, refreshing if needed."""
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        client = await self._ensure_client()
        resp = await client.post(
            OCM_SSO_TOKEN_URL,
            data={
                'grant_type': 'refresh_token',
                'client_id': self._client_id,
                'refresh_token': self._offline_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data['access_token']
        self._token_expiry = time.time() + data.get('expires_in', 900) - _TOKEN_REFRESH_BUFFER
        logger.debug('OCM access token refreshed')
        return self._access_token

    async def _headers(self) -> dict[str, str]:
        token = await self._ensure_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    async def _get(self, path: str, params: dict | None = None) -> dict:
        client = await self._ensure_client()
        headers = await self._headers()
        resp = await client.get(f'{self._api_url}{API_PATH}{path}', headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, body: dict) -> dict:
        client = await self._ensure_client()
        headers = await self._headers()
        resp = await client.post(f'{self._api_url}{API_PATH}{path}', headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()

    async def _patch(self, path: str, body: dict) -> dict:
        client = await self._ensure_client()
        headers = await self._headers()
        resp = await client.patch(f'{self._api_url}{API_PATH}{path}', headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()

    async def _delete(self, path: str, params: dict | None = None) -> int:
        client = await self._ensure_client()
        headers = await self._headers()
        resp = await client.delete(
            f'{self._api_url}{API_PATH}{path}', headers=headers, params=params
        )
        resp.raise_for_status()
        return resp.status_code

    # --- Clusters ---

    async def list_clusters(
        self, search: str | None = None, page: int = 1, size: int = 100
    ) -> dict:
        """List clusters with optional search filter."""
        params: dict = {'page': page, 'size': size}
        if search:
            params['search'] = search
        return await self._get('/clusters', params=params)

    async def get_cluster(self, cluster_id: str) -> dict:
        """Get a single cluster by ID."""
        return await self._get(f'/clusters/{cluster_id}')

    async def create_cluster(self, body: dict) -> dict:
        """Create a new cluster."""
        return await self._post('/clusters', body)

    async def update_cluster(self, cluster_id: str, body: dict) -> dict:
        """Update (PATCH) a cluster."""
        return await self._patch(f'/clusters/{cluster_id}', body)

    async def delete_cluster(self, cluster_id: str, deprovision: bool = True) -> int:
        """Delete a cluster."""
        return await self._delete(
            f'/clusters/{cluster_id}', params={'deprovision': str(deprovision).lower()}
        )

    async def get_cluster_credentials(self, cluster_id: str) -> dict:
        """Get cluster credentials (kubeconfig, admin password)."""
        return await self._get(f'/clusters/{cluster_id}/credentials')

    async def get_install_logs(self, cluster_id: str, tail: int | None = None) -> dict:
        """Get cluster install logs."""
        params = {}
        if tail:
            params['tail'] = tail
        return await self._get(f'/clusters/{cluster_id}/logs/install', params=params or None)

    async def get_uninstall_logs(self, cluster_id: str, tail: int | None = None) -> dict:
        """Get cluster uninstall logs."""
        params = {}
        if tail:
            params['tail'] = tail
        return await self._get(f'/clusters/{cluster_id}/logs/uninstall', params=params or None)

    # --- Versions ---

    async def list_versions(
        self, search: str | None = None, page: int = 1, size: int = 100
    ) -> dict:
        """List available OpenShift versions."""
        params: dict = {'page': page, 'size': size}
        if search:
            params['search'] = search
        return await self._get('/versions', params=params)

    # --- Machine Pools ---

    async def list_machine_pools(self, cluster_id: str) -> dict:
        """List machine pools for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/machine_pools')

    async def get_machine_pool(self, cluster_id: str, pool_id: str) -> dict:
        """Get a specific machine pool."""
        return await self._get(f'/clusters/{cluster_id}/machine_pools/{pool_id}')

    async def create_machine_pool(self, cluster_id: str, body: dict) -> dict:
        """Create a machine pool."""
        return await self._post(f'/clusters/{cluster_id}/machine_pools', body)

    async def update_machine_pool(self, cluster_id: str, pool_id: str, body: dict) -> dict:
        """Update a machine pool."""
        return await self._patch(f'/clusters/{cluster_id}/machine_pools/{pool_id}', body)

    async def delete_machine_pool(self, cluster_id: str, pool_id: str) -> int:
        """Delete a machine pool."""
        return await self._delete(f'/clusters/{cluster_id}/machine_pools/{pool_id}')

    # --- Node Pools (HCP) ---

    async def list_node_pools(self, cluster_id: str) -> dict:
        """List node pools for an HCP cluster."""
        return await self._get(f'/clusters/{cluster_id}/node_pools')

    async def get_node_pool(self, cluster_id: str, pool_id: str) -> dict:
        """Get a specific node pool."""
        return await self._get(f'/clusters/{cluster_id}/node_pools/{pool_id}')

    async def create_node_pool(self, cluster_id: str, body: dict) -> dict:
        """Create a node pool on an HCP cluster."""
        return await self._post(f'/clusters/{cluster_id}/node_pools', body)

    async def update_node_pool(self, cluster_id: str, pool_id: str, body: dict) -> dict:
        """Update a node pool."""
        return await self._patch(f'/clusters/{cluster_id}/node_pools/{pool_id}', body)

    async def delete_node_pool(self, cluster_id: str, pool_id: str) -> int:
        """Delete a node pool."""
        return await self._delete(f'/clusters/{cluster_id}/node_pools/{pool_id}')

    # --- Identity Providers ---

    async def list_identity_providers(self, cluster_id: str) -> dict:
        """List identity providers for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/identity_providers')

    async def create_identity_provider(self, cluster_id: str, body: dict) -> dict:
        """Create an identity provider."""
        return await self._post(f'/clusters/{cluster_id}/identity_providers', body)

    async def delete_identity_provider(self, cluster_id: str, idp_id: str) -> int:
        """Delete an identity provider."""
        return await self._delete(f'/clusters/{cluster_id}/identity_providers/{idp_id}')

    # --- Upgrade Policies ---

    async def list_upgrade_policies(self, cluster_id: str) -> dict:
        """List upgrade policies for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/upgrade_policies')

    async def create_upgrade_policy(self, cluster_id: str, body: dict) -> dict:
        """Create an upgrade policy."""
        return await self._post(f'/clusters/{cluster_id}/upgrade_policies', body)

    async def delete_upgrade_policy(self, cluster_id: str, policy_id: str) -> int:
        """Delete an upgrade policy."""
        return await self._delete(f'/clusters/{cluster_id}/upgrade_policies/{policy_id}')

    # --- Ingresses ---

    async def list_ingresses(self, cluster_id: str) -> dict:
        """List ingresses for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/ingresses')

    async def create_ingress(self, cluster_id: str, body: dict) -> dict:
        """Create an ingress."""
        return await self._post(f'/clusters/{cluster_id}/ingresses', body)

    async def update_ingress(self, cluster_id: str, ingress_id: str, body: dict) -> dict:
        """Update an ingress."""
        return await self._patch(f'/clusters/{cluster_id}/ingresses/{ingress_id}', body)

    async def delete_ingress(self, cluster_id: str, ingress_id: str) -> int:
        """Delete an ingress."""
        return await self._delete(f'/clusters/{cluster_id}/ingresses/{ingress_id}')

    # --- AWS Inquiries ---

    async def get_available_regions(self, body: dict) -> dict:
        """Get available AWS regions for ROSA."""
        return await self._post('/aws_inquiries/regions', body)

    async def get_available_machine_types(self, body: dict) -> dict:
        """Get available machine types for a region."""
        return await self._post('/aws_inquiries/machine_types', body)

    async def validate_credentials(self, body: dict) -> dict:
        """Validate AWS credentials for ROSA."""
        return await self._post('/aws_inquiries/validate_credentials', body)
