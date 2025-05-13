import pytest
import pytest_asyncio
import asyncio
from moto import mock_aws
import boto3
from awslabs.dynamodb_mcp_server.dynamodb_server import (
    create_table, put_item, get_item, update_item, delete_item,
    scan, query, describe_table, list_tables, create_backup,
    describe_backup, list_backups, restore_table_from_backup,
    describe_limits, describe_time_to_live, update_time_to_live,
    describe_endpoints, describe_continuous_backups, 
    update_continuous_backups, put_resource_policy, 
    get_resource_policy, tag_resource, untag_resource,
    list_tags_of_resource, delete_table
)

@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'

@pytest_asyncio.fixture
async def dynamodb(aws_credentials):
    """DynamoDB resource."""
    with mock_aws():
        yield boto3.client('dynamodb', region_name='us-west-2')

async def wait_for_table(table_name: str, region_name: str = "us-west-2"):
    """Wait for a table to become active."""
    for _ in range(10):  # Try up to 10 times
        result = await describe_table(table_name=table_name, region_name=region_name)
        if "error" not in result and result.get("TableStatus") == "ACTIVE":
            return result
        await asyncio.sleep(1)  # Wait 1 second between checks
    raise Exception("Table did not become active in time")

@pytest_asyncio.fixture
async def test_table(dynamodb):
    """Create a test table for use in other tests."""
    import asyncio
    
    # Create the table
    result = await create_table(
        table_name="TestTable",
        attribute_definitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "sort", "AttributeType": "S"}
        ],
        key_schema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "sort", "KeyType": "RANGE"}
        ],
        billing_mode="PROVISIONED",
        provisioned_throughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
            global_secondary_indexes=None,
            region_name="us-west-2"
    )
    
    if "error" in result:
        raise Exception(f"Failed to create table: {result['error']}")
    
    # Wait for table to become active
    table_info = await wait_for_table("TestTable", "us-west-2")
    return table_info

@pytest.mark.asyncio
async def test_create_table_with_gsi(dynamodb):
    """Test creating a table with a global secondary index"""
    # Create table with GSI
    result = await create_table(
        table_name="TestTableWithGSI",
        attribute_definitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"}
        ],
        key_schema=[{"AttributeName": "id", "KeyType": "HASH"}],
        billing_mode="PROVISIONED",  # Changed to PROVISIONED since we need to provide throughput
        provisioned_throughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},  # Minimal values
        global_secondary_indexes=[{
            "IndexName": "EmailIndex",
            "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 1,
                "WriteCapacityUnits": 1
            }
        }],
        region_name="us-west-2"
    )
    
    # Check if we got an error
    if "error" in result:
        pytest.fail(f"Failed to create table: {result['error']}")
        
    # Assert table properties
    assert result.get("TableName") == "TestTableWithGSI"
    assert result.get("TableStatus") in ["CREATING", "ACTIVE"]  # moto might return ACTIVE immediately
    
    # Assert GSI properties
    gsis = result.get("GlobalSecondaryIndexes", [])
    assert len(gsis) == 1, "Expected 1 GSI"
    gsi = gsis[0]
    assert gsi["IndexName"] == "EmailIndex"
    assert result.get("BillingModeSummary", {}).get("BillingMode") == "PROVISIONED"

@pytest.mark.asyncio
async def test_put_item(test_table):
    """Test putting an item into a table"""
    result = await put_item(
        table_name="TestTable",
        item={
            "id": {"S": "test1"},
            "sort": {"S": "data1"},
            "data": {"S": "test data"}
        },
        region_name="us-west-2",
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None
    )
    
    if "error" in result:
        pytest.fail(f"Failed to put item: {result['error']}")
    
    # DynamoDB returns empty response on success unless ReturnValues is specified
    assert "error" not in result

@pytest.mark.asyncio
async def test_get_item(test_table):
    """Test getting an item from a table"""
    # First put an item
    await put_item(
        table_name="TestTable",
        item={
            "id": {"S": "test1"},
            "sort": {"S": "data1"},
            "data": {"S": "test data"}
        },
        region_name="us-west-2",
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None
    )
    
    # Then get the item
    result = await get_item(
        table_name="TestTable",
        key={
            "id": {"S": "test1"},
            "sort": {"S": "data1"}
        },
        region_name="us-west-2",
        expression_attribute_names=None,
        projection_expression=None
    )
    
    if "error" in result:
        pytest.fail(f"Failed to get item: {result['error']}")
    
    assert result["Item"]["id"]["S"] == "test1"
    assert result["Item"]["sort"]["S"] == "data1"
    assert result["Item"]["data"]["S"] == "test data"

