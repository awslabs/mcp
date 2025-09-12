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

import json
import yaml
import re
from typing import List, Dict, Any
from loguru import logger

from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import AlarmRecommendation, COMPARISON_OPERATOR_ANOMALY


def _format_dimensions(dimensions):
    import shlex
    return ' '.join([f'Name={dim.name},Value={shlex.quote(dim.value)}' for dim in dimensions])


def _convert_to_yaml(template: Dict[str, Any]) -> str:
    try:
        return yaml.dump(template, default_flow_style=False, sort_keys=False)
    except yaml.YAMLError as e:
        logger.error(f"Failed to serialize template to YAML: {e}")
        raise ValueError(f"Template serialization failed: {e}")


def _sanitize_resource_name(name: str) -> str:
    sanitized = re.sub(r'[^a-zA-Z0-9]', '', name)
    if not sanitized:
        return "DefaultResource"
    return sanitized


class CloudWatchTemplateGenerator:
    def generate_output(self, recommendations: List[AlarmRecommendation], output_format: str):
        if output_format == 'cloudformation':
            return self.generate_cloudformation_template(recommendations)
        elif output_format == 'cli':
            return self.generate_cli_commands(recommendations)
        elif output_format == 'complete':
            cfn_recommendations = self.generate_cloudformation_template(recommendations.copy())
            return self.generate_cli_commands(cfn_recommendations)
        else:
            raise ValueError(f"Invalid output_format: {output_format}. Must be 'cloudformation', 'cli', or 'complete'")

    def generate_cloudformation_template(self, recommendations: List[AlarmRecommendation]) -> List[AlarmRecommendation]:
        for rec in recommendations:
            if self._is_anomaly_detection(rec):
                rec.cloudformation_template = self._generate_anomaly_cfn_template(rec)
                rec.cli_commands = '\n\n'.join(self._generate_anomaly_cli_commands(rec))
            else:
                rec.cloudformation_template = self._generate_threshold_cfn_template(rec)
                rec.cli_commands = self._generate_threshold_cli_command(rec)
        return recommendations

    def _is_anomaly_detection(self, rec: AlarmRecommendation) -> bool:
        return (rec.comparisonOperator == COMPARISON_OPERATOR_ANOMALY and 
                rec.threshold is not None and hasattr(rec.threshold, 'sensitivity'))

    def generate_cli_commands(self, recommendations: List[AlarmRecommendation]) -> List[AlarmRecommendation]:
        for rec in recommendations:
            if self._is_anomaly_detection(rec):
                rec.cli_commands = '\n\n'.join(self._generate_anomaly_cli_commands(rec))
            else:
                rec.cli_commands = self._generate_threshold_cli_command(rec)
        return recommendations

    def _generate_anomaly_cfn_template(self, rec: AlarmRecommendation) -> str:
        template = {
            'AWSTemplateFormatVersion': '2010-09-09',
            'Resources': {},
            'Outputs': {}
        }
        self._add_anomaly_detection_resources(template, rec)
        return _convert_to_yaml(template)

    def _generate_threshold_cfn_template(self, rec: AlarmRecommendation) -> str:
        template = {
            'AWSTemplateFormatVersion': '2010-09-09',
            'Resources': {},
            'Outputs': {}
        }
        self._add_threshold_alarm_resource(template, rec)
        return _convert_to_yaml(template)

    def _add_anomaly_detection_resources(self, template: Dict[str, Any], rec: AlarmRecommendation):
        metric_name = rec.metricName or "UnknownMetric"
        detector_name = f"{_sanitize_resource_name(metric_name)}AnomalyDetector"
        alarm_name = f"{_sanitize_resource_name(metric_name)}AnomalyAlarm"

        # Add anomaly detector
        template['Resources'][detector_name] = {
            'Type': 'AWS::CloudWatch::AnomalyDetector',
            'Properties': {
                'MetricName': metric_name,
                'Namespace': rec.namespace,
                'Stat': rec.statistic
            }
        }

        if rec.dimensions:
            template['Resources'][detector_name]['Properties']['Dimensions'] = [
                {'Name': dim.name, 'Value': dim.value} for dim in rec.dimensions
            ]

        # Add anomaly alarm
        sensitivity = getattr(rec.threshold, 'sensitivity', 2)
        template['Resources'][alarm_name] = {
            'Type': 'AWS::CloudWatch::Alarm',
            'Properties': {
                'AlarmDescription': rec.alarmDescription,
                'AlarmName': alarm_name,
                'ComparisonOperator': COMPARISON_OPERATOR_ANOMALY,
                'EvaluationPeriods': rec.evaluationPeriods,
                'Metrics': [
                    {
                        'Expression': f'ANOMALY_DETECTION_BAND(m1, {sensitivity})',
                        'Id': 'ad1'
                    },
                    {
                        'Id': 'm1',
                        'MetricStat': {
                            'Metric': {
                                'MetricName': metric_name,
                                'Namespace': rec.namespace
                            },
                            'Period': rec.period,
                            'Stat': rec.statistic
                        }
                    }
                ],
                'ThresholdMetricId': 'ad1',
                'TreatMissingData': rec.treatMissingData
            }
        }

        if rec.dimensions:
            template['Resources'][alarm_name]['Properties']['Metrics'][1]['MetricStat']['Metric']['Dimensions'] = [
                {'Name': dim.name, 'Value': dim.value} for dim in rec.dimensions
            ]

        template['Outputs'][f'{alarm_name}Arn'] = {
            'Description': f'ARN of the {alarm_name}',
            'Value': {'Ref': alarm_name}
        }

    def _add_threshold_alarm_resource(self, template: Dict[str, Any], rec: AlarmRecommendation):
        metric_name = rec.metricName or "UnknownMetric"
        alarm_name = f"{_sanitize_resource_name(metric_name)}Alarm"

        template['Resources'][alarm_name] = {
            'Type': 'AWS::CloudWatch::Alarm',
            'Properties': {
                'AlarmDescription': rec.alarmDescription,
                'AlarmName': alarm_name,
                'MetricName': metric_name,
                'Namespace': rec.namespace,
                'Statistic': rec.statistic,
                'Period': rec.period,
                'EvaluationPeriods': rec.evaluationPeriods,
                'ComparisonOperator': rec.comparisonOperator,
                'Threshold': rec.threshold.value,
                'TreatMissingData': rec.treatMissingData
            }
        }

        if rec.dimensions:
            template['Resources'][alarm_name]['Properties']['Dimensions'] = [
                {'Name': dim.name, 'Value': dim.value} for dim in rec.dimensions
            ]

        template['Outputs'][f'{alarm_name}Arn'] = {
            'Description': f'ARN of the {alarm_name}',
            'Value': {'Ref': alarm_name}
        }

    def _generate_anomaly_cli_commands(self, rec: AlarmRecommendation) -> List[str]:
        commands = []
        
        # Anomaly detector command
        detector_cmd = [
            'aws cloudwatch put-anomaly-detector',
            f'--namespace "{rec.namespace}"',
            f'--metric-name "{rec.metricName}"',
            f'--stat "{rec.statistic}"'
        ]

        if rec.dimensions:
            dimensions = _format_dimensions(rec.dimensions)
            detector_cmd.append(f'--dimensions {dimensions}')

        commands.append(' \\\n  '.join(detector_cmd))

        # Anomaly alarm command
        metric_name = rec.metricName or "UnknownMetric"
        sensitivity = getattr(rec.threshold, 'sensitivity', 2)
        
        metrics_json = [
            {
                'Id': 'm1',
                'MetricStat': {
                    'Metric': {
                        'MetricName': rec.metricName,
                        'Namespace': rec.namespace
                    },
                    'Period': rec.period,
                    'Stat': rec.statistic
                }
            },
            {
                'Id': 'ad1',
                'Expression': f'ANOMALY_DETECTION_BAND(m1, {sensitivity})'
            }
        ]

        if rec.dimensions:
            metrics_json[0]['MetricStat']['Metric']['Dimensions'] = [
                {'Name': dim.name, 'Value': dim.value} for dim in rec.dimensions
            ]

        alarm_cmd = [
            'aws cloudwatch put-metric-alarm',
            f'--alarm-name "{metric_name.replace("/", "")}AnomalyAlarm"',
            f'--alarm-description "{rec.alarmDescription}"',
            f'--comparison-operator "{COMPARISON_OPERATOR_ANOMALY}"',
            f'--evaluation-periods {rec.evaluationPeriods}',
            f"--metrics '{json.dumps(metrics_json, separators=(',', ':'))}'",
            '--threshold-metric-id "ad1"',
            f'--treat-missing-data "{rec.treatMissingData}"'
        ]

        commands.append(' \\\n  '.join(alarm_cmd))
        return commands

    def _generate_threshold_cli_command(self, rec: AlarmRecommendation) -> str:
        metric_name = rec.metricName or "UnknownMetric"
        
        cmd = [
            'aws cloudwatch put-metric-alarm',
            f'--alarm-name "{metric_name.replace("/", "")}Alarm"',
            f'--alarm-description "{rec.alarmDescription}"',
            f'--metric-name "{rec.metricName}"',
            f'--namespace "{rec.namespace}"',
            f'--statistic "{rec.statistic}"',
            f'--period {rec.period}',
            f'--evaluation-periods {rec.evaluationPeriods}',
            f'--comparison-operator "{rec.comparisonOperator}"',
            f'--threshold {rec.threshold.value}',
            f'--treat-missing-data "{rec.treatMissingData}"'
        ]

        if rec.dimensions:
            dimensions = _format_dimensions(rec.dimensions)
            cmd.append(f'--dimensions {dimensions}')

        return ' \\\n  '.join(cmd)
