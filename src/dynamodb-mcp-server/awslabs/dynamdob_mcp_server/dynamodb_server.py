#!/usr/bin/env python3

import os
import json
from typing import Optional, List, Literal, Dict, Any, Union
from typing_extensions import TypedDict

import boto3
from fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict


# Type definitions
AttributeValue = Dict[Literal['S', 'N', 'B', 'BOOL', 'NULL', 'L', 'M', 'SS', 'NS', 'BS'], Any]
KeyAttributeValue = Dict[Literal['S', 'N', 'B'], Any]

# Return value enums
ReturnValue = Literal['NONE', 'ALL_OLD', 'UPDATED_OLD', 'ALL_NEW', 'UPDATED_NEW']
ReturnConsumedCapacity = Literal['INDEXES', 'TOTAL', 'NONE']
ReturnItemCollectionMetrics = Literal['SIZE', 'NONE']
Select = Literal['ALL_ATTRIBUTES', 'ALL_PROJECTED_ATTRIBUTES', 'SPECIFIC_ATTRIBUTES', 'COUNT']

class ScanInput(TypedDict, total=False):
    """Parameters for Scan operation."""
    TableName: str  # required
    IndexName: Optional[str]
    AttributesToGet: Optional[List[str]]  # Legacy parameter
    Limit: Optional[int]
    Select: Optional[Select]
    ScanFilter: Optional[Dict[str, AttributeValue]]  # Legacy parameter (must use AttributeValue format e.g. {'S': 'value'})
    ConditionalOperator: Optional[Literal['AND', 'OR']]  # Legacy parameter
    ExclusiveStartKey: Optional[Dict[str, KeyAttributeValue]]  # Primary key attributes in AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]
    TotalSegments: Optional[int]
    Segment: Optional[int]
    ProjectionExpression: Optional[str]
    FilterExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[Dict[str, AttributeValue]]  # values must use AttributeValue format e.g. {'S': 'value'}
    ConsistentRead: Optional[bool]


class QueryInput(TypedDict, total=False):
    """Parameters for Query operation."""
    TableName: str  # required
    IndexName: Optional[str]
    Select: Optional[Select]
    AttributesToGet: Optional[List[str]]  # Legacy parameter
    Limit: Optional[int]
    ConsistentRead: Optional[bool]
    KeyConditionExpression: Optional[str]
    FilterExpression: Optional[str]
    ProjectionExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[Dict[str, AttributeValue]]  # values must use AttributeValue format e.g. {'S': 'value'}
    ScanIndexForward: Optional[bool]
    ExclusiveStartKey: Optional[Dict[str, KeyAttributeValue]]  # Primary key attributes in AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]

class DeleteItemInput(TypedDict, total=False):
    """Parameters for DeleteItem operation."""
    TableName: str  # required
    Key: Dict[str, KeyAttributeValue]  # required - primary key attributes in AttributeValue format e.g. {'S': 'value'}
    ConditionExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[Dict[str, AttributeValue]]  # values must use AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]
    ReturnItemCollectionMetrics: Optional[ReturnItemCollectionMetrics]
    ReturnValues: Optional[ReturnValue]
    ReturnValuesOnConditionCheckFailure: Optional[Literal['ALL_OLD', 'NONE']]

class UpdateItemInput(TypedDict, total=False):
    """Parameters for UpdateItem operation."""
    TableName: str  # required
    Key: Dict[str, KeyAttributeValue]  # required - primary key attributes in AttributeValue format e.g. {'S': 'value'}
    UpdateExpression: Optional[str]
    ConditionExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[Dict[str, AttributeValue]]  # values must use AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]
    ReturnItemCollectionMetrics: Optional[ReturnItemCollectionMetrics]
    ReturnValues: Optional[ReturnValue]
    ReturnValuesOnConditionCheckFailure: Optional[Literal['ALL_OLD', 'NONE']]

class GetItemInput(TypedDict, total=False):
    """Parameters for GetItem operation."""
    TableName: str  # required
    Key: Dict[str, KeyAttributeValue]  # required - primary key attributes in AttributeValue format e.g. {'S': 'value'}
    AttributesToGet: Optional[List[str]]
    ConsistentRead: Optional[bool]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ProjectionExpression: Optional[str]
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]

