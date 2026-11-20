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

"""Regression tests: validate FES request bodies against the C2J service model.

Uses botocore's ParamValidator against the vendored service-2.json to catch
parameter mismatches that mocked tests would miss.
"""
# ruff: noqa: D101, D102, D103

import pytest
from tests.service_model_validation import _CLIENT, validate_request


class TestRegressions:
    def test_file_metadata_rejects_fileName(self):
        """Bug fix: fileMetadata.fileName does not exist in the service model."""
        with pytest.raises(ValueError, match='fileName'):
            validate_request(
                'CreateArtifactUploadUrl',
                {
                    'workspaceId': 'w',
                    'contentDigest': {'Sha256': 'abc'},
                    'artifactReference': {
                        'artifactType': {'categoryType': 'CUSTOMER_INPUT', 'fileType': 'JSON'}
                    },
                    'fileMetadata': {'fileName': 'bad.json', 'path': 'bad.json'},
                },
            )

    def test_list_plan_updates_requires_timestamp_and_plan_version(self):
        """Bug fix: ListPlanUpdates requires timestamp and planVersion."""
        with pytest.raises(ValueError, match='timestamp'):
            validate_request('ListPlanUpdates', {'workspaceId': 'w', 'jobId': 'j'})


_ENGAGEMENT_OPERATIONS = {
    'AcceptEngagementInvitation',
    'AddEngagementTenant',
    'AddEngagementUser',
    'AddEngagementWorkspace',
    'CreateEngagement',
    'GetEngagement',
    'ListEngagementInvitations',
    'ListEngagementTenants',
    'ListEngagementUsers',
    'ListEngagementWorkspaces',
    'ListEngagements',
    'ListEngagementsForWorkspace',
    'ListPartnerTypes',
    'RejectEngagementInvitation',
    'RemoveEngagementTenant',
    'RemoveEngagementUser',
    'RemoveEngagementWorkspace',
    'UpdateEngagement',
}


class TestEngagementContracts:
    def test_all_exposed_engagement_operations_are_vendored(self):
        operations = set(_CLIENT._service_model.operation_names)
        assert _ENGAGEMENT_OPERATIONS <= operations
        assert 'TerminateEngagement' not in operations
        assert 'UpdateEngagementWorkspace' not in operations

    @pytest.mark.parametrize(
        'operation,body',
        [
            (
                'CreateEngagement',
                {
                    'name': 'Migration',
                    'description': 'Migration engagement',
                    'tenantType': 'PARTNER',
                    'partnerType': 'CONSULTING_PARTNER',
                },
            ),
            ('GetEngagement', {'engagementId': 'e-1'}),
            ('UpdateEngagement', {'engagementId': 'e-1', 'name': 'Updated'}),
            ('ListEngagements', {}),
            (
                'AddEngagementTenant',
                {
                    'engagementId': 'e-1',
                    'targetTenantId': 't-2',
                    'type': 'PARTNER',
                    'description': 'Delivery partner',
                    'customerConsent': 'GRANTED',
                    'partnerIntent': 'PERFORM_ASSESSMENT_AND_MIGRATION',
                },
            ),
            ('RemoveEngagementTenant', {'engagementId': 'e-1', 'targetTenantId': 't-2'}),
            ('ListEngagementTenants', {'engagementId': 'e-1'}),
            ('ListEngagementInvitations', {}),
            (
                'AcceptEngagementInvitation',
                {'engagementId': 'e-1', 'partnerType': 'DISTRIBUTOR'},
            ),
            ('RejectEngagementInvitation', {'engagementId': 'e-1'}),
            (
                'AddEngagementUser',
                {'engagementId': 'e-1', 'targetUserId': 'u-2', 'role': 'LEAD'},
            ),
            ('ListEngagementUsers', {'engagementId': 'e-1'}),
            ('RemoveEngagementUser', {'engagementId': 'e-1', 'targetUserId': 'u-2'}),
            (
                'AddEngagementWorkspace',
                {
                    'engagementId': 'e-1',
                    'workspaceId': '00000000-0000-0000-0000-000000000001',
                },
            ),
            ('ListEngagementWorkspaces', {'engagementId': 'e-1'}),
            (
                'RemoveEngagementWorkspace',
                {
                    'engagementId': 'e-1',
                    'workspaceId': '00000000-0000-0000-0000-000000000001',
                },
            ),
            (
                'ListEngagementsForWorkspace',
                {'workspaceId': '00000000-0000-0000-0000-000000000001'},
            ),
            ('ListPartnerTypes', {}),
        ],
    )
    def test_request_body_matches_c2j(self, operation, body):
        validate_request(operation, body)

    def test_invitation_consent_metadata_is_vendored(self):
        service_model = _CLIENT._service_model
        add_tenant = service_model.shape_for('AddEngagementTenantRequest')
        tenant_summary = service_model.shape_for('TenantSummary')

        assert {'customerConsent', 'partnerIntent'} <= set(add_tenant.members)
        assert {
            'consentedByUserId',
            'consentedAt',
            'partnerIntent',
            'invitedByUserId',
        } <= set(tenant_summary.members)

    def test_add_workspace_does_not_accept_partner_tenant(self):
        add_workspace = _CLIENT._service_model.shape_for('AddEngagementWorkspaceRequest')
        assert 'partnerTenantId' not in add_workspace.members

    def test_engagement_id_uses_safe_ascii_pattern(self):
        engagement_id = _CLIENT._service_model.shape_for('EngagementId')
        assert engagement_id.metadata['pattern'] == '^[a-z0-9-]+$'
