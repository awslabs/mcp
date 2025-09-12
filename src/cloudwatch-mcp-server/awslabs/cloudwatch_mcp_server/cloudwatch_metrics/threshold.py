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

from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict

from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import DEFAULT_SENSITIVITY, ANOMALY_DETECTION_TYPE, STATIC_TYPE, SEASONALITY_STRENGTH_THRESHOLD


class BaseThreshold(BaseModel):
    type: str = Field(...)
    justification: str = Field(default="")


class StaticThreshold(BaseThreshold):
    type: str = Field(default=STATIC_TYPE)
    value: float = Field(...)


class AnomalyDetectionThreshold(BaseThreshold):
    type: str = Field(default=ANOMALY_DETECTION_TYPE)
    sensitivity: float = Field(default=DEFAULT_SENSITIVITY)
    
    @field_validator('sensitivity')
    @classmethod
    def validate_sensitivity(cls, v):
        if not 1 <= v <= 100:
            raise ValueError('Sensitivity must be between 1 and 100')
        return v


THRESHOLD_REGISTRY = {
    STATIC_TYPE: StaticThreshold,
    ANOMALY_DETECTION_TYPE: AnomalyDetectionThreshold,
}


def create_threshold(threshold_data: Dict[str, Any]) -> BaseThreshold:
    if not isinstance(threshold_data, dict):
        raise ValueError("threshold_data must be a dictionary")
    
    threshold_type = threshold_data.get("type", STATIC_TYPE)
    
    # Validate required fields based on threshold type
    if threshold_type == STATIC_TYPE and "value" not in threshold_data:
        raise ValueError("StaticThreshold requires 'value' field")
    elif threshold_type == ANOMALY_DETECTION_TYPE and "sensitivity" not in threshold_data:
        raise ValueError("AnomalyDetectionThreshold requires 'sensitivity' field")
    
    try:
        return THRESHOLD_REGISTRY[threshold_type](**threshold_data)
    except KeyError:
        raise ValueError(f"Unknown threshold type: {threshold_type}")


