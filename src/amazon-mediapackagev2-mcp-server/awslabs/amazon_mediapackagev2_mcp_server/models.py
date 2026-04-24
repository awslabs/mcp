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


"""Auto-generated Pydantic models from botocore service model.

DO NOT EDIT — regenerate with: python src/codegen/generate.py mediapackagev2
Generated from: mediapackagev2 2022-12-25
Botocore version: 1.40.49
"""

from __future__ import annotations

from awslabs.amazon_mediapackagev2_mcp_server.enums import (
    AdMarkerDash,
    AdMarkerHls,
    CmafEncryptionMethod,
    ConflictExceptionType,
    ContainerType,
    DashCompactness,
    DashDrmSignaling,
    DashPeriodTrigger,
    DashProfile,
    DashSegmentTemplateFormat,
    DashTtmlProfile,
    DashUtcTimingMode,
    DrmSystem,
    EndpointErrorCondition,
    HarvestJobStatus,
    InputType,
    IsmEncryptionMethod,
    MssManifestLayout,
    PresetSpeke20Audio,
    PresetSpeke20Video,
    ResourceTypeNotFound,
    ScteFilter,
    TsEncryptionMethod,
    ValidationExceptionType,
)
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Optional


class AccessDeniedException(BaseModel):
    """Access is denied because either you don't have permissions to perform the requested operation or MediaPackage is getting throttling errors with CDN authorization. The user or role that is making the request must have at least one IAM permissions policy attached that grants the required permissions."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class CancelHarvestJobRequest(BaseModel):
    """Cancel Harvest Job Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group containing the channel from which the harvest job is running.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel from which the harvest job is running.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name of the origin endpoint that the harvest job is harvesting from. This cannot be changed after the harvest job is submitted.',
        ),
    ]

    harvest_job_name: Annotated[
        str,
        Field(
            ...,
            alias='HarvestJobName',
            description='The name of the harvest job to cancel. This name must be unique within the channel and cannot be changed after the harvest job is submitted.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with the harvest job. Used for concurrency control.',
        ),
    ]


class CancelHarvestJobResponse(BaseModel):
    """Cancel Harvest Job Response."""

    model_config = ConfigDict(populate_by_name=True)


class CdnAuthConfiguration(BaseModel):
    """The settings to enable CDN authorization headers in MediaPackage."""

    model_config = ConfigDict(populate_by_name=True)

    cdn_identifier_secret_arns: Annotated[
        list[str],
        Field(
            ...,
            alias='CdnIdentifierSecretArns',
            description='The ARN for the secret in Secrets Manager that your CDN uses for authorization to access the endpoint.',
        ),
    ]

    secrets_role_arn: Annotated[
        str,
        Field(
            ...,
            alias='SecretsRoleArn',
            description='The ARN for the IAM role that gives MediaPackage read access to Secrets Manager and KMS for CDN authorization.',
        ),
    ]


class ChannelGroupListConfiguration(BaseModel):
    """The configuration of the channel group."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the channel group was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the channel group was modified.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Any descriptive information that you want to add to the channel group for future identification purposes.',
        ),
    ]


class ChannelListConfiguration(BaseModel):
    """The configuration of the channel."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the channel was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the channel was modified.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Any descriptive information that you want to add to the channel for future identification purposes.',
        ),
    ]

    input_type: Annotated[
        Optional[InputType],
        Field(
            None,
            alias='InputType',
            description='The input type will be an immutable field which will be used to define whether the channel will allow CMAF ingest or HLS ingest. If unprovided, it will default to HLS to preserve current behavior. The allowed values are: HLS - The HLS streaming specification (which defines M3U8 manifests and TS segments). CMAF - The DASH-IF CMAF Ingest specification (which defines CMAF segments with optional DASH manifests).',
        ),
    ]


class ConflictException(BaseModel):
    """Updating or deleting this resource can cause an inconsistent state."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]

    conflict_exception_type: Annotated[
        Optional[ConflictExceptionType],
        Field(
            None,
            alias='ConflictExceptionType',
            description='The type of ConflictException.',
        ),
    ]


class CreateChannelGroupRequest(BaseModel):
    """Create Channel Group Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region. You can\u0027t use spaces in the name. You can\u0027t change the name after you create the channel group.',
        ),
    ]

    client_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClientToken',
            description='A unique, case-sensitive token that you provide to ensure the idempotency of the request.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Enter any descriptive text that helps you to identify the channel group.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A comma-separated list of tag key:value pairs that you define. For example: "Key1": "Value1", "Key2": "Value2"',
        ),
    ]


class CreateChannelGroupResponse(BaseModel):
    """Create Channel Group Response."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    egress_domain: Annotated[
        str,
        Field(
            ...,
            alias='EgressDomain',
            description='The output domain where the source stream should be sent. Integrate the egress domain with a downstream CDN (such as Amazon CloudFront) or playback device.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the channel group was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the channel group was modified.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description for your channel group.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the channel group.',
        ),
    ]


class DashBaseUrl(BaseModel):
    """The base URLs to use for retrieving segments. You can specify multiple locations and indicate the priority and weight for when each should be used, for use in mutli-CDN workflows."""

    model_config = ConfigDict(populate_by_name=True)

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='A source location for segments.',
        ),
    ]

    service_location: Annotated[
        Optional[str],
        Field(
            None,
            alias='ServiceLocation',
            description='The name of the source location.',
        ),
    ]

    dvb_priority: Annotated[
        Optional[int],
        Field(
            None,
            alias='DvbPriority',
            description='For use with DVB-DASH profiles only. The priority of this location for servings segments. The lower the number, the higher the priority.',
        ),
    ]

    dvb_weight: Annotated[
        Optional[int],
        Field(
            None,
            alias='DvbWeight',
            description='For use with DVB-DASH profiles only. The weighting for source locations that have the same priority.',
        ),
    ]


class DashDvbFontDownload(BaseModel):
    """For use with DVB-DASH profiles only. The settings for font downloads that you want Elemental MediaPackage to pass through to the manifest."""

    model_config = ConfigDict(populate_by_name=True)

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='The URL for downloading fonts for subtitles.',
        ),
    ]

    mime_type: Annotated[
        Optional[str],
        Field(
            None,
            alias='MimeType',
            description='The mimeType of the resource that\u0027s at the font download URL. For information about font MIME types, see the MPEG-DASH Profile for Transport of ISO BMFF Based DVB Services over IP Based Networks document.',
        ),
    ]

    font_family: Annotated[
        Optional[str],
        Field(
            None,
            alias='FontFamily',
            description='The fontFamily name for subtitles, as described in EBU-TT-D Subtitling Distribution Format.',
        ),
    ]


class DashDvbMetricsReporting(BaseModel):
    """For use with DVB-DASH profiles only. The settings for error reporting from the playback device that you want Elemental MediaPackage to pass through to the manifest."""

    model_config = ConfigDict(populate_by_name=True)

    reporting_url: Annotated[
        str,
        Field(
            ...,
            alias='ReportingUrl',
            description='The URL where playback devices send error reports.',
        ),
    ]

    probability: Annotated[
        Optional[int],
        Field(
            None,
            alias='Probability',
            description='The number of playback devices per 1000 that will send error reports to the reporting URL. This represents the probability that a playback device will be a reporting player for this session.',
        ),
    ]


class DashDvbSettings(BaseModel):
    """For endpoints that use the DVB-DASH profile only. The font download and error reporting information that you want MediaPackage to pass through to the manifest."""

    model_config = ConfigDict(populate_by_name=True)

    font_download: Annotated[
        Optional[DashDvbFontDownload],
        Field(
            None,
            alias='FontDownload',
            description='Subtitle font settings.',
        ),
    ]

    error_metrics: Annotated[
        Optional[list[DashDvbMetricsReporting]],
        Field(
            None,
            alias='ErrorMetrics',
            description='Playback device error reporting settings.',
        ),
    ]


class DashProgramInformation(BaseModel):
    """Details about the content that you want MediaPackage to pass through in the manifest to the playback device."""

    model_config = ConfigDict(populate_by_name=True)

    title: Annotated[
        Optional[str],
        Field(
            None,
            alias='Title',
            description='The title for the manifest.',
        ),
    ]

    source: Annotated[
        Optional[str],
        Field(
            None,
            alias='Source',
            description='Information about the content provider.',
        ),
    ]

    copyright: Annotated[
        Optional[str],
        Field(
            None,
            alias='Copyright',
            description='A copyright statement about the content.',
        ),
    ]

    language_code: Annotated[
        Optional[str],
        Field(
            None,
            alias='LanguageCode',
            description='The language code for this manifest.',
        ),
    ]

    more_information_url: Annotated[
        Optional[str],
        Field(
            None,
            alias='MoreInformationUrl',
            description='An absolute URL that contains more information about this content.',
        ),
    ]


class DashTtmlConfiguration(BaseModel):
    """The settings for TTML subtitles."""

    model_config = ConfigDict(populate_by_name=True)

    ttml_profile: Annotated[
        DashTtmlProfile,
        Field(
            ...,
            alias='TtmlProfile',
            description='The profile that MediaPackage uses when signaling subtitles in the manifest. IMSC is the default profile. EBU-TT-D produces subtitles that are compliant with the EBU-TT-D TTML profile. MediaPackage passes through subtitle styles to the manifest. For more information about EBU-TT-D subtitles, see EBU-TT-D Subtitling Distribution Format.',
        ),
    ]


class DashSubtitleConfiguration(BaseModel):
    """The configuration for DASH subtitles."""

    model_config = ConfigDict(populate_by_name=True)

    ttml_configuration: Annotated[
        Optional[DashTtmlConfiguration],
        Field(
            None,
            alias='TtmlConfiguration',
            description='Settings for TTML subtitles.',
        ),
    ]


class DashUtcTiming(BaseModel):
    """Determines the type of UTC timing included in the DASH Media Presentation Description (MPD)."""

    model_config = ConfigDict(populate_by_name=True)

    timing_mode: Annotated[
        Optional[DashUtcTimingMode],
        Field(
            None,
            alias='TimingMode',
            description='The UTC timing mode.',
        ),
    ]

    timing_source: Annotated[
        Optional[str],
        Field(
            None,
            alias='TimingSource',
            description='The the method that the player uses to synchronize to coordinated universal time (UTC) wall clock time.',
        ),
    ]


class DeleteChannelGroupRequest(BaseModel):
    """Delete Channel Group Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]


class DeleteChannelGroupResponse(BaseModel):
    """Delete Channel Group Response."""

    model_config = ConfigDict(populate_by_name=True)


class DeleteChannelPolicyRequest(BaseModel):
    """Delete Channel Policy Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]


class DeleteChannelPolicyResponse(BaseModel):
    """Delete Channel Policy Response."""

    model_config = ConfigDict(populate_by_name=True)


class DeleteChannelRequest(BaseModel):
    """Delete Channel Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]