class PutItemInput(TypedDict, total=False):
    """Parameters for PutItem operation."""
    TableName: str  # required
    Item: Dict[str, AttributeValue]  # required - maps attribute name to AttributeValue (must use AttributeValue format e.g. {'S': 'value'})
    ConditionExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[Dict[str, AttributeValue]]  # values must use AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]
    ReturnItemCollectionMetrics: Optional[ReturnItemCollectionMetrics]
    ReturnValues: Optional[ReturnValue]
    ReturnValuesOnConditionCheckFailure: Optional[Literal['ALL_OLD', 'NONE']]

class AttributeDefinition(TypedDict):
    AttributeName: str
    AttributeType: Literal['S', 'N', 'B']


class KeySchemaElement(TypedDict):
    AttributeName: str
    KeyType: Literal['HASH', 'RANGE']


class ProvisionedThroughput(TypedDict):
    ReadCapacityUnits: int
    WriteCapacityUnits: int


class Projection(TypedDict, total=False):
    ProjectionType: Literal['KEYS_ONLY', 'INCLUDE', 'ALL']
    NonKeyAttributes: List[str]


class OnDemandThroughput(TypedDict, total=False):
    MaxReadRequestUnits: int
    MaxWriteRequestUnits: int


class WarmThroughput(TypedDict, total=False):
    ReadUnitsPerSecond: int
    WriteUnitsPerSecond: int


class GlobalSecondaryIndex(TypedDict, total=False):
    IndexName: str  # required
    KeySchema: List[KeySchemaElement]  # required
    Projection: Projection  # required
    ProvisionedThroughput: ProvisionedThroughput
    OnDemandThroughput: OnDemandThroughput


class GlobalSecondaryIndexUpdateAction(TypedDict, total=False):
    IndexName: str
    ProvisionedThroughput: ProvisionedThroughput
    OnDemandThroughput: OnDemandThroughput
    WarmThroughput: WarmThroughput

class GlobalSecondaryIndexDeleteAction(TypedDict):
    IndexName: str

class GlobalSecondaryIndexUpdate(TypedDict, total=False):
    Create: GlobalSecondaryIndex
    Delete: GlobalSecondaryIndexDeleteAction
    Update: GlobalSecondaryIndexUpdateAction


class StreamSpecification(TypedDict, total=False):
    StreamEnabled: bool
    StreamViewType: Literal['KEYS_ONLY', 'NEW_IMAGE', 'OLD_IMAGE', 'NEW_AND_OLD_IMAGES']


class Tag(TypedDict):
    Key: str
    Value: str


