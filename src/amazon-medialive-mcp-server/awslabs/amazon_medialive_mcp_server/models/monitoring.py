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

"""Monitoring-related Pydantic models — CloudWatch alarms, EventBridge, signal maps, reservations."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    ChannelClass,
    CloudWatchAlarmTemplateComparisonOperator,
    CloudWatchAlarmTemplateStatistic,
    CloudWatchAlarmTemplateTargetResourceType,
    CloudWatchAlarmTemplateTreatMissingData,
    EventBridgeRuleTemplateEventType,
    NielsenPcmToId3TaggingState,
    NielsenWatermarksCbetStepaside,
    NielsenWatermarksDistributionTypes,
    NielsenWatermarkTimezones,
    OfferingDurationUnits,
    OfferingType,
    ReservationCodec,
    ReservationMaximumBitrate,
    ReservationMaximumFramerate,
    ReservationResolution,
    ReservationResourceType,
    ReservationSpecialFeature,
    ReservationState,
    ReservationVideoQuality,
    SignalMapMonitorDeploymentStatus,
    SignalMapStatus,
)
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.common import (
        AudioDescription,
        CaptionDescription,
        RenewalSettings,
    )
    from awslabs.amazon_medialive_mcp_server.models.encoding import (
        AvailBlanking,
        AvailConfiguration,
        BlackoutSlate,
        ColorCorrectionSettings,
        FeatureActivations,
        GlobalConfiguration,
        ThumbnailConfiguration,
        TimecodeConfig,
        VideoDescription,
    )
    from awslabs.amazon_medialive_mcp_server.models.output import OutputGroup
    from awslabs.amazon_medialive_mcp_server.models.schedule import MotionGraphicsConfiguration


class CloudWatchAlarmTemplateGroupSummary(BaseModel):
    """Placeholder documentation for CloudWatchAlarmTemplateGroupSummary."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='A cloudwatch alarm template group\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    id: Annotated[
        str,
        Field(
            ...,
            alias='Id',
            description='A cloudwatch alarm template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    modified_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ModifiedAt',
            description='',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='',
        ),
    ]

    template_count: Annotated[
        int,
        Field(
            ...,
            alias='TemplateCount',
            description='The number of templates in a group.',
        ),
    ]


class CloudWatchAlarmTemplateSummary(BaseModel):
    """Placeholder documentation for CloudWatchAlarmTemplateSummary."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='A cloudwatch alarm template\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    comparison_operator: Annotated[
        CloudWatchAlarmTemplateComparisonOperator,
        Field(
            ...,
            alias='ComparisonOperator',
            description='',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='',
        ),
    ]

    datapoints_to_alarm: Annotated[
        Optional[int],
        Field(
            None,
            alias='DatapointsToAlarm',
            description='The number of datapoints within the evaluation period that must be breaching to trigger the alarm.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    evaluation_periods: Annotated[
        int,
        Field(
            ...,
            alias='EvaluationPeriods',
            description='The number of periods over which data is compared to the specified threshold.',
        ),
    ]

    group_id: Annotated[
        str,
        Field(
            ...,
            alias='GroupId',
            description='A cloudwatch alarm template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    id: Annotated[
        str,
        Field(
            ...,
            alias='Id',
            description='A cloudwatch alarm template\u0027s id. AWS provided templates have ids that start with `aws-`',
        ),
    ]

    metric_name: Annotated[
        str,
        Field(
            ...,
            alias='MetricName',
            description='The name of the metric associated with the alarm. Must be compatible with targetResourceType.',
        ),
    ]

    modified_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ModifiedAt',
            description='',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    period: Annotated[
        int,
        Field(
            ...,
            alias='Period',
            description='The period, in seconds, over which the specified statistic is applied.',
        ),
    ]

    statistic: Annotated[
        CloudWatchAlarmTemplateStatistic,
        Field(
            ...,
            alias='Statistic',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='',
        ),
    ]

    target_resource_type: Annotated[
        CloudWatchAlarmTemplateTargetResourceType,
        Field(
            ...,
            alias='TargetResourceType',
            description='',
        ),
    ]

    threshold: Annotated[
        float,
        Field(
            ...,
            alias='Threshold',
            description='The threshold value to compare with the specified statistic.',
        ),
    ]

    treat_missing_data: Annotated[
        CloudWatchAlarmTemplateTreatMissingData,
        Field(
            ...,
            alias='TreatMissingData',
            description='',
        ),
    ]


class EventBridgeRuleTemplateGroupSummary(BaseModel):
    """Placeholder documentation for EventBridgeRuleTemplateGroupSummary."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='An eventbridge rule template group\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    id: Annotated[
        str,
        Field(
            ...,
            alias='Id',
            description='An eventbridge rule template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    modified_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ModifiedAt',
            description='',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='',
        ),
    ]

    template_count: Annotated[
        int,
        Field(
            ...,
            alias='TemplateCount',
            description='The number of templates in a group.',
        ),
    ]