class DeleteChannelResponse(BaseModel):
    """Delete Channel Response."""

    model_config = ConfigDict(populate_by_name=True)


class DeleteOriginEndpointPolicyRequest(BaseModel):
    """Delete Origin Endpoint Policy Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]


class DeleteOriginEndpointPolicyResponse(BaseModel):
    """Delete Origin Endpoint Policy Response."""

    model_config = ConfigDict(populate_by_name=True)


class DeleteOriginEndpointRequest(BaseModel):
    """Delete Origin Endpoint Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]


class DeleteOriginEndpointResponse(BaseModel):
    """Delete Origin Endpoint Response."""

    model_config = ConfigDict(populate_by_name=True)


class EncryptionContractConfiguration(BaseModel):
    """Configure one or more content encryption keys for your endpoints that use SPEKE Version 2.0. The encryption contract defines which content keys are used to encrypt the audio and video tracks in your stream. To configure the encryption contract, specify which audio and video encryption presets to use."""

    model_config = ConfigDict(populate_by_name=True)

    preset_speke20_audio: Annotated[
        PresetSpeke20Audio,
        Field(
            ...,
            alias='PresetSpeke20Audio',
            description='A collection of audio encryption presets. Value description: PRESET-AUDIO-1 - Use one content key to encrypt all of the audio tracks in your stream. PRESET-AUDIO-2 - Use one content key to encrypt all of the stereo audio tracks and one content key to encrypt all of the multichannel audio tracks. PRESET-AUDIO-3 - Use one content key to encrypt all of the stereo audio tracks, one content key to encrypt all of the multichannel audio tracks with 3 to 6 channels, and one content key to encrypt all of the multichannel audio tracks with more than 6 channels. SHARED - Use the same content key for all of the audio and video tracks in your stream. UNENCRYPTED - Don\u0027t encrypt any of the audio tracks in your stream.',
        ),
    ]

    preset_speke20_video: Annotated[
        PresetSpeke20Video,
        Field(
            ...,
            alias='PresetSpeke20Video',
            description='A collection of video encryption presets. Value description: PRESET-VIDEO-1 - Use one content key to encrypt all of the video tracks in your stream. PRESET-VIDEO-2 - Use one content key to encrypt all of the SD video tracks and one content key for all HD and higher resolutions video tracks. PRESET-VIDEO-3 - Use one content key to encrypt all of the SD video tracks, one content key for HD video tracks and one content key for all UHD video tracks. PRESET-VIDEO-4 - Use one content key to encrypt all of the SD video tracks, one content key for HD video tracks, one content key for all UHD1 video tracks and one content key for all UHD2 video tracks. PRESET-VIDEO-5 - Use one content key to encrypt all of the SD video tracks, one content key for HD1 video tracks, one content key for HD2 video tracks, one content key for all UHD1 video tracks and one content key for all UHD2 video tracks. PRESET-VIDEO-6 - Use one content key to encrypt all of the SD video tracks, one content key for HD1 video tracks, one content key for HD2 video tracks and one content key for all UHD video tracks. PRESET-VIDEO-7 - Use one content key to encrypt all of the SD+HD1 video tracks, one content key for HD2 video tracks and one content key for all UHD video tracks. PRESET-VIDEO-8 - Use one content key to encrypt all of the SD+HD1 video tracks, one content key for HD2 video tracks, one content key for all UHD1 video tracks and one content key for all UHD2 video tracks. SHARED - Use the same content key for all of the video and audio tracks in your stream. UNENCRYPTED - Don\u0027t encrypt any of the video tracks in your stream.',
        ),
    ]


class EncryptionMethod(BaseModel):
    """The encryption type."""

    model_config = ConfigDict(populate_by_name=True)

    ts_encryption_method: Annotated[
        Optional[TsEncryptionMethod],
        Field(
            None,
            alias='TsEncryptionMethod',
            description='The encryption method to use.',
        ),
    ]

    cmaf_encryption_method: Annotated[
        Optional[CmafEncryptionMethod],
        Field(
            None,
            alias='CmafEncryptionMethod',
            description='The encryption method to use.',
        ),
    ]

    ism_encryption_method: Annotated[
        Optional[IsmEncryptionMethod],
        Field(
            None,
            alias='IsmEncryptionMethod',
            description='The encryption method used for Microsoft Smooth Streaming (MSS) content. This specifies how the MSS segments are encrypted to protect the content during delivery to client players.',
        ),
    ]


class FilterConfiguration(BaseModel):
    """Filter configuration includes settings for manifest filtering, start and end times, and time delay that apply to all of your egress requests for this manifest."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_filter: Annotated[
        Optional[str],
        Field(
            None,
            alias='ManifestFilter',
            description='Optionally specify one or more manifest filters for all of your manifest egress requests. When you include a manifest filter, note that you cannot use an identical manifest filter query parameter for this manifest\u0027s endpoint URL.',
        ),
    ]

    start: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='Start',
            description='Optionally specify the start time for all of your manifest egress requests. When you include start time, note that you cannot use start time query parameters for this manifest\u0027s endpoint URL.',
        ),
    ]

    end: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='End',
            description='Optionally specify the end time for all of your manifest egress requests. When you include end time, note that you cannot use end time query parameters for this manifest\u0027s endpoint URL.',
        ),
    ]

    time_delay_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='TimeDelaySeconds',
            description='Optionally specify the time delay for all of your manifest egress requests. Enter a value that is smaller than your endpoint\u0027s startover window. When you include time delay, note that you cannot use time delay query parameters for this manifest\u0027s endpoint URL.',
        ),
    ]

    clip_start_time: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ClipStartTime',
            description='Optionally specify the clip start time for all of your manifest egress requests. When you include clip start time, note that you cannot use clip start time query parameters for this manifest\u0027s endpoint URL.',
        ),
    ]


class CreateMssManifestConfiguration(BaseModel):
    """Configuration parameters for creating a Microsoft Smooth Streaming (MSS) manifest. MSS is a streaming media format developed by Microsoft that delivers adaptive bitrate streaming content to compatible players and devices."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short string that\u0027s appended to the endpoint URL to create a unique path to this MSS manifest. The manifest name must be unique within the origin endpoint and can contain letters, numbers, hyphens, and underscores.',
        ),
    ]

    manifest_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ManifestWindowSeconds',
            description='The total duration (in seconds) of the manifest window. This determines how much content is available in the manifest at any given time. The manifest window slides forward as new segments become available, maintaining a consistent duration of content. The minimum value is 30 seconds.',
        ),
    ]

    filter_configuration: Annotated[
        Optional[FilterConfiguration],
        Field(
            None,
            alias='FilterConfiguration',
            description='',
        ),
    ]

    manifest_layout: Annotated[
        Optional[MssManifestLayout],
        Field(
            None,
            alias='ManifestLayout',
            description='Determines the layout format of the MSS manifest. This controls how the manifest is structured and presented to client players, affecting compatibility with different MSS-compatible devices and applications.',
        ),
    ]


class ForceEndpointErrorConfiguration(BaseModel):
    """The failover settings for the endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    endpoint_error_conditions: Annotated[
        Optional[list[EndpointErrorCondition]],
        Field(
            None,
            alias='EndpointErrorConditions',
            description='The failover conditions for the endpoint. The options are: STALE_MANIFEST - The manifest stalled and there are no new segments or parts. INCOMPLETE_MANIFEST - There is a gap in the manifest. MISSING_DRM_KEY - Key rotation is enabled but we\u0027re unable to fetch the key for the current key period. SLATE_INPUT - The segments which contain slate content are considered to be missing content.',
        ),
    ]


class GetChannelGroupRequest(BaseModel):
    """Get Channel Group Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]


class GetChannelGroupResponse(BaseModel):
    """Get Channel Group Response."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    egress_domain: Annotated[
        str,
        Field(
            ...,
            alias='EgressDomain',
            description='The output domain where the source stream should be sent. Integrate the domain with a downstream CDN (such as Amazon CloudFront) or playback device.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the channel group was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the channel group was modified.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description for your channel group.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the channel group.',
        ),
    ]


class GetChannelPolicyRequest(BaseModel):
    """Get Channel Policy Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]


class GetChannelPolicyResponse(BaseModel):
    """Get Channel Policy Response."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    policy: Annotated[
        str,
        Field(
            ...,
            alias='Policy',
            description='The policy assigned to the channel.',
        ),
    ]


class GetChannelRequest(BaseModel):
    """Get Channel Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]


class GetHarvestJobRequest(BaseModel):
    """The request object for retrieving a specific harvest job."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group containing the channel associated with the harvest job.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel associated with the harvest job.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name of the origin endpoint associated with the harvest job.',
        ),
    ]

    harvest_job_name: Annotated[
        str,
        Field(
            ...,
            alias='HarvestJobName',
            description='The name of the harvest job to retrieve.',
        ),
    ]


class GetMssManifestConfiguration(BaseModel):
    """Configuration details for a Microsoft Smooth Streaming (MSS) manifest associated with an origin endpoint. This includes all the settings and properties that define how the MSS content is packaged and delivered."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='The name of the MSS manifest. This name is appended to the origin endpoint URL to create the unique path for accessing this specific MSS manifest.',
        ),
    ]

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='The complete URL for accessing the MSS manifest. Client players use this URL to retrieve the manifest and begin streaming the Microsoft Smooth Streaming content.',
        ),
    ]

    filter_configuration: Annotated[
        Optional[FilterConfiguration],
        Field(
            None,
            alias='FilterConfiguration',
            description='',
        ),
    ]

    manifest_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ManifestWindowSeconds',
            description='The duration (in seconds) of the manifest window. This represents the total amount of content available in the manifest at any given time.',
        ),
    ]

    manifest_layout: Annotated[
        Optional[MssManifestLayout],
        Field(
            None,
            alias='ManifestLayout',
            description='The layout format of the MSS manifest, which determines how the manifest is structured for client compatibility.',
        ),
    ]


class GetOriginEndpointPolicyRequest(BaseModel):
    """Get Origin Endpoint Policy Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]


class GetOriginEndpointPolicyResponse(BaseModel):
    """Get Origin Endpoint Policy Response."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]

    policy: Annotated[
        str,
        Field(
            ...,
            alias='Policy',
            description='The policy assigned to the origin endpoint.',
        ),
    ]

    cdn_auth_configuration: Annotated[
        Optional[CdnAuthConfiguration],
        Field(
            None,
            alias='CdnAuthConfiguration',
            description='The settings for using authorization headers between the MediaPackage endpoint and your CDN. For information about CDN authorization, see CDN authorization in Elemental MediaPackage in the MediaPackage user guide.',
        ),
    ]


class GetOriginEndpointRequest(BaseModel):
    """Get Origin Endpoint Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]


class HarvestedDashManifest(BaseModel):
    """Information about a harvested DASH manifest."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='The name of the harvested DASH manifest.',
        ),
    ]


