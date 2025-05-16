import asyncio
import boto3
import pytest
import pytest_asyncio
from awslabs.dynamodb_mcp_server.server import (
    create_backup,
    create_table,
    delete_item,
    delete_table,
    describe_backup,
    describe_continuous_backups,
    describe_endpoints,
    describe_limits,
    describe_table,
    describe_time_to_live,
    get_item,
    get_resource_policy,
    list_backups,
    list_tables,
    list_tags_of_resource,
    put_item,
    put_resource_policy,
    query,
    restore_table_from_backup,
    scan,
    tag_resource,
    untag_resource,
    update_continuous_backups,
    update_item,
    update_table,
    update_time_to_live,
)
from moto import mock_aws


@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os

    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'


@pytest_asyncio.fixture
async def dynamodb(aws_credentials):
    """DynamoDB resource."""
    with mock_aws():
        yield boto3.client('dynamodb', region_name='us-west-2')


async def wait_for_table(table_name: str, region_name: str = 'us-west-2'):
    """Wait for a table to become active."""
    for _ in range(10):  # Try up to 10 times
        result = await describe_table(table_name=table_name, region_name=region_name)
        if 'error' not in result and result.get('TableStatus') == 'ACTIVE':
            return result
        await asyncio.sleep(1)  # Wait 1 second between checks
    raise Exception('Table did not become active in time')


@pytest_asyncio.fixture
async def test_table(dynamodb):
    """Create a test table for use in other tests."""
    # Create the table
    result = await create_table(
        table_name='TestTable',
        attribute_definitions=[
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'sort', 'AttributeType': 'S'},
        ],
        key_schema=[
            {'AttributeName': 'id', 'KeyType': 'HASH'},
            {'AttributeName': 'sort', 'KeyType': 'RANGE'},
        ],
        billing_mode='PROVISIONED',
        provisioned_throughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
        global_secondary_indexes=None,
        region_name='us-west-2',
    )

    if 'error' in result:
        raise Exception(f'Failed to create table: {result["error"]}')

    # Wait for table to become active
    table_info = await wait_for_table('TestTable', 'us-west-2')
    return table_info


@pytest.mark.asyncio
async def test_create_table_with_gsi(dynamodb):
    """Test creating a table with a global secondary index."""
    # Create table with GSI
    result = await create_table(
        table_name='TestTableWithGSI',
        attribute_definitions=[
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'},
        ],
        key_schema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        billing_mode='PROVISIONED',  # Changed to PROVISIONED since we need to provide throughput
        provisioned_throughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},  # Minimal values
        global_secondary_indexes=[
            {
                'IndexName': 'EmailIndex',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
            }
        ],
        region_name='us-west-2',
    )

    # Check if we got an error
    if 'error' in result:
        pytest.fail(f'Failed to create table: {result["error"]}')

    # Assert table properties
    assert result.get('TableName') == 'TestTableWithGSI'
    assert result.get('TableStatus') in [
        'CREATING',
        'ACTIVE',
    ]  # moto might return ACTIVE immediately

    # Assert GSI properties
    gsis = result.get('GlobalSecondaryIndexes', [])
    assert len(gsis) == 1, 'Expected 1 GSI'
    gsi = gsis[0]
    assert gsi['IndexName'] == 'EmailIndex'
    assert result.get('BillingModeSummary', {}).get('BillingMode') == 'PROVISIONED'


@pytest.mark.asyncio
async def test_put_item(test_table):
    """Test putting an item into a table with condition expression."""
    # Test 1: Put item with condition that it doesn't exist
    result = await put_item(
        table_name='TestTable',
        item={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}, 'data': {'S': 'test data'}},
        region_name='us-west-2',
        condition_expression='attribute_not_exists(id) AND attribute_not_exists(#sort)',
        expression_attribute_names={'#sort': 'sort'},
        expression_attribute_values=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to put item: {result["error"]}')

    # DynamoDB returns empty response on success unless ReturnValues is specified
    assert 'error' not in result

    # Test 2: Try to put same item again, should fail due to condition
    result = await put_item(
        table_name='TestTable',
        item={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}, 'data': {'S': 'new data'}},
        region_name='us-west-2',
        condition_expression='attribute_not_exists(id) AND attribute_not_exists(#sort)',
        expression_attribute_names={'#sort': 'sort'},
        expression_attribute_values=None,
    )

    # Verify the conditional put failed
    assert 'error' in result
    assert 'ConditionalCheckFailedException' in str(result['error'])

    # Verify the original item is unchanged
    get_result = await get_item(
        table_name='TestTable',
        key={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}},
        expression_attribute_names=None,
        projection_expression=None,
        region_name='us-west-2',
    )

    assert get_result['Item']['data']['S'] == 'test data'


