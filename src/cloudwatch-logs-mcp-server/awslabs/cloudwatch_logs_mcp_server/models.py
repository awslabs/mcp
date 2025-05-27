import datetime
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class LogGroupMetadata(BaseModel):
    """Represents metadata for a CloudWatch log group."""

    logGroupName: str = Field(..., description='The name of the log group')
    creationTime: str = Field(..., description='ISO 8601 timestamp when the log group was created')
    retentionInDays: Optional[int] = Field(default=None, description='Retention period, if set')
    metricFilterCount: int = Field(..., description='Number of metric filters')
    storedBytes: int = Field(..., description='The number of bytes stored')
    kmsKeyId: Optional[str] = Field(
        default=None, description='KMS Key Id used for data encryption, if set'
    )
    dataProtectionStatus: Optional[str] = Field(
        default=None,
        description='Displays whether this log group has a protection policy, or whether it had one in the past',
    )
    inheritedProperties: List[str] = Field(
        [], description='List of inherited properties for the log group'
    )
    logGroupClass: str = Field(
        'STANDARD', description='Type of log group class either STANDARD or INFREQUENT_ACCESS'
    )
    logGroupArn: str = Field(
        ...,
        description="The Amazon Resource Name (ARN) of the log group. This version of the ARN doesn't include a trailing :* after the log group name",
    )

    @field_validator('creationTime', mode='before')
    @classmethod
    def convert_to_iso8601(cls, v):
        """If value passed is an int of Unix Epoch, convert to an ISO timestamp string."""
        if isinstance(v, int):
            return datetime.datetime.fromtimestamp(v / 1000.0).isoformat()
        return v


class CancelQueryResult(BaseModel):
    """Result of canceling a query."""

    success: bool = Field(
        ..., description='True if the query was successfully cancelled, false otherwise'
    )