class HarvestedHlsManifest(BaseModel):
    """Information about a harvested HLS manifest."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='The name of the harvested HLS manifest.',
        ),
    ]


class HarvestedLowLatencyHlsManifest(BaseModel):
    """Information about a harvested Low-Latency HLS manifest."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='The name of the harvested Low-Latency HLS manifest.',
        ),
    ]


class HarvestedManifests(BaseModel):
    """A collection of harvested manifests of different types."""

    model_config = ConfigDict(populate_by_name=True)

    hls_manifests: Annotated[
        Optional[list[HarvestedHlsManifest]],
        Field(
            None,
            alias='HlsManifests',
            description='A list of harvested HLS manifests.',
        ),
    ]

    dash_manifests: Annotated[
        Optional[list[HarvestedDashManifest]],
        Field(
            None,
            alias='DashManifests',
            description='A list of harvested DASH manifests.',
        ),
    ]

    low_latency_hls_manifests: Annotated[
        Optional[list[HarvestedLowLatencyHlsManifest]],
        Field(
            None,
            alias='LowLatencyHlsManifests',
            description='A list of harvested Low-Latency HLS manifests.',
        ),
    ]


class HarvesterScheduleConfiguration(BaseModel):
    """Defines the schedule configuration for a harvest job."""

    model_config = ConfigDict(populate_by_name=True)

    start_time: Annotated[
        datetime,
        Field(
            ...,
            alias='StartTime',
            description='The start time for the harvest job.',
        ),
    ]

    end_time: Annotated[
        datetime,
        Field(
            ...,
            alias='EndTime',
            description='The end time for the harvest job.',
        ),
    ]


class IngestEndpoint(BaseModel):
    """The ingest domain URL where the source stream should be sent."""

    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The system-generated unique identifier for the IngestEndpoint.',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='The ingest domain URL where the source stream should be sent.',
        ),
    ]


class InputSwitchConfiguration(BaseModel):
    """The configuration for input switching based on the media quality confidence score (MQCS) as provided from AWS Elemental MediaLive."""

    model_config = ConfigDict(populate_by_name=True)

    mqcs_input_switching: Annotated[
        Optional[bool],
        Field(
            None,
            alias='MQCSInputSwitching',
            description='When true, AWS Elemental MediaPackage performs input switching based on the MQCS. Default is true. This setting is valid only when InputType is CMAF.',
        ),
    ]

    preferred_input: Annotated[
        Optional[int],
        Field(
            None,
            alias='PreferredInput',
            description='For CMAF inputs, indicates which input MediaPackage should prefer when both inputs have equal MQCS scores. Select 1 to prefer the first ingest endpoint, or 2 to prefer the second ingest endpoint. If you don\u0027t specify a preferred input, MediaPackage uses its default switching behavior when MQCS scores are equal.',
        ),
    ]


class InternalServerException(BaseModel):
    """Indicates that an error from the service occurred while trying to process a request."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class ListChannelGroupsRequest(BaseModel):
    """List Channel Groups Request."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of results to return in the response.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The pagination token from the GET list request. Use the token to fetch the next page of results.',
        ),
    ]


class ListChannelGroupsResponse(BaseModel):
    """List Channel Groups Response."""

    model_config = ConfigDict(populate_by_name=True)

    items: Annotated[
        Optional[list[ChannelGroupListConfiguration]],
        Field(
            None,
            alias='Items',
            description='The objects being returned.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The pagination token from the GET list request. Use the token to fetch the next page of results.',
        ),
    ]


class ListChannelsRequest(BaseModel):
    """List Channels Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of results to return in the response.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The pagination token from the GET list request. Use the token to fetch the next page of results.',
        ),
    ]


class ListChannelsResponse(BaseModel):
    """List Channels Response."""

    model_config = ConfigDict(populate_by_name=True)

    items: Annotated[
        Optional[list[ChannelListConfiguration]],
        Field(
            None,
            alias='Items',
            description='The objects being returned.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The pagination token from the GET list request.',
        ),
    ]


class ListDashManifestConfiguration(BaseModel):
    """List the DASH manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index.',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='The egress domain URL for stream delivery from MediaPackage.',
        ),
    ]


class ListHarvestJobsRequest(BaseModel):
    """The request object for listing harvest jobs."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group to filter the harvest jobs by. If specified, only harvest jobs associated with channels in this group will be returned.',
        ),
    ]

    channel_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelName',
            description='The name of the channel to filter the harvest jobs by. If specified, only harvest jobs associated with this channel will be returned.',
        ),
    ]

    origin_endpoint_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='OriginEndpointName',
            description='The name of the origin endpoint to filter the harvest jobs by. If specified, only harvest jobs associated with this origin endpoint will be returned.',
        ),
    ]

    status: Annotated[
        Optional[HarvestJobStatus],
        Field(
            None,
            alias='Status',
            description='The status to filter the harvest jobs by. If specified, only harvest jobs with this status will be returned.',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of harvest jobs to return in a single request. If not specified, a default value will be used.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used for pagination. Provide this value in subsequent requests to retrieve the next set of results.',
        ),
    ]


class ListHlsManifestConfiguration(BaseModel):
    """List the HTTP live streaming (HLS) manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short short string that\u0027s appended to the endpoint URL. The manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index. MediaPackage automatically inserts the format extension, such as .m3u8. You can\u0027t use the same manifest name if you use HLS manifest and low-latency HLS manifest. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    child_manifest_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChildManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The child manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default child manifest name, index_1. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='The egress domain URL for stream delivery from MediaPackage.',
        ),
    ]


class ListLowLatencyHlsManifestConfiguration(BaseModel):
    """List the low-latency HTTP live streaming (HLS) manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short short string that\u0027s appended to the endpoint URL. The manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index. MediaPackage automatically inserts the format extension, such as .m3u8. You can\u0027t use the same manifest name if you use HLS manifest and low-latency HLS manifest. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    child_manifest_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChildManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The child manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default child manifest name, index_1. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='The egress domain URL for stream delivery from MediaPackage.',
        ),
    ]


class ListMssManifestConfiguration(BaseModel):
    """Summary information about a Microsoft Smooth Streaming (MSS) manifest configuration. This provides key details about the MSS manifest without including all configuration parameters."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='The name of the MSS manifest configuration.',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='The URL for accessing the MSS manifest.',
        ),
    ]


class ListOriginEndpointsRequest(BaseModel):
    """List Origin Endpoints Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of results to return in the response.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The pagination token from the GET list request. Use the token to fetch the next page of results.',
        ),
    ]


class ListTagsForResourceRequest(BaseModel):
    """List Tags For Resource Request."""

    model_config = ConfigDict(populate_by_name=True)

    resource_arn: Annotated[
        str,
        Field(
            ...,
            alias='ResourceArn',
            description='The ARN of the CloudWatch resource that you want to view tags for.',
        ),
    ]


class ListTagsForResourceResponse(BaseModel):
    """List Tags For Resource Response."""

    model_config = ConfigDict(populate_by_name=True)

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='Contains a map of the key-value pairs for the resource tag or tags assigned to the resource.',
        ),
    ]


class OriginEndpointListConfiguration(BaseModel):
    """The configuration of the origin endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]

    container_type: Annotated[
        ContainerType,
        Field(
            ...,
            alias='ContainerType',
            description='The type of container attached to this origin endpoint. A container type is a file format that encapsulates one or more media streams, such as audio and video, into a single file.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Any descriptive information that you want to add to the origin endpoint for future identification purposes.',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='CreatedAt',
            description='The date and time the origin endpoint was created.',
        ),
    ]

    modified_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ModifiedAt',
            description='The date and time the origin endpoint was modified.',
        ),
    ]

    hls_manifests: Annotated[
        Optional[list[ListHlsManifestConfiguration]],
        Field(
            None,
            alias='HlsManifests',
            description='An HTTP live streaming (HLS) manifest configuration.',
        ),
    ]

    low_latency_hls_manifests: Annotated[
        Optional[list[ListLowLatencyHlsManifestConfiguration]],
        Field(
            None,
            alias='LowLatencyHlsManifests',
            description='A low-latency HLS manifest configuration.',
        ),
    ]

    dash_manifests: Annotated[
        Optional[list[ListDashManifestConfiguration]],
        Field(
            None,
            alias='DashManifests',
            description='A DASH manifest configuration.',
        ),
    ]

    mss_manifests: Annotated[
        Optional[list[ListMssManifestConfiguration]],
        Field(
            None,
            alias='MssManifests',
            description='A list of Microsoft Smooth Streaming (MSS) manifest configurations associated with the origin endpoint. Each configuration represents a different MSS streaming option available from this endpoint.',
        ),
    ]

    force_endpoint_error_configuration: Annotated[
        Optional[ForceEndpointErrorConfiguration],
        Field(
            None,
            alias='ForceEndpointErrorConfiguration',
            description='The failover settings for the endpoint.',
        ),
    ]


class ListOriginEndpointsResponse(BaseModel):
    """List Origin Endpoints Response."""

    model_config = ConfigDict(populate_by_name=True)

    items: Annotated[
        Optional[list[OriginEndpointListConfiguration]],
        Field(
            None,
            alias='Items',
            description='The objects being returned.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The pagination token from the GET list request. Use the token to fetch the next page of results.',
        ),
    ]


class OutputHeaderConfiguration(BaseModel):
    """The settings for what common media server data (CMSD) headers AWS Elemental MediaPackage includes in responses to the CDN."""

    model_config = ConfigDict(populate_by_name=True)

    publish_mqcs: Annotated[
        Optional[bool],
        Field(
            None,
            alias='PublishMQCS',
            description='When true, AWS Elemental MediaPackage includes the MQCS in responses to the CDN. This setting is valid only when InputType is CMAF.',
        ),
    ]


