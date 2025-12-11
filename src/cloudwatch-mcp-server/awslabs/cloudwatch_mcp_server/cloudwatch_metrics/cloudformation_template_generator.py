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

import logging
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import COMPARISON_OPERATOR_ANOMALY
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import AnomalyDetectionAlarmThreshold
from typing import Any, Dict


logger = logging.getLogger(__name__)


class CloudFormationTemplateGenerator:
    """Generate CloudFormation JSON for CloudWatch Anomaly Detection Alarms."""

    def generate_metric_alarm_template(self, alarm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate CFN template for a single CloudWatch Alarm."""
        if not self._is_anomaly_detection_alarm(alarm_data):
            return {}

        # Validate required fields
        if not alarm_data.get('metricName'):
            raise ValueError(
                'Metric Name is required to generate CloudFormation templates for Cloudwatch Alarms'
            )
        if not alarm_data.get('namespace'):
            raise ValueError(
                'Metric Namespace is required to generate CloudFormation templates for Cloudwatch Alarms'
            )

        # Process alarm data and add computed fields
        formatted_data = self._format_anomaly_detection_alarm_data(alarm_data)

        # Build resources dict
        anomaly_detector_key = f'{formatted_data["resourceKey"]}AnomalyDetector'
        alarm_key = f'{formatted_data["resourceKey"]}Alarm'

        resources = {
            anomaly_detector_key: {
                'Type': 'AWS::CloudWatch::AnomalyDetector',
                'Properties': {
                    'MetricName': formatted_data['metricName'],
                    'Namespace': formatted_data['namespace'],
                    'Stat': formatted_data['statistic'],
                    'Dimensions': formatted_data['dimensions'],
                },
            },
            alarm_key: {
                'Type': 'AWS::CloudWatch::Alarm',
                'DependsOn': anomaly_detector_key,
                'Properties': {
                    'AlarmDescription': formatted_data['alarmDescription'],
                    'Metrics': [
                        {
                            'Expression': f'ANOMALY_DETECTION_BAND(m1, {formatted_data["sensitivity"]})',
                            'Id': 'ad1',
                        },
                        {
                            'Id': 'm1',
                            'MetricStat': {
                                'Metric': {
                                    'MetricName': formatted_data['metricName'],
                                    'Namespace': formatted_data['namespace'],
                                    'Dimensions': formatted_data['dimensions'],
                                },
                                'Stat': formatted_data['statistic'],
                                'Period': formatted_data['period'],
                            },
                        },
                    ],
                    'EvaluationPeriods': formatted_data['evaluationPeriods'],
                    'DatapointsToAlarm': formatted_data['datapointsToAlarm'],
                    'ThresholdMetricId': 'ad1',
                    'ComparisonOperator': formatted_data['comparisonOperator'],
                    'TreatMissingData': formatted_data['treatMissingData'],
                },
            },
        }

        final_template = {
            'AWSTemplateFormatVersion': '2010-09-09',
            'Description': 'CloudWatch Alarms and Anomaly Detectors',
            'Resources': resources,
        }

        return final_template

    def _is_anomaly_detection_alarm(self, alarm_data: Dict[str, Any]) -> bool:
        return alarm_data.get('comparisonOperator') == COMPARISON_OPERATOR_ANOMALY

    def _format_anomaly_detection_alarm_data(self, alarm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize alarm data and add computed fields."""
        formatted_data = alarm_data.copy()

        # Generate resource key from metric name and namespace
        formatted_data['resourceKey'] = self._generate_resource_key(
            metric_name=alarm_data.get('metricName', ''),
            namespace=alarm_data.get('namespace', ''),
            dimensions=alarm_data.get('dimensions', []),
        )

        # Process threshold value
        threshold = alarm_data.get('threshold', {})
        formatted_data['sensitivity'] = threshold.get(
            'sensitivity', AnomalyDetectionAlarmThreshold.DEFAULT_SENSITIVITY
        )

        # Set defaults
        formatted_data.setdefault(
            'alarmDescription', 'CloudWatch Alarm generated by CloudWatch MCP server.'
        )
        formatted_data.setdefault('statistic', 'Average')
        formatted_data.setdefault('period', 300)
        formatted_data.setdefault('evaluationPeriods', 2)
        formatted_data.setdefault('datapointsToAlarm', 2)
        formatted_data.setdefault('comparisonOperator', COMPARISON_OPERATOR_ANOMALY)
        formatted_data.setdefault('treatMissingData', 'missing')
        formatted_data.setdefault('dimensions', [])

        return formatted_data

    def _generate_resource_key(self, metric_name: str, namespace: str, dimensions: list) -> str:
        """Generate CloudFormation resource key from metric components to act as logical id."""
        # Strip AWS/ prefix from namespace (AWS CDK style)
        clean_namespace = namespace.replace('AWS/', '')

        # Add first dimension key and value for uniqueness if present
        dimension_suffix = ''
        if dimensions:
            first_dim = dimensions[0]
            dim_name = first_dim.get('Name', '')
            dim_value = first_dim.get('Value', '')
            dimension_suffix = f'{dim_name}{dim_value}'

        resource_base = f'{clean_namespace}{metric_name}{dimension_suffix}'
        return self._sanitize_resource_name(resource_base)

    def _sanitize_resource_name(self, name: str) -> str:
        """Sanitize name for CloudFormation resource key."""
        # Remove non-alphanumeric characters
        sanitized = ''.join(c for c in name if c.isalnum())

        # Ensure it starts with letter
        if not sanitized or not sanitized[0].isalpha():
            sanitized = 'Resource' + sanitized

        # Truncate if too long
        if len(sanitized) > 255:
            sanitized = sanitized[:255]

        return sanitized
