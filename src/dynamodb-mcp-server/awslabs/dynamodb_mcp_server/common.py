from typing import Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict


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
    ScanFilter: Optional[
        Dict[str, AttributeValue]
    ]  # Legacy parameter (must use AttributeValue format e.g. {'S': 'value'})
    ConditionalOperator: Optional[Literal['AND', 'OR']]  # Legacy parameter
    ExclusiveStartKey: Optional[
        Dict[str, KeyAttributeValue]
    ]  # Primary key attributes in AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]
    TotalSegments: Optional[int]
    Segment: Optional[int]
    ProjectionExpression: Optional[str]
    FilterExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[
        Dict[str, AttributeValue]
    ]  # values must use AttributeValue format e.g. {'S': 'value'}
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
    ExpressionAttributeValues: Optional[
        Dict[str, AttributeValue]
    ]  # values must use AttributeValue format e.g. {'S': 'value'}
    ScanIndexForward: Optional[bool]
    ExclusiveStartKey: Optional[
        Dict[str, KeyAttributeValue]
    ]  # Primary key attributes in AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]


class DeleteItemInput(TypedDict, total=False):
    """Parameters for DeleteItem operation."""

    TableName: str  # required
    Key: Dict[
        str, KeyAttributeValue
    ]  # required - primary key attributes in AttributeValue format e.g. {'S': 'value'}
    ConditionExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[
        Dict[str, AttributeValue]
    ]  # values must use AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]
    ReturnItemCollectionMetrics: Optional[ReturnItemCollectionMetrics]
    ReturnValues: Optional[ReturnValue]
    ReturnValuesOnConditionCheckFailure: Optional[Literal['ALL_OLD', 'NONE']]


class UpdateItemInput(TypedDict, total=False):
    """Parameters for UpdateItem operation."""

    TableName: str  # required
    Key: Dict[
        str, KeyAttributeValue
    ]  # required - primary key attributes in AttributeValue format e.g. {'S': 'value'}
    UpdateExpression: Optional[str]
    ConditionExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[
        Dict[str, AttributeValue]
    ]  # values must use AttributeValue format e.g. {'S': 'value'}
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]
    ReturnItemCollectionMetrics: Optional[ReturnItemCollectionMetrics]
    ReturnValues: Optional[ReturnValue]
    ReturnValuesOnConditionCheckFailure: Optional[Literal['ALL_OLD', 'NONE']]


class GetItemInput(TypedDict, total=False):
    """Parameters for GetItem operation."""

    TableName: str  # required
    Key: Dict[
        str, KeyAttributeValue
    ]  # required - primary key attributes in AttributeValue format e.g. {'S': 'value'}
    AttributesToGet: Optional[List[str]]
    ConsistentRead: Optional[bool]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ProjectionExpression: Optional[str]
    ReturnConsumedCapacity: Optional[ReturnConsumedCapacity]


class PutItemInput(TypedDict, total=False):
    """Parameters for PutItem operation."""

    TableName: str  # required
    Item: Dict[
        str, AttributeValue
    ]  # required - maps attribute name to AttributeValue (must use AttributeValue format e.g. {'S': 'value'})
    ConditionExpression: Optional[str]
    ExpressionAttributeNames: Optional[Dict[str, str]]
    ExpressionAttributeValues: Optional[
        Dict[str, AttributeValue]
    ]  # values must use AttributeValue format e.g. {'S': 'value'}
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


class SSESpecification(TypedDict, total=False):
    """Set Enabled to true for AWS managed key (KMS charges apply). set it to false for AWS owned key."""

    Enabled: bool
    SSEType: Literal['KMS']
    KMSMasterKeyId: str


class TimeToLiveSpecification(TypedDict):
    AttributeName: str  # The name of the TTL attribute used to store the expiration time for items
    Enabled: bool  # Indicates whether TTL is enabled (true) or disabled (false) on the table


class GetResourcePolicyInput(TypedDict):
    ResourceArn: str  # The Amazon Resource Name (ARN) of the DynamoDB resource to which the policy is attached


class PutResourcePolicyInput(TypedDict, total=False):
    Policy: str  # An AWS resource-based policy document in JSON format
    ResourceArn: str  # The Amazon Resource Name (ARN) of the DynamoDB resource to which the policy will be attached
    ConfirmRemoveSelfResourceAccess: (
        bool  # Set to true to confirm removing your permissions to change the policy in the future
    )
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


class CreateTableInput(TypedDict, total=False):
    """Parameters for CreateTable operation."""

    TableName: str  # required
    AttributeDefinitions: List[AttributeDefinition]  # required
    KeySchema: List[KeySchemaElement]  # required
    BillingMode: Literal['PROVISIONED', 'PAY_PER_REQUEST']
    GlobalSecondaryIndexes: List[GlobalSecondaryIndex]
    ProvisionedThroughput: ProvisionedThroughput


class UpdateTableInput(TypedDict, total=False):
    """Parameters for UpdateTable operation."""

    TableName: str  # required
    AttributeDefinitions: List[AttributeDefinition]
    BillingMode: Literal['PROVISIONED', 'PAY_PER_REQUEST']
    DeletionProtectionEnabled: bool
    GlobalSecondaryIndexUpdates: List[GlobalSecondaryIndexUpdate]
    OnDemandThroughput: OnDemandThroughput
    ProvisionedThroughput: ProvisionedThroughput
    ReplicaUpdates: List[ReplicationGroupUpdate]
    SSESpecification: SSESpecification
    StreamSpecification: StreamSpecification
    TableClass: Literal['STANDARD', 'STANDARD_INFREQUENT_ACCESS']
    WarmThroughput: WarmThroughput