@pytest.mark.asyncio
async def test_get_item(test_table):
    """Test getting an item from a table."""
    # First put an item
    await put_item(
        table_name='TestTable',
        item={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}, 'data': {'S': 'test data'}},
        region_name='us-west-2',
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None,
    )

    # Then get the item
    result = await get_item(
        table_name='TestTable',
        key={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}},
        region_name='us-west-2',
        expression_attribute_names=None,
        projection_expression=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to get item: {result["error"]}')

    assert result['Item']['id']['S'] == 'test1'
    assert result['Item']['sort']['S'] == 'data1'
    assert result['Item']['data']['S'] == 'test data'


@pytest.mark.asyncio
async def test_update_item(test_table):
    """Test updating an item in a table with conditional expression."""
    # First put an item
    await put_item(
        table_name='TestTable',
        item={
            'id': {'S': 'test1'},
            'sort': {'S': 'data1'},
            'data': {'S': 'old data'},
            'status': {'S': 'active'},
            'version': {'N': '1'},
        },
        region_name='us-west-2',
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None,
    )

    # Test 1: Basic update without condition
    result = await update_item(
        table_name='TestTable',
        key={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}},
        update_expression='SET #d = :new_data',
        expression_attribute_names={'#d': 'data'},
        expression_attribute_values={':new_data': {'S': 'new data'}},
        region_name='us-west-2',
        condition_expression=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to update item: {result["error"]}')

    # Verify the update
    get_result = await get_item(
        table_name='TestTable',
        key={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}},
        expression_attribute_names=None,
        projection_expression=None,
        region_name='us-west-2',
    )

    assert get_result['Item']['data']['S'] == 'new data'

    # Test 2: Update with condition that succeeds
    result = await update_item(
        table_name='TestTable',
        key={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}},
        update_expression='SET #v = :new_version, #s = :new_status',
        expression_attribute_names={'#v': 'version', '#s': 'status', '#curr_status': 'status'},
        expression_attribute_values={
            ':new_version': {'N': '2'},
            ':new_status': {'S': 'updated'},
            ':expected_status': {'S': 'active'},
        },
        condition_expression='#curr_status = :expected_status',
        region_name='us-west-2',
    )

    if 'error' in result:
        pytest.fail(f'Failed to update item with condition: {result["error"]}')

    # Verify the conditional update succeeded
    get_result = await get_item(
        table_name='TestTable',
        key={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}},
        expression_attribute_names=None,
        projection_expression=None,
        region_name='us-west-2',
    )

    assert get_result['Item']['version']['N'] == '2'
    assert get_result['Item']['status']['S'] == 'updated'


@pytest.mark.asyncio
async def test_delete_item(test_table):
    """Test deleting an item from a table with conditional expressions."""
    # First put some test items
    items = [
        {
            'id': {'S': 'test1'},
            'sort': {'S': 'data1'},
            'data': {'S': 'test data'},
            'status': {'S': 'active'},
            'version': {'N': '1'},
        },
        {
            'id': {'S': 'test2'},
            'sort': {'S': 'data1'},
            'data': {'S': 'test data'},
            'status': {'S': 'inactive'},
            'version': {'N': '1'},
        },
    ]
    for item in items:
        await put_item(
            table_name='TestTable',
            item=item,
            region_name='us-west-2',
        )

    result = await delete_item(
        table_name='TestTable',
        key={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}},
        region_name='us-west-2',
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to delete item with condition: {result["error"]}')

    # Verify the item is deleted
    get_result = await get_item(
        table_name='TestTable',
        key={'id': {'S': 'test1'}, 'sort': {'S': 'data1'}},
        region_name='us-west-2',
    )

    assert 'Item' not in get_result


