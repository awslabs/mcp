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

# Analysis period constants
DEFAULT_ANALYSIS_PERIOD_HOURS = 2 * 7 * 24  # 2 weeks in hours
MINUTES_PER_HOUR = 60

# Threshold constants
DEFAULT_SENSITIVITY = 2.0
ANOMALY_DETECTION_TYPE = "anomaly_detection"
STATIC_TYPE = "static"

# Seasonality constants
SEASONALITY_STRENGTH_THRESHOLD = 0.6 # See https://robjhyndman.com/hyndsight/tsoutliers/

# Numerical stability
NUMERICAL_STABILITY_THRESHOLD = 1e-10
STATISTICAL_SIGNIFICANCE_THRESHOLD = 0.05
