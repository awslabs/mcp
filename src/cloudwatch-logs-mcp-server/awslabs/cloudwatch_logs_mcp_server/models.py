import datetime
import re
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Set


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


class SavedQuery(BaseModel):
    """Represents a saved CloudWatch Logs Insights query."""

    logGroupNames: Set[str] = Field(
        default_factory=set, description='Log groups associated with the query, optional.'
    )
    name: str = Field(..., description='Name of the saved query')
    queryString: str = Field(
        ..., description='The query string in the Cloudwatch Log Insights Query Language.'
    )
    logGroupPrefixes: Set[str] = Field(
        default_factory=set,
        description='Prefixes of log groups associated with the query, optional.',
    )

    @model_validator(mode='before')
    @classmethod
    def extract_prefixes(cls, values):
        """Extract log group prefixes by parsing the SOURCE command of the query string, if present."""
        query_string = values['queryString']
        if query_string:
            # Match the SOURCE ... pattern and extract the content inside parentheses
            source_match = re.search(r'SOURCE\s+logGroups\((.*?)\)', query_string)
            if source_match:
                content = source_match.group(1)
                # Extract namePrefix and its values
                prefix_match = re.search(r'namePrefix:\s*\[(.*?)\]', content)
                if prefix_match:
                    # Split the prefixes and strip whitespace and quotes
                    values['logGroupPrefixes'] = {
                        p.strip().strip('\'"') for p in prefix_match.group(1).split(',')
                    }
        return values


class LogMetadata(BaseModel):
    """Represents information about a CloudWatch log."""

    log_group_metadata: List[LogGroupMetadata] = Field(
        ..., description='List of metadata about log groups'
    )
    saved_queries: List[SavedQuery] = Field(
        ..., description='Saved queries associated with the log'
    )


class CancelQueryResult(BaseModel):
    """Result of canceling a query."""

    success: bool = Field(
        ..., description='True if the query was successfully cancelled, false otherwise'
    )