@pytest.mark.asyncio
async def test_query(test_table):
    """Test querying items from a table with filter and projection expressions."""
    # Put some test items with varied attributes
    items = [
        {
            'id': {'S': 'user1'},
            'sort': {'S': 'order1'},
            'status': {'S': 'pending'},
            'amount': {'N': '100'},
            'category': {'S': 'electronics'},
            'notes': {'S': 'priority delivery'},
        },
        {
            'id': {'S': 'user1'},
            'sort': {'S': 'order2'},
            'status': {'S': 'completed'},
            'amount': {'N': '50'},
            'category': {'S': 'books'},
            'notes': {'S': 'standard delivery'},
        },
        {
            'id': {'S': 'user1'},
            'sort': {'S': 'order3'},
            'status': {'S': 'pending'},
            'amount': {'N': '75'},
            'category': {'S': 'electronics'},
            'notes': {'S': 'gift wrapped'},
        },
    ]
    for item in items:
        await put_item(
            table_name='TestTable',
            item=item,
            region_name='us-west-2',
            condition_expression=None,
            expression_attribute_names=None,
            expression_attribute_values=None,
        )

    # Test 1: Basic query with filter expression
    result = await query(
        table_name='TestTable',
        key_condition_expression='#id = :id_val',
        expression_attribute_names={'#id': 'id', '#status': 'status', '#category': 'category'},
        expression_attribute_values={
            ':id_val': {'S': 'user1'},
            ':status_val': {'S': 'pending'},
            ':category_val': {'S': 'electronics'},
        },
        filter_expression='#status = :status_val AND #category = :category_val',
        region_name='us-west-2',
        index_name=None,
        projection_expression=None,
        select=None,
        limit=None,
        scan_index_forward=None,
        exclusive_start_key=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to query items with filter: {result["error"]}')

    assert result['Count'] == 2
    assert len(result['Items']) == 2
    assert all(
        item['status']['S'] == 'pending' and item['category']['S'] == 'electronics'
        for item in result['Items']
    )

    # Test 3: Query with both filter and projection expressions
    result = await query(
        table_name='TestTable',
        key_condition_expression='#id = :id_val',
        expression_attribute_names={'#id': 'id', '#status': 'status', '#amount': 'amount'},
        expression_attribute_values={
            ':id_val': {'S': 'user1'},
            ':status_val': {'S': 'pending'},
            ':amount_val': {'N': '50'},
        },
        filter_expression='#status = :status_val AND #amount > :amount_val',
        projection_expression='#status, #amount',
        region_name='us-west-2',
        index_name=None,
        select=None,
        limit=100,
        scan_index_forward=True,
        exclusive_start_key=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to query items with filter and projection: {result["error"]}')

    assert result['Count'] == 2
    assert len(result['Items']) == 2
    # Verify results match filter criteria and only include projected attributes
    for item in result['Items']:
        assert set(item.keys()) == {'status', 'amount'}
        assert item['status']['S'] == 'pending'
        assert float(item['amount']['N']) > 50


@pytest.mark.asyncio
async def test_scan(test_table):
    """Test scanning items from a table with filter and projection expressions."""
    # Put some test items with varied attributes
    items = [
        {
            'id': {'S': 'user1'},
            'sort': {'S': 'data1'},
            'status': {'S': 'active'},
            'price': {'N': '299'},
            'category': {'S': 'electronics'},
            'stock': {'N': '50'},
            'description': {'S': 'High-end product'},
        },
        {
            'id': {'S': 'user2'},
            'sort': {'S': 'data1'},
            'status': {'S': 'inactive'},
            'price': {'N': '199'},
            'category': {'S': 'books'},
            'stock': {'N': '100'},
            'description': {'S': 'Bestseller'},
        },
        {
            'id': {'S': 'user3'},
            'sort': {'S': 'data1'},
            'status': {'S': 'active'},
            'price': {'N': '399'},
            'category': {'S': 'electronics'},
            'stock': {'N': '25'},
            'description': {'S': 'Premium product'},
        },
    ]
    for item in items:
        await put_item(
            table_name='TestTable',
            item=item,
            region_name='us-west-2',
            condition_expression=None,
            expression_attribute_names=None,
            expression_attribute_values=None,
        )

    # Test 1: Basic scan with filter expression
    result = await scan(
        table_name='TestTable',
        filter_expression='#status = :status_val AND #category = :category_val AND #stock < :stock_val',
        expression_attribute_names={
            '#status': 'status',
            '#category': 'category',
            '#stock': 'stock',
        },
        expression_attribute_values={
            ':status_val': {'S': 'active'},
            ':category_val': {'S': 'electronics'},
            ':stock_val': {'N': '30'},
        },
        region_name='us-west-2',
        index_name=None,
        projection_expression=None,
        select='ALL_ATTRIBUTES',
        limit=None,
        exclusive_start_key=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to scan items with filter: {result["error"]}')

    assert result['Count'] == 1
    assert len(result['Items']) == 1
    assert result['Items'][0]['stock']['N'] == '25'
    assert result['Items'][0]['status']['S'] == 'active'
    assert result['Items'][0]['category']['S'] == 'electronics'

    # Test 3: Scan with both filter and projection expressions
    result = await scan(
        table_name='TestTable',
        filter_expression='#price > :price_val AND #category = :category_val',
        expression_attribute_names={'#price': 'price', '#category': 'category', '#stock': 'stock'},
        expression_attribute_values={
            ':price_val': {'N': '200'},
            ':category_val': {'S': 'electronics'},
        },
        projection_expression='#price, #stock',
        region_name='us-west-2',
        index_name=None,
        select=None,
        limit=100,
        exclusive_start_key=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to scan items with filter and projection: {result["error"]}')

    assert result['Count'] == 2
    assert len(result['Items']) == 2
    # Verify results match filter criteria and only include projected attributes
    for item in result['Items']:
        assert set(item.keys()) == {'price', 'stock'}
        assert float(item['price']['N']) > 200
        assert 'category' not in item


@pytest.mark.asyncio
async def test_describe_table(test_table):
    """Test describing a table."""
    result = await describe_table(table_name='TestTable', region_name='us-west-2')

    if 'error' in result:
        pytest.fail(f'Failed to describe table: {result["error"]}')

    assert result['TableName'] == 'TestTable'
    assert result['TableStatus'] in ['CREATING', 'ACTIVE']
    assert len(result['KeySchema']) == 2


@pytest.mark.asyncio
async def test_list_tables(test_table):
    """Test listing tables."""
    result = await list_tables(region_name='us-west-2', exclusive_start_table_name=None, limit=100)

    if 'error' in result:
        pytest.fail(f'Failed to list tables: {result["error"]}')

    assert 'TestTable' in result['TableNames']


@pytest.mark.asyncio
async def test_backup_operations(test_table):
    """Test backup operations (create, describe, list, restore)."""
    # Create backup
    backup_result = await create_backup(
        table_name='TestTable', backup_name='TestBackup', region_name='us-west-2'
    )

    if 'error' in backup_result:
        pytest.fail(f'Failed to create backup: {backup_result["error"]}')

    backup_arn = backup_result['BackupArn']

    # Describe backup
    describe_result = await describe_backup(backup_arn=backup_arn, region_name='us-west-2')

    if 'error' in describe_result:
        pytest.fail(f'Failed to describe backup: {describe_result["error"]}')

    assert describe_result['BackupDetails']['BackupName'] == 'TestBackup'

    # List backups
    list_result = await list_backups(
        table_name='TestTable',
        region_name='us-west-2',
        backup_type='USER',
        exclusive_start_backup_arn=None,
        limit=100,
    )

    if 'error' in list_result:
        pytest.fail(f'Failed to list backups: {list_result["error"]}')

    assert len(list_result['BackupSummaries']) > 0

    # Restore from backup
    restore_result = await restore_table_from_backup(
        backup_arn=backup_arn, target_table_name='TestTableRestore', region_name='us-west-2'
    )

    if 'error' in restore_result:
        pytest.fail(f'Failed to restore from backup: {restore_result["error"]}')
    assert restore_result['TableName'] == 'TestTableRestore'


@pytest.mark.asyncio
async def test_delete_table(test_table):
    """Test deleting a table."""
    result = await delete_table(table_name='TestTable', region_name='us-west-2')

    if 'error' in result:
        pytest.fail(f'Failed to delete table: {result["error"]}')
    assert result['TableName'] == 'TestTable'


@pytest.mark.asyncio
async def test_ttl_operations(test_table):
    """Test Time to Live operations."""
    # First describe TTL settings (should be disabled by default)
    describe_result = await describe_time_to_live(table_name='TestTable', region_name='us-west-2')

    if 'error' in describe_result:
        pytest.fail(f'Failed to describe TTL: {describe_result["error"]}')

    assert describe_result['TimeToLiveStatus'] in ['DISABLED', 'ENABLING', 'ENABLED', 'DISABLING']

    # Enable TTL with expiry_date attribute
    update_result = await update_time_to_live(
        table_name='TestTable',
        time_to_live_specification={'Enabled': True, 'AttributeName': 'expiry_date'},
        region_name='us-west-2',
    )

    if 'error' in update_result:
        pytest.fail(f'Failed to update TTL: {update_result["error"]}')

    assert update_result['Enabled'] is True
    assert update_result['AttributeName'] == 'expiry_date'

    # Verify TTL settings
    describe_result = await describe_time_to_live(table_name='TestTable', region_name='us-west-2')

    if 'error' in describe_result:
        pytest.fail(f'Failed to describe TTL: {describe_result["error"]}')

    assert describe_result['TimeToLiveStatus'] in ['ENABLING', 'ENABLED']
    assert describe_result.get('AttributeName') == 'expiry_date'

    # Disable TTL
    update_result = await update_time_to_live(
        table_name='TestTable',
        time_to_live_specification={'Enabled': False, 'AttributeName': 'expiry_date'},
        region_name='us-west-2',
    )

    if 'error' in update_result:
        pytest.fail(f'Failed to update TTL: {update_result["error"]}')

    assert update_result['Enabled'] is False


@pytest.mark.asyncio
async def test_continuous_backup_operations(test_table):
    """Test continuous backup operations."""
    # First describe continuous backups (should be disabled by default)
    describe_result = await describe_continuous_backups(
        table_name='TestTable', region_name='us-west-2'
    )

    if 'error' in describe_result:
        pytest.fail(f'Failed to describe continuous backups: {describe_result["error"]}')

    # Enable point in time recovery
    update_result = await update_continuous_backups(
        table_name='TestTable',
        point_in_time_recovery_enabled=True,
        recovery_period_in_days=7,
        region_name='us-west-2',
    )

    if 'error' in update_result:
        pytest.fail(f'Failed to update continuous backups: {update_result["error"]}')

    assert update_result['PointInTimeRecoveryDescription']['PointInTimeRecoveryStatus'] in [
        'ENABLED',
        'ENABLING',
    ]

    # Verify continuous backup settings
    describe_result = await describe_continuous_backups(
        table_name='TestTable', region_name='us-west-2'
    )

    if 'error' in describe_result:
        pytest.fail(f'Failed to describe continuous backups: {describe_result["error"]}')

    assert describe_result['PointInTimeRecoveryDescription']['PointInTimeRecoveryStatus'] in [
        'ENABLED',
        'ENABLING',
    ]

    # Disable point in time recovery
    update_result = await update_continuous_backups(
        table_name='TestTable',
        point_in_time_recovery_enabled=False,
        recovery_period_in_days=30,
        region_name='us-west-2',
    )

    if 'error' in update_result:
        pytest.fail(f'Failed to update continuous backups: {update_result["error"]}')

    assert update_result['PointInTimeRecoveryDescription']['PointInTimeRecoveryStatus'] in [
        'DISABLED',
        'DISABLING',
    ]


@pytest.mark.asyncio
async def test_resource_policy_operations(test_table):
    """Test resource policy operations."""
    # Get table ARN from describe_table
    describe_result = await describe_table(table_name='TestTable', region_name='us-west-2')
    table_arn = describe_result['TableArn']

    # Test 1: Put valid resource policy
    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'AWS': '*'},
                'Action': ['dynamodb:GetItem'],
                'Resource': table_arn,
            }
        ],
    }

    put_result = await put_resource_policy(
        resource_arn=table_arn, policy=policy, region_name='us-west-2'
    )

    if 'error' in put_result:
        pytest.fail(f'Failed to put resource policy: {put_result["error"]}')

    # Get resource policy
    get_result = await get_resource_policy(resource_arn=table_arn, region_name='us-west-2')

    if 'error' in get_result:
        pytest.fail(f'Failed to get resource policy: {get_result["error"]}')


