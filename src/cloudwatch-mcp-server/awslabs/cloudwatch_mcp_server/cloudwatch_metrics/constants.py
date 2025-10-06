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

# CloudWatch MCP Server Constants

# Time constants
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7

# Analysis period constants
DEFAULT_ANALYSIS_WEEKS = 2
DEFAULT_ANALYSIS_PERIOD = (
    MINUTES_PER_HOUR * HOURS_PER_DAY * DEFAULT_ANALYSIS_WEEKS * DAYS_PER_WEEK
)  # 2 weeks in minutes

# Threshold constants
DEFAULT_SENSITIVITY = 2.0
ANOMALY_DETECTION_TYPE = 'anomaly_detection'
STATIC_TYPE = 'static'
COMPARISON_OPERATOR_ANOMALY = 'LessThanLowerOrGreaterThanUpperThreshold'
TREAT_MISSING_DATA_BREACHING = 'breaching'

# Seasonality constants
SEASONALITY_STRENGTH_THRESHOLD = 0.6  # See https://robjhyndman.com/hyndsight/tsoutliers/
ROUNDING_THRESHOLD = 0.1

# Numerical stability
NUMERICAL_STABILITY_THRESHOLD = 1e-10
STATISTICAL_SIGNIFICANCE_THRESHOLD = 0.05