@pytest.mark.asyncio
async def test_update_item(test_table):
    """Test updating an item in a table"""
    # First put an item
    await put_item(
        table_name="TestTable",
        item={
            "id": {"S": "test1"},
            "sort": {"S": "data1"},
            "data": {"S": "old data"}
        },
        region_name="us-west-2",
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None
    )
    
    # Then update the item
    result = await update_item(
        table_name="TestTable",
        key={
            "id": {"S": "test1"},
            "sort": {"S": "data1"}
        },
        update_expression="SET #d = :new_data",
        expression_attribute_names={"#d": "data"},
        expression_attribute_values={":new_data": {"S": "new data"}},
        region_name="us-west-2",
        condition_expression=None
    )
    
    if "error" in result:
        pytest.fail(f"Failed to update item: {result['error']}")
    
    # Verify the update
    get_result = await get_item(
        table_name="TestTable",
        key={
            "id": {"S": "test1"},
            "sort": {"S": "data1"}
        },
        expression_attribute_names=None,
        projection_expression=None,
        region_name="us-west-2"
    )
    
    assert get_result["Item"]["data"]["S"] == "new data"

@pytest.mark.asyncio
async def test_delete_item(test_table):
    """Test deleting an item from a table"""
    # First put an item
    await put_item(
        table_name="TestTable",
        item={
            "id": {"S": "test1"},
            "sort": {"S": "data1"},
            "data": {"S": "test data"}
        },
        region_name="us-west-2"
    )
    
    # Then delete the item
    result = await delete_item(
        table_name="TestTable",
        key={
            "id": {"S": "test1"},
            "sort": {"S": "data1"}
        },
        region_name="us-west-2",
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None
    )
    
    if "error" in result:
        pytest.fail(f"Failed to delete item: {result['error']}")
    
    # Verify the item is deleted
    get_result = await get_item(
        table_name="TestTable",
        key={
            "id": {"S": "test1"},
            "sort": {"S": "data1"}
        },
        region_name="us-west-2"
    )
    
    assert "Item" not in get_result

@pytest.mark.asyncio
async def test_query(test_table):
    """Test querying items from a table"""
    # Put some test items
    items = [
        {
            "id": {"S": "user1"},
            "sort": {"S": "order1"},
            "status": {"S": "pending"}
        },
        {
            "id": {"S": "user1"},
            "sort": {"S": "order2"},
            "status": {"S": "completed"}
        }
    ]
    for item in items:
        await put_item(
            table_name="TestTable",
            item=item,
            region_name="us-west-2",
            condition_expression=None,
            expression_attribute_names=None,
            expression_attribute_values=None
        )
    
    # Query items for user1
    result = await query(
        table_name="TestTable",
        key_condition_expression="#id = :id_val",
        expression_attribute_names={"#id": "id"},
        expression_attribute_values={":id_val": {"S": "user1"}},
        region_name="us-west-2",
        index_name=None,
        filter_expression=None,
        projection_expression=None,
        select=None,
        limit=None,
        scan_index_forward=None,
        exclusive_start_key=None
    )
    
    if "error" in result:
        pytest.fail(f"Failed to query items: {result['error']}")
    
    assert result["Count"] == 2
    assert len(result["Items"]) == 2
    assert all(item["id"]["S"] == "user1" for item in result["Items"])

@pytest.mark.asyncio
async def test_scan(test_table):
    """Test scanning items from a table"""
    # Put some test items
    items = [
        {
            "id": {"S": "user1"},
            "sort": {"S": "data1"},
            "status": {"S": "active"}
        },
        {
            "id": {"S": "user2"},
            "sort": {"S": "data1"},
            "status": {"S": "active"}
        }
    ]
    for item in items:
        await put_item(
            table_name="TestTable",
            item=item,
            region_name="us-west-2",
            condition_expression=None,
            expression_attribute_names=None,
            expression_attribute_values=None
        )
    
    # Scan for active items
    result = await scan(
        table_name="TestTable",
        filter_expression="#status = :status_val",
        expression_attribute_names={"#status": "status"},
        expression_attribute_values={":status_val": {"S": "active"}},
        region_name="us-west-2",
        index_name=None,
        projection_expression=None,
        select=None,
        limit=None,
        exclusive_start_key=None
    )
    
    if "error" in result:
        pytest.fail(f"Failed to scan items: {result['error']}")
    
    assert result["Count"] == 2
    assert len(result["Items"]) == 2
    assert all(item["status"]["S"] == "active" for item in result["Items"])