class CreateChannelRequest(BaseModel):
    """Create Channel Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group. You can\u0027t change the name after you create the channel.',
        ),
    ]

    client_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClientToken',
            description='A unique, case-sensitive token that you provide to ensure the idempotency of the request.',
        ),
    ]

    input_type: Annotated[
        Optional[InputType],
        Field(
            None,
            alias='InputType',
            description='The input type will be an immutable field which will be used to define whether the channel will allow CMAF ingest or HLS ingest. If unprovided, it will default to HLS to preserve current behavior. The allowed values are: HLS - The HLS streaming specification (which defines M3U8 manifests and TS segments). CMAF - The DASH-IF CMAF Ingest specification (which defines CMAF segments with optional DASH manifests).',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Enter any descriptive text that helps you to identify the channel.',
        ),
    ]

    input_switch_configuration: Annotated[
        Optional[InputSwitchConfiguration],
        Field(
            None,
            alias='InputSwitchConfiguration',
            description='The configuration for input switching based on the media quality confidence score (MQCS) as provided from AWS Elemental MediaLive. This setting is valid only when InputType is CMAF.',
        ),
    ]

    output_header_configuration: Annotated[
        Optional[OutputHeaderConfiguration],
        Field(
            None,
            alias='OutputHeaderConfiguration',
            description='The settings for what common media server data (CMSD) headers AWS Elemental MediaPackage includes in responses to the CDN. This setting is valid only when InputType is CMAF.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A comma-separated list of tag key:value pairs that you define. For example: "Key1": "Value1", "Key2": "Value2"',
        ),
    ]


class CreateChannelResponse(BaseModel):
    """Create Channel Response."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the channel was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the channel was modified.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description for your channel.',
        ),
    ]

    ingest_endpoints: Annotated[
        Optional[list[IngestEndpoint]],
        Field(
            None,
            alias='IngestEndpoints',
            description='',
        ),
    ]

    input_type: Annotated[
        Optional[InputType],
        Field(
            None,
            alias='InputType',
            description='The input type will be an immutable field which will be used to define whether the channel will allow CMAF ingest or HLS ingest. If unprovided, it will default to HLS to preserve current behavior. The allowed values are: HLS - The HLS streaming specification (which defines M3U8 manifests and TS segments). CMAF - The DASH-IF CMAF Ingest specification (which defines CMAF segments with optional DASH manifests).',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the channel.',
        ),
    ]

    input_switch_configuration: Annotated[
        Optional[InputSwitchConfiguration],
        Field(
            None,
            alias='InputSwitchConfiguration',
            description='The configuration for input switching based on the media quality confidence score (MQCS) as provided from AWS Elemental MediaLive. This setting is valid only when InputType is CMAF.',
        ),
    ]

    output_header_configuration: Annotated[
        Optional[OutputHeaderConfiguration],
        Field(
            None,
            alias='OutputHeaderConfiguration',
            description='The settings for what common media server data (CMSD) headers AWS Elemental MediaPackage includes in responses to the CDN. This setting is valid only when InputType is CMAF.',
        ),
    ]


class GetChannelResponse(BaseModel):
    """Get Channel Response."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the channel was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the channel was modified.',
        ),
    ]

    reset_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ResetAt',
            description='The time that the channel was last reset.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description for your channel.',
        ),
    ]

    ingest_endpoints: Annotated[
        Optional[list[IngestEndpoint]],
        Field(
            None,
            alias='IngestEndpoints',
            description='',
        ),
    ]

    input_type: Annotated[
        Optional[InputType],
        Field(
            None,
            alias='InputType',
            description='The input type will be an immutable field which will be used to define whether the channel will allow CMAF ingest or HLS ingest. If unprovided, it will default to HLS to preserve current behavior. The allowed values are: HLS - The HLS streaming specification (which defines M3U8 manifests and TS segments). CMAF - The DASH-IF CMAF Ingest specification (which defines CMAF segments with optional DASH manifests).',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the channel.',
        ),
    ]

    input_switch_configuration: Annotated[
        Optional[InputSwitchConfiguration],
        Field(
            None,
            alias='InputSwitchConfiguration',
            description='The configuration for input switching based on the media quality confidence score (MQCS) as provided from AWS Elemental MediaLive. This setting is valid only when InputType is CMAF.',
        ),
    ]

    output_header_configuration: Annotated[
        Optional[OutputHeaderConfiguration],
        Field(
            None,
            alias='OutputHeaderConfiguration',
            description='The settings for what common media server data (CMSD) headers AWS Elemental MediaPackage includes in responses to the CDN. This setting is valid only when InputType is CMAF.',
        ),
    ]


class PutChannelPolicyRequest(BaseModel):
    """Put Channel Policy Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    policy: Annotated[
        str,
        Field(
            ...,
            alias='Policy',
            description='The policy to attach to the specified channel.',
        ),
    ]


class PutChannelPolicyResponse(BaseModel):
    """Put Channel Policy Response."""

    model_config = ConfigDict(populate_by_name=True)


class PutOriginEndpointPolicyRequest(BaseModel):
    """Put Origin Endpoint Policy Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]

    policy: Annotated[
        str,
        Field(
            ...,
            alias='Policy',
            description='The policy to attach to the specified origin endpoint.',
        ),
    ]

    cdn_auth_configuration: Annotated[
        Optional[CdnAuthConfiguration],
        Field(
            None,
            alias='CdnAuthConfiguration',
            description='The settings for using authorization headers between the MediaPackage endpoint and your CDN. For information about CDN authorization, see CDN authorization in Elemental MediaPackage in the MediaPackage user guide.',
        ),
    ]


class PutOriginEndpointPolicyResponse(BaseModel):
    """Put Origin Endpoint Policy Response."""

    model_config = ConfigDict(populate_by_name=True)


class ResetChannelStateRequest(BaseModel):
    """Reset Channel State Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group that contains the channel that you are resetting.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel that you are resetting.',
        ),
    ]


class ResetChannelStateResponse(BaseModel):
    """Reset Channel State Response."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group that contains the channel that you just reset.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel that you just reset.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the channel that you just reset.',
        ),
    ]

    reset_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ResetAt',
            description='The time that the channel was last reset.',
        ),
    ]


class ResetOriginEndpointStateRequest(BaseModel):
    """Reset Origin Endpoint State Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group that contains the channel with the origin endpoint that you are resetting.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel with the origin endpoint that you are resetting.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name of the origin endpoint that you are resetting.',
        ),
    ]


class ResetOriginEndpointStateResponse(BaseModel):
    """Reset Origin Endpoint State Response."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group that contains the channel with the origin endpoint that you just reset.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel with the origin endpoint that you just reset.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name of the origin endpoint that you just reset.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the endpoint that you just reset.',
        ),
    ]

    reset_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ResetAt',
            description='The time that the origin endpoint was last reset.',
        ),
    ]


class ResourceNotFoundException(BaseModel):
    """The specified resource doesn't exist."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]

    resource_type_not_found: Annotated[
        Optional[ResourceTypeNotFound],
        Field(
            None,
            alias='ResourceTypeNotFound',
            description='The specified resource type wasn\u0027t found.',
        ),
    ]


class S3DestinationConfig(BaseModel):
    """Configuration parameters for where in an S3 bucket to place the harvested content."""

    model_config = ConfigDict(populate_by_name=True)

    bucket_name: Annotated[
        str,
        Field(
            ...,
            alias='BucketName',
            description='The name of an S3 bucket within which harvested content will be exported.',
        ),
    ]

    destination_path: Annotated[
        str,
        Field(
            ...,
            alias='DestinationPath',
            description='The path within the specified S3 bucket where the harvested content will be placed.',
        ),
    ]


class Destination(BaseModel):
    """The configuration for the destination where the harvested content will be exported."""

    model_config = ConfigDict(populate_by_name=True)

    s3_destination: Annotated[
        S3DestinationConfig,
        Field(
            ...,
            alias='S3Destination',
            description='The configuration for exporting harvested content to an S3 bucket. This includes details such as the bucket name and destination path within the bucket.',
        ),
    ]


class CreateHarvestJobRequest(BaseModel):
    """The request object for creating a new harvest job."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group containing the channel from which to harvest content.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel from which to harvest content.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name of the origin endpoint from which to harvest content.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='An optional description for the harvest job.',
        ),
    ]

    harvested_manifests: Annotated[
        HarvestedManifests,
        Field(
            ...,
            alias='HarvestedManifests',
            description='A list of manifests to be harvested.',
        ),
    ]

    schedule_configuration: Annotated[
        HarvesterScheduleConfiguration,
        Field(
            ...,
            alias='ScheduleConfiguration',
            description='The configuration for when the harvest job should run, including start and end times.',
        ),
    ]

    destination: Annotated[
        Destination,
        Field(
            ...,
            alias='Destination',
            description='The S3 destination where the harvested content will be placed.',
        ),
    ]

    client_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClientToken',
            description='A unique, case-sensitive identifier that you provide to ensure the idempotency of the request.',
        ),
    ]

    harvest_job_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='HarvestJobName',
            description='A name for the harvest job. This name must be unique within the channel.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of tags associated with the harvest job.',
        ),
    ]


class CreateHarvestJobResponse(BaseModel):
    """The response object returned after creating a harvest job."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group containing the channel from which content is being harvested.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel from which content is being harvested.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name of the origin endpoint from which content is being harvested.',
        ),
    ]

    destination: Annotated[
        Destination,
        Field(
            ...,
            alias='Destination',
            description='The S3 destination where the harvested content will be placed.',
        ),
    ]

    harvest_job_name: Annotated[
        str,
        Field(
            ...,
            alias='HarvestJobName',
            description='The name of the created harvest job.',
        ),
    ]

    harvested_manifests: Annotated[
        HarvestedManifests,
        Field(
            ...,
            alias='HarvestedManifests',
            description='A list of manifests that will be harvested.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description of the harvest job, if provided.',
        ),
    ]

    schedule_configuration: Annotated[
        HarvesterScheduleConfiguration,
        Field(
            ...,
            alias='ScheduleConfiguration',
            description='The configuration for when the harvest job will run, including start and end times.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) of the created harvest job.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the harvest job was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the harvest job was last modified.',
        ),
    ]

    status: Annotated[
        HarvestJobStatus,
        Field(
            ...,
            alias='Status',
            description='The current status of the harvest job (e.g., CREATED, IN_PROGRESS, ABORTED, COMPLETED, FAILED).',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='An error message if the harvest job creation failed.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current version of the harvest job. Used for concurrency control.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of tags associated with the harvest job.',
        ),
    ]


class GetHarvestJobResponse(BaseModel):
    """The response object containing the details of the requested harvest job."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group containing the channel associated with the harvest job.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel associated with the harvest job.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name of the origin endpoint associated with the harvest job.',
        ),
    ]

    destination: Annotated[
        Destination,
        Field(
            ...,
            alias='Destination',
            description='The S3 destination where the harvested content is being placed.',
        ),
    ]

    harvest_job_name: Annotated[
        str,
        Field(
            ...,
            alias='HarvestJobName',
            description='The name of the harvest job.',
        ),
    ]

    harvested_manifests: Annotated[
        HarvestedManifests,
        Field(
            ...,
            alias='HarvestedManifests',
            description='A list of manifests that are being or have been harvested.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description of the harvest job, if provided.',
        ),
    ]

    schedule_configuration: Annotated[
        HarvesterScheduleConfiguration,
        Field(
            ...,
            alias='ScheduleConfiguration',
            description='The configuration for when the harvest job is scheduled to run, including start and end times.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) of the harvest job.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time when the harvest job was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time when the harvest job was last modified.',
        ),
    ]

    status: Annotated[
        HarvestJobStatus,
        Field(
            ...,
            alias='Status',
            description='The current status of the harvest job (e.g., QUEUED, IN_PROGRESS, CANCELLED, COMPLETED, FAILED).',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='An error message if the harvest job encountered any issues.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current version of the harvest job. Used for concurrency control.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of tags associated with the harvest job.',
        ),
    ]


class HarvestJob(BaseModel):
    """Represents a harvest job resource in MediaPackage v2, which is used to export content from an origin endpoint to an S3 bucket."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name of the channel group containing the channel associated with this harvest job.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name of the channel associated with this harvest job.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name of the origin endpoint associated with this harvest job.',
        ),
    ]

    destination: Annotated[
        Destination,
        Field(
            ...,
            alias='Destination',
            description='The S3 destination where the harvested content will be placed.',
        ),
    ]

    harvest_job_name: Annotated[
        str,
        Field(
            ...,
            alias='HarvestJobName',
            description='The name of the harvest job.',
        ),
    ]

    harvested_manifests: Annotated[
        HarvestedManifests,
        Field(
            ...,
            alias='HarvestedManifests',
            description='A list of manifests that are being or have been harvested.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='An optional description of the harvest job.',
        ),
    ]

    schedule_configuration: Annotated[
        HarvesterScheduleConfiguration,
        Field(
            ...,
            alias='ScheduleConfiguration',
            description='The configuration for when the harvest job is scheduled to run.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) of the harvest job.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time when the harvest job was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time when the harvest job was last modified.',
        ),
    ]

    status: Annotated[
        HarvestJobStatus,
        Field(
            ...,
            alias='Status',
            description='The current status of the harvest job (e.g., QUEUED, IN_PROGRESS, CANCELLED, COMPLETED, FAILED).',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='An error message if the harvest job encountered any issues.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current version of the harvest job. Used for concurrency control.',
        ),
    ]


