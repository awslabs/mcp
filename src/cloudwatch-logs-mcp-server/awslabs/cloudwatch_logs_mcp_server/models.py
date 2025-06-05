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

import re
from awslabs.cloudwatch_logs_mcp_server.common import epoch_ms_to_utc_iso
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Dict, List, Optional, Set


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
            return epoch_ms_to_utc_iso(v)
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


class AnomalyDetector(BaseModel):
    """Represents a CloudWatch Logs Anomaly Detector."""

    anomalyDetectorArn: str = Field(..., description='The ARN of the anomaly detector')
    detectorName: str = Field(..., description='The name of the anomaly detector')
    anomalyDetectorStatus: str = Field(
        ..., description='The current status of the anomaly detector'
    )


class LogAnomaly(BaseModel):
    """Represents a detected log anomaly."""

    anomalyDetectorArn: str = Field(
        ..., description='The ARN of the detector that found this anomaly'
    )
    logGroupArnList: List[str] = Field(
        ..., description='List of log group ARNs that match this anomaly'
    )
    firstSeen: str = Field(..., description='ISO 8601 timestamp when this pattern was first seen')
    lastSeen: str = Field(..., description='ISO 8601 timestamp when this pattern was last seen')
    description: str = Field(..., description='Description of the anomaly')
    priority: str = Field(..., description='Priority of the anomaly')
    patternRegex: str = Field(..., description='Regex pattern that matched this anomaly')
    patternString: str = Field(..., description='String pattern that matched this anomaly')
    logSamples: List[Dict[str, str]] = Field(
        ..., description='Sample log messages that matched this anomaly'
    )
    histogram: Dict[str, int] = Field(
        ..., description='Histogram of log message counts for this anomaly'
    )

    @field_validator('firstSeen', 'lastSeen', mode='before')
    @classmethod
    def convert_to_iso8601(cls, v):
        """If value passed is an int of Unix Epoch, convert to an ISO timestamp string."""
        if isinstance(v, int):
            return epoch_ms_to_utc_iso(v)
        return v

    @field_validator('histogram', mode='before')
    @classmethod
    def convert_histogram_to_iso8601(cls, v):
        """If value passed is an int of Unix Epoch, convert to an ISO timestamp string."""
        return {epoch_ms_to_utc_iso(int(timestamp)): count for timestamp, count in v.items()}

    @field_validator('logSamples', mode='before')
    @classmethod
    def convert_log_samples_to_iso8601(cls, v):
        """If value passed is an int of Unix Epoch, convert to an ISO timestamp string, limit to 1.

        LogSamples are limited to 1 to conserve context window tokens
        """

        def replace_timestamp_with_iso8601(sample: Dict):
            sample['timestamp'] = epoch_ms_to_utc_iso(sample['timestamp'])
            return sample

        return [replace_timestamp_with_iso8601(sample) for sample in v[:1]]


class LogAnomalyResults(BaseModel):
    """Represents the results of a log anomaly query."""

    anomaly_detectors: List[AnomalyDetector] = Field(
        ..., description='List of anomaly detectors monitoring this log group'
    )
    anomalies: List[LogAnomaly] = Field(
        ..., description='List of anomalies found in the specified time range'
    )


class LogAnalysisResult(BaseModel):
    """Result of analyzing a log group."""

    log_anomaly_results: LogAnomalyResults = Field(
        ..., description='Results of looking for applicable log anomalies in the log group'
    )
    top_patterns: Dict[str, Any] = Field(
        ..., description='Top message patterns found in the log group'
    )
    top_patterns_containing_errors: Dict[str, Any] = Field(
        ..., description='Top error patterns for messages containing errors found in the log group'
    )


class CancelQueryResult(BaseModel):
    """Result of canceling a query."""

    success: bool = Field(
        ..., description='True if the query was successfully cancelled, false otherwise'
    )