@pytest.mark.asyncio
async def test_describe_table(test_table):
    """Test describing a table"""
    result = await describe_table(
        table_name="TestTable",
        region_name="us-west-2"
    )
    
    if "error" in result:
        pytest.fail(f"Failed to describe table: {result['error']}")
    
    assert result["TableName"] == "TestTable"
    assert result["TableStatus"] in ["CREATING", "ACTIVE"]
    assert len(result["KeySchema"]) == 2

@pytest.mark.asyncio
async def test_list_tables(test_table):
    """Test listing tables"""
    result = await list_tables(
        region_name="us-west-2",
        exclusive_start_table_name=None,
        limit=None
    )
    
    if "error" in result:
        pytest.fail(f"Failed to list tables: {result['error']}")
    
    assert "TestTable" in result["TableNames"]

@pytest.mark.asyncio
async def test_backup_operations(test_table):
    """Test backup operations (create, describe, list, restore)"""
    # Create backup
    backup_result = await create_backup(
        table_name="TestTable",
        backup_name="TestBackup",
        region_name="us-west-2"
    )
    
    if "error" in backup_result:
        pytest.fail(f"Failed to create backup: {backup_result['error']}")
    
    backup_arn = backup_result["BackupArn"]
    
    # Describe backup
    describe_result = await describe_backup(
        backup_arn=backup_arn,
        region_name="us-west-2"
    )
    
    if "error" in describe_result:
        pytest.fail(f"Failed to describe backup: {describe_result['error']}")
    
    assert describe_result["BackupDetails"]["BackupName"] == "TestBackup"
    
    # List backups
    list_result = await list_backups(
        table_name="TestTable",
        region_name="us-west-2",
        backup_type = None,
        exclusive_start_backup_arn = None,
        limit = None,
    )
    
    if "error" in list_result:
        pytest.fail(f"Failed to list backups: {list_result['error']}")
    
    assert len(list_result["BackupSummaries"]) > 0
    
    # Restore from backup
    restore_result = await restore_table_from_backup(
        backup_arn=backup_arn,
        target_table_name="TestTableRestore",
        region_name="us-west-2"
    )
    
    if "error" in restore_result:
        pytest.fail(f"Failed to restore from backup: {restore_result['error']}")
    assert restore_result["TableName"] == "TestTableRestore"

@pytest.mark.asyncio
async def test_delete_table(test_table):
    """Test deleting a table"""
    result = await delete_table(
        table_name="TestTable",
        region_name="us-west-2"
    )
    
    if "error" in result:
        pytest.fail(f"Failed to delete table: {result['error']}")
    assert result["TableName"] == "TestTable"

@pytest.mark.asyncio
async def test_ttl_operations(test_table):
    """Test Time to Live operations"""
    # First describe TTL settings (should be disabled by default)
    describe_result = await describe_time_to_live(
        table_name="TestTable",
        region_name="us-west-2"
    )
    
    if "error" in describe_result:
        pytest.fail(f"Failed to describe TTL: {describe_result['error']}")
    
    assert describe_result["TimeToLiveStatus"] in ["DISABLED", "ENABLING", "ENABLED", "DISABLING"]
    
    # Enable TTL with expiry_date attribute
    update_result = await update_time_to_live(
        table_name="TestTable",
        time_to_live_specification={
            "Enabled": True,
            "AttributeName": "expiry_date"
        },
        region_name="us-west-2"
    )
    
    if "error" in update_result:
        pytest.fail(f"Failed to update TTL: {update_result['error']}")
    
    assert update_result["Enabled"] is True
    assert update_result["AttributeName"] == "expiry_date"
    
    # Verify TTL settings
    describe_result = await describe_time_to_live(
        table_name="TestTable",
        region_name="us-west-2"
    )
    
    if "error" in describe_result:
        pytest.fail(f"Failed to describe TTL: {describe_result['error']}")
    
    assert describe_result["TimeToLiveStatus"] in ["ENABLING", "ENABLED"]
    assert describe_result.get("AttributeName") == "expiry_date"
    
    # Disable TTL
    update_result = await update_time_to_live(
        table_name="TestTable",
        time_to_live_specification={
            "Enabled": False,
            "AttributeName": "expiry_date"
        },
        region_name="us-west-2"
    )
    
    if "error" in update_result:
        pytest.fail(f"Failed to update TTL: {update_result['error']}")
    
    assert update_result["Enabled"] is False