class ListHarvestJobsResponse(BaseModel):
    """The response object containing the list of harvest jobs that match the specified criteria."""

    model_config = ConfigDict(populate_by_name=True)

    items: Annotated[
        Optional[list[HarvestJob]],
        Field(
            None,
            alias='Items',
            description='An array of harvest job objects that match the specified criteria.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used for pagination. Include this value in subsequent requests to retrieve the next set of results. If null, there are no more results to retrieve.',
        ),
    ]


class Scte(BaseModel):
    """The SCTE configuration."""

    model_config = ConfigDict(populate_by_name=True)

    scte_filter: Annotated[
        Optional[list[ScteFilter]],
        Field(
            None,
            alias='ScteFilter',
            description='The SCTE-35 message types that you want to be treated as ad markers in the output.',
        ),
    ]


class ScteDash(BaseModel):
    """The SCTE configuration."""

    model_config = ConfigDict(populate_by_name=True)

    ad_marker_dash: Annotated[
        Optional[AdMarkerDash],
        Field(
            None,
            alias='AdMarkerDash',
            description='Choose how ad markers are included in the packaged content. If you include ad markers in the content stream in your upstream encoders, then you need to inform MediaPackage what to do with the ad markers in the output. Value description: Binary - The SCTE-35 marker is expressed as a hex-string (Base64 string) rather than full XML. XML - The SCTE marker is expressed fully in XML.',
        ),
    ]


class CreateDashManifestConfiguration(BaseModel):
    """Create a DASH manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The child manifest name creates a unique path to this endpoint.',
        ),
    ]

    manifest_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ManifestWindowSeconds',
            description='The total duration (in seconds) of the manifest\u0027s content.',
        ),
    ]

    filter_configuration: Annotated[
        Optional[FilterConfiguration],
        Field(
            None,
            alias='FilterConfiguration',
            description='',
        ),
    ]

    min_update_period_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinUpdatePeriodSeconds',
            description='Minimum amount of time (in seconds) that the player should wait before requesting updates to the manifest.',
        ),
    ]

    min_buffer_time_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinBufferTimeSeconds',
            description='Minimum amount of content (in seconds) that a player must keep available in the buffer.',
        ),
    ]

    suggested_presentation_delay_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='SuggestedPresentationDelaySeconds',
            description='The amount of time (in seconds) that the player should be from the end of the manifest.',
        ),
    ]

    segment_template_format: Annotated[
        Optional[DashSegmentTemplateFormat],
        Field(
            None,
            alias='SegmentTemplateFormat',
            description='Determines the type of variable used in the media URL of the SegmentTemplate tag in the manifest. Also specifies if segment timeline information is included in SegmentTimeline or SegmentTemplate. Value description: NUMBER_WITH_TIMELINE - The $Number$ variable is used in the media URL. The value of this variable is the sequential number of the segment. A full SegmentTimeline object is presented in each SegmentTemplate.',
        ),
    ]

    period_triggers: Annotated[
        Optional[list[DashPeriodTrigger]],
        Field(
            None,
            alias='PeriodTriggers',
            description='A list of triggers that controls when AWS Elemental MediaPackage separates the MPEG-DASH manifest into multiple periods. Type ADS to indicate that AWS Elemental MediaPackage must create periods in the output manifest that correspond to SCTE-35 ad markers in the input source. Leave this value empty to indicate that the manifest is contained all in one period. For more information about periods in the DASH manifest, see Multi-period DASH in AWS Elemental MediaPackage.',
        ),
    ]

    scte_dash: Annotated[
        Optional[ScteDash],
        Field(
            None,
            alias='ScteDash',
            description='The SCTE configuration.',
        ),
    ]

    drm_signaling: Annotated[
        Optional[DashDrmSignaling],
        Field(
            None,
            alias='DrmSignaling',
            description='Determines how the DASH manifest signals the DRM content.',
        ),
    ]

    utc_timing: Annotated[
        Optional[DashUtcTiming],
        Field(
            None,
            alias='UtcTiming',
            description='Determines the type of UTC timing included in the DASH Media Presentation Description (MPD).',
        ),
    ]

    profiles: Annotated[
        Optional[list[DashProfile]],
        Field(
            None,
            alias='Profiles',
            description='The profile that the output is compliant with.',
        ),
    ]

    base_urls: Annotated[
        Optional[list[DashBaseUrl]],
        Field(
            None,
            alias='BaseUrls',
            description='The base URLs to use for retrieving segments.',
        ),
    ]

    program_information: Annotated[
        Optional[DashProgramInformation],
        Field(
            None,
            alias='ProgramInformation',
            description='Details about the content that you want MediaPackage to pass through in the manifest to the playback device.',
        ),
    ]

    dvb_settings: Annotated[
        Optional[DashDvbSettings],
        Field(
            None,
            alias='DvbSettings',
            description='For endpoints that use the DVB-DASH profile only. The font download and error reporting information that you want MediaPackage to pass through to the manifest.',
        ),
    ]

    compactness: Annotated[
        Optional[DashCompactness],
        Field(
            None,
            alias='Compactness',
            description='The layout of the DASH manifest that MediaPackage produces. STANDARD indicates a default manifest, which is compacted. NONE indicates a full manifest. For information about compactness, see DASH manifest compactness in the Elemental MediaPackage v2 User Guide.',
        ),
    ]

    subtitle_configuration: Annotated[
        Optional[DashSubtitleConfiguration],
        Field(
            None,
            alias='SubtitleConfiguration',
            description='The configuration for DASH subtitles.',
        ),
    ]


class GetDashManifestConfiguration(BaseModel):
    """Retrieve the DASH manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index.',
        ),
    ]

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='The egress domain URL for stream delivery from MediaPackage.',
        ),
    ]

    manifest_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ManifestWindowSeconds',
            description='The total duration (in seconds) of the manifest\u0027s content.',
        ),
    ]

    filter_configuration: Annotated[
        Optional[FilterConfiguration],
        Field(
            None,
            alias='FilterConfiguration',
            description='',
        ),
    ]

    min_update_period_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinUpdatePeriodSeconds',
            description='Minimum amount of time (in seconds) that the player should wait before requesting updates to the manifest.',
        ),
    ]

    min_buffer_time_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinBufferTimeSeconds',
            description='Minimum amount of content (in seconds) that a player must keep available in the buffer.',
        ),
    ]

    suggested_presentation_delay_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='SuggestedPresentationDelaySeconds',
            description='The amount of time (in seconds) that the player should be from the end of the manifest.',
        ),
    ]

    segment_template_format: Annotated[
        Optional[DashSegmentTemplateFormat],
        Field(
            None,
            alias='SegmentTemplateFormat',
            description='Determines the type of variable used in the media URL of the SegmentTemplate tag in the manifest. Also specifies if segment timeline information is included in SegmentTimeline or SegmentTemplate. Value description: NUMBER_WITH_TIMELINE - The $Number$ variable is used in the media URL. The value of this variable is the sequential number of the segment. A full SegmentTimeline object is presented in each SegmentTemplate.',
        ),
    ]

    period_triggers: Annotated[
        Optional[list[DashPeriodTrigger]],
        Field(
            None,
            alias='PeriodTriggers',
            description='A list of triggers that controls when AWS Elemental MediaPackage separates the MPEG-DASH manifest into multiple periods. Leave this value empty to indicate that the manifest is contained all in one period. For more information about periods in the DASH manifest, see Multi-period DASH in AWS Elemental MediaPackage.',
        ),
    ]

    scte_dash: Annotated[
        Optional[ScteDash],
        Field(
            None,
            alias='ScteDash',
            description='The SCTE configuration.',
        ),
    ]

    drm_signaling: Annotated[
        Optional[DashDrmSignaling],
        Field(
            None,
            alias='DrmSignaling',
            description='Determines how the DASH manifest signals the DRM content.',
        ),
    ]

    utc_timing: Annotated[
        Optional[DashUtcTiming],
        Field(
            None,
            alias='UtcTiming',
            description='Determines the type of UTC timing included in the DASH Media Presentation Description (MPD).',
        ),
    ]

    profiles: Annotated[
        Optional[list[DashProfile]],
        Field(
            None,
            alias='Profiles',
            description='The profile that the output is compliant with.',
        ),
    ]

    base_urls: Annotated[
        Optional[list[DashBaseUrl]],
        Field(
            None,
            alias='BaseUrls',
            description='The base URL to use for retrieving segments.',
        ),
    ]

    program_information: Annotated[
        Optional[DashProgramInformation],
        Field(
            None,
            alias='ProgramInformation',
            description='Details about the content that you want MediaPackage to pass through in the manifest to the playback device.',
        ),
    ]

    dvb_settings: Annotated[
        Optional[DashDvbSettings],
        Field(
            None,
            alias='DvbSettings',
            description='For endpoints that use the DVB-DASH profile only. The font download and error reporting information that you want MediaPackage to pass through to the manifest.',
        ),
    ]

    compactness: Annotated[
        Optional[DashCompactness],
        Field(
            None,
            alias='Compactness',
            description='The layout of the DASH manifest that MediaPackage produces. STANDARD indicates a default manifest, which is compacted. NONE indicates a full manifest.',
        ),
    ]

    subtitle_configuration: Annotated[
        Optional[DashSubtitleConfiguration],
        Field(
            None,
            alias='SubtitleConfiguration',
            description='The configuration for DASH subtitles.',
        ),
    ]


