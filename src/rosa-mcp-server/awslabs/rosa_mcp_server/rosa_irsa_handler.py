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

"""IRSA (IAM Roles for Service Accounts) handler for the ROSA MCP Server.

Automates the setup of fine-grained IAM permissions for Kubernetes pods
running on ROSA clusters using OIDC federation and STS.
"""

import boto3
import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaIRSAHandler:
    """Handler for IRSA (IAM Roles for Service Accounts) operations on ROSA clusters."""

    def __init__(
        self,
        mcp,
        ocm_client: OCMClient,
        allow_write: bool = False,
    ):
        """Initialize the IRSA handler.

        Args:
            mcp: The FastMCP server instance.
            ocm_client: Shared OCM API client.
            allow_write: Whether write operations are permitted.
        """
        self.mcp = mcp
        self.ocm = ocm_client
        self.allow_write = allow_write

        self.mcp.tool(name='rosa_configure_irsa')(self.rosa_configure_irsa)
        self.mcp.tool(name='rosa_describe_irsa')(self.rosa_describe_irsa)
        self.mcp.tool(name='rosa_delete_irsa')(self.rosa_delete_irsa)

    async def _get_oidc_issuer(self, cluster_id: str) -> str:
        """Extract the OIDC issuer URL from cluster details."""
        cluster = await self.ocm.get_cluster(cluster_id)
        # HCP clusters: aws.sts.oidc_endpoint_url
        # Classic STS: aws.sts.oidc_endpoint_url or identity_providers OIDC
        aws_config = cluster.get('aws', {})
        sts_config = aws_config.get('sts', {})
        oidc_url = sts_config.get('oidc_endpoint_url', '')
        if not oidc_url:
            raise ValueError(
                f'Cluster {cluster_id} does not have an OIDC endpoint. '
                'IRSA requires a ROSA STS cluster.'
            )
        # Strip https:// prefix for IAM trust policy
        return oidc_url.removeprefix('https://')

    def _build_trust_policy(
        self,
        account_id: str,
        oidc_issuer: str,
        namespace: str,
        service_account: str,
    ) -> dict:
        """Build the IAM trust policy for IRSA."""
        return {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'Federated': f'arn:aws:iam::{account_id}:oidc-provider/{oidc_issuer}',
                    },
                    'Action': 'sts:AssumeRoleWithWebIdentity',
                    'Condition': {
                        'StringEquals': {
                            f'{oidc_issuer}:sub': f'system:serviceaccount:{namespace}:{service_account}',
                        },
                    },
                },
            ],
        }

    async def rosa_configure_irsa(
        self,
        ctx: Context,
        cluster_id: str,
        namespace: str,
        service_account: str,
        role_name: str,
        policy_arn: str,
        region: Optional[str] = None,
        annotate_service_account: bool = True,
    ) -> list[TextContent]:
        """Configure IRSA for a ROSA workload (create IAM role + annotate service account).

        Creates an IAM role with an OIDC trust policy scoped to the specified
        namespace/service-account, attaches the given policy, and optionally
        annotates the Kubernetes service account with the role ARN.

        Args:
            ctx: MCP context.
            cluster_id: ROSA cluster ID (from rosa_list_clusters).
            namespace: Kubernetes namespace of the service account.
            service_account: Name of the Kubernetes service account.
            role_name: IAM role name to create.
            policy_arn: ARN of the IAM policy to attach to the role.
            region: AWS region. If omitted, uses default.
            annotate_service_account: Whether to annotate the K8s SA (requires --allow-write).
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        try:
            # 1. Get OIDC issuer from cluster
            oidc_issuer = await self._get_oidc_issuer(cluster_id)

            # 2. Get AWS account ID
            kwargs = {}
            if region:
                kwargs['region_name'] = region
            sts_client = boto3.client('sts', **kwargs)
            account_id = sts_client.get_caller_identity()['Account']

            # 3. Create IAM role with trust policy
            iam_client = boto3.client('iam', **kwargs)
            trust_policy = self._build_trust_policy(
                account_id, oidc_issuer, namespace, service_account
            )

            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f'IRSA role for {namespace}/{service_account} on ROSA cluster {cluster_id}',
                Tags=[
                    {'Key': 'rosa_cluster_id', 'Value': cluster_id},
                    {'Key': 'rosa_managed', 'Value': 'true'},
                    {'Key': 'irsa_namespace', 'Value': namespace},
                    {'Key': 'irsa_service_account', 'Value': service_account},
                ],
            )

            # 4. Attach policy
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

            role_arn = f'arn:aws:iam::{account_id}:role/{role_name}'

            # 5. Annotate the K8s service account (if requested)
            k8s_annotated = False
            if annotate_service_account:
                try:
                    import tempfile
                    from kubernetes import client as k8s_client_lib
                    from kubernetes import config as k8s_config

                    creds = await self.ocm.get_cluster_credentials(cluster_id)
                    kubeconfig_data = creds.get('kubeconfig', '')
                    if kubeconfig_data:
                        with tempfile.NamedTemporaryFile(
                            mode='w', suffix='.yaml', delete=False
                        ) as f:
                            f.write(kubeconfig_data)
                            f.flush()
                            k8s_config.load_kube_config(config_file=f.name)

                        v1 = k8s_client_lib.CoreV1Api()
                        body = {
                            'metadata': {
                                'annotations': {
                                    'eks.amazonaws.com/role-arn': role_arn,
                                }
                            }
                        }
                        v1.patch_namespaced_service_account(
                            name=service_account, namespace=namespace, body=body
                        )
                        k8s_annotated = True
                except Exception:
                    # Non-fatal: role was created, annotation can be done manually
                    k8s_annotated = False

            return [TextContent(
                type='text',
                text=json.dumps({
                    'message': 'IRSA configured successfully.',
                    'role_name': role_name,
                    'role_arn': role_arn,
                    'oidc_issuer': oidc_issuer,
                    'namespace': namespace,
                    'service_account': service_account,
                    'policy_arn': policy_arn,
                    'k8s_service_account_annotated': k8s_annotated,
                    'annotation': f'eks.amazonaws.com/role-arn: {role_arn}',
                }),
            )]

        except Exception as e:
            return [TextContent(type='text', text=f'Error configuring IRSA: {str(e)}')]

    async def rosa_describe_irsa(
        self,
        ctx: Context,
        cluster_id: str,
        namespace: str,
        service_account: str,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """Describe IRSA configuration for a service account on a ROSA cluster.

        Shows the OIDC issuer, associated IAM role (if any), attached policies,
        and trust policy details.

        Args:
            ctx: MCP context.
            cluster_id: ROSA cluster ID.
            namespace: Kubernetes namespace.
            service_account: Kubernetes service account name.
            region: AWS region.
        """
        try:
            oidc_issuer = await self._get_oidc_issuer(cluster_id)

            kwargs = {}
            if region:
                kwargs['region_name'] = region
            iam_client = boto3.client('iam', **kwargs)

            # Find roles that trust this OIDC issuer + SA combination
            expected_sub = f'system:serviceaccount:{namespace}:{service_account}'
            matching_roles = []

            paginator = iam_client.get_paginator('list_roles')
            for page in paginator.paginate():
                for role in page['Roles']:
                    trust_doc = role.get('AssumeRolePolicyDocument', {})
                    if isinstance(trust_doc, str):
                        trust_doc = json.loads(trust_doc)
                    for stmt in trust_doc.get('Statement', []):
                        principal = stmt.get('Principal', {})
                        federated = principal.get('Federated', '')
                        if oidc_issuer not in federated:
                            continue
                        condition = stmt.get('Condition', {})
                        string_equals = condition.get('StringEquals', {})
                        sub_value = string_equals.get(f'{oidc_issuer}:sub', '')
                        if sub_value == expected_sub:
                            # Get attached policies
                            attached = iam_client.list_attached_role_policies(
                                RoleName=role['RoleName']
                            ).get('AttachedPolicies', [])
                            matching_roles.append({
                                'RoleName': role['RoleName'],
                                'Arn': role['Arn'],
                                'AttachedPolicies': attached,
                            })

            return [TextContent(
                type='text',
                text=json.dumps({
                    'cluster_id': cluster_id,
                    'oidc_issuer': oidc_issuer,
                    'namespace': namespace,
                    'service_account': service_account,
                    'matching_roles': matching_roles,
                    'role_count': len(matching_roles),
                }, default=str),
            )]

        except Exception as e:
            return [TextContent(type='text', text=f'Error describing IRSA: {str(e)}')]

    async def rosa_delete_irsa(
        self,
        ctx: Context,
        role_name: str,
        cluster_id: Optional[str] = None,
        namespace: Optional[str] = None,
        service_account: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """Delete an IRSA IAM role and optionally remove the service account annotation.

        Detaches all policies and deletes the IAM role. If cluster_id, namespace,
        and service_account are provided, also removes the annotation from the K8s SA.

        Args:
            ctx: MCP context.
            role_name: IAM role name to delete.
            cluster_id: ROSA cluster ID (optional, for removing SA annotation).
            namespace: Kubernetes namespace (optional).
            service_account: Kubernetes service account name (optional).
            region: AWS region.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region
            iam_client = boto3.client('iam', **kwargs)

            # Detach all managed policies
            attached = iam_client.list_attached_role_policies(
                RoleName=role_name
            ).get('AttachedPolicies', [])
            for policy in attached:
                iam_client.detach_role_policy(
                    RoleName=role_name, PolicyArn=policy['PolicyArn']
                )

            # Delete inline policies
            inline = iam_client.list_role_policies(
                RoleName=role_name
            ).get('PolicyNames', [])
            for policy_name in inline:
                iam_client.delete_role_policy(
                    RoleName=role_name, PolicyName=policy_name
                )

            # Delete the role
            iam_client.delete_role(RoleName=role_name)

            # Remove K8s annotation if cluster info provided
            k8s_annotation_removed = False
            if cluster_id and namespace and service_account:
                try:
                    import tempfile
                    from kubernetes import client as k8s_client_lib
                    from kubernetes import config as k8s_config

                    creds = await self.ocm.get_cluster_credentials(cluster_id)
                    kubeconfig_data = creds.get('kubeconfig', '')
                    if kubeconfig_data:
                        with tempfile.NamedTemporaryFile(
                            mode='w', suffix='.yaml', delete=False
                        ) as f:
                            f.write(kubeconfig_data)
                            f.flush()
                            k8s_config.load_kube_config(config_file=f.name)

                        v1 = k8s_client_lib.CoreV1Api()
                        body = {
                            'metadata': {
                                'annotations': {
                                    'eks.amazonaws.com/role-arn': None,
                                }
                            }
                        }
                        v1.patch_namespaced_service_account(
                            name=service_account, namespace=namespace, body=body
                        )
                        k8s_annotation_removed = True
                except Exception:
                    pass

            return [TextContent(
                type='text',
                text=json.dumps({
                    'message': f'IRSA role "{role_name}" deleted successfully.',
                    'role_name': role_name,
                    'policies_detached': len(attached) + len(inline),
                    'k8s_annotation_removed': k8s_annotation_removed,
                }),
            )]

        except Exception as e:
            return [TextContent(type='text', text=f'Error deleting IRSA role: {str(e)}')]
