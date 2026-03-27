"""Unit tests for sparse GSI support (exclude_none behavior)."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.languages.python.base_repository import (
    BaseRepository,
    ConfigurableEntity,
    EntityConfig,
)
from unittest.mock import patch


class SparseTestEntity(ConfigurableEntity):
    """Test entity with optional fields for sparse GSI testing."""

    user_id: str
    watch_key: str
    brand_id: str | None = None
    notes: str | None = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        """Get entity configuration for key generation."""
        return EntityConfig(
            entity_type='WATCH',
            pk_builder=lambda self: f'USER#{self.user_id}',
            pk_lookup_builder=lambda user_id: f'USER#{user_id}',
            sk_builder=lambda self: f'WATCH#{self.watch_key}',
            sk_lookup_builder=lambda watch_key: f'WATCH#{watch_key}',
        )


class TestSparseGSICreate:
    """Test create() method excludes None values for sparse GSI support."""

    def test_create_excludes_none_values(self):
        """Test create() excludes None values from DynamoDB item."""
        entity = SparseTestEntity(user_id='user123', watch_key='watch1', brand_id=None, notes=None)
        repo = BaseRepository(SparseTestEntity, 'TestTable', 'pk', 'sk')

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.create(entity)

            # Verify put_item was called
            assert mock_put.called

            # Get the Item that was passed to put_item
            call_kwargs = mock_put.call_args[1]
            item = call_kwargs['Item']

            # Verify None values are excluded
            assert 'brand_id' not in item
            assert 'notes' not in item

            # Verify required fields are present
            assert 'pk' in item
            assert 'sk' in item
            assert item['pk'] == 'USER#user123'
            assert item['sk'] == 'WATCH#watch1'
            assert item['version'] == 1

    def test_create_includes_non_none_values(self):
        """Test create() includes fields with actual values."""
        entity = SparseTestEntity(
            user_id='user123', watch_key='watch1', brand_id='nike', notes='Great brand'
        )
        repo = BaseRepository(SparseTestEntity, 'TestTable', 'pk', 'sk')

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.create(entity)

            call_kwargs = mock_put.call_args[1]
            item = call_kwargs['Item']

            # Verify all non-None values are included
            assert item['brand_id'] == 'nike'
            assert item['notes'] == 'Great brand'

    def test_create_with_mixed_none_and_values(self):
        """Test create() with mix of None and actual values."""
        entity = SparseTestEntity(
            user_id='user123', watch_key='watch1', brand_id='nike', notes=None
        )
        repo = BaseRepository(SparseTestEntity, 'TestTable', 'pk', 'sk')

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.create(entity)

            call_kwargs = mock_put.call_args[1]
            item = call_kwargs['Item']

            # brand_id should be included
            assert item['brand_id'] == 'nike'

            # notes should be excluded
            assert 'notes' not in item


class TestSparseGSIUpdate:
    """Test update() method excludes None values for sparse GSI support."""

    def test_update_excludes_none_values(self):
        """Test update() excludes None values from DynamoDB item."""
        entity = SparseTestEntity(user_id='user123', watch_key='watch1', brand_id=None, notes=None)
        entity.version = 1
        repo = BaseRepository(SparseTestEntity, 'TestTable', 'pk', 'sk')

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.update(entity)

            call_kwargs = mock_put.call_args[1]
            item = call_kwargs['Item']

            # Verify None values are excluded
            assert 'brand_id' not in item
            assert 'notes' not in item

            # Verify version is incremented
            assert item['version'] == 2

    def test_update_removes_fields_by_setting_none(self):
        """Test update() removes fields from DynamoDB when set to None.

        This tests the sparse GSI behavior on updates - setting a GSI key field
        to None will remove the item from that GSI.
        """
        # Start with an entity that has brand_id
        entity = SparseTestEntity(
            user_id='user123', watch_key='watch1', brand_id='nike', notes='test'
        )
        entity.version = 1
        repo = BaseRepository(SparseTestEntity, 'TestTable', 'pk', 'sk')

        # Update: Remove brand_id by setting to None
        entity.brand_id = None

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.update(entity)

            call_kwargs = mock_put.call_args[1]
            item = call_kwargs['Item']

            # brand_id should NOT be in the item (will be removed from DynamoDB)
            assert 'brand_id' not in item

            # notes should still be present
            assert item['notes'] == 'test'

    def test_update_includes_non_none_values(self):
        """Test update() includes fields with actual values."""
        entity = SparseTestEntity(
            user_id='user123', watch_key='watch1', brand_id='nike', notes='Great brand'
        )
        entity.version = 1
        repo = BaseRepository(SparseTestEntity, 'TestTable', 'pk', 'sk')

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.update(entity)

            call_kwargs = mock_put.call_args[1]
            item = call_kwargs['Item']

            # Verify all non-None values are included
            assert item['brand_id'] == 'nike'
            assert item['notes'] == 'Great brand'


class TestSparseGSIBehavior:
    """Test overall sparse GSI behavior."""

    def test_sparse_gsi_lifecycle(self):
        """Test complete lifecycle: create without GSI key, update to add it, update to remove it."""
        repo = BaseRepository(SparseTestEntity, 'TestTable', 'pk', 'sk')

        # Step 1: Create without brand_id (not in GSI)
        entity = SparseTestEntity(user_id='user123', watch_key='watch1', brand_id=None)

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.create(entity)
            item = mock_put.call_args[1]['Item']
            assert 'brand_id' not in item  # Not indexed in WatchesByBrand GSI

        # Step 2: Update to add brand_id (now in GSI)
        entity.brand_id = 'nike'
        entity.version = 1

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.update(entity)
            item = mock_put.call_args[1]['Item']
            assert item['brand_id'] == 'nike'  # Now indexed in WatchesByBrand GSI

        # Step 3: Update to remove brand_id (removed from GSI)
        entity.brand_id = None
        entity.version = 2

        with patch.object(repo.table, 'put_item') as mock_put:
            repo.update(entity)
            item = mock_put.call_args[1]['Item']
            assert 'brand_id' not in item  # Removed from WatchesByBrand GSI