class ScteHls(BaseModel):
    """The SCTE configuration."""

    model_config = ConfigDict(populate_by_name=True)

    ad_marker_hls: Annotated[
        Optional[AdMarkerHls],
        Field(
            None,
            alias='AdMarkerHls',
            description='Ad markers indicate when ads should be inserted during playback. If you include ad markers in the content stream in your upstream encoders, then you need to inform MediaPackage what to do with the ad markers in the output. Choose what you want MediaPackage to do with the ad markers. Value description: DATERANGE - Insert EXT-X-DATERANGE tags to signal ad and program transition events in TS and CMAF manifests. If you use DATERANGE, you must set a programDateTimeIntervalSeconds value of 1 or higher. To learn more about DATERANGE, see SCTE-35 Ad Marker EXT-X-DATERANGE.',
        ),
    ]


class ServiceQuotaExceededException(BaseModel):
    """The request would cause a service quota to be exceeded."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class SpekeKeyProvider(BaseModel):
    """The parameters for the SPEKE key provider."""

    model_config = ConfigDict(populate_by_name=True)

    encryption_contract_configuration: Annotated[
        EncryptionContractConfiguration,
        Field(
            ...,
            alias='EncryptionContractConfiguration',
            description='Configure one or more content encryption keys for your endpoints that use SPEKE Version 2.0. The encryption contract defines which content keys are used to encrypt the audio and video tracks in your stream. To configure the encryption contract, specify which audio and video encryption presets to use.',
        ),
    ]

    resource_id: Annotated[
        str,
        Field(
            ...,
            alias='ResourceId',
            description='The unique identifier for the content. The service sends this to the key server to identify the current endpoint. How unique you make this depends on how fine-grained you want access controls to be. The service does not permit you to use the same ID for two simultaneous encryption processes. The resource ID is also known as the content ID. The following example shows a resource ID: MovieNight20171126093045',
        ),
    ]

    drm_systems: Annotated[
        list[DrmSystem],
        Field(
            ...,
            alias='DrmSystems',
            description='The DRM solution provider you\u0027re using to protect your content during distribution.',
        ),
    ]

    role_arn: Annotated[
        str,
        Field(
            ...,
            alias='RoleArn',
            description='The ARN for the IAM role granted by the key provider that provides access to the key provider API. This role must have a trust policy that allows MediaPackage to assume the role, and it must have a sufficient permissions policy to allow access to the specific key retrieval URL. Get this from your DRM solution provider. Valid format: arn:aws:iam::{accountID}:role/{name}. The following example shows a role ARN: arn:aws:iam::444455556666:role/SpekeAccess',
        ),
    ]

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='The URL of the API Gateway proxy that you set up to talk to your key server. The API Gateway proxy must reside in the same AWS Region as MediaPackage and must start with https://. The following example shows a URL: https://1wm2dx1f33.execute-api.us-west-2.amazonaws.com/SpekeSample/copyProtection',
        ),
    ]


class Encryption(BaseModel):
    """The parameters for encrypting content."""

    model_config = ConfigDict(populate_by_name=True)

    constant_initialization_vector: Annotated[
        Optional[str],
        Field(
            None,
            alias='ConstantInitializationVector',
            description='A 128-bit, 16-byte hex value represented by a 32-character string, used in conjunction with the key for encrypting content. If you don\u0027t specify a value, then MediaPackage creates the constant initialization vector (IV).',
        ),
    ]

    encryption_method: Annotated[
        EncryptionMethod,
        Field(
            ...,
            alias='EncryptionMethod',
            description='The encryption method to use.',
        ),
    ]

    key_rotation_interval_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='KeyRotationIntervalSeconds',
            description='The frequency (in seconds) of key changes for live workflows, in which content is streamed real time. The service retrieves content keys before the live content begins streaming, and then retrieves them as needed over the lifetime of the workflow. By default, key rotation is set to 300 seconds (5 minutes), the minimum rotation interval, which is equivalent to setting it to 300. If you don\u0027t enter an interval, content keys aren\u0027t rotated. The following example setting causes the service to rotate keys every thirty minutes: 1800',
        ),
    ]

    cmaf_exclude_segment_drm_metadata: Annotated[
        Optional[bool],
        Field(
            None,
            alias='CmafExcludeSegmentDrmMetadata',
            description='Excludes SEIG and SGPD boxes from segment metadata in CMAF containers. When set to true, MediaPackage omits these DRM metadata boxes from CMAF segments, which can improve compatibility with certain devices and players that don\u0027t support these boxes. Important considerations: This setting only affects CMAF container formats Key rotation can still be handled through media playlist signaling PSSH and TENC boxes remain unaffected Default behavior is preserved when this setting is disabled Valid values: true | false Default: false',
        ),
    ]

    speke_key_provider: Annotated[
        SpekeKeyProvider,
        Field(
            ...,
            alias='SpekeKeyProvider',
            description='The parameters for the SPEKE key provider.',
        ),
    ]


class Segment(BaseModel):
    """The segment configuration, including the segment name, duration, and other configuration values."""

    model_config = ConfigDict(populate_by_name=True)

    segment_duration_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentDurationSeconds',
            description='The duration (in seconds) of each segment. Enter a value equal to, or a multiple of, the input segment duration. If the value that you enter is different from the input segment duration, MediaPackage rounds segments to the nearest multiple of the input segment duration.',
        ),
    ]

    segment_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='SegmentName',
            description='The name that describes the segment. The name is the base name of the segment used in all content manifests inside of the endpoint. You can\u0027t use spaces in the name.',
        ),
    ]

    ts_use_audio_rendition_group: Annotated[
        Optional[bool],
        Field(
            None,
            alias='TsUseAudioRenditionGroup',
            description='When selected, MediaPackage bundles all audio tracks in a rendition group. All other tracks in the stream can be used with any audio rendition from the group.',
        ),
    ]

    include_iframe_only_streams: Annotated[
        Optional[bool],
        Field(
            None,
            alias='IncludeIframeOnlyStreams',
            description='When selected, the stream set includes an additional I-frame only stream, along with the other tracks. If false, this extra stream is not included. MediaPackage generates an I-frame only stream from the first rendition in the manifest. The service inserts EXT-I-FRAMES-ONLY tags in the output manifest, and then generates and includes an I-frames only playlist in the stream. This playlist permits player functionality like fast forward and rewind.',
        ),
    ]

    ts_include_dvb_subtitles: Annotated[
        Optional[bool],
        Field(
            None,
            alias='TsIncludeDvbSubtitles',
            description='By default, MediaPackage excludes all digital video broadcasting (DVB) subtitles from the output. When selected, MediaPackage passes through DVB subtitles into the output.',
        ),
    ]

    scte: Annotated[
        Optional[Scte],
        Field(
            None,
            alias='Scte',
            description='The SCTE configuration options in the segment settings.',
        ),
    ]

    encryption: Annotated[
        Optional[Encryption],
        Field(
            None,
            alias='Encryption',
            description='',
        ),
    ]


class StartTag(BaseModel):
    """To insert an EXT-X-START tag in your HLS playlist, specify a StartTag configuration object with a valid TimeOffset. When you do, you can also optionally specify whether to include a PRECISE value in the EXT-X-START tag."""

    model_config = ConfigDict(populate_by_name=True)

    time_offset: Annotated[
        float,
        Field(
            ...,
            alias='TimeOffset',
            description='Specify the value for TIME-OFFSET within your EXT-X-START tag. Enter a signed floating point value which, if positive, must be less than the configured manifest duration minus three times the configured segment target duration. If negative, the absolute value must be larger than three times the configured segment target duration, and the absolute value must be smaller than the configured manifest duration.',
        ),
    ]

    precise: Annotated[
        Optional[bool],
        Field(
            None,
            alias='Precise',
            description='Specify the value for PRECISE within your EXT-X-START tag. Leave blank, or choose false, to use the default value NO. Choose yes to use the value YES.',
        ),
    ]


class CreateHlsManifestConfiguration(BaseModel):
    """Create an HTTP live streaming (HLS) manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short short string that\u0027s appended to the endpoint URL. The manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index. MediaPackage automatically inserts the format extension, such as .m3u8. You can\u0027t use the same manifest name if you use HLS manifest and low-latency HLS manifest. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    child_manifest_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChildManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The child manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index, with an added suffix to distinguish it from the manifest name. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    scte_hls: Annotated[
        Optional[ScteHls],
        Field(
            None,
            alias='ScteHls',
            description='',
        ),
    ]

    start_tag: Annotated[
        Optional[StartTag],
        Field(
            None,
            alias='StartTag',
            description='',
        ),
    ]

    manifest_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ManifestWindowSeconds',
            description='The total duration (in seconds) of the manifest\u0027s content.',
        ),
    ]

    program_date_time_interval_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramDateTimeIntervalSeconds',
            description='Inserts EXT-X-PROGRAM-DATE-TIME tags in the output manifest at the interval that you specify. If you don\u0027t enter an interval, EXT-X-PROGRAM-DATE-TIME tags aren\u0027t included in the manifest. The tags sync the stream to the wall clock so that viewers can seek to a specific time in the playback timeline on the player. Irrespective of this parameter, if any ID3Timed metadata is in the HLS input, it is passed through to the HLS output.',
        ),
    ]

    filter_configuration: Annotated[
        Optional[FilterConfiguration],
        Field(
            None,
            alias='FilterConfiguration',
            description='',
        ),
    ]

    url_encode_child_manifest: Annotated[
        Optional[bool],
        Field(
            None,
            alias='UrlEncodeChildManifest',
            description='When enabled, MediaPackage URL-encodes the query string for API requests for HLS child manifests to comply with Amazon Web Services Signature Version 4 (SigV4) signature signing protocol. For more information, see Amazon Web Services Signature Version 4 for API requests in Identity and Access Management User Guide.',
        ),
    ]


