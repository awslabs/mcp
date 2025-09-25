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

"""Retrieve service SLI status based on configured Application Signals SLOs."""

import logging
from .aws_clients import appsignals_client, cloudwatch_client
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


# Initialize module logger
logger = logging.getLogger(__name__)


@dataclass
class AWSConfig:
    """Configuration class for AWS settings and service parameters.

    Attributes:
        region (str): AWS region identifier (default: us-west-1)
        period_in_hours (int): Time period for metrics collection (max 24 hours)
        service_name (str): Name of the AWS service to monitor
        key_attributes (Dict[str, str]): Key attributes to identify the service
    """

    region: str
    period_in_hours: int
    service_name: str
    key_attributes: Dict[str, str] = field(default_factory=dict)

    def __init__(
        self,
        region: str = 'us-east-1',
        period_in_hours: int = 24,
        service_name: str = 'UnknownService',
        key_attributes: Optional[Dict[str, str]] = None,
    ):
        """Initialize AWSConfig with region, period, and service name.

        Args:
            region: AWS region identifier (default: us-east-1)
            period_in_hours: Time period for metrics collection, max 24 hours (default: 24)
            service_name: Name of the AWS service to monitor (default: UnknownService)
            key_attributes: Optional key attributes to override defaults
        """
        self.region = region
        self.period_in_hours = min(period_in_hours, 24)  # Ensure period doesn't exceed 24 hours
        self.service_name = service_name
        if key_attributes is not None:
            self.key_attributes = key_attributes
        else:
            self.key_attributes = {
                'Name': self.service_name,
                'Type': 'Service',
                'Environment': self.region,
            }


@dataclass
class SLOSummary:
    """Data class representing a Service Level Objective summary.

    Attributes:
        name (str): Name of the SLO
        arn (str): Amazon Resource Name
        key_attributes (Dict): Service identification attributes
        operation_name (str): Name of the monitored operation
        created_time (datetime): When the SLO was created
    """

    name: str
    arn: str
    key_attributes: Dict[str, str]
    operation_name: str
    created_time: datetime


@dataclass
class MetricDataResult:
    """Data class holding CloudWatch metric data results.

    Attributes:
        timestamps (List[datetime]): Timestamps of metric data points
        values (List[float]): Corresponding metric values
    """

    timestamps: List[datetime]
    values: List[float]


class SLIReport:
    """Class representing an SLI report with various metrics and status information.

    Provides read-only access to report data including start/end times,
    SLI status, and counts of total, successful, and breached SLOs.
    """

    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        sli_status: str,
        total_slo_count: int,
        ok_slo_count: int,
        breached_slo_count: int,
        breached_slo_names: List[str],
    ):
        """Initialize SLIReport with metrics and status information.

        Args:
            start_time: Start time of the reporting period
            end_time: End time of the reporting period
            sli_status: Overall SLI status (OK/CRITICAL)
            total_slo_count: Total number of SLOs monitored
            ok_slo_count: Number of SLOs meeting their objectives
            breached_slo_count: Number of SLOs failing to meet their objectives
            breached_slo_names: Names of SLOs that failed to meet their objectives
        """
        self._start_time = start_time
        self._end_time = end_time
        self._sli_status = sli_status
        self._total_slo_count = total_slo_count
        self._ok_slo_count = ok_slo_count
        self._breached_slo_count = breached_slo_count
        self._breached_slo_names = breached_slo_names

    # Property getters for all attributes
    @property
    def start_time(self) -> datetime:
        """Start time of the reporting period."""
        return self._start_time

    @property
    def end_time(self) -> datetime:
        """End time of the reporting period."""
        return self._end_time

    @property
    def sli_status(self) -> str:
        """Overall SLI status (OK/CRITICAL)."""
        return self._sli_status

    @property
    def total_slo_count(self) -> int:
        """Total number of SLOs monitored."""
        return self._total_slo_count

    @property
    def ok_slo_count(self) -> int:
        """Number of SLOs meeting their objectives."""
        return self._ok_slo_count

    @property
    def breached_slo_count(self) -> int:
        """Number of SLOs failing to meet their objectives."""
        return self._breached_slo_count

    @property
    def breached_slo_names(self) -> List[str]:
        """Names of SLOs that failed to meet their objectives."""
        return self._breached_slo_names.copy()


