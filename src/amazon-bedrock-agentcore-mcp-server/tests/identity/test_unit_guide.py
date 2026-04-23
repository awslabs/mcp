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

"""Unit tests for Identity guide tool."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.guide import (
    IDENTITY_GUIDE,
    GuideTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.models import (
    IdentityGuideResponse,
)


class TestGetIdentityGuide:
    """Tests for get_identity_guide tool."""

    @pytest.mark.asyncio
    async def test_returns_guide_response(self, mock_ctx):
        """Returns an IdentityGuideResponse with substantial content."""
        tools = GuideTools()
        result = await tools.get_identity_guide(ctx=mock_ctx)
        assert isinstance(result, IdentityGuideResponse)
        assert result.status == 'success'
        assert len(result.guide) > 100

    def test_guide_constant_is_populated(self):
        """IDENTITY_GUIDE is a non-trivial string."""
        assert isinstance(IDENTITY_GUIDE, str)
        assert len(IDENTITY_GUIDE) > 100

    def test_guide_contains_cli_commands(self):
        """Guide includes agentcore CLI credential commands."""
        assert 'agentcore add credential' in IDENTITY_GUIDE
        assert 'agentcore remove credential' in IDENTITY_GUIDE

    def test_guide_contains_schema(self):
        """Guide includes agentcore.json schema references."""
        assert 'ApiKeyCredentialProvider' in IDENTITY_GUIDE
        assert 'OAuthCredentialProvider' in IDENTITY_GUIDE
        assert 'credentials' in IDENTITY_GUIDE

    def test_guide_contains_iam(self):
        """Guide includes IAM action references."""
        assert 'bedrock-agentcore:CreateWorkloadIdentity' in IDENTITY_GUIDE
        assert 'bedrock-agentcore:' in IDENTITY_GUIDE

    def test_guide_contains_cost_tiers(self):
        """Guide documents cost tiers for tools."""
        assert 'Read-only tools' in IDENTITY_GUIDE
        assert 'Destructive tools' in IDENTITY_GUIDE

    def test_guide_contains_troubleshooting(self):
        """Guide includes troubleshooting section."""
        assert 'Troubleshooting' in IDENTITY_GUIDE
        assert 'AccessDeniedException' in IDENTITY_GUIDE
        assert 'ConflictException' in IDENTITY_GUIDE

    def test_guide_contains_migration(self):
        """Guide includes migration notes from starter-toolkit."""
        assert 'Migration' in IDENTITY_GUIDE
        assert 'starter-toolkit' in IDENTITY_GUIDE

    def test_guide_contains_prerequisites(self):
        """Guide documents prerequisites and CLI installation note."""
        assert 'Prerequisites' in IDENTITY_GUIDE
        assert 'do NOT need the CLI' in IDENTITY_GUIDE

    def test_guide_contains_data_plane_exclusion(self):
        """Guide explains why data plane tools are not exposed."""
        # The SDK decorator names are the concrete alternative users should reach for.
        assert 'requires_access_token' in IDENTITY_GUIDE
        assert 'requires_api_key' in IDENTITY_GUIDE

    def test_guide_contains_oauth2_vendors(self):
        """Guide lists the major OAuth2 vendor values."""
        assert 'GoogleOauth2' in IDENTITY_GUIDE
        assert 'GithubOauth2' in IDENTITY_GUIDE
        assert 'CustomOauth2' in IDENTITY_GUIDE

    def test_guide_contains_security_notes(self):
        """Guide includes security guidance for secret handling."""
        # The guide must tell callers not to pass production secrets through LLM context
        # and to prefer the CLI path. The exact phrasing is flexible — these tokens
        # are load-bearing.
        lowered = IDENTITY_GUIDE.lower()
        assert 'security' in lowered
        assert 'llm' in lowered or 'context' in lowered