class SSESpecification(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    Enabled: bool = Field(
        description="If true, uses AWS managed key (KMS charges apply). If false/not specified, uses AWS owned key",
        default = None,
    )
    SSEType: Literal["KMS"] = Field(
        description="Server-side encryption type",
        default = None,
    )
    KMSMasterKeyId: str = Field(
        description="Custom KMS key identifier (only if not using default DynamoDB key)",
        default = None,
    )


class TimeToLiveSpecification(TypedDict):
    AttributeName: str  # The name of the TTL attribute used to store the expiration time for items
    Enabled: bool  # Indicates whether TTL is enabled (true) or disabled (false) on the table


class GetResourcePolicyInput(TypedDict):
    ResourceArn: str  # The Amazon Resource Name (ARN) of the DynamoDB resource to which the policy is attached


class PutResourcePolicyInput(TypedDict, total=False):
    Policy: str  # An AWS resource-based policy document in JSON format
    ResourceArn: str  # The Amazon Resource Name (ARN) of the DynamoDB resource to which the policy will be attached
    ConfirmRemoveSelfResourceAccess: bool  # Set to true to confirm removing your permissions to change the policy in the future
    ExpectedRevisionId: str  # A string value for conditional updates of your policy


class OnDemandThroughputOverride(TypedDict):
    MaxReadRequestUnits: int

class ProvisionedThroughputOverride(TypedDict):
    ReadCapacityUnits: int

class ReplicaCreate(TypedDict, total=False):
    RegionName: str
    KMSMasterKeyId: str

class ReplicaDelete(TypedDict):
    RegionName: str

class ReplicaUpdate(TypedDict, total=False):
    KMSMasterKeyId: str
    OnDemandThroughputOverride: OnDemandThroughputOverride
    ProvisionedThroughputOverride: ProvisionedThroughputOverride
    RegionName: str
    TableClassOverride: Literal['STANDARD', 'STANDARD_INFREQUENT_ACCESS']


class ReplicationGroupUpdate(TypedDict, total=False):
    Create: ReplicaCreate
    Update: ReplicaUpdate
    Delete: ReplicaDelete


app = FastMCP(
    name="dynamodb-server",
    instructions="The official MCP Server for interacting with AWS DynamoDB",
    version="0.1.0"
)


def get_dynamodb_client(region_name: str | None):
    """
    Create a boto3 DynamoDB client using credentials from environment variables.
    Falls back to 'us-west-2' if no region is specified or found in environment.
    """
    # Use provided region, or get from env, or fall back to us-west-2
    region = region_name or os.getenv('AWS_REGION') or 'us-west-2'
    
    # Configure custom user agent to identify requests from LLM/MCP
    config = boto3.session.Config(
        user_agent_extra='MCP/DynamoDBServer'
    )
    
    # Create a new session to force credentials to reload
    # so that if user changes credential, it will be reflected immediately in the next call
    session = boto3.Session()

    # boto3 will automatically load credentials from environment variables:
    # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
    return session.client('dynamodb', region_name=region, config=config)


table_name = Field(
    description="Table Name or Amazon Resource Name (ARN)"
)
index_name = Field(
    default=None,
    description="The name of a GSI",
)
key: Dict[str, KeyAttributeValue] = Field(
    description="The primary key of an item"
)
filter_expression: str = Field(
    default=None,
    description="Filter conditions expression that DynamoDB applies to filter out data"
)
projection_expression: str = Field(
    default=None,
    description="Attributes to retrieve, can include scalars, sets, or elements of a JSON document."
)
expression_attribute_names: Dict[str, str] = Field(
    default=None,
    description="Substitution tokens for attribute names in an expression."
)
expression_attribute_values: Dict[str, AttributeValue] = Field(
    default=None,
    description="Values that can be substituted in an expression"
)
select: Select = Field(
    default=None,
    description="The attributes to be returned. Valid values: ALL_ATTRIBUTES, ALL_PROJECTED_ATTRIBUTES, SPECIFIC_ATTRIBUTES, COUNT"
)
limit: int = Field(
    default=None,
    description="The maximum number of items to evaluate",
    ge=1
)
exclusive_start_key: Dict[str, KeyAttributeValue] = Field(
    default=None,
    description="Use the LastEvaluatedKey from the previous call."
)

billing_mode: Literal['PROVISIONED', 'PAY_PER_REQUEST'] = Field(
    default=None,
    description="Specifies if billing is PAY_PER_REQUEST or by provisioned throughput"
)
resource_arn: str = Field(
    description="The Amazon Resource Name (ARN) of the DynamoDB resource"
)


@app.tool()
async def put_resource_policy(
    resource_arn: str = resource_arn,
    policy: Union[str, Dict[str, Any]] = Field(
        description="An AWS resource-based policy document in JSON format or dictionary."
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Attaches a resource-based policy document (max 20 KB) to a DynamoDB table or stream. You can control permissions for both tables and their indexes through the policy."""
    try:
        client = get_dynamodb_client(region_name)
        # Convert policy to string if it's a dictionary
        policy_str = json.dumps(policy) if isinstance(policy, dict) else policy
        
        params: PutResourcePolicyInput = {
            'ResourceArn': resource_arn,
            'Policy': policy_str
        }
            
        response = client.put_resource_policy(**params)
        return {
            'RevisionId': response.get('RevisionId')
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def get_resource_policy(
    resource_arn: str = resource_arn,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns the resource-based policy document attached to a DynamoDB table or stream in JSON format."""
    try:
        client = get_dynamodb_client(region_name)
        params: GetResourcePolicyInput = {
            'ResourceArn': resource_arn
        }
        
        response = client.get_resource_policy(**params)
        return {
            'Policy': response.get('Policy'),
            'RevisionId': response.get('RevisionId')
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def scan(
    table_name: str = table_name,
    index_name: str = index_name,
    filter_expression: str = filter_expression,
    projection_expression: str = projection_expression,
    expression_attribute_names: Dict[str, str] = expression_attribute_names,
    expression_attribute_values: Dict[str, AttributeValue] = expression_attribute_values,
    select: Select = select,
    limit: int = limit,
    exclusive_start_key: Dict[str, KeyAttributeValue] = exclusive_start_key,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns items and attributes by scanning a table or secondary index. Reads up to Limit items or 1 MB of data, with optional FilterExpression to reduce results."""
    try:
        client = get_dynamodb_client(region_name)
        params: ScanInput = {
            'TableName': table_name
        }
        
        if index_name:
            params['IndexName'] = index_name
        if filter_expression:
            params['FilterExpression'] = filter_expression
        if projection_expression:
            params['ProjectionExpression'] = projection_expression
        if expression_attribute_names:
            params['ExpressionAttributeNames'] = expression_attribute_names
        if expression_attribute_values:
            params['ExpressionAttributeValues'] = expression_attribute_values
        if select:
            params['Select'] = select
        if limit:
            params['Limit'] = limit
        if exclusive_start_key:
            params['ExclusiveStartKey'] = exclusive_start_key
        params['ReturnConsumedCapacity'] = 'TOTAL'
            
        response = client.scan(**params)
        return {
            'Items': response.get('Items', []),
            'Count': response.get('Count'),
            'ScannedCount': response.get('ScannedCount'),
            'LastEvaluatedKey': response.get('LastEvaluatedKey'),
            'ConsumedCapacity': response.get('ConsumedCapacity')
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def query(
    table_name: str = table_name,
    key_condition_expression: str = Field(
        description="Key condition expression. Must perform an equality test on partition key value."
    ),
    index_name: str = index_name,
    filter_expression: str = filter_expression,
    projection_expression: str = projection_expression,
    expression_attribute_names: Dict[str, str] = expression_attribute_names,
    expression_attribute_values: Dict[str, AttributeValue] = expression_attribute_values,
    select: Select = select,
    limit: int = limit,
    scan_index_forward: bool = Field(
        default=None,
        description="Ascending (true) or descending (false)."
    ),
    exclusive_start_key: Dict[str, KeyAttributeValue] = exclusive_start_key,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns items from a table or index matching a partition key value, with optional sort key filtering."""
    try:
        client = get_dynamodb_client(region_name)
        params: QueryInput = {
            'TableName': table_name,
            'KeyConditionExpression': key_condition_expression
        }
        
        if index_name:
            params['IndexName'] = index_name
        if filter_expression:
            params['FilterExpression'] = filter_expression
        if projection_expression:
            params['ProjectionExpression'] = projection_expression
        if expression_attribute_names:
            params['ExpressionAttributeNames'] = expression_attribute_names
        if expression_attribute_values:
            params['ExpressionAttributeValues'] = expression_attribute_values
        if select:
            params['Select'] = select
        if limit:
            params['Limit'] = limit
        if scan_index_forward is not None:
            params['ScanIndexForward'] = scan_index_forward
        if exclusive_start_key:
            params['ExclusiveStartKey'] = exclusive_start_key
        params['ReturnConsumedCapacity'] = 'TOTAL'
            
        response = client.query(**params)
        return {
            'Items': response.get('Items', []),
            'Count': response.get('Count'),
            'ScannedCount': response.get('ScannedCount'),
            'LastEvaluatedKey': response.get('LastEvaluatedKey'),
            'ConsumedCapacity': response.get('ConsumedCapacity')
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def update_item(
    table_name: str = table_name,
    key: Dict[str, KeyAttributeValue] = key,
    update_expression: str = Field(
        default=None,
        description="""Defines the attributes to be updated, the action to be performed on them, and new value(s) for them. The following actions are available:
    * SET - Adds one or more attributes and values to an item. If any of these attributes already exist, they are replaced by the new values.
    * REMOVE - Removes one or more attributes from an item.
    * ADD - Only supports Number and Set data types. Adds a value to a number attribute or adds elements to a set.
    * DELETE - Only supports Set data type. Removes elements from a set.
    For example: 'SET a=:value1, b=:value2 DELETE :value3, :value4, :value5'""",
    ),
    condition_expression: str = Field(
        default=None,
        description="A condition that must be satisfied in order for a conditional update to succeed."
    ),
    expression_attribute_names: Dict[str, str] = expression_attribute_names,
    expression_attribute_values: Dict[str, AttributeValue] = expression_attribute_values,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Edits an existing item's attributes, or adds a new item to the table if it does not already exist"""
    try:
        client = get_dynamodb_client(region_name)
        params: UpdateItemInput = {
            'TableName': table_name,
            'Key': key
        }
        
        if update_expression:
            params['UpdateExpression'] = update_expression
        if condition_expression:
            params['ConditionExpression'] = condition_expression
        if expression_attribute_names:
            params['ExpressionAttributeNames'] = expression_attribute_names
        if expression_attribute_values:
            params['ExpressionAttributeValues'] = expression_attribute_values
        params['ReturnConsumedCapacity'] = 'TOTAL'
        params['ReturnValuesOnConditionCheckFailure'] = 'ALL_OLD'
            
        response = client.update_item(**params)
        return {
            'Attributes': response.get('Attributes'),
            'ConsumedCapacity': response.get('ConsumedCapacity'),
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def get_item(
    table_name: str = table_name,
    key: Dict[str, KeyAttributeValue] = key,
    expression_attribute_names: Dict[str, str] = expression_attribute_names,
    projection_expression: str = projection_expression,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns attributes for an item with the given primary key. Uses eventually consistent reads by default, or set ConsistentRead=true for strongly consistent reads."""
    try:
        client = get_dynamodb_client(region_name)
        params: GetItemInput = {
            'TableName': table_name,
            'Key': key
        }
        
        if expression_attribute_names:
            params['ExpressionAttributeNames'] = expression_attribute_names
        if projection_expression:
            params['ProjectionExpression'] = projection_expression
        params['ReturnConsumedCapacity'] = 'TOTAL'
            
        response = client.get_item(**params)
        return {
            'Item': response.get('Item'),
            'ConsumedCapacity': response.get('ConsumedCapacity')
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def put_item(
    table_name: str = table_name,
    item: Dict[str, AttributeValue] = Field(
        description="A map of attribute name/value pairs, one for each attribute."
    ),
    condition_expression: str = Field(
        default=None,
        description="A condition that must be satisfied in order for a conditional put operation to succeed."
    ),
    expression_attribute_names: Dict[str, str] = expression_attribute_names,
    expression_attribute_values: Dict[str, Any] = expression_attribute_values,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Creates a new item or replaces an existing item in a table. Use condition expressions to control whether to create new items or update existing ones."""
    try:
        client = get_dynamodb_client(region_name)
        params: PutItemInput = {
            'TableName': table_name,
            'Item': item
        }
        
        if condition_expression:
            params['ConditionExpression'] = condition_expression
        if expression_attribute_names:
            params['ExpressionAttributeNames'] = expression_attribute_names
        if expression_attribute_values:
            params['ExpressionAttributeValues'] = expression_attribute_values
        params['ReturnConsumedCapacity'] = 'TOTAL'
            
        response = client.put_item(**params)
        return {
            'Attributes': response.get('Attributes'),
            'ConsumedCapacity': response.get('ConsumedCapacity'),
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def delete_item(
    table_name: str = table_name,
    key: Dict[str, KeyAttributeValue] = key,
    condition_expression: str = Field(
        default=None,
        description="The condition that must be satisfied in order for delete to succeed."
    ),
    expression_attribute_names: Dict[str, str] = expression_attribute_names,
    expression_attribute_values: Dict[str, AttributeValue] = expression_attribute_values,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Deletes a single item in a table by primary key. You can perform a conditional delete operation that deletes the item if it exists, or if it has an expected attribute value."""
    try:
        client = get_dynamodb_client(region_name)
        params: DeleteItemInput = {
            'TableName': table_name,
            'Key': key
        }
        
        if condition_expression:
            params['ConditionExpression'] = condition_expression
        if expression_attribute_names:
            params['ExpressionAttributeNames'] = expression_attribute_names
        if expression_attribute_values:
            params['ExpressionAttributeValues'] = expression_attribute_values
        params['ReturnConsumedCapacity'] = 'TOTAL'

        response = client.delete_item(**params)
        return {
            'Attributes': response.get('Attributes'),
            'ConsumedCapacity': response.get('ConsumedCapacity'),
            'ItemCollectionMetrics': response.get('ItemCollectionMetrics')
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def update_time_to_live(
    table_name: str = table_name,
    time_to_live_specification: TimeToLiveSpecification = Field(
        description="The new TTL settings"
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Enables or disables Time to Live (TTL) for the specified table. Note: The epoch time format is the number of seconds elapsed since 12:00:00 AM January 1, 1970 UTC."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification=time_to_live_specification
        )
        return response['TimeToLiveSpecification']
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def update_table(
    table_name: str = table_name,
    attribute_definitions: List[AttributeDefinition] = Field(
        default=None,
        description="Describe the key schema for the table and indexes. Required when adding a new GSI."
    ),
    billing_mode: Literal['PROVISIONED', 'PAY_PER_REQUEST'] = billing_mode,
    deletion_protection_enabled: bool = Field(
        default=None,
        description="Indicates whether deletion protection is to be enabled"
    ),
    global_secondary_index_updates: List[GlobalSecondaryIndexUpdate] = Field(
        default=None,
        description="List of GSIs to be added, updated or deleted."
    ),
    on_demand_throughput: OnDemandThroughput = Field(
        default=None,
        description="Set the max number of read and write units."
    ),
    provisioned_throughput: ProvisionedThroughput = Field(
        default=None,
        description="The new provisioned throughput settings."
    ),
    replica_updates: List[ReplicationGroupUpdate] = Field(
        default=None,
        description="A list of replica update actions (create, delete, or update)."
    ),
    sse_specification: SSESpecification = Field(
        default=None,
        description="The new server-side encryption settings."
    ),
    stream_specification: StreamSpecification = Field(
        default=None,
        description="DynamoDB Streams configuration."
    ),
    table_class: Literal['STANDARD', 'STANDARD_INFREQUENT_ACCESS'] = Field(
        default=None,
        description="The new table class."
    ),
    warm_throughput: WarmThroughput = Field(
        default=None,
        description="The new warm throughput settings."
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Modifies table settings including provisioned throughput, global secondary indexes, and DynamoDB Streams configuration. This is an asynchronous operation."""
    try:
        client = get_dynamodb_client(region_name)
        params = {
            'TableName': table_name
        }
        
        if attribute_definitions:
            params['AttributeDefinitions'] = attribute_definitions
        if billing_mode:
            params['BillingMode'] = billing_mode
        if deletion_protection_enabled is not None:
            params['DeletionProtectionEnabled'] = deletion_protection_enabled
        if global_secondary_index_updates:
            params['GlobalSecondaryIndexUpdates'] = global_secondary_index_updates
        if on_demand_throughput:
            params['OnDemandThroughput'] = on_demand_throughput
        if provisioned_throughput:
            params['ProvisionedThroughput'] = provisioned_throughput
        if replica_updates:
            params['ReplicaUpdates'] = replica_updates
        if sse_specification:
            params['SSESpecification'] = sse_specification.model_dump(exclude_none=True)
        if stream_specification:
            params['StreamSpecification'] = stream_specification
        if table_class:
            params['TableClass'] = table_class
        if warm_throughput:
            params['WarmThroughput'] = warm_throughput
            
        response = client.update_table(**params)
        return response['TableDescription']
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def list_tables(
    exclusive_start_table_name: str = Field(
        default=None,
        description="The LastEvaluatedTableName value from the previous paginated call"
    ),
    limit: int = Field(
        default=None,
        description="Max number of table names to return",
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns a paginated list of table names in your account."""
    try:
        client = get_dynamodb_client(region_name)
        params = {}
        if exclusive_start_table_name:
            params['ExclusiveStartTableName'] = exclusive_start_table_name
        if limit:
            params['Limit'] = limit
        response = client.list_tables(**params)
        return {
            'TableNames': response['TableNames'],
            'LastEvaluatedTableName': response.get('LastEvaluatedTableName')
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def create_table(
    table_name: str = Field(
        description="The name of the table to create.",
    ),
    attribute_definitions: List[AttributeDefinition] = Field(
        description="Describe the key schema for the table and indexes."
    ),
    key_schema: List[KeySchemaElement] = Field(
        description="Specifies primary key attributes of the table."
    ),
    billing_mode: Literal['PROVISIONED', 'PAY_PER_REQUEST'] = billing_mode,
    global_secondary_indexes: List[GlobalSecondaryIndex] = Field(
        default=None,
        description="GSIs to be created on the table."
    ),
    provisioned_throughput: ProvisionedThroughput = Field(
        default=None,
        description="Provisioned throughput settings. Required if BillingMode is PROVISIONED."
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Creates a new DynamoDB table with optional secondary indexes. This is an asynchronous operation."""
    try:
        client = get_dynamodb_client(region_name)
        params = {
            'TableName': table_name,
            'AttributeDefinitions': attribute_definitions,
            'KeySchema': key_schema
        }
        
        if billing_mode:
            params['BillingMode'] = billing_mode
        if global_secondary_indexes:
            params['GlobalSecondaryIndexes'] = global_secondary_indexes
        if provisioned_throughput:
            params['ProvisionedThroughput'] = provisioned_throughput
        
        response = client.create_table(**params)
        return response['TableDescription']
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def describe_table(
    table_name: str = table_name,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns table information including status, creation time, key schema and indexes."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.describe_table(TableName=table_name)
        return response['Table']
    except Exception as e:
        # Convert boto3 errors to dict for JSON serialization
        return {"error": str(e)}


@app.tool()
async def create_backup(
    table_name: str = table_name,
    backup_name: str = Field(
        description="Specified name for the backup.",
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Creates a backup of a DynamoDB table."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.create_backup(
            TableName=table_name,
            BackupName=backup_name
        )
        return response['BackupDetails']
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def describe_backup(
    backup_arn: str = Field(
        description="The Amazon Resource Name (ARN) associated with the backup.",
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Describes an existing backup of a table."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.describe_backup(
            BackupArn=backup_arn
        )
        return response['BackupDescription']
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def list_backups(
    table_name: str = table_name,
    backup_type: str = Field(
        default=None,
        description="Filter by backup type: USER (on-demand backup created by you), SYSTEM (automatically created by DynamoDB), AWS_BACKUP (created by AWS Backup), or ALL (all types).",
        pattern="^(USER|SYSTEM|AWS_BACKUP|ALL)$"
    ),
    exclusive_start_backup_arn: str = Field(
        default=None,
        description="LastEvaluatedBackupArn from a previous paginated call.",
    ),
    limit: int = Field(
        default=None,
        description="Maximum number of backups to return.",
        ge=1,
        le=100
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns a list of table backups."""
    try:
        client = get_dynamodb_client(region_name)
        params = {}
        if backup_type:
            params['BackupType'] = backup_type
        if exclusive_start_backup_arn:
            params['ExclusiveStartBackupArn'] = exclusive_start_backup_arn
        if limit:
            params['Limit'] = limit
        if table_name:
            params['TableName'] = table_name
        
        response = client.list_backups(**params)
        return {
            'BackupSummaries': response.get('BackupSummaries', []),
            'LastEvaluatedBackupArn': response.get('LastEvaluatedBackupArn')
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def restore_table_from_backup(
    backup_arn: str = Field(
        description="The Amazon Resource Name (ARN) associated with the backup.",
    ),
    target_table_name: str = Field(
        description="The name of the new table.",
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Creates a new table from a backup."""
    try:
        client = get_dynamodb_client(region_name)
        params = {
            'BackupArn': backup_arn,
            'TargetTableName': target_table_name
        }
        
        response = client.restore_table_from_backup(**params)
        return response['TableDescription']
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def describe_limits(
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns the current provisioned-capacity quotas for your AWS account and tables in a Region."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.describe_limits()
        return {
            'AccountMaxReadCapacityUnits': response['AccountMaxReadCapacityUnits'],
            'AccountMaxWriteCapacityUnits': response['AccountMaxWriteCapacityUnits'],
            'TableMaxReadCapacityUnits': response['TableMaxReadCapacityUnits'],
            'TableMaxWriteCapacityUnits': response['TableMaxWriteCapacityUnits']
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def describe_time_to_live(
    table_name: str = table_name,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns the Time to Live (TTL) settings for a table."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.describe_time_to_live(
            TableName=table_name
        )
        return response['TimeToLiveDescription']
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def describe_endpoints(
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns DynamoDB endpoints for the current region."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.describe_endpoints()
        return {
            'Endpoints': response['Endpoints']
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def describe_export(
    export_arn: str = Field(
        description="The Amazon Resource Name (ARN) associated with the export.",
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns information about a table export."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.describe_export(
            ExportArn=export_arn
        )
        return response['ExportDescription']
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def list_exports(
    max_results: int = Field(
        default=None,
        description="Maximum number of results to return per page.",
    ),
    next_token: str = Field(
        default=None,
        description="Token to fetch the next page of results."
    ),
    table_arn: str = Field(
        default=None,
        description="The Amazon Resource Name (ARN) associated with the exported table.",
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns a list of table exports."""
    try:
        client = get_dynamodb_client(region_name)
        params = {}
        if max_results:
            params['MaxResults'] = max_results
        if next_token:
            params['NextToken'] = next_token
        if table_arn:
            params['TableArn'] = table_arn
        
        response = client.list_exports(**params)
        return {
            'ExportSummaries': response.get('ExportSummaries', []),
            'NextToken': response.get('NextToken')
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def describe_continuous_backups(
    table_name: str = table_name,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns continuous backup and point in time recovery status for a table."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.describe_continuous_backups(
            TableName=table_name
        )
        return response['ContinuousBackupsDescription']
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def untag_resource(
    resource_arn: str = resource_arn,
    tag_keys: List[str] = Field(
        description="List of tags to remove.",
        min_items=1
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Removes tags from a DynamoDB resource."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.untag_resource(
            ResourceArn=resource_arn,
            TagKeys=tag_keys
        )
        return response
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def tag_resource(
    resource_arn: str = resource_arn,
    tags: List[Tag] = Field(
        description="Tags to be assigned."
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Adds tags to a DynamoDB resource."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.tag_resource(
            ResourceArn=resource_arn,
            Tags=tags
        )
        return response
    except Exception as e:
        return {"error": str(e)}


@app.tool()
async def list_tags_of_resource(
    resource_arn: str = resource_arn,
    next_token: str = Field(
        default=None,
        description="The NextToken from the previous paginated call"
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Returns tags for a DynamoDB resource."""
    try:
        client = get_dynamodb_client(region_name)
        params = {
            'ResourceArn': resource_arn
        }
        if next_token:
            params['NextToken'] = next_token
            
        response = client.list_tags_of_resource(**params)
        return {
            'Tags': response.get('Tags', []),
            'NextToken': response.get('NextToken')
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def delete_table(
    table_name: str = table_name,
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """The DeleteTable operation deletes a table and all of its items. This is an asynchronous operation that puts the table into DELETING state until DynamoDB completes the deletion."""
    try:
        client = get_dynamodb_client(region_name)
        response = client.delete_table(TableName=table_name)
        return response['TableDescription']
    except Exception as e:
        return {"error": str(e)}

@app.tool()
async def update_continuous_backups(
    table_name: str = table_name,
    point_in_time_recovery_enabled: bool = Field(
        description="Enable or disable point in time recovery."
    ),
    recovery_period_in_days: int = Field(
        default=None,
        description="Number of days to retain point in time recovery backups.",
    ),
    region_name: str = Field(
        default=None,
        description="The aws region to run the tool"
    )
) -> dict:
    """Enables or disables point in time recovery for the specified table."""
    try:
        client = get_dynamodb_client(region_name)
        params = {
            'TableName': table_name,
            'PointInTimeRecoverySpecification': {
                'PointInTimeRecoveryEnabled': point_in_time_recovery_enabled
            }
        }
        if recovery_period_in_days:
            params['PointInTimeRecoverySpecification']['RecoveryPeriodInDays'] = recovery_period_in_days
        
        response = client.update_continuous_backups(**params)
        return response['ContinuousBackupsDescription']
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    app.run()