class EventBridgeRuleTemplateSummary(BaseModel):
    """Placeholder documentation for EventBridgeRuleTemplateSummary."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='An eventbridge rule template\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    event_target_count: Annotated[
        int,
        Field(
            ...,
            alias='EventTargetCount',
            description='The number of targets configured to send matching events.',
        ),
    ]

    event_type: Annotated[
        EventBridgeRuleTemplateEventType,
        Field(
            ...,
            alias='EventType',
            description='',
        ),
    ]

    group_id: Annotated[
        str,
        Field(
            ...,
            alias='GroupId',
            description='An eventbridge rule template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    id: Annotated[
        str,
        Field(
            ...,
            alias='Id',
            description='An eventbridge rule template\u0027s id. AWS provided templates have ids that start with `aws-`',
        ),
    ]

    modified_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ModifiedAt',
            description='',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='',
        ),
    ]


class EventBridgeRuleTemplateTarget(BaseModel):
    """The target to which to send matching events."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='Target ARNs must be either an SNS topic or CloudWatch log group.',
        ),
    ]


class NielsenCBET(BaseModel):
    """Nielsen CBET."""

    model_config = ConfigDict(populate_by_name=True)

    cbet_check_digit_string: Annotated[
        str,
        Field(
            ...,
            alias='CbetCheckDigitString',
            description='Enter the CBET check digits to use in the watermark.',
        ),
    ]

    cbet_stepaside: Annotated[
        NielsenWatermarksCbetStepaside,
        Field(
            ...,
            alias='CbetStepaside',
            description='Determines the method of CBET insertion mode when prior encoding is detected on the same layer.',
        ),
    ]

    csid: Annotated[
        str,
        Field(
            ...,
            alias='Csid',
            description='Enter the CBET Source ID (CSID) to use in the watermark',
        ),
    ]


class NielsenConfiguration(BaseModel):
    """Nielsen Configuration."""

    model_config = ConfigDict(populate_by_name=True)

    distributor_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='DistributorId',
            description='Enter the Distributor ID assigned to your organization by Nielsen.',
        ),
    ]

    nielsen_pcm_to_id3_tagging: Annotated[
        Optional[NielsenPcmToId3TaggingState],
        Field(
            None,
            alias='NielsenPcmToId3Tagging',
            description='Enables Nielsen PCM to ID3 tagging',
        ),
    ]


class NielsenNaesIiNw(BaseModel):
    """Nielsen Naes Ii Nw."""

    model_config = ConfigDict(populate_by_name=True)

    check_digit_string: Annotated[
        str,
        Field(
            ...,
            alias='CheckDigitString',
            description='Enter the check digit string for the watermark',
        ),
    ]

    sid: Annotated[
        float,
        Field(
            ...,
            alias='Sid',
            description='Enter the Nielsen Source ID (SID) to include in the watermark',
        ),
    ]

    timezone: Annotated[
        Optional[NielsenWatermarkTimezones],
        Field(
            None,
            alias='Timezone',
            description='Choose the timezone for the time stamps in the watermark. If not provided, the timestamps will be in Coordinated Universal Time (UTC)',
        ),
    ]


class NielsenWatermarksSettings(BaseModel):
    """Nielsen Watermarks Settings."""

    model_config = ConfigDict(populate_by_name=True)

    nielsen_cbet_settings: Annotated[
        Optional[NielsenCBET],
        Field(
            None,
            alias='NielsenCbetSettings',
            description='Complete these fields only if you want to insert watermarks of type Nielsen CBET',
        ),
    ]

    nielsen_distribution_type: Annotated[
        Optional[NielsenWatermarksDistributionTypes],
        Field(
            None,
            alias='NielsenDistributionType',
            description='Choose the distribution types that you want to assign to the watermarks: - PROGRAM_CONTENT - FINAL_DISTRIBUTOR',
        ),
    ]

    nielsen_naes_ii_nw_settings: Annotated[
        Optional[NielsenNaesIiNw],
        Field(
            None,
            alias='NielsenNaesIiNwSettings',
            description='Complete these fields only if you want to insert watermarks of type Nielsen NAES II (N2) and Nielsen NAES VI (NW).',
        ),
    ]


