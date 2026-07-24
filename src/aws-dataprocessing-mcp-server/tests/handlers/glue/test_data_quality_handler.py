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

"""Tests for the Glue Data Quality Handler."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_quality_handler import (
    GlueDataQualityHandler,
)
from unittest.mock import ANY, AsyncMock, MagicMock, patch


class TestGlueDataQualityHandler:
    """Tests for the GlueDataQualityHandler class."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_data_quality_manager(self):
        """Create a mock DataCatalogDataQualityManager."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def handler(self, mock_mcp, mock_data_quality_manager):
        """Create a GlueDataQualityHandler instance with mocked dependencies."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_quality_handler.DataCatalogDataQualityManager',
            return_value=mock_data_quality_manager,
        ):
            handler = GlueDataQualityHandler(mock_mcp)
            handler.data_catalog_data_quality_manager = mock_data_quality_manager
            return handler

    @pytest.fixture
    def handler_with_write_access(self, mock_mcp, mock_data_quality_manager):
        """Create a GlueDataQualityHandler instance with write access enabled."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_quality_handler.DataCatalogDataQualityManager',
            return_value=mock_data_quality_manager,
        ):
            handler = GlueDataQualityHandler(mock_mcp, allow_write=True)
            handler.data_catalog_data_quality_manager = mock_data_quality_manager
            return handler

    def test_initialization(self, mock_mcp):
        """Test that the handler is initialized correctly and registers its tool."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = GlueDataQualityHandler(mock_mcp)

            assert handler.mcp == mock_mcp
            assert handler.allow_write is False
            assert handler.allow_sensitive_data_access is False

            mock_mcp.tool.assert_called_once_with(name='manage_aws_glue_data_quality')

    def test_initialization_with_write_access(self, mock_mcp):
        """Test that the handler is initialized correctly with write access."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = GlueDataQualityHandler(mock_mcp, allow_write=True)

            assert handler.allow_write is True

    @pytest.mark.asyncio
    async def test_invalid_operation(self, handler, mock_ctx):
        """Test that an invalid operation returns an error response."""
        result = await handler.manage_aws_glue_data_quality(mock_ctx, operation='invalid-op')

        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_rulesets_read_access(self, handler, mock_ctx, mock_data_quality_manager):
        """Test that list-rulesets is allowed without write access and dispatches correctly."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.list_rulesets.return_value = expected_response

        result = await handler.manage_aws_glue_data_quality(
            mock_ctx, operation='list-rulesets', database_name='test-db', table_name='test-table'
        )

        mock_data_quality_manager.list_rulesets.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            max_results=ANY,
            next_token=ANY,
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_ruleset_read_access(self, handler, mock_ctx, mock_data_quality_manager):
        """Test that get-ruleset is allowed without write access and dispatches correctly."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.get_ruleset.return_value = expected_response

        result = await handler.manage_aws_glue_data_quality(
            mock_ctx, operation='get-ruleset', name='my-ruleset'
        )

        mock_data_quality_manager.get_ruleset.assert_called_once_with(
            ctx=mock_ctx, name='my-ruleset'
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_ruleset_missing_name(self, handler, mock_ctx):
        """Test that get-ruleset requires name."""
        with pytest.raises(ValueError):
            await handler.manage_aws_glue_data_quality(mock_ctx, operation='get-ruleset')

    @pytest.mark.asyncio
    async def test_create_ruleset_no_write_access(self, handler, mock_ctx):
        """Test that create-ruleset is rejected without write access."""
        result = await handler.manage_aws_glue_data_quality(
            mock_ctx,
            operation='create-ruleset',
            name='my-ruleset',
            ruleset='Rules = [ColumnCount = 10]',
        )
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_ruleset_write_access(
        self, handler_with_write_access, mock_ctx, mock_data_quality_manager
    ):
        """Test that create-ruleset dispatches correctly with write access."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.create_ruleset.return_value = expected_response

        result = await handler_with_write_access.manage_aws_glue_data_quality(
            mock_ctx,
            operation='create-ruleset',
            name='my-ruleset',
            ruleset='Rules = [ColumnCount = 10]',
            database_name='test-db',
            table_name='test-table',
        )

        mock_data_quality_manager.create_ruleset.assert_called_once_with(
            ctx=mock_ctx,
            name='my-ruleset',
            ruleset='Rules = [ColumnCount = 10]',
            description=ANY,
            database_name='test-db',
            table_name='test-table',
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_create_ruleset_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that create-ruleset requires name and ruleset."""
        with pytest.raises(ValueError):
            await handler_with_write_access.manage_aws_glue_data_quality(
                mock_ctx, operation='create-ruleset', name='my-ruleset'
            )

    @pytest.mark.asyncio
    async def test_update_ruleset_no_write_access(self, handler, mock_ctx):
        """Test that update-ruleset is rejected without write access."""
        result = await handler.manage_aws_glue_data_quality(
            mock_ctx, operation='update-ruleset', name='my-ruleset'
        )
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_ruleset_no_write_access(self, handler, mock_ctx):
        """Test that delete-ruleset is rejected without write access."""
        result = await handler.manage_aws_glue_data_quality(
            mock_ctx, operation='delete-ruleset', name='my-ruleset'
        )
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_ruleset_write_access(
        self, handler_with_write_access, mock_ctx, mock_data_quality_manager
    ):
        """Test that delete-ruleset dispatches correctly with write access."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.delete_ruleset.return_value = expected_response

        result = await handler_with_write_access.manage_aws_glue_data_quality(
            mock_ctx, operation='delete-ruleset', name='my-ruleset'
        )

        mock_data_quality_manager.delete_ruleset.assert_called_once_with(
            ctx=mock_ctx, name='my-ruleset'
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_start_ruleset_evaluation_run_no_write_access(self, handler, mock_ctx):
        """Test that start-ruleset-evaluation-run is rejected without write access."""
        result = await handler.manage_aws_glue_data_quality(
            mock_ctx,
            operation='start-ruleset-evaluation-run',
            database_name='test-db',
            table_name='test-table',
            ruleset_names=['my-ruleset'],
            role='arn:aws:iam::123456789012:role/GlueDataQualityRole',
        )
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_start_ruleset_evaluation_run_write_access(
        self, handler_with_write_access, mock_ctx, mock_data_quality_manager
    ):
        """Test that start-ruleset-evaluation-run dispatches correctly with write access."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.start_ruleset_evaluation_run.return_value = expected_response

        result = await handler_with_write_access.manage_aws_glue_data_quality(
            mock_ctx,
            operation='start-ruleset-evaluation-run',
            database_name='test-db',
            table_name='test-table',
            ruleset_names=['my-ruleset'],
            role='arn:aws:iam::123456789012:role/GlueDataQualityRole',
        )

        mock_data_quality_manager.start_ruleset_evaluation_run.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            ruleset_names=['my-ruleset'],
            role='arn:aws:iam::123456789012:role/GlueDataQualityRole',
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_start_ruleset_evaluation_run_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that start-ruleset-evaluation-run requires database_name, table_name, ruleset_names, and role."""
        with pytest.raises(ValueError):
            await handler_with_write_access.manage_aws_glue_data_quality(
                mock_ctx, operation='start-ruleset-evaluation-run', database_name='test-db'
            )

    @pytest.mark.asyncio
    async def test_get_ruleset_evaluation_run_read_access(
        self, handler, mock_ctx, mock_data_quality_manager
    ):
        """Test that get-ruleset-evaluation-run is allowed without write access."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.get_ruleset_evaluation_run.return_value = expected_response

        result = await handler.manage_aws_glue_data_quality(
            mock_ctx, operation='get-ruleset-evaluation-run', run_id='dqrun-123'
        )

        mock_data_quality_manager.get_ruleset_evaluation_run.assert_called_once_with(
            ctx=mock_ctx, run_id='dqrun-123'
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_ruleset_evaluation_run_missing_run_id(self, handler, mock_ctx):
        """Test that get-ruleset-evaluation-run requires run_id."""
        with pytest.raises(ValueError):
            await handler.manage_aws_glue_data_quality(
                mock_ctx, operation='get-ruleset-evaluation-run'
            )

    @pytest.mark.asyncio
    async def test_list_ruleset_evaluation_runs_read_access(
        self, handler, mock_ctx, mock_data_quality_manager
    ):
        """Test that list-ruleset-evaluation-runs dispatches correctly."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.list_ruleset_evaluation_runs.return_value = expected_response

        result = await handler.manage_aws_glue_data_quality(
            mock_ctx,
            operation='list-ruleset-evaluation-runs',
            database_name='test-db',
            table_name='test-table',
        )

        mock_data_quality_manager.list_ruleset_evaluation_runs.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            max_results=ANY,
            next_token=ANY,
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_list_ruleset_evaluation_runs_missing_required_params(self, handler, mock_ctx):
        """Test that list-ruleset-evaluation-runs requires database_name and table_name."""
        with pytest.raises(ValueError):
            await handler.manage_aws_glue_data_quality(
                mock_ctx, operation='list-ruleset-evaluation-runs'
            )

    @pytest.mark.asyncio
    async def test_get_data_quality_result_read_access(
        self, handler, mock_ctx, mock_data_quality_manager
    ):
        """Test that get-data-quality-result dispatches correctly."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.get_data_quality_result.return_value = expected_response

        result = await handler.manage_aws_glue_data_quality(
            mock_ctx, operation='get-data-quality-result', result_id='dqresult-1'
        )

        mock_data_quality_manager.get_data_quality_result.assert_called_once_with(
            ctx=mock_ctx, result_id='dqresult-1'
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_get_data_quality_result_missing_result_id(self, handler, mock_ctx):
        """Test that get-data-quality-result requires result_id."""
        with pytest.raises(ValueError):
            await handler.manage_aws_glue_data_quality(
                mock_ctx, operation='get-data-quality-result'
            )

    @pytest.mark.asyncio
    async def test_list_data_quality_results_read_access(
        self, handler, mock_ctx, mock_data_quality_manager
    ):
        """Test that list-data-quality-results dispatches correctly."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.list_data_quality_results.return_value = expected_response

        result = await handler.manage_aws_glue_data_quality(
            mock_ctx, operation='list-data-quality-results'
        )

        mock_data_quality_manager.list_data_quality_results.assert_called_once_with(
            ctx=mock_ctx,
            database_name=ANY,
            table_name=ANY,
            max_results=ANY,
            next_token=ANY,
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_batch_get_data_quality_result_read_access(
        self, handler, mock_ctx, mock_data_quality_manager
    ):
        """Test that batch-get-data-quality-result dispatches correctly."""
        expected_response = MagicMock()
        expected_response.isError = False
        mock_data_quality_manager.batch_get_data_quality_result.return_value = expected_response

        result = await handler.manage_aws_glue_data_quality(
            mock_ctx, operation='batch-get-data-quality-result', result_ids=['dqresult-1']
        )

        mock_data_quality_manager.batch_get_data_quality_result.assert_called_once_with(
            ctx=mock_ctx, result_ids=['dqresult-1']
        )
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_batch_get_data_quality_result_missing_result_ids(self, handler, mock_ctx):
        """Test that batch-get-data-quality-result requires result_ids."""
        with pytest.raises(ValueError):
            await handler.manage_aws_glue_data_quality(
                mock_ctx, operation='batch-get-data-quality-result'
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self, handler, mock_ctx, mock_data_quality_manager):
        """Test that unexpected exceptions are caught and returned as an error response."""
        mock_data_quality_manager.list_rulesets.side_effect = Exception('Unexpected error')

        result = await handler.manage_aws_glue_data_quality(mock_ctx, operation='list-rulesets')

        assert result.isError is True
        assert 'Error in manage_aws_glue_data_quality: Unexpected error' in result.content[0].text