@pytest.mark.asyncio
async def test_tag_operations(test_table):
    """Test tag operations."""
    # Get table ARN from describe_table
    describe_result = await describe_table(table_name='TestTable', region_name='us-west-2')
    table_arn = describe_result['TableArn']

    # Add tags
    tag_result = await tag_resource(
        resource_arn=table_arn,
        tags=[{'Key': 'Environment', 'Value': 'Test'}, {'Key': 'Project', 'Value': 'DynamoDB'}],
        region_name='us-west-2',
    )

    if 'error' in tag_result:
        pytest.fail(f'Failed to add tags: {tag_result["error"]}')

    # List tags
    list_result = await list_tags_of_resource(
        resource_arn=table_arn, region_name='us-west-2', next_token=None
    )

    if 'error' in list_result:
        pytest.fail(f'Failed to list tags: {list_result["error"]}')

    assert any(
        tag['Key'] == 'Environment' and tag['Value'] == 'Test' for tag in list_result['Tags']
    )

    # Remove tags
    untag_result = await untag_resource(
        resource_arn=table_arn, tag_keys=['Environment'], region_name='us-west-2'
    )

    if 'error' in untag_result:
        pytest.fail(f'Failed to remove tags: {untag_result["error"]}')


@pytest.mark.asyncio
async def test_describe_limits(dynamodb):
    """Test describing account limits."""
    result = await describe_limits(region_name='us-west-2')

    if 'error' in result:
        pytest.fail(f'Failed to describe limits: {result["error"]}')

    assert 'AccountMaxReadCapacityUnits' in result
    assert 'AccountMaxWriteCapacityUnits' in result
    assert 'TableMaxReadCapacityUnits' in result
    assert 'TableMaxWriteCapacityUnits' in result