class PurchaseOffering(BaseModel):
    """PurchaseOffering request."""

    model_config = ConfigDict(populate_by_name=True)

    count: Annotated[
        int,
        Field(
            ...,
            alias='Count',
            description='Number of resources',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name for the new reservation',
        ),
    ]

    renewal_settings: Annotated[
        Optional[RenewalSettings],
        Field(
            None,
            alias='RenewalSettings',
            description='Renewal settings for the reservation',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='Unique request ID to be specified. This is needed to prevent retries from creating multiple resources.',
        ),
    ]

    start: Annotated[
        Optional[str],
        Field(
            None,
            alias='Start',
            description='Requested reservation start time (UTC) in ISO-8601 format. The specified time must be between the first day of the current month and one year from now. If no value is given, the default is now.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs',
        ),
    ]


class PurchaseOfferingRequest(BaseModel):
    """Placeholder documentation for PurchaseOfferingRequest."""

    model_config = ConfigDict(populate_by_name=True)

    count: Annotated[
        int,
        Field(
            ...,
            alias='Count',
            description='Number of resources',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name for the new reservation',
        ),
    ]

    offering_id: Annotated[
        str,
        Field(
            ...,
            alias='OfferingId',
            description='Offering to purchase, e.g. \u002787654321\u0027',
        ),
    ]

    renewal_settings: Annotated[
        Optional[RenewalSettings],
        Field(
            None,
            alias='RenewalSettings',
            description='Renewal settings for the reservation',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='Unique request ID to be specified. This is needed to prevent retries from creating multiple resources.',
        ),
    ]

    start: Annotated[
        Optional[str],
        Field(
            None,
            alias='Start',
            description='Requested reservation start time (UTC) in ISO-8601 format. The specified time must be between the first day of the current month and one year from now. If no value is given, the default is now.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs',
        ),
    ]


class ReservationResourceSpecification(BaseModel):
    """Resource configuration (codec, resolution, bitrate, ...)."""

    model_config = ConfigDict(populate_by_name=True)

    channel_class: Annotated[
        Optional[ChannelClass],
        Field(
            None,
            alias='ChannelClass',
            description='Channel class, e.g. \u0027STANDARD\u0027',
        ),
    ]

    codec: Annotated[
        Optional[ReservationCodec],
        Field(
            None,
            alias='Codec',
            description='Codec, e.g. \u0027AVC\u0027',
        ),
    ]

    maximum_bitrate: Annotated[
        Optional[ReservationMaximumBitrate],
        Field(
            None,
            alias='MaximumBitrate',
            description='Maximum bitrate, e.g. \u0027MAX_20_MBPS\u0027',
        ),
    ]

    maximum_framerate: Annotated[
        Optional[ReservationMaximumFramerate],
        Field(
            None,
            alias='MaximumFramerate',
            description='Maximum framerate, e.g. \u0027MAX_30_FPS\u0027 (Outputs only)',
        ),
    ]

    resolution: Annotated[
        Optional[ReservationResolution],
        Field(
            None,
            alias='Resolution',
            description='Resolution, e.g. \u0027HD\u0027',
        ),
    ]

    resource_type: Annotated[
        Optional[ReservationResourceType],
        Field(
            None,
            alias='ResourceType',
            description='Resource type, \u0027INPUT\u0027, \u0027OUTPUT\u0027, \u0027MULTIPLEX\u0027, or \u0027CHANNEL\u0027',
        ),
    ]

    special_feature: Annotated[
        Optional[ReservationSpecialFeature],
        Field(
            None,
            alias='SpecialFeature',
            description='Special feature, e.g. \u0027AUDIO_NORMALIZATION\u0027 (Channels only)',
        ),
    ]

    video_quality: Annotated[
        Optional[ReservationVideoQuality],
        Field(
            None,
            alias='VideoQuality',
            description='Video quality, e.g. \u0027STANDARD\u0027 (Outputs only)',
        ),
    ]