class CreateLowLatencyHlsManifestConfiguration(BaseModel):
    """Create a low-latency HTTP live streaming (HLS) manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short short string that\u0027s appended to the endpoint URL. The manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index. MediaPackage automatically inserts the format extension, such as .m3u8. You can\u0027t use the same manifest name if you use HLS manifest and low-latency HLS manifest. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    child_manifest_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChildManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The child manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index, with an added suffix to distinguish it from the manifest name. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    scte_hls: Annotated[
        Optional[ScteHls],
        Field(
            None,
            alias='ScteHls',
            description='',
        ),
    ]

    start_tag: Annotated[
        Optional[StartTag],
        Field(
            None,
            alias='StartTag',
            description='',
        ),
    ]

    manifest_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ManifestWindowSeconds',
            description='The total duration (in seconds) of the manifest\u0027s content.',
        ),
    ]

    program_date_time_interval_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramDateTimeIntervalSeconds',
            description='Inserts EXT-X-PROGRAM-DATE-TIME tags in the output manifest at the interval that you specify. If you don\u0027t enter an interval, EXT-X-PROGRAM-DATE-TIME tags aren\u0027t included in the manifest. The tags sync the stream to the wall clock so that viewers can seek to a specific time in the playback timeline on the player. Irrespective of this parameter, if any ID3Timed metadata is in the HLS input, it is passed through to the HLS output.',
        ),
    ]

    filter_configuration: Annotated[
        Optional[FilterConfiguration],
        Field(
            None,
            alias='FilterConfiguration',
            description='',
        ),
    ]

    url_encode_child_manifest: Annotated[
        Optional[bool],
        Field(
            None,
            alias='UrlEncodeChildManifest',
            description='When enabled, MediaPackage URL-encodes the query string for API requests for LL-HLS child manifests to comply with Amazon Web Services Signature Version 4 (SigV4) signature signing protocol. For more information, see Amazon Web Services Signature Version 4 for API requests in Identity and Access Management User Guide.',
        ),
    ]


class CreateOriginEndpointRequest(BaseModel):
    """Create Origin Endpoint Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and must be unique for your account in the AWS Region and channel. You can\u0027t use spaces in the name. You can\u0027t change the name after you create the endpoint.',
        ),
    ]

    container_type: Annotated[
        ContainerType,
        Field(
            ...,
            alias='ContainerType',
            description='The type of container to attach to this origin endpoint. A container type is a file format that encapsulates one or more media streams, such as audio and video, into a single file. You can\u0027t change the container type after you create the endpoint.',
        ),
    ]

    segment: Annotated[
        Optional[Segment],
        Field(
            None,
            alias='Segment',
            description='The segment configuration, including the segment name, duration, and other configuration values.',
        ),
    ]

    client_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClientToken',
            description='A unique, case-sensitive token that you provide to ensure the idempotency of the request.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Enter any descriptive text that helps you to identify the origin endpoint.',
        ),
    ]

    startover_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='StartoverWindowSeconds',
            description='The size of the window (in seconds) to create a window of the live stream that\u0027s available for on-demand viewing. Viewers can start-over or catch-up on content that falls within the window. The maximum startover window is 1,209,600 seconds (14 days).',
        ),
    ]

    hls_manifests: Annotated[
        Optional[list[CreateHlsManifestConfiguration]],
        Field(
            None,
            alias='HlsManifests',
            description='An HTTP live streaming (HLS) manifest configuration.',
        ),
    ]

    low_latency_hls_manifests: Annotated[
        Optional[list[CreateLowLatencyHlsManifestConfiguration]],
        Field(
            None,
            alias='LowLatencyHlsManifests',
            description='A low-latency HLS manifest configuration.',
        ),
    ]

    dash_manifests: Annotated[
        Optional[list[CreateDashManifestConfiguration]],
        Field(
            None,
            alias='DashManifests',
            description='A DASH manifest configuration.',
        ),
    ]

    mss_manifests: Annotated[
        Optional[list[CreateMssManifestConfiguration]],
        Field(
            None,
            alias='MssManifests',
            description='A list of Microsoft Smooth Streaming (MSS) manifest configurations for the origin endpoint. You can configure multiple MSS manifests to provide different streaming experiences or to support different client requirements.',
        ),
    ]

    force_endpoint_error_configuration: Annotated[
        Optional[ForceEndpointErrorConfiguration],
        Field(
            None,
            alias='ForceEndpointErrorConfiguration',
            description='The failover settings for the endpoint.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A comma-separated list of tag key:value pairs that you define. For example: "Key1": "Value1", "Key2": "Value2"',
        ),
    ]


class GetHlsManifestConfiguration(BaseModel):
    """Retrieve the HTTP live streaming (HLS) manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short short string that\u0027s appended to the endpoint URL. The manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index. MediaPackage automatically inserts the format extension, such as .m3u8. You can\u0027t use the same manifest name if you use HLS manifest and low-latency HLS manifest. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='The egress domain URL for stream delivery from MediaPackage.',
        ),
    ]

    child_manifest_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChildManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The child manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default child manifest name, index_1. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    manifest_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ManifestWindowSeconds',
            description='The total duration (in seconds) of the manifest\u0027s content.',
        ),
    ]

    program_date_time_interval_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramDateTimeIntervalSeconds',
            description='Inserts EXT-X-PROGRAM-DATE-TIME tags in the output manifest at the interval that you specify. If you don\u0027t enter an interval, EXT-X-PROGRAM-DATE-TIME tags aren\u0027t included in the manifest. The tags sync the stream to the wall clock so that viewers can seek to a specific time in the playback timeline on the player. Irrespective of this parameter, if any ID3Timed metadata is in the HLS input, it is passed through to the HLS output.',
        ),
    ]

    scte_hls: Annotated[
        Optional[ScteHls],
        Field(
            None,
            alias='ScteHls',
            description='',
        ),
    ]

    filter_configuration: Annotated[
        Optional[FilterConfiguration],
        Field(
            None,
            alias='FilterConfiguration',
            description='',
        ),
    ]

    start_tag: Annotated[
        Optional[StartTag],
        Field(
            None,
            alias='StartTag',
            description='',
        ),
    ]

    url_encode_child_manifest: Annotated[
        Optional[bool],
        Field(
            None,
            alias='UrlEncodeChildManifest',
            description='When enabled, MediaPackage URL-encodes the query string for API requests for HLS child manifests to comply with Amazon Web Services Signature Version 4 (SigV4) signature signing protocol. For more information, see Amazon Web Services Signature Version 4 for API requests in Identity and Access Management User Guide.',
        ),
    ]


class GetLowLatencyHlsManifestConfiguration(BaseModel):
    """Retrieve the low-latency HTTP live streaming (HLS) manifest configuration."""

    model_config = ConfigDict(populate_by_name=True)

    manifest_name: Annotated[
        str,
        Field(
            ...,
            alias='ManifestName',
            description='A short short string that\u0027s appended to the endpoint URL. The manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default manifest name, index. MediaPackage automatically inserts the format extension, such as .m3u8. You can\u0027t use the same manifest name if you use HLS manifest and low-latency HLS manifest. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='The egress domain URL for stream delivery from MediaPackage.',
        ),
    ]

    child_manifest_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChildManifestName',
            description='A short string that\u0027s appended to the endpoint URL. The child manifest name creates a unique path to this endpoint. If you don\u0027t enter a value, MediaPackage uses the default child manifest name, index_1. The manifestName on the HLSManifest object overrides the manifestName you provided on the originEndpoint object.',
        ),
    ]

    manifest_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ManifestWindowSeconds',
            description='The total duration (in seconds) of the manifest\u0027s content.',
        ),
    ]

    program_date_time_interval_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramDateTimeIntervalSeconds',
            description='Inserts EXT-X-PROGRAM-DATE-TIME tags in the output manifest at the interval that you specify. If you don\u0027t enter an interval, EXT-X-PROGRAM-DATE-TIME tags aren\u0027t included in the manifest. The tags sync the stream to the wall clock so that viewers can seek to a specific time in the playback timeline on the player. Irrespective of this parameter, if any ID3Timed metadata is in the HLS input, it is passed through to the HLS output.',
        ),
    ]

    scte_hls: Annotated[
        Optional[ScteHls],
        Field(
            None,
            alias='ScteHls',
            description='',
        ),
    ]

    filter_configuration: Annotated[
        Optional[FilterConfiguration],
        Field(
            None,
            alias='FilterConfiguration',
            description='',
        ),
    ]

    start_tag: Annotated[
        Optional[StartTag],
        Field(
            None,
            alias='StartTag',
            description='',
        ),
    ]

    url_encode_child_manifest: Annotated[
        Optional[bool],
        Field(
            None,
            alias='UrlEncodeChildManifest',
            description='When enabled, MediaPackage URL-encodes the query string for API requests for LL-HLS child manifests to comply with Amazon Web Services Signature Version 4 (SigV4) signature signing protocol. For more information, see Amazon Web Services Signature Version 4 for API requests in Identity and Access Management User Guide.',
        ),
    ]


class CreateOriginEndpointResponse(BaseModel):
    """Create Origin Endpoint Response."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]

    container_type: Annotated[
        ContainerType,
        Field(
            ...,
            alias='ContainerType',
            description='The type of container attached to this origin endpoint.',
        ),
    ]

    segment: Annotated[
        Segment,
        Field(
            ...,
            alias='Segment',
            description='The segment configuration, including the segment name, duration, and other configuration values.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the origin endpoint was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the origin endpoint was modified.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description for your origin endpoint.',
        ),
    ]

    startover_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='StartoverWindowSeconds',
            description='The size of the window (in seconds) to create a window of the live stream that\u0027s available for on-demand viewing. Viewers can start-over or catch-up on content that falls within the window.',
        ),
    ]

    hls_manifests: Annotated[
        Optional[list[GetHlsManifestConfiguration]],
        Field(
            None,
            alias='HlsManifests',
            description='An HTTP live streaming (HLS) manifest configuration.',
        ),
    ]

    low_latency_hls_manifests: Annotated[
        Optional[list[GetLowLatencyHlsManifestConfiguration]],
        Field(
            None,
            alias='LowLatencyHlsManifests',
            description='A low-latency HLS manifest configuration.',
        ),
    ]

    dash_manifests: Annotated[
        Optional[list[GetDashManifestConfiguration]],
        Field(
            None,
            alias='DashManifests',
            description='A DASH manifest configuration.',
        ),
    ]

    mss_manifests: Annotated[
        Optional[list[GetMssManifestConfiguration]],
        Field(
            None,
            alias='MssManifests',
            description='The Microsoft Smooth Streaming (MSS) manifest configurations that were created for this origin endpoint.',
        ),
    ]

    force_endpoint_error_configuration: Annotated[
        Optional[ForceEndpointErrorConfiguration],
        Field(
            None,
            alias='ForceEndpointErrorConfiguration',
            description='The failover settings for the endpoint.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the origin endpoint.',
        ),
    ]


