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

import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.threshold import (
    BaseThreshold,
    StaticThreshold,
    AnomalyDetectionThreshold,
    create_threshold,
    STATIC_TYPE,
    ANOMALY_DETECTION_TYPE,
    DEFAULT_SENSITIVITY
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.seasonal_detector import Seasonality


class TestStaticThreshold:

    def test_static_threshold_creation(self):
        threshold = StaticThreshold(value=80.0, justification="CPU limit")
        
        assert threshold.type == STATIC_TYPE
        assert threshold.value == 80.0
        assert threshold.justification == "CPU limit"

    def test_static_threshold_defaults(self):
        threshold = StaticThreshold(value=90.0)
        
        assert threshold.type == STATIC_TYPE
        assert threshold.value == 90.0
        assert threshold.justification == ""


class TestAnomalyDetectionThreshold:

    def test_anomaly_threshold_creation(self):
        threshold = AnomalyDetectionThreshold(
            sensitivity=50,
            justification="Daily pattern"
        )
        
        assert threshold.type == ANOMALY_DETECTION_TYPE
        assert threshold.sensitivity == 50
        assert threshold.justification == "Daily pattern"

    def test_anomaly_threshold_defaults(self):
        threshold = AnomalyDetectionThreshold()
        
        assert threshold.type == ANOMALY_DETECTION_TYPE
        assert threshold.sensitivity == DEFAULT_SENSITIVITY
        assert threshold.justification == ""

    def test_sensitivity_validation(self):
        with pytest.raises(ValueError, match="Sensitivity must be between 1 and 100"):
            AnomalyDetectionThreshold(sensitivity=0)
        
        with pytest.raises(ValueError, match="Sensitivity must be between 1 and 100"):
            AnomalyDetectionThreshold(sensitivity=101)


class TestThresholdFactory:

    def test_create_static_threshold(self):
        data = {"type": STATIC_TYPE, "value": 75.0, "justification": "Test"}
        threshold = create_threshold(data)
        
        assert isinstance(threshold, StaticThreshold)
        assert threshold.value == 75.0
        assert threshold.justification == "Test"

    def test_create_anomaly_threshold(self):
        data = {
            "type": ANOMALY_DETECTION_TYPE, 
            "sensitivity": 25,
        }
        threshold = create_threshold(data)
        
        assert isinstance(threshold, AnomalyDetectionThreshold)
        assert threshold.sensitivity == 25

    def test_create_threshold_defaults_to_static(self):
        data = {"value": 85.0}
        threshold = create_threshold(data)
        
        assert isinstance(threshold, StaticThreshold)
        assert threshold.value == 85.0
        assert threshold.type == STATIC_TYPE

    def test_create_threshold_unknown_type(self):
        data = {"type": "unknown", "value": 50.0}
        
        with pytest.raises(ValueError, match="Unknown threshold type: unknown"):
            create_threshold(data)
