"""Tests for read-only mode functionality."""

import pytest
from awslabs.amazon_datazone_mcp_server.context import Context


class TestReadOnlyMode:
    """Test read-only mode blocks write operations."""

    def test_context_initialization_defaults(self):
        """Test that Context defaults to read-only mode."""
        # Reset the Context class state to its default
        Context._readonly = True  # Reset to default

        # Create a fresh context
        test_context = Context()
        # The default should be read-only
        assert test_context._readonly

    def test_context_initialization_with_readonly_false(self):
        """Test that Context can be initialized with readonly=False."""
        Context.initialize(readonly=False)
        assert not Context.readonly_mode()

    def test_context_initialization_with_readonly_true(self):
        """Test that Context can be initialized with readonly=True."""
        Context.initialize(readonly=True)
        assert Context.readonly_mode()

    def test_check_write_permission_allows_when_readonly_false(self):
        """Test that write operations are allowed when readonly=False."""
        Context.initialize(readonly=False)
        # This should not raise an exception
        Context.check_write_permission('test_operation')

    def test_check_write_permission_blocks_when_readonly_true(self):
        """Test that write operations are blocked when readonly=True."""
        Context.initialize(readonly=True)

        with pytest.raises(ValueError) as exc_info:
            Context.check_write_permission('test_operation')

        error_message = str(exc_info.value)
        assert 'read-only mode' in error_message
        assert '--allow-writes' in error_message
        assert 'test_operation' in error_message

    @pytest.mark.asyncio
    async def test_create_domain_blocked_in_readonly_mode(
        self, mcp_server_with_tools, tool_extractor, sample_domain_data
    ):
        """Test that create_domain is blocked in read-only mode."""
        # Enable read-only mode
        original_readonly = Context._readonly
        Context.initialize(readonly=True)

        try:
            create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

            with pytest.raises(ValueError) as exc_info:
                await create_domain(
                    name=sample_domain_data['name'],
                    domain_execution_role=sample_domain_data['domain_execution_role'],
                    service_role=sample_domain_data['service_role'],
                )

            assert 'read-only mode' in str(exc_info.value)

        finally:
            # Restore original state
            Context.initialize(readonly=original_readonly)

    @pytest.mark.asyncio
    async def test_create_domain_unit_blocked_in_readonly_mode(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test that create_domain_unit is blocked in read-only mode."""
        # Enable read-only mode
        original_readonly = Context._readonly
        Context.initialize(readonly=True)

        try:
            create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

            with pytest.raises(ValueError) as exc_info:
                await create_domain_unit(
                    domain_identifier=test_data_helper.get_domain_id(),
                    name='Test Unit',
                    parent_domain_unit_identifier='parent_unit_123',
                )

            assert 'read-only mode' in str(exc_info.value)

        finally:
            # Restore original state
            Context.initialize(readonly=original_readonly)

    @pytest.mark.asyncio
    async def test_create_project_blocked_in_readonly_mode(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test that create_project is blocked in read-only mode."""
        # Enable read-only mode
        original_readonly = Context._readonly
        Context.initialize(readonly=True)

        try:
            create_project = tool_extractor(mcp_server_with_tools, 'create_project')

            with pytest.raises(ValueError) as exc_info:
                await create_project(
                    domain_identifier=test_data_helper.get_domain_id(), name='Test Project'
                )

            assert 'read-only mode' in str(exc_info.value)

        finally:
            # Restore original state
            Context.initialize(readonly=original_readonly)

    @pytest.mark.asyncio
    async def test_create_asset_blocked_in_readonly_mode(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test that create_asset is blocked in read-only mode."""
        # Enable read-only mode
        original_readonly = Context._readonly
        Context.initialize(readonly=True)

        try:
            create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

            with pytest.raises(ValueError) as exc_info:
                await create_asset(
                    domain_identifier=test_data_helper.get_domain_id(),
                    name='Test Asset',
                    type_identifier='amazon.datazone.S3Asset',
                    owning_project_identifier=test_data_helper.get_project_id(),
                )

            assert 'read-only mode' in str(exc_info.value)

        finally:
            # Restore original state
            Context.initialize(readonly=original_readonly)

    @pytest.mark.asyncio
    async def test_create_glossary_blocked_in_readonly_mode(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test that create_glossary is blocked in read-only mode."""
        # Enable read-only mode
        original_readonly = Context._readonly
        Context.initialize(readonly=True)

        try:
            create_glossary = tool_extractor(mcp_server_with_tools, 'create_glossary')

            with pytest.raises(ValueError) as exc_info:
                await create_glossary(
                    domain_identifier=test_data_helper.get_domain_id(),
                    name='Test Glossary',
                    owning_project_identifier=test_data_helper.get_project_id(),
                )

            assert 'read-only mode' in str(exc_info.value)

        finally:
            # Restore original state
            Context.initialize(readonly=original_readonly)

    @pytest.mark.asyncio
    async def test_read_operations_work_in_readonly_mode(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test that read operations still work in read-only mode."""
        # Enable read-only mode
        original_readonly = Context._readonly
        Context.initialize(readonly=True)

        try:
            # These should all work fine in read-only mode
            get_domain = tool_extractor(mcp_server_with_tools, 'get_domain')
            get_project = tool_extractor(mcp_server_with_tools, 'get_project')
            get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

            # These should not raise any exceptions
            await get_domain(test_data_helper.get_domain_id())
            await get_project(test_data_helper.get_domain_id(), test_data_helper.get_project_id())
            await get_asset(test_data_helper.get_domain_id(), test_data_helper.get_asset_id())

        finally:
            # Restore original state
            Context.initialize(readonly=original_readonly)