class Offering(BaseModel):
    """Reserved resources available for purchase."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='Unique offering ARN, e.g. \u0027arn:aws:medialive:us-west-2:123456789012:offering:87654321\u0027',
        ),
    ]

    currency_code: Annotated[
        Optional[str],
        Field(
            None,
            alias='CurrencyCode',
            description='Currency code for usagePrice and fixedPrice in ISO-4217 format, e.g. \u0027USD\u0027',
        ),
    ]

    duration: Annotated[
        Optional[int],
        Field(
            None,
            alias='Duration',
            description='Lease duration, e.g. \u002712\u0027',
        ),
    ]

    duration_units: Annotated[
        Optional[OfferingDurationUnits],
        Field(
            None,
            alias='DurationUnits',
            description='Units for duration, e.g. \u0027MONTHS\u0027',
        ),
    ]

    fixed_price: Annotated[
        Optional[float],
        Field(
            None,
            alias='FixedPrice',
            description='One-time charge for each reserved resource, e.g. \u00270.0\u0027 for a NO_UPFRONT offering',
        ),
    ]

    offering_description: Annotated[
        Optional[str],
        Field(
            None,
            alias='OfferingDescription',
            description='Offering description, e.g. \u0027HD AVC output at 10-20 Mbps, 30 fps, and standard VQ in US West (Oregon)\u0027',
        ),
    ]

    offering_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='OfferingId',
            description='Unique offering ID, e.g. \u002787654321\u0027',
        ),
    ]

    offering_type: Annotated[
        Optional[OfferingType],
        Field(
            None,
            alias='OfferingType',
            description='Offering type, e.g. \u0027NO_UPFRONT\u0027',
        ),
    ]

    region: Annotated[
        Optional[str],
        Field(
            None,
            alias='Region',
            description='AWS region, e.g. \u0027us-west-2\u0027',
        ),
    ]

    resource_specification: Annotated[
        Optional[ReservationResourceSpecification],
        Field(
            None,
            alias='ResourceSpecification',
            description='Resource configuration details',
        ),
    ]

    usage_price: Annotated[
        Optional[float],
        Field(
            None,
            alias='UsagePrice',
            description='Recurring usage charge for each reserved resource, e.g. \u0027157.0\u0027',
        ),
    ]


class Reservation(BaseModel):
    """Reserved resources available to use."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='Unique reservation ARN, e.g. \u0027arn:aws:medialive:us-west-2:123456789012:reservation:1234567\u0027',
        ),
    ]

    count: Annotated[
        Optional[int],
        Field(
            None,
            alias='Count',
            description='Number of reserved resources',
        ),
    ]

    currency_code: Annotated[
        Optional[str],
        Field(
            None,
            alias='CurrencyCode',
            description='Currency code for usagePrice and fixedPrice in ISO-4217 format, e.g. \u0027USD\u0027',
        ),
    ]

    duration: Annotated[
        Optional[int],
        Field(
            None,
            alias='Duration',
            description='Lease duration, e.g. \u002712\u0027',
        ),
    ]

    duration_units: Annotated[
        Optional[OfferingDurationUnits],
        Field(
            None,
            alias='DurationUnits',
            description='Units for duration, e.g. \u0027MONTHS\u0027',
        ),
    ]

    end: Annotated[
        Optional[str],
        Field(
            None,
            alias='End',
            description='Reservation UTC end date and time in ISO-8601 format, e.g. \u00272019-03-01T00:00:00\u0027',
        ),
    ]

    fixed_price: Annotated[
        Optional[float],
        Field(
            None,
            alias='FixedPrice',
            description='One-time charge for each reserved resource, e.g. \u00270.0\u0027 for a NO_UPFRONT offering',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='User specified reservation name',
        ),
    ]

    offering_description: Annotated[
        Optional[str],
        Field(
            None,
            alias='OfferingDescription',
            description='Offering description, e.g. \u0027HD AVC output at 10-20 Mbps, 30 fps, and standard VQ in US West (Oregon)\u0027',
        ),
    ]

    offering_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='OfferingId',
            description='Unique offering ID, e.g. \u002787654321\u0027',
        ),
    ]

    offering_type: Annotated[
        Optional[OfferingType],
        Field(
            None,
            alias='OfferingType',
            description='Offering type, e.g. \u0027NO_UPFRONT\u0027',
        ),
    ]

    region: Annotated[
        Optional[str],
        Field(
            None,
            alias='Region',
            description='AWS region, e.g. \u0027us-west-2\u0027',
        ),
    ]

    renewal_settings: Annotated[
        Optional[RenewalSettings],
        Field(
            None,
            alias='RenewalSettings',
            description='Renewal settings for the reservation',
        ),
    ]

    reservation_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ReservationId',
            description='Unique reservation ID, e.g. \u00271234567\u0027',
        ),
    ]

    resource_specification: Annotated[
        Optional[ReservationResourceSpecification],
        Field(
            None,
            alias='ResourceSpecification',
            description='Resource configuration details',
        ),
    ]

    start: Annotated[
        Optional[str],
        Field(
            None,
            alias='Start',
            description='Reservation UTC start date and time in ISO-8601 format, e.g. \u00272018-03-01T00:00:00\u0027',
        ),
    ]

    state: Annotated[
        Optional[ReservationState],
        Field(
            None,
            alias='State',
            description='Current state of reservation, e.g. \u0027ACTIVE\u0027',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs',
        ),
    ]

    usage_price: Annotated[
        Optional[float],
        Field(
            None,
            alias='UsagePrice',
            description='Recurring usage charge for each reserved resource, e.g. \u0027157.0\u0027',
        ),
    ]