@pytest.mark.asyncio
async def test_describe_endpoints(dynamodb):
    """Test describing endpoints."""
    result = await describe_endpoints(region_name='us-west-2')

    if 'error' in result:
        pytest.fail(f'Failed to describe endpoints: {result["error"]}')

    assert 'Endpoints' in result


@pytest.mark.asyncio
async def test_update_table(test_table):
    """Test updating a table's provisioned throughput."""
    # Update the table's read and write capacity
    result = await update_table(
        table_name='TestTable',
        provisioned_throughput={'ReadCapacityUnits': 2, 'WriteCapacityUnits': 2},
        region_name='us-west-2',
        attribute_definitions=None,
        billing_mode='PROVISIONED',
        deletion_protection_enabled=True,
        global_secondary_index_updates=None,
        on_demand_throughput=None,
        replica_updates=None,
        sse_specification={'Enabled': False},
        stream_specification={
            'StreamEnabled': True,
            'StreamViewType': 'KEYS_ONLY',
        },
        table_class='STANDARD_INFREQUENT_ACCESS',
        warm_throughput=None,
    )

    if 'error' in result:
        pytest.fail(f'Failed to update table: {result["error"]}')

    # Verify the update
    assert result['TableName'] == 'TestTable'
    assert result['ProvisionedThroughput']['ReadCapacityUnits'] == 2
    assert result['ProvisionedThroughput']['WriteCapacityUnits'] == 2


@pytest.mark.asyncio
async def test_exception_handling(test_table):
    """Test exception handling."""
    # Test error handling by using invalid region

    # Test 1: Put valid resource policy
    # Get table ARN
    describe_result = await describe_table(table_name='TestTable', region_name='us-west-2')
    table_arn = describe_result['TableArn']

    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'AWS': '*'},
                'Action': ['dynamodb:GetItem'],
                'Resource': table_arn,
            }
        ],
    }
    error_result = await put_resource_policy(
        resource_arn=table_arn, policy=policy, region_name='invalid'
    )

    # Verify error is returned
    assert 'error' in error_result
    print(error_result)