class GetOriginEndpointResponse(BaseModel):
    """Get Origin Endpoint Response."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]

    container_type: Annotated[
        ContainerType,
        Field(
            ...,
            alias='ContainerType',
            description='The type of container attached to this origin endpoint.',
        ),
    ]

    segment: Annotated[
        Segment,
        Field(
            ...,
            alias='Segment',
            description='',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the origin endpoint was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the origin endpoint was modified.',
        ),
    ]

    reset_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='ResetAt',
            description='The time that the origin endpoint was last reset.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description for your origin endpoint.',
        ),
    ]

    startover_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='StartoverWindowSeconds',
            description='The size of the window (in seconds) to create a window of the live stream that\u0027s available for on-demand viewing. Viewers can start-over or catch-up on content that falls within the window.',
        ),
    ]

    hls_manifests: Annotated[
        Optional[list[GetHlsManifestConfiguration]],
        Field(
            None,
            alias='HlsManifests',
            description='An HTTP live streaming (HLS) manifest configuration.',
        ),
    ]

    low_latency_hls_manifests: Annotated[
        Optional[list[GetLowLatencyHlsManifestConfiguration]],
        Field(
            None,
            alias='LowLatencyHlsManifests',
            description='A low-latency HLS manifest configuration.',
        ),
    ]

    dash_manifests: Annotated[
        Optional[list[GetDashManifestConfiguration]],
        Field(
            None,
            alias='DashManifests',
            description='A DASH manifest configuration.',
        ),
    ]

    mss_manifests: Annotated[
        Optional[list[GetMssManifestConfiguration]],
        Field(
            None,
            alias='MssManifests',
            description='The Microsoft Smooth Streaming (MSS) manifest configurations associated with this origin endpoint.',
        ),
    ]

    force_endpoint_error_configuration: Annotated[
        Optional[ForceEndpointErrorConfiguration],
        Field(
            None,
            alias='ForceEndpointErrorConfiguration',
            description='The failover settings for the endpoint.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the origin endpoint.',
        ),
    ]


class TagResourceRequest(BaseModel):
    """Tag Resource Request."""

    model_config = ConfigDict(populate_by_name=True)

    resource_arn: Annotated[
        str,
        Field(
            ...,
            alias='ResourceArn',
            description='The ARN of the MediaPackage resource that you\u0027re adding tags to.',
        ),
    ]

    tags: Annotated[
        dict[str, str],
        Field(
            ...,
            alias='Tags',
            description='Contains a map of the key-value pairs for the resource tag or tags assigned to the resource.',
        ),
    ]


class ThrottlingException(BaseModel):
    """The request throughput limit was exceeded."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class UntagResourceRequest(BaseModel):
    """Untag Resource Request."""

    model_config = ConfigDict(populate_by_name=True)

    resource_arn: Annotated[
        str,
        Field(
            ...,
            alias='ResourceArn',
            description='The ARN of the MediaPackage resource that you\u0027re removing tags from.',
        ),
    ]

    tag_keys: Annotated[
        list[str],
        Field(
            ...,
            alias='TagKeys',
            description='The list of tag keys to remove from the resource.',
        ),
    ]


class UpdateChannelGroupRequest(BaseModel):
    """Update Channel Group Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The expected current Entity Tag (ETag) for the resource. If the specified ETag does not match the resource\u0027s current entity tag, the update request will be rejected.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Any descriptive information that you want to add to the channel group for future identification purposes.',
        ),
    ]


class UpdateChannelGroupResponse(BaseModel):
    """Update Channel Group Response."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    egress_domain: Annotated[
        str,
        Field(
            ...,
            alias='EgressDomain',
            description='The output domain where the source stream is sent. Integrate the domain with a downstream CDN (such as Amazon CloudFront) or playback device.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the channel group was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the channel group was modified.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description for your channel group.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the channel group.',
        ),
    ]


class UpdateChannelRequest(BaseModel):
    """Update Channel Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The expected current Entity Tag (ETag) for the resource. If the specified ETag does not match the resource\u0027s current entity tag, the update request will be rejected.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Any descriptive information that you want to add to the channel for future identification purposes.',
        ),
    ]

    input_switch_configuration: Annotated[
        Optional[InputSwitchConfiguration],
        Field(
            None,
            alias='InputSwitchConfiguration',
            description='The configuration for input switching based on the media quality confidence score (MQCS) as provided from AWS Elemental MediaLive. This setting is valid only when InputType is CMAF.',
        ),
    ]

    output_header_configuration: Annotated[
        Optional[OutputHeaderConfiguration],
        Field(
            None,
            alias='OutputHeaderConfiguration',
            description='The settings for what common media server data (CMSD) headers AWS Elemental MediaPackage includes in responses to the CDN. This setting is valid only when InputType is CMAF.',
        ),
    ]


class UpdateChannelResponse(BaseModel):
    """Update Channel Response."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The Amazon Resource Name (ARN) associated with the resource.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the channel was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the channel was modified.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description for your channel.',
        ),
    ]

    ingest_endpoints: Annotated[
        Optional[list[IngestEndpoint]],
        Field(
            None,
            alias='IngestEndpoints',
            description='',
        ),
    ]

    input_type: Annotated[
        Optional[InputType],
        Field(
            None,
            alias='InputType',
            description='The input type will be an immutable field which will be used to define whether the channel will allow CMAF ingest or HLS ingest. If unprovided, it will default to HLS to preserve current behavior. The allowed values are: HLS - The HLS streaming specification (which defines M3U8 manifests and TS segments). CMAF - The DASH-IF CMAF Ingest specification (which defines CMAF segments with optional DASH manifests).',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the channel.',
        ),
    ]

    input_switch_configuration: Annotated[
        Optional[InputSwitchConfiguration],
        Field(
            None,
            alias='InputSwitchConfiguration',
            description='The configuration for input switching based on the media quality confidence score (MQCS) as provided from AWS Elemental MediaLive. This setting is valid only when InputType is CMAF.',
        ),
    ]

    output_header_configuration: Annotated[
        Optional[OutputHeaderConfiguration],
        Field(
            None,
            alias='OutputHeaderConfiguration',
            description='The settings for what common media server data (CMSD) headers AWS Elemental MediaPackage includes in responses to the CDN. This setting is valid only when InputType is CMAF.',
        ),
    ]


class UpdateOriginEndpointRequest(BaseModel):
    """Update Origin Endpoint Request."""

    model_config = ConfigDict(populate_by_name=True)

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]

    container_type: Annotated[
        ContainerType,
        Field(
            ...,
            alias='ContainerType',
            description='The type of container attached to this origin endpoint. A container type is a file format that encapsulates one or more media streams, such as audio and video, into a single file.',
        ),
    ]

    segment: Annotated[
        Optional[Segment],
        Field(
            None,
            alias='Segment',
            description='The segment configuration, including the segment name, duration, and other configuration values.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='Any descriptive information that you want to add to the origin endpoint for future identification purposes.',
        ),
    ]

    startover_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='StartoverWindowSeconds',
            description='The size of the window (in seconds) to create a window of the live stream that\u0027s available for on-demand viewing. Viewers can start-over or catch-up on content that falls within the window. The maximum startover window is 1,209,600 seconds (14 days).',
        ),
    ]

    hls_manifests: Annotated[
        Optional[list[CreateHlsManifestConfiguration]],
        Field(
            None,
            alias='HlsManifests',
            description='An HTTP live streaming (HLS) manifest configuration.',
        ),
    ]

    low_latency_hls_manifests: Annotated[
        Optional[list[CreateLowLatencyHlsManifestConfiguration]],
        Field(
            None,
            alias='LowLatencyHlsManifests',
            description='A low-latency HLS manifest configuration.',
        ),
    ]

    dash_manifests: Annotated[
        Optional[list[CreateDashManifestConfiguration]],
        Field(
            None,
            alias='DashManifests',
            description='A DASH manifest configuration.',
        ),
    ]

    mss_manifests: Annotated[
        Optional[list[CreateMssManifestConfiguration]],
        Field(
            None,
            alias='MssManifests',
            description='A list of Microsoft Smooth Streaming (MSS) manifest configurations to update for the origin endpoint. This replaces the existing MSS manifest configurations.',
        ),
    ]

    force_endpoint_error_configuration: Annotated[
        Optional[ForceEndpointErrorConfiguration],
        Field(
            None,
            alias='ForceEndpointErrorConfiguration',
            description='The failover settings for the endpoint.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The expected current Entity Tag (ETag) for the resource. If the specified ETag does not match the resource\u0027s current entity tag, the update request will be rejected.',
        ),
    ]


class UpdateOriginEndpointResponse(BaseModel):
    """Update Origin Endpoint Response."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The ARN associated with the resource.',
        ),
    ]

    channel_group_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelGroupName',
            description='The name that describes the channel group. The name is the primary identifier for the channel group, and must be unique for your account in the AWS Region.',
        ),
    ]

    channel_name: Annotated[
        str,
        Field(
            ...,
            alias='ChannelName',
            description='The name that describes the channel. The name is the primary identifier for the channel, and must be unique for your account in the AWS Region and channel group.',
        ),
    ]

    origin_endpoint_name: Annotated[
        str,
        Field(
            ...,
            alias='OriginEndpointName',
            description='The name that describes the origin endpoint. The name is the primary identifier for the origin endpoint, and and must be unique for your account in the AWS Region and channel.',
        ),
    ]

    container_type: Annotated[
        ContainerType,
        Field(
            ...,
            alias='ContainerType',
            description='The type of container attached to this origin endpoint.',
        ),
    ]

    segment: Annotated[
        Segment,
        Field(
            ...,
            alias='Segment',
            description='The segment configuration, including the segment name, duration, and other configuration values.',
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(
            ...,
            alias='CreatedAt',
            description='The date and time the origin endpoint was created.',
        ),
    ]

    modified_at: Annotated[
        datetime,
        Field(
            ...,
            alias='ModifiedAt',
            description='The date and time the origin endpoint was modified.',
        ),
    ]

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='The description of the origin endpoint.',
        ),
    ]

    startover_window_seconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='StartoverWindowSeconds',
            description='The size of the window (in seconds) to create a window of the live stream that\u0027s available for on-demand viewing. Viewers can start-over or catch-up on content that falls within the window.',
        ),
    ]

    hls_manifests: Annotated[
        Optional[list[GetHlsManifestConfiguration]],
        Field(
            None,
            alias='HlsManifests',
            description='An HTTP live streaming (HLS) manifest configuration.',
        ),
    ]

    low_latency_hls_manifests: Annotated[
        Optional[list[GetLowLatencyHlsManifestConfiguration]],
        Field(
            None,
            alias='LowLatencyHlsManifests',
            description='A low-latency HLS manifest configuration.',
        ),
    ]

    mss_manifests: Annotated[
        Optional[list[GetMssManifestConfiguration]],
        Field(
            None,
            alias='MssManifests',
            description='The updated Microsoft Smooth Streaming (MSS) manifest configurations for this origin endpoint.',
        ),
    ]

    force_endpoint_error_configuration: Annotated[
        Optional[ForceEndpointErrorConfiguration],
        Field(
            None,
            alias='ForceEndpointErrorConfiguration',
            description='The failover settings for the endpoint.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The current Entity Tag (ETag) associated with this resource. The entity tag can be used to safely make concurrent updates to the resource.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='The comma-separated list of tag key:value pairs assigned to the origin endpoint.',
        ),
    ]

    dash_manifests: Annotated[
        Optional[list[GetDashManifestConfiguration]],
        Field(
            None,
            alias='DashManifests',
            description='A DASH manifest configuration.',
        ),
    ]


class ValidationException(BaseModel):
    """The input failed to meet the constraints specified by the AWS service."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]

    validation_exception_type: Annotated[
        Optional[ValidationExceptionType],
        Field(
            None,
            alias='ValidationExceptionType',
            description='The type of ValidationException.',
        ),
    ]
