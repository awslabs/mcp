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

    # --- Cluster Autoscaler ---

    async def get_autoscaler(self, cluster_id: str) -> dict:
        """Get the cluster autoscaler configuration."""
        return await self._get(f'/clusters/{cluster_id}/autoscaler')

    async def create_autoscaler(self, cluster_id: str, body: dict) -> dict:
        """Create a cluster autoscaler configuration."""
        return await self._post(f'/clusters/{cluster_id}/autoscaler', body)

    async def update_autoscaler(self, cluster_id: str, body: dict) -> dict:
        """Update the cluster autoscaler configuration."""
        return await self._patch(f'/clusters/{cluster_id}/autoscaler', body)

    async def delete_autoscaler(self, cluster_id: str) -> int:
        """Delete the cluster autoscaler configuration."""
        return await self._delete(f'/clusters/{cluster_id}/autoscaler')

    # --- Cluster Status & Metrics ---

    async def get_cluster_status(self, cluster_id: str) -> dict:
        """Get the current status of a cluster."""
        return await self._get(f'/clusters/{cluster_id}/status')

    async def get_cluster_metrics(self, cluster_id: str, metric: str) -> dict:
        """Get cluster metrics by metric name.

        Args:
            cluster_id: The cluster identifier.
            metric: One of: alerts, cluster_operators, cpu_total_by_node_roles_os,
                    nodes, socket_total_by_node_roles_os.
        """
        return await self._get(f'/clusters/{cluster_id}/metric_queries/{metric}')

    # --- Hibernation (Classic only) ---

    async def hibernate_cluster(self, cluster_id: str) -> int:
        """Hibernate a classic cluster.

        Sends a POST request with an empty body to initiate cluster hibernation.
        Only supported for ROSA Classic clusters.
        """
        client = await self._ensure_client()
        headers = await self._headers()
        resp = await client.post(
            f'{self._api_url}{API_PATH}/clusters/{cluster_id}/hibernate',
            headers=headers, json={}
        )
        resp.raise_for_status()
        return resp.status_code

    async def resume_cluster(self, cluster_id: str) -> int:
        """Resume a hibernated classic cluster.

        Sends a POST request with an empty body to resume a hibernated cluster.
        Only supported for ROSA Classic clusters.
        """
        client = await self._ensure_client()
        headers = await self._headers()
        resp = await client.post(
            f'{self._api_url}{API_PATH}/clusters/{cluster_id}/resume',
            headers=headers, json={}
        )
        resp.raise_for_status()
        return resp.status_code

    # --- Add-ons ---

    async def list_available_addons(self, page: int = 1, size: int = 100) -> dict:
        """List all available add-ons in the catalog."""
        params: dict = {'page': page, 'size': size}
        return await self._get('/addons', params=params)

    async def list_cluster_addons(self, cluster_id: str) -> dict:
        """List add-ons installed on a cluster."""
        return await self._get(f'/clusters/{cluster_id}/addons')

    async def install_addon(self, cluster_id: str, body: dict) -> dict:
        """Install an add-on on a cluster."""
        return await self._post(f'/clusters/{cluster_id}/addons', body)

    async def get_addon_installation(self, cluster_id: str, addon_id: str) -> dict:
        """Get details of an add-on installation on a cluster."""
        return await self._get(f'/clusters/{cluster_id}/addons/{addon_id}')

    async def uninstall_addon(self, cluster_id: str, addon_id: str) -> int:
        """Uninstall an add-on from a cluster."""
        return await self._delete(f'/clusters/{cluster_id}/addons/{addon_id}')

    # --- Groups & Users ---

    async def list_groups(self, cluster_id: str) -> dict:
        """List groups for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/groups')

    async def list_group_users(self, cluster_id: str, group_id: str) -> dict:
        """List users in a cluster group."""
        return await self._get(f'/clusters/{cluster_id}/groups/{group_id}/users')

    async def add_user_to_group(self, cluster_id: str, group_id: str, body: dict) -> dict:
        """Add a user to a cluster group."""
        return await self._post(f'/clusters/{cluster_id}/groups/{group_id}/users', body)

    async def remove_user_from_group(
        self, cluster_id: str, group_id: str, user_id: str
    ) -> int:
        """Remove a user from a cluster group."""
        return await self._delete(f'/clusters/{cluster_id}/groups/{group_id}/users/{user_id}')

    # --- Break-Glass Credentials (HCP) ---

    async def list_break_glass_credentials(self, cluster_id: str) -> dict:
        """List break-glass credentials for an HCP cluster."""
        return await self._get(f'/clusters/{cluster_id}/break_glass_credentials')

    async def create_break_glass_credential(self, cluster_id: str, body: dict) -> dict:
        """Create a break-glass credential for an HCP cluster."""
        return await self._post(f'/clusters/{cluster_id}/break_glass_credentials', body)

    async def get_break_glass_credential(
        self, cluster_id: str, credential_id: str
    ) -> dict:
        """Get a specific break-glass credential."""
        return await self._get(
            f'/clusters/{cluster_id}/break_glass_credentials/{credential_id}'
        )

    # --- Tuning Configs ---

    async def list_tuning_configs(self, cluster_id: str) -> dict:
        """List tuning configurations for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/tuning_configs')

    async def create_tuning_config(self, cluster_id: str, body: dict) -> dict:
        """Create a tuning configuration for a cluster."""
        return await self._post(f'/clusters/{cluster_id}/tuning_configs', body)

    async def get_tuning_config(self, cluster_id: str, config_id: str) -> dict:
        """Get a specific tuning configuration."""
        return await self._get(f'/clusters/{cluster_id}/tuning_configs/{config_id}')

    async def update_tuning_config(
        self, cluster_id: str, config_id: str, body: dict
    ) -> dict:
        """Update a tuning configuration."""
        return await self._patch(f'/clusters/{cluster_id}/tuning_configs/{config_id}', body)

    async def delete_tuning_config(self, cluster_id: str, config_id: str) -> int:
        """Delete a tuning configuration."""
        return await self._delete(f'/clusters/{cluster_id}/tuning_configs/{config_id}')

    # --- Kubelet Config ---

    async def get_kubelet_config(self, cluster_id: str) -> dict:
        """Get the kubelet configuration for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/kubelet_config')

    async def create_kubelet_config(self, cluster_id: str, body: dict) -> dict:
        """Create a kubelet configuration for a cluster."""
        return await self._post(f'/clusters/{cluster_id}/kubelet_config', body)

    async def update_kubelet_config(self, cluster_id: str, body: dict) -> dict:
        """Update the kubelet configuration for a cluster."""
        return await self._patch(f'/clusters/{cluster_id}/kubelet_config', body)

    async def delete_kubelet_config(self, cluster_id: str) -> int:
        """Delete the kubelet configuration for a cluster."""
        return await self._delete(f'/clusters/{cluster_id}/kubelet_config')

    # --- External Auth (HCP) ---

    async def list_external_auths(self, cluster_id: str) -> dict:
        """List external authentication configurations for an HCP cluster."""
        return await self._get(f'/clusters/{cluster_id}/external_auths')

    async def create_external_auth(self, cluster_id: str, body: dict) -> dict:
        """Create an external authentication configuration for an HCP cluster."""
        return await self._post(f'/clusters/{cluster_id}/external_auths', body)

    async def delete_external_auth(self, cluster_id: str, auth_id: str) -> int:
        """Delete an external authentication configuration."""
        return await self._delete(f'/clusters/{cluster_id}/external_auths/{auth_id}')

    # --- DNS Domains ---

    async def list_dns_domains(self) -> dict:
        """List DNS domains."""
        return await self._get('/dns_domains')

    async def create_dns_domain(self, body: dict) -> dict:
        """Create a DNS domain."""
        return await self._post('/dns_domains', body)

    async def delete_dns_domain(self, domain_id: str) -> int:
        """Delete a DNS domain."""
        return await self._delete(f'/dns_domains/{domain_id}')

    # --- OIDC Configs ---

    async def list_oidc_configs(self) -> dict:
        """List OIDC configurations."""
        return await self._get('/oidc_configs')

    async def create_oidc_config(self, body: dict) -> dict:
        """Create an OIDC configuration."""
        return await self._post('/oidc_configs', body)

    async def delete_oidc_config(self, config_id: str) -> int:
        """Delete an OIDC configuration."""
        return await self._delete(f'/oidc_configs/{config_id}')

    # --- Network Verification ---

    async def create_network_verification(self, body: dict) -> dict:
        """Create a network verification request."""
        return await self._post('/network_verifications', body)

    async def list_network_verifications(self) -> dict:
        """List network verification results."""
        return await self._get('/network_verifications')

    # --- Machine Types ---

    async def list_machine_types(self, page: int = 1, size: int = 100) -> dict:
        """List available machine types."""
        params: dict = {'page': page, 'size': size}
        return await self._get('/machine_types', params=params)

    # --- Delete Protection ---

    async def get_delete_protection(self, cluster_id: str) -> dict:
        """Get the delete protection configuration for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/delete_protection')

    async def update_delete_protection(self, cluster_id: str, body: dict) -> dict:
        """Update the delete protection configuration for a cluster."""
        return await self._patch(f'/clusters/{cluster_id}/delete_protection', body)

    # --- Log Forwarders (HCP) ---

    async def list_log_forwarders(self, cluster_id: str) -> dict:
        """List log forwarders for an HCP cluster."""
        return await self._get(f'/clusters/{cluster_id}/log_forwarders')

    async def create_log_forwarder(self, cluster_id: str, body: dict) -> dict:
        """Create a log forwarder for an HCP cluster."""
        return await self._post(f'/clusters/{cluster_id}/log_forwarders', body)

    async def get_log_forwarder(self, cluster_id: str, forwarder_id: str) -> dict:
        """Get a specific log forwarder."""
        return await self._get(f'/clusters/{cluster_id}/log_forwarders/{forwarder_id}')

    async def delete_log_forwarder(self, cluster_id: str, forwarder_id: str) -> int:
        """Delete a log forwarder."""
        return await self._delete(f'/clusters/{cluster_id}/log_forwarders/{forwarder_id}')

    # --- STS Operator Roles ---

    async def list_sts_operator_roles(self, cluster_id: str) -> dict:
        """List STS operator IAM roles for a cluster."""
        return await self._get(f'/clusters/{cluster_id}/sts_operator_roles')

    # --- STS Credential Requests ---

    async def list_sts_credential_requests(self) -> dict:
        """List STS credential request templates (required operator roles)."""
        return await self._get('/aws_inquiries/sts_credential_requests')

    # --- STS Policies ---

    async def list_sts_policies(self) -> dict:
        """List all STS IAM policies (operator, account, backup roles)."""
        return await self._get('/aws_inquiries/sts_policies')

    # --- Cluster Operators (via metric queries, returns operator health) ---
    # Already exists as get_cluster_metrics(cluster_id, 'cluster_operators')
    # Adding a convenience alias:

    async def get_cluster_operators(self, cluster_id: str) -> dict:
        """Get health status of all cluster operators."""
        return await self._get(f'/clusters/{cluster_id}/metric_queries/cluster_operators')

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