@pytest.mark.asyncio
async def test_continuous_backup_operations(test_table):
    """Test continuous backup operations"""
    # First describe continuous backups (should be disabled by default)
    describe_result = await describe_continuous_backups(
        table_name="TestTable",
        region_name="us-west-2"
    )
    
    if "error" in describe_result:
        pytest.fail(f"Failed to describe continuous backups: {describe_result['error']}")
    
    # Enable point in time recovery
    update_result = await update_continuous_backups(
        table_name="TestTable",
        point_in_time_recovery_enabled=True,
        recovery_period_in_days = 7,
        region_name="us-west-2"
    )
    
    if "error" in update_result:
        pytest.fail(f"Failed to update continuous backups: {update_result['error']}")
    
    assert update_result["PointInTimeRecoveryDescription"]["PointInTimeRecoveryStatus"] in ["ENABLED", "ENABLING"]
    
    # Verify continuous backup settings
    describe_result = await describe_continuous_backups(
        table_name="TestTable",
        region_name="us-west-2"
    )
    
    if "error" in describe_result:
        pytest.fail(f"Failed to describe continuous backups: {describe_result['error']}")
    
    assert describe_result["PointInTimeRecoveryDescription"]["PointInTimeRecoveryStatus"] in ["ENABLED", "ENABLING"]
    
    # Disable point in time recovery
    update_result = await update_continuous_backups(
        table_name="TestTable",
        point_in_time_recovery_enabled=False,
        recovery_period_in_days = None,
        region_name="us-west-2"
    )
    
    if "error" in update_result:
        pytest.fail(f"Failed to update continuous backups: {update_result['error']}")
    
    assert update_result["PointInTimeRecoveryDescription"]["PointInTimeRecoveryStatus"] in ["DISABLED", "DISABLING"]

@pytest.mark.asyncio
async def test_resource_policy_operations(test_table):
    """Test resource policy operations"""
    # Get table ARN from describe_table
    describe_result = await describe_table(
        table_name="TestTable",
        region_name="us-west-2"
    )
    table_arn = describe_result["TableArn"]
    
    # Put resource policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["dynamodb:GetItem"],
            "Resource": table_arn
        }]
    }
    
    put_result = await put_resource_policy(
        resource_arn=table_arn,
        policy=policy,
        region_name="us-west-2"
    )
    
    if "error" in put_result:
        pytest.fail(f"Failed to put resource policy: {put_result['error']}")
    
    # Get resource policy
    get_result = await get_resource_policy(
        resource_arn=table_arn,
        region_name="us-west-2"
    )
    
    if "error" in get_result:
        pytest.fail(f"Failed to get resource policy: {get_result['error']}")

@pytest.mark.asyncio
async def test_tag_operations(test_table):
    """Test tag operations"""
    # Get table ARN from describe_table
    describe_result = await describe_table(
        table_name="TestTable",
        region_name="us-west-2"
    )
    table_arn = describe_result["TableArn"]
    
    # Add tags
    tag_result = await tag_resource(
        resource_arn=table_arn,
        tags=[
            {"Key": "Environment", "Value": "Test"},
            {"Key": "Project", "Value": "DynamoDB"}
        ],
        region_name="us-west-2"
    )
    
    if "error" in tag_result:
        pytest.fail(f"Failed to add tags: {tag_result['error']}")
    
    # List tags
    list_result = await list_tags_of_resource(
        resource_arn=table_arn,
        region_name="us-west-2",
        next_token=None
    )
    
    if "error" in list_result:
        pytest.fail(f"Failed to list tags: {list_result['error']}")
    
    assert any(tag["Key"] == "Environment" and tag["Value"] == "Test" for tag in list_result["Tags"])
    
    # Remove tags
    untag_result = await untag_resource(
        resource_arn=table_arn,
        tag_keys=["Environment"],
        region_name="us-west-2"
    )
    
    if "error" in untag_result:
        pytest.fail(f"Failed to remove tags: {untag_result['error']}")

@pytest.mark.asyncio
async def test_describe_limits(dynamodb):
    """Test describing account limits"""
    result = await describe_limits(
        region_name="us-west-2"
    )
    
    if "error" in result:
        pytest.fail(f"Failed to describe limits: {result['error']}")
    
    assert "AccountMaxReadCapacityUnits" in result
    assert "AccountMaxWriteCapacityUnits" in result
    assert "TableMaxReadCapacityUnits" in result
    assert "TableMaxWriteCapacityUnits" in result

@pytest.mark.asyncio
async def test_describe_endpoints(dynamodb):
    """Test describing endpoints"""
    result = await describe_endpoints(
        region_name="us-west-2"
    )
    
    if "error" in result:
        pytest.fail(f"Failed to describe endpoints: {result['error']}")
    
    assert "Endpoints" in result