class SLIReportClient:
    """Client for generating SLI reports using AWS Application Signals and CloudWatch.

    Handles interaction with AWS services to collect and analyze SLO data.
    """

    def __init__(self, config: AWSConfig):
        """Initialize SLIReportClient with AWS configuration.

        Args:
            config: AWSConfig instance containing region, period, and service settings
        """
        self.config = config
        logger.info(
            f'Initializing SLIReportClient for service: {config.service_name}, region: {config.region}'
        )

        # Use shared AWS clients from aws_clients module
        self.signals_client = appsignals_client
        self.cloudwatch_client = cloudwatch_client
        logger.debug('Using shared AWS clients')

    def get_slo_summaries(self) -> List[SLOSummary]:
        """Fetches SLO summaries from AWS Application Signals."""
        logger.debug(f'Fetching SLO summaries for {self.config.service_name}')

        try:
            response = self.signals_client.list_service_level_objectives(
                KeyAttributes=self.config.key_attributes,
                MetricSourceTypes=['ServiceOperation'],
                IncludeLinkedAccounts=True,
            )
            logger.info(f'Retrieved {len(response.get("SloSummaries", []))} SLO summaries')
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', 'Unknown error')
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f'AWS ClientError getting SLO summaries: {error_code} - {error_msg}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error getting SLO summaries: {str(e)}', exc_info=True)
            raise

        return [
            SLOSummary(
                name=slo['Name'],
                arn=slo['Arn'],
                key_attributes=slo.get('KeyAttributes', {}),
                operation_name=slo.get('OperationName', 'N/A'),
                created_time=slo.get('CreatedTime', datetime.now(timezone.utc)),
            )
            for slo in response['SloSummaries']
        ]

    def create_metric_queries(self, slo_summaries: List[SLOSummary]) -> List[Dict[str, Any]]:
        """Creates CloudWatch metric queries for each SLO."""
        return [
            {
                'Id': f'slo{i}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/ApplicationSignals',
                        'MetricName': 'BreachedCount',
                        'Dimensions': [{'Name': 'SloName', 'Value': slo.name}],
                    },
                    'Period': self.config.period_in_hours * 60 * 60,
                    'Stat': 'Maximum',
                },
                'ReturnData': True,
            }
            for i, slo in enumerate(slo_summaries)
        ]

    def get_metric_data(
        self, queries: List[Dict[str, Any]], start_time: datetime, end_time: datetime
    ) -> List[MetricDataResult]:
        """Retrieves metric data from CloudWatch using the specified queries."""
        logger.debug(f'Fetching metric data with {len(queries)} queries')

        try:
            response = self.cloudwatch_client.get_metric_data(
                MetricDataQueries=queries,  # type: ignore
                StartTime=start_time,
                EndTime=end_time,
            )
            logger.debug(f'Retrieved {len(response.get("MetricDataResults", []))} metric results')
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', 'Unknown error')
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f'AWS ClientError getting metric data: {error_code} - {error_msg}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error getting metric data: {str(e)}', exc_info=True)
            raise

        return [
            MetricDataResult(
                timestamps=result.get('Timestamps', []), values=result.get('Values', [])
            )
            for result in response['MetricDataResults']
        ]

    def get_sli_status(self, num_breaching: int) -> str:
        """Determines overall SLI status based on number of breaching SLOs."""
        return 'CRITICAL' if num_breaching > 0 else 'OK'

    def generate_sli_report(self) -> SLIReport:
        """Generates a comprehensive SLI report.

        Collects SLO data, analyzes metrics, and produces a report containing
        the overall status and details about breaching/healthy SLOs.
        """
        logger.info(f'Generating SLI report for {self.config.service_name}')
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.config.period_in_hours)
        logger.debug(f'Report time range: {start_time} to {end_time}')

        slo_summaries = self.get_slo_summaries()

        # If no SLOs found, return empty report
        if not slo_summaries:
            logger.warning(f'No SLOs found for service {self.config.service_name}')
            return SLIReport(
                start_time=start_time,
                end_time=end_time,
                sli_status='OK',  # No SLOs means nothing can be breached
                total_slo_count=0,
                ok_slo_count=0,
                breached_slo_count=0,
                breached_slo_names=[],
            )

        metric_queries = self.create_metric_queries(slo_summaries)
        metric_results = self.get_metric_data(metric_queries, start_time, end_time)

        healthy_slos = []
        breaching_slos = []

        for i, result in enumerate(metric_results):
            # Check if we have any values and if the SLO is breached
            if result.values and len(result.values) > 0 and result.values[0] > 0:
                breaching_slos.append(slo_summaries[i].name)
            else:
                healthy_slos.append(slo_summaries[i].name)

        logger.debug(
            f'SLI report generated - Total SLOs: {len(slo_summaries)}, Breaching: {len(breaching_slos)}, Healthy: {len(healthy_slos)}'
        )
        return SLIReport(
            start_time=start_time,
            end_time=end_time,
            sli_status=self.get_sli_status(len(breaching_slos)),
            total_slo_count=len(slo_summaries),
            ok_slo_count=len(healthy_slos),
            breached_slo_count=len(breaching_slos),
            breached_slo_names=breaching_slos,
        )