class PurchaseOfferingResponse(BaseModel):
    """Placeholder documentation for PurchaseOfferingResponse."""

    model_config = ConfigDict(populate_by_name=True)

    reservation: Annotated[
        Optional[Reservation],
        Field(
            None,
            alias='Reservation',
            description='',
        ),
    ]


class PurchaseOfferingResultModel(BaseModel):
    """PurchaseOffering response."""

    model_config = ConfigDict(populate_by_name=True)

    reservation: Annotated[
        Optional[Reservation],
        Field(
            None,
            alias='Reservation',
            description='',
        ),
    ]


class SignalMapSummary(BaseModel):
    """Placeholder documentation for SignalMapSummary."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    id: Annotated[
        str,
        Field(
            ...,
            alias='Id',
            description='A signal map\u0027s id.',
        ),
    ]

    modified_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ModifiedAt',
            description='',
        ),
    ]

    monitor_deployment_status: Annotated[
        SignalMapMonitorDeploymentStatus,
        Field(
            ...,
            alias='MonitorDeploymentStatus',
            description='',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    status: Annotated[
        SignalMapStatus,
        Field(
            ...,
            alias='Status',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='',
        ),
    ]


class EncoderSettings(BaseModel):
    """Encoder Settings."""

    model_config = ConfigDict(populate_by_name=True)

    audio_descriptions: Annotated[
        list[AudioDescription],
        Field(
            ...,
            alias='AudioDescriptions',
            description='',
        ),
    ]

    avail_blanking: Annotated[
        Optional[AvailBlanking],
        Field(
            None,
            alias='AvailBlanking',
            description='Settings for ad avail blanking.',
        ),
    ]

    avail_configuration: Annotated[
        Optional[AvailConfiguration],
        Field(
            None,
            alias='AvailConfiguration',
            description='Event-wide configuration settings for ad avail insertion.',
        ),
    ]

    blackout_slate: Annotated[
        Optional[BlackoutSlate],
        Field(
            None,
            alias='BlackoutSlate',
            description='Settings for blackout slate.',
        ),
    ]

    caption_descriptions: Annotated[
        Optional[list[CaptionDescription]],
        Field(
            None,
            alias='CaptionDescriptions',
            description='Settings for caption decriptions',
        ),
    ]

    feature_activations: Annotated[
        Optional[FeatureActivations],
        Field(
            None,
            alias='FeatureActivations',
            description='Feature Activations',
        ),
    ]

    global_configuration: Annotated[
        Optional[GlobalConfiguration],
        Field(
            None,
            alias='GlobalConfiguration',
            description='Configuration settings that apply to the event as a whole.',
        ),
    ]

    motion_graphics_configuration: Annotated[
        Optional[MotionGraphicsConfiguration],
        Field(
            None,
            alias='MotionGraphicsConfiguration',
            description='Settings for motion graphics.',
        ),
    ]

    nielsen_configuration: Annotated[
        Optional[NielsenConfiguration],
        Field(
            None,
            alias='NielsenConfiguration',
            description='Nielsen configuration settings.',
        ),
    ]

    output_groups: Annotated[
        list[OutputGroup],
        Field(
            ...,
            alias='OutputGroups',
            description='',
        ),
    ]

    timecode_config: Annotated[
        TimecodeConfig,
        Field(
            ...,
            alias='TimecodeConfig',
            description='Contains settings used to acquire and adjust timecode information from inputs.',
        ),
    ]

    video_descriptions: Annotated[
        list[VideoDescription],
        Field(
            ...,
            alias='VideoDescriptions',
            description='',
        ),
    ]

    thumbnail_configuration: Annotated[
        Optional[ThumbnailConfiguration],
        Field(
            None,
            alias='ThumbnailConfiguration',
            description='Thumbnail configuration settings.',
        ),
    ]

    color_correction_settings: Annotated[
        Optional[ColorCorrectionSettings],
        Field(
            None,
            alias='ColorCorrectionSettings',
            description='Color Correction Settings',
        ),
    ]
