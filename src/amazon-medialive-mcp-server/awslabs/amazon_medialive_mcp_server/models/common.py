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

"""Common Pydantic models — shared types used across multiple MediaLive domains."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    AacCodingMode,
    AacInputType,
    AacProfile,
    AacRateControlMode,
    AacRawFormat,
    AacSpec,
    AacVbrQuality,
    Ac3AttenuationControl,
    Ac3BitstreamMode,
    Ac3CodingMode,
    Ac3DrcProfile,
    Ac3LfeFilter,
    Ac3MetadataControl,
    AcceptHeader,
    AccessibilityType,
    AudioDescriptionAudioTypeControl,
    AudioDescriptionLanguageCodeControl,
    AudioLanguageSelectionPolicy,
    AudioNormalizationAlgorithm,
    AudioNormalizationAlgorithmControl,
    AudioOnlyHlsSegmentType,
    AudioOnlyHlsTrackType,
    AudioType,
    BurnInAlignment,
    BurnInBackgroundColor,
    BurnInDestinationSubtitleRows,
    BurnInFontColor,
    BurnInOutlineColor,
    BurnInShadowColor,
    BurnInTeletextGridControl,
    CdiInputResolution,
    CloudWatchAlarmTemplateComparisonOperator,
    CloudWatchAlarmTemplateStatistic,
    CloudWatchAlarmTemplateTargetResourceType,
    CloudWatchAlarmTemplateTreatMissingData,
    ClusterState,
    ClusterType,
    ContentType,
    DashRoleAudio,
    DashRoleCaption,
    DeviceSettingsSyncState,
    DeviceUpdateStatus,
    DolbyEProgramSelection,
    DvbDashAccessibility,
    DvbSdtOutputSdt,
    DvbSubDestinationAlignment,
    DvbSubDestinationBackgroundColor,
    DvbSubDestinationFontColor,
    DvbSubDestinationOutlineColor,
    DvbSubDestinationShadowColor,
    DvbSubDestinationSubtitleRows,
    DvbSubDestinationTeletextGridControl,
    DvbSubOcrLanguage,
    Eac3AtmosCodingMode,
    Eac3AtmosDrcLine,
    Eac3AtmosDrcRf,
    Eac3AttenuationControl,
    Eac3BitstreamMode,
    Eac3CodingMode,
    Eac3DcFilter,
    Eac3DrcLine,
    Eac3DrcRf,
    Eac3LfeControl,
    Eac3LfeFilter,
    Eac3MetadataControl,
    Eac3PassthroughControl,
    Eac3PhaseControl,
    Eac3StereoDownmix,
    Eac3SurroundExMode,
    Eac3SurroundMode,
    EbuTtDDestinationStyleControl,
    EbuTtDFillLineGapControl,
    EmbeddedConvert608To708,
    EmbeddedScte20Detection,
    EventBridgeRuleTemplateEventType,
    InputClass,
    InputDeviceConnectionState,
    InputDeviceOutputType,
    InputDeviceType,
    InputNetworkLocation,
    InputSecurityGroupState,
    InputSourceType,
    InputState,
    InputType,
    LastFrameClippingBehavior,
    Mp2CodingMode,
    MultiplexState,
    NetworkState,
    NodeConnectionState,
    NodeRole,
    NodeState,
    OfferingDurationUnits,
    OfferingType,
    ReservationAutomaticRenewal,
    ReservationState,
    SdiSourceMode,
    SdiSourceType,
    SignalMapMonitorDeploymentStatus,
    SignalMapStatus,
    TtmlDestinationStyleControl,
    UpdateNodeState,
    WavCodingMode,
    WebvttDestinationStyleControl,
)
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.channel import (
        ChannelEngineVersionResponse,
        TransferringInputDeviceSummary,
    )
    from awslabs.amazon_medialive_mcp_server.models.encoding import (
        ThumbnailDetail,
    )
    from awslabs.amazon_medialive_mcp_server.models.infrastructure import (
        AccountConfiguration,
        ClusterNetworkSettings,
        ClusterNetworkSettingsCreateRequest,
        ClusterNetworkSettingsUpdateRequest,
        NodeInterfaceMapping,
        NodeInterfaceMappingCreateRequest,
        SdiSource,
        SdiSourceMapping,
        SdiSourceMappingUpdateRequest,
        SdiSourceSummary,
    )
    from awslabs.amazon_medialive_mcp_server.models.input import (
        Input,
        InputChannelLevel,
        InputDestination,
        InputDestinationRequest,
        InputDeviceConfigurableSettings,
        InputDeviceHdSettings,
        InputDeviceNetworkSettings,
        InputDeviceRequest,
        InputDeviceSettings,
        InputDeviceSummary,
        InputDeviceUhdSettings,
        InputLocation,
        InputSecurityGroup,
        InputSource,
        InputSourceRequest,
        InputVpcRequest,
        InputWhitelistRule,
        InputWhitelistRuleCidr,
        MulticastSettings,
        MulticastSettingsCreateRequest,
        MulticastSettingsUpdateRequest,
        Smpte2110ReceiverGroupSettings,
        SrtSettings,
        SrtSettingsRequest,
    )
    from awslabs.amazon_medialive_mcp_server.models.monitoring import (
        CloudWatchAlarmTemplateGroupSummary,
        CloudWatchAlarmTemplateSummary,
        EventBridgeRuleTemplateGroupSummary,
        EventBridgeRuleTemplateSummary,
        EventBridgeRuleTemplateTarget,
        NielsenWatermarksSettings,
        Offering,
        Reservation,
        ReservationResourceSpecification,
        SignalMapSummary,
    )
    from awslabs.amazon_medialive_mcp_server.models.multiplex import (
        Multiplex,
        MultiplexOutputDestination,
        MultiplexProgram,
        MultiplexProgramPacketIdentifiersMap,
        MultiplexProgramPipelineDetail,
        MultiplexProgramSettings,
        MultiplexProgramSummary,
        MultiplexSettings,
        MultiplexSummary,
    )
    from awslabs.amazon_medialive_mcp_server.models.output import (
        M3u8Settings,
        OutputLocationRef,
        RtmpCaptionInfoDestinationSettings,
    )
    from awslabs.amazon_medialive_mcp_server.models.schedule import (
        ScheduleAction,
        Scte20PlusEmbeddedDestinationSettings,
        Scte20SourceSettings,
        Scte27DestinationSettings,
        Scte27SourceSettings,
    )


class AacSettings(BaseModel):
    """Aac Settings."""

    model_config = ConfigDict(populate_by_name=True)

    bitrate: Annotated[
        Optional[float],
        Field(
            None,
            alias='Bitrate',
            description='Average bitrate in bits/second. Valid values depend on rate control mode and profile.',
        ),
    ]

    coding_mode: Annotated[
        Optional[AacCodingMode],
        Field(
            None,
            alias='CodingMode',
            description='Mono, Stereo, or 5.1 channel layout. Valid values depend on rate control mode and profile. The adReceiverMix setting receives a stereo description plus control track and emits a mono AAC encode of the description track, with control data emitted in the PES header as per ETSI TS 101 154 Annex E.',
        ),
    ]

    input_type: Annotated[
        Optional[AacInputType],
        Field(
            None,
            alias='InputType',
            description='Set to "broadcasterMixedAd" when input contains pre-mixed main audio + AD (narration) as a stereo pair. The Audio Type field (audioType) will be set to 3, which signals to downstream systems that this stream contains "broadcaster mixed AD". Note that the input received by the encoder must contain pre-mixed audio; the encoder does not perform the mixing. The values in audioTypeControl and audioType (in AudioDescription) are ignored when set to broadcasterMixedAd. Leave set to "normal" when input does not contain pre-mixed audio + AD.',
        ),
    ]

    profile: Annotated[
        Optional[AacProfile],
        Field(
            None,
            alias='Profile',
            description='AAC Profile.',
        ),
    ]

    rate_control_mode: Annotated[
        Optional[AacRateControlMode],
        Field(
            None,
            alias='RateControlMode',
            description='Rate Control Mode.',
        ),
    ]

    raw_format: Annotated[
        Optional[AacRawFormat],
        Field(
            None,
            alias='RawFormat',
            description='Sets LATM / LOAS AAC output for raw containers.',
        ),
    ]

    sample_rate: Annotated[
        Optional[float],
        Field(
            None,
            alias='SampleRate',
            description='Sample rate in Hz. Valid values depend on rate control mode and profile.',
        ),
    ]

    spec: Annotated[
        Optional[AacSpec],
        Field(
            None,
            alias='Spec',
            description='Use MPEG-2 AAC audio instead of MPEG-4 AAC audio for raw or MPEG-2 Transport Stream containers.',
        ),
    ]

    vbr_quality: Annotated[
        Optional[AacVbrQuality],
        Field(
            None,
            alias='VbrQuality',
            description='VBR Quality Level - Only used if rateControlMode is VBR.',
        ),
    ]


class Ac3Settings(BaseModel):
    """Ac3 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    bitrate: Annotated[
        Optional[float],
        Field(
            None,
            alias='Bitrate',
            description='Average bitrate in bits/second. Valid bitrates depend on the coding mode.',
        ),
    ]

    bitstream_mode: Annotated[
        Optional[Ac3BitstreamMode],
        Field(
            None,
            alias='BitstreamMode',
            description='Specifies the bitstream mode (bsmod) for the emitted AC-3 stream. See ATSC A/52-2012 for background on these values.',
        ),
    ]

    coding_mode: Annotated[
        Optional[Ac3CodingMode],
        Field(
            None,
            alias='CodingMode',
            description='Dolby Digital coding mode. Determines number of channels.',
        ),
    ]

    dialnorm: Annotated[
        Optional[int],
        Field(
            None,
            alias='Dialnorm',
            description='Sets the dialnorm for the output. If excluded and input audio is Dolby Digital, dialnorm will be passed through.',
        ),
    ]

    drc_profile: Annotated[
        Optional[Ac3DrcProfile],
        Field(
            None,
            alias='DrcProfile',
            description='If set to filmStandard, adds dynamic range compression signaling to the output bitstream as defined in the Dolby Digital specification.',
        ),
    ]

    lfe_filter: Annotated[
        Optional[Ac3LfeFilter],
        Field(
            None,
            alias='LfeFilter',
            description='When set to enabled, applies a 120Hz lowpass filter to the LFE channel prior to encoding. Only valid in codingMode32Lfe mode.',
        ),
    ]

    metadata_control: Annotated[
        Optional[Ac3MetadataControl],
        Field(
            None,
            alias='MetadataControl',
            description='When set to "followInput", encoder metadata will be sourced from the DD, DD+, or DolbyE decoder that supplied this audio data. If audio was not supplied from one of these streams, then the static metadata settings will be used.',
        ),
    ]

    attenuation_control: Annotated[
        Optional[Ac3AttenuationControl],
        Field(
            None,
            alias='AttenuationControl',
            description='Applies a 3 dB attenuation to the surround channels. Applies only when the coding mode parameter is CODING_MODE_3_2_LFE.',
        ),
    ]


class AccessDenied(BaseModel):
    """Placeholder documentation for AccessDenied."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class AncillarySourceSettings(BaseModel):
    """Ancillary Source Settings."""

    model_config = ConfigDict(populate_by_name=True)

    source_ancillary_channel_number: Annotated[
        Optional[int],
        Field(
            None,
            alias='SourceAncillaryChannelNumber',
            description='Specifies the number (1 to 4) of the captions channel you want to extract from the ancillary captions. If you plan to convert the ancillary captions to another format, complete this field. If you plan to choose Embedded as the captions destination in the output (to pass through all the channels in the ancillary captions), leave this field blank because MediaLive ignores the field.',
        ),
    ]


class AribDestinationSettings(BaseModel):
    """Arib Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)


class AribSourceSettings(BaseModel):
    """Arib Source Settings."""

    model_config = ConfigDict(populate_by_name=True)


class AudioDolbyEDecode(BaseModel):
    """Audio Dolby EDecode."""

    model_config = ConfigDict(populate_by_name=True)

    program_selection: Annotated[
        DolbyEProgramSelection,
        Field(
            ...,
            alias='ProgramSelection',
            description='Applies only to Dolby E. Enter the program ID (according to the metadata in the audio) of the Dolby E program to extract from the specified track. One program extracted per audio selector. To select multiple programs, create multiple selectors with the same Track and different Program numbers. \u201cAll channels\u201d means to ignore the program IDs and include all the channels in this selector; useful if metadata is known to be incorrect.',
        ),
    ]


class AudioHlsRenditionSelection(BaseModel):
    """Audio Hls Rendition Selection."""

    model_config = ConfigDict(populate_by_name=True)

    group_id: Annotated[
        str,
        Field(
            ...,
            alias='GroupId',
            description='Specifies the GROUP-ID in the #EXT-X-MEDIA tag of the target HLS audio rendition.',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='Specifies the NAME in the #EXT-X-MEDIA tag of the target HLS audio rendition.',
        ),
    ]


class AudioLanguageSelection(BaseModel):
    """Audio Language Selection."""

    model_config = ConfigDict(populate_by_name=True)

    language_code: Annotated[
        str,
        Field(
            ...,
            alias='LanguageCode',
            description='Selects a specific three-letter language code from within an audio source.',
        ),
    ]

    language_selection_policy: Annotated[
        Optional[AudioLanguageSelectionPolicy],
        Field(
            None,
            alias='LanguageSelectionPolicy',
            description='When set to "strict", the transport stream demux strictly identifies audio streams by their language descriptor. If a PMT update occurs such that an audio stream matching the initially selected language is no longer present then mute will be encoded until the language returns. If "loose", then on a PMT update the demux will choose another audio stream in the program with the same stream type if it can\u0027t find one with the same language.',
        ),
    ]


class AudioNormalizationSettings(BaseModel):
    """Audio Normalization Settings."""

    model_config = ConfigDict(populate_by_name=True)

    algorithm: Annotated[
        Optional[AudioNormalizationAlgorithm],
        Field(
            None,
            alias='Algorithm',
            description='Audio normalization algorithm to use. itu17701 conforms to the CALM Act specification, itu17702 conforms to the EBU R-128 specification.',
        ),
    ]

    algorithm_control: Annotated[
        Optional[AudioNormalizationAlgorithmControl],
        Field(
            None,
            alias='AlgorithmControl',
            description='When set to correctAudio the output audio is corrected using the chosen algorithm. If set to measureOnly, the audio will be measured but not adjusted.',
        ),
    ]

    target_lkfs: Annotated[
        Optional[float],
        Field(
            None,
            alias='TargetLkfs',
            description='Target LKFS(loudness) to adjust volume to. If no value is entered, a default value will be used according to the chosen algorithm. The CALM Act (1770-1) recommends a target of -24 LKFS. The EBU R-128 specification (1770-2) recommends a target of -23 LKFS.',
        ),
    ]


class AudioPidSelection(BaseModel):
    """Audio Pid Selection."""

    model_config = ConfigDict(populate_by_name=True)

    pid: Annotated[
        int,
        Field(
            ...,
            alias='Pid',
            description='Selects a specific PID from within a source.',
        ),
    ]


class AudioTrack(BaseModel):
    """Audio Track."""

    model_config = ConfigDict(populate_by_name=True)

    track: Annotated[
        int,
        Field(
            ...,
            alias='Track',
            description='1-based integer value that maps to a specific audio track',
        ),
    ]


class AudioTrackSelection(BaseModel):
    """Audio Track Selection."""

    model_config = ConfigDict(populate_by_name=True)

    tracks: Annotated[
        list[AudioTrack],
        Field(
            ...,
            alias='Tracks',
            description='Selects one or more unique audio tracks from within a source.',
        ),
    ]

    dolby_e_decode: Annotated[
        Optional[AudioDolbyEDecode],
        Field(
            None,
            alias='DolbyEDecode',
            description='Configure decoding options for Dolby E streams - these should be Dolby E frames carried in PCM streams tagged with SMPTE-337',
        ),
    ]


class AudioSelectorSettings(BaseModel):
    """Audio Selector Settings."""

    model_config = ConfigDict(populate_by_name=True)

    audio_hls_rendition_selection: Annotated[
        Optional[AudioHlsRenditionSelection],
        Field(
            None,
            alias='AudioHlsRenditionSelection',
            description='',
        ),
    ]

    audio_language_selection: Annotated[
        Optional[AudioLanguageSelection],
        Field(
            None,
            alias='AudioLanguageSelection',
            description='',
        ),
    ]

    audio_pid_selection: Annotated[
        Optional[AudioPidSelection],
        Field(
            None,
            alias='AudioPidSelection',
            description='',
        ),
    ]

    audio_track_selection: Annotated[
        Optional[AudioTrackSelection],
        Field(
            None,
            alias='AudioTrackSelection',
            description='',
        ),
    ]


class AudioSelector(BaseModel):
    """Audio Selector."""

    model_config = ConfigDict(populate_by_name=True)

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='The name of this AudioSelector. AudioDescriptions will use this name to uniquely identify this Selector. Selector names should be unique per input.',
        ),
    ]

    selector_settings: Annotated[
        Optional[AudioSelectorSettings],
        Field(
            None,
            alias='SelectorSettings',
            description='The audio selector settings.',
        ),
    ]


class BadGatewayException(BaseModel):
    """Placeholder documentation for BadGatewayException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class BadRequestException(BaseModel):
    """Placeholder documentation for BadRequestException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class BadRequestExceptionResponseContent(BaseModel):
    """The input fails to satisfy the constraints specified by an AWS service."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='Exception error message.',
        ),
    ]


class BatchFailedResultModel(BaseModel):
    """Details from a failed operation."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='ARN of the resource',
        ),
    ]

    code: Annotated[
        Optional[str],
        Field(
            None,
            alias='Code',
            description='Error code for the failed operation',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='ID of the resource',
        ),
    ]

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='Error message for the failed operation',
        ),
    ]


class BatchScheduleActionDeleteRequest(BaseModel):
    """A list of schedule actions to delete."""

    model_config = ConfigDict(populate_by_name=True)

    action_names: Annotated[
        list[str],
        Field(
            ...,
            alias='ActionNames',
            description='A list of schedule actions to delete.',
        ),
    ]


class BatchSuccessfulResultModel(BaseModel):
    """Details from a successful operation."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='ARN of the resource',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='ID of the resource',
        ),
    ]

    state: Annotated[
        Optional[str],
        Field(
            None,
            alias='State',
            description='Current state of the resource',
        ),
    ]


class CaptionLanguageMapping(BaseModel):
    """Maps a caption channel to an ISO 693-2 language code (http://www.loc.gov/standards/iso639-2), with an optional description."""

    model_config = ConfigDict(populate_by_name=True)

    caption_channel: Annotated[
        int,
        Field(
            ...,
            alias='CaptionChannel',
            description='The closed caption channel being described by this CaptionLanguageMapping. Each channel mapping must have a unique channel number (maximum of 4)',
        ),
    ]

    language_code: Annotated[
        str,
        Field(
            ...,
            alias='LanguageCode',
            description='Three character ISO 639-2 language code (see http://www.loc.gov/standards/iso639-2)',
        ),
    ]

    language_description: Annotated[
        str,
        Field(
            ...,
            alias='LanguageDescription',
            description='Textual description of language',
        ),
    ]


class CaptionRectangle(BaseModel):
    """Caption Rectangle."""

    model_config = ConfigDict(populate_by_name=True)

    height: Annotated[
        float,
        Field(
            ...,
            alias='Height',
            description='See the description in leftOffset. For height, specify the entire height of the rectangle as a percentage of the underlying frame height. For example, \\"80\\" means the rectangle height is 80% of the underlying frame height. The topOffset and rectangleHeight must add up to 100% or less. This field corresponds to tts:extent - Y in the TTML standard.',
        ),
    ]

    left_offset: Annotated[
        float,
        Field(
            ...,
            alias='LeftOffset',
            description='Applies only if you plan to convert these source captions to EBU-TT-D or TTML in an output. (Make sure to leave the default if you don\u0027t have either of these formats in the output.) You can define a display rectangle for the captions that is smaller than the underlying video frame. You define the rectangle by specifying the position of the left edge, top edge, bottom edge, and right edge of the rectangle, all within the underlying video frame. The units for the measurements are percentages. If you specify a value for one of these fields, you must specify a value for all of them. For leftOffset, specify the position of the left edge of the rectangle, as a percentage of the underlying frame width, and relative to the left edge of the frame. For example, \\"10\\" means the measurement is 10% of the underlying frame width. The rectangle left edge starts at that position from the left edge of the frame. This field corresponds to tts:origin - X in the TTML standard.',
        ),
    ]

    top_offset: Annotated[
        float,
        Field(
            ...,
            alias='TopOffset',
            description='See the description in leftOffset. For topOffset, specify the position of the top edge of the rectangle, as a percentage of the underlying frame height, and relative to the top edge of the frame. For example, \\"10\\" means the measurement is 10% of the underlying frame height. The rectangle top edge starts at that position from the top edge of the frame. This field corresponds to tts:origin - Y in the TTML standard.',
        ),
    ]

    width: Annotated[
        float,
        Field(
            ...,
            alias='Width',
            description='See the description in leftOffset. For width, specify the entire width of the rectangle as a percentage of the underlying frame width. For example, \\"80\\" means the rectangle width is 80% of the underlying frame width. The leftOffset and rectangleWidth must add up to 100% or less. This field corresponds to tts:extent - X in the TTML standard.',
        ),
    ]


class CdiInputSpecification(BaseModel):
    """Placeholder documentation for CdiInputSpecification."""

    model_config = ConfigDict(populate_by_name=True)

    resolution: Annotated[
        Optional[CdiInputResolution],
        Field(
            None,
            alias='Resolution',
            description='Maximum CDI input resolution',
        ),
    ]


class ConflictException(BaseModel):
    """Placeholder documentation for ConflictException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class ConflictExceptionResponseContent(BaseModel):
    """Updating or deleting a resource can cause an inconsistent state."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='Exception error message.',
        ),
    ]


class CreateCloudWatchAlarmTemplateGroupRequest(BaseModel):
    """Placeholder documentation for CreateCloudWatchAlarmTemplateGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateCloudWatchAlarmTemplateGroupRequestContent(BaseModel):
    """Placeholder documentation for CreateCloudWatchAlarmTemplateGroupRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateCloudWatchAlarmTemplateGroupResponse(BaseModel):
    """Placeholder documentation for CreateCloudWatchAlarmTemplateGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A cloudwatch alarm template group\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class CreateCloudWatchAlarmTemplateGroupResponseContent(BaseModel):
    """Placeholder documentation for CreateCloudWatchAlarmTemplateGroupResponseContent."""

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


class CreateCloudWatchAlarmTemplateRequest(BaseModel):
    """Placeholder documentation for CreateCloudWatchAlarmTemplateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    comparison_operator: Annotated[
        CloudWatchAlarmTemplateComparisonOperator,
        Field(
            ...,
            alias='ComparisonOperator',
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

    group_identifier: Annotated[
        str,
        Field(
            ...,
            alias='GroupIdentifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateCloudWatchAlarmTemplateRequestContent(BaseModel):
    """Placeholder documentation for CreateCloudWatchAlarmTemplateRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    comparison_operator: Annotated[
        CloudWatchAlarmTemplateComparisonOperator,
        Field(
            ...,
            alias='ComparisonOperator',
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

    group_identifier: Annotated[
        str,
        Field(
            ...,
            alias='GroupIdentifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateCloudWatchAlarmTemplateResponse(BaseModel):
    """Placeholder documentation for CreateCloudWatchAlarmTemplateResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A cloudwatch alarm template\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    comparison_operator: Annotated[
        Optional[CloudWatchAlarmTemplateComparisonOperator],
        Field(
            None,
            alias='ComparisonOperator',
            description='',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[int],
        Field(
            None,
            alias='EvaluationPeriods',
            description='The number of periods over which data is compared to the specified threshold.',
        ),
    ]

    group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupId',
            description='A cloudwatch alarm template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='A cloudwatch alarm template\u0027s id. AWS provided templates have ids that start with `aws-`',
        ),
    ]

    metric_name: Annotated[
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    period: Annotated[
        Optional[int],
        Field(
            None,
            alias='Period',
            description='The period, in seconds, over which the specified statistic is applied.',
        ),
    ]

    statistic: Annotated[
        Optional[CloudWatchAlarmTemplateStatistic],
        Field(
            None,
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
        Optional[CloudWatchAlarmTemplateTargetResourceType],
        Field(
            None,
            alias='TargetResourceType',
            description='',
        ),
    ]

    threshold: Annotated[
        Optional[float],
        Field(
            None,
            alias='Threshold',
            description='The threshold value to compare with the specified statistic.',
        ),
    ]

    treat_missing_data: Annotated[
        Optional[CloudWatchAlarmTemplateTreatMissingData],
        Field(
            None,
            alias='TreatMissingData',
            description='',
        ),
    ]


class CreateCloudWatchAlarmTemplateResponseContent(BaseModel):
    """Placeholder documentation for CreateCloudWatchAlarmTemplateResponseContent."""

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


class CreateEventBridgeRuleTemplateGroupRequest(BaseModel):
    """Placeholder documentation for CreateEventBridgeRuleTemplateGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateEventBridgeRuleTemplateGroupRequestContent(BaseModel):
    """Placeholder documentation for CreateEventBridgeRuleTemplateGroupRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateEventBridgeRuleTemplateGroupResponse(BaseModel):
    """Placeholder documentation for CreateEventBridgeRuleTemplateGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='An eventbridge rule template group\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class CreateEventBridgeRuleTemplateGroupResponseContent(BaseModel):
    """Placeholder documentation for CreateEventBridgeRuleTemplateGroupResponseContent."""

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


class CreateNodeRegistrationScriptResponse(BaseModel):
    """Placeholder documentation for CreateNodeRegistrationScriptResponse."""

    model_config = ConfigDict(populate_by_name=True)

    node_registration_script: Annotated[
        Optional[str],
        Field(
            None,
            alias='NodeRegistrationScript',
            description='A script that can be run on a Bring Your Own Device Elemental Anywhere system to create a node in a cluster.',
        ),
    ]


class CreateNodeRegistrationScriptResult(BaseModel):
    """Contains the response for CreateNodeRegistrationScript."""

    model_config = ConfigDict(populate_by_name=True)

    node_registration_script: Annotated[
        Optional[str],
        Field(
            None,
            alias='NodeRegistrationScript',
            description='A script that can be run on a Bring Your Own Device Elemental Anywhere system to create a node in a cluster.',
        ),
    ]


class CreatePartnerInput(BaseModel):
    """Placeholder documentation for CreatePartnerInput."""

    model_config = ConfigDict(populate_by_name=True)

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='Unique identifier of the request to ensure the request is handled exactly once in case of retries.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class CreatePartnerInputRequest(BaseModel):
    """A request to create a partner input."""

    model_config = ConfigDict(populate_by_name=True)

    input_id: Annotated[
        str,
        Field(
            ...,
            alias='InputId',
            description='Unique ID of the input.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='Unique identifier of the request to ensure the request is handled exactly once in case of retries.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class CreateSdiSourceRequest(BaseModel):
    """A request to create a SdiSource."""

    model_config = ConfigDict(populate_by_name=True)

    mode: Annotated[
        Optional[SdiSourceMode],
        Field(
            None,
            alias='Mode',
            description='Applies only if the type is QUAD. Specify the mode for handling the quad-link signal: QUADRANT or INTERLEAVE.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Specify a name that is unique in the AWS account. We recommend you assign a name that describes the source, for example curling-cameraA. Names are case-sensitive.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    type: Annotated[
        Optional[SdiSourceType],
        Field(
            None,
            alias='Type',
            description='Specify the type of the SDI source: SINGLE: The source is a single-link source. QUAD: The source is one part of a quad-link source.',
        ),
    ]


class CreateSignalMapRequest(BaseModel):
    """Placeholder documentation for CreateSignalMapRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_template_group_identifiers: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIdentifiers',
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

    discovery_entry_point_arn: Annotated[
        str,
        Field(
            ...,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    event_bridge_rule_template_group_identifiers: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIdentifiers',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateSignalMapRequestContent(BaseModel):
    """Placeholder documentation for CreateSignalMapRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_template_group_identifiers: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIdentifiers',
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

    discovery_entry_point_arn: Annotated[
        str,
        Field(
            ...,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    event_bridge_rule_template_group_identifiers: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIdentifiers',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateTagsRequest(BaseModel):
    """Placeholder documentation for CreateTagsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    resource_arn: Annotated[
        str,
        Field(
            ...,
            alias='ResourceArn',
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


class DeleteCloudWatchAlarmTemplateGroupRequest(BaseModel):
    """Placeholder documentation for DeleteCloudWatchAlarmTemplateGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class DeleteCloudWatchAlarmTemplateRequest(BaseModel):
    """Placeholder documentation for DeleteCloudWatchAlarmTemplateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A cloudwatch alarm template\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class DeleteClusterRequest(BaseModel):
    """Placeholder documentation for DeleteClusterRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster.',
        ),
    ]


class DeleteEventBridgeRuleTemplateGroupRequest(BaseModel):
    """Placeholder documentation for DeleteEventBridgeRuleTemplateGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class DeleteEventBridgeRuleTemplateRequest(BaseModel):
    """Placeholder documentation for DeleteEventBridgeRuleTemplateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='An eventbridge rule template\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class DeleteInputRequest(BaseModel):
    """Placeholder documentation for DeleteInputRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_id: Annotated[
        str,
        Field(
            ...,
            alias='InputId',
            description='Unique ID of the input',
        ),
    ]


class DeleteInputResponse(BaseModel):
    """Placeholder documentation for DeleteInputResponse."""

    model_config = ConfigDict(populate_by_name=True)


class DeleteInputSecurityGroupRequest(BaseModel):
    """Placeholder documentation for DeleteInputSecurityGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_security_group_id: Annotated[
        str,
        Field(
            ...,
            alias='InputSecurityGroupId',
            description='The Input Security Group to delete',
        ),
    ]


class DeleteInputSecurityGroupResponse(BaseModel):
    """Placeholder documentation for DeleteInputSecurityGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)


class DeleteMultiplexProgramRequest(BaseModel):
    """Placeholder documentation for DeleteMultiplexProgramRequest."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='The ID of the multiplex that the program belongs to.',
        ),
    ]

    program_name: Annotated[
        str,
        Field(
            ...,
            alias='ProgramName',
            description='The multiplex program name.',
        ),
    ]


class DeleteMultiplexRequest(BaseModel):
    """Placeholder documentation for DeleteMultiplexRequest."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='The ID of the multiplex.',
        ),
    ]


class DeleteNetworkRequest(BaseModel):
    """Placeholder documentation for DeleteNetworkRequest."""

    model_config = ConfigDict(populate_by_name=True)

    network_id: Annotated[
        str,
        Field(
            ...,
            alias='NetworkId',
            description='The ID of the network.',
        ),
    ]


class DeleteNodeRequest(BaseModel):
    """Placeholder documentation for DeleteNodeRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster',
        ),
    ]

    node_id: Annotated[
        str,
        Field(
            ...,
            alias='NodeId',
            description='The ID of the node.',
        ),
    ]


class DeleteReservationRequest(BaseModel):
    """Placeholder documentation for DeleteReservationRequest."""

    model_config = ConfigDict(populate_by_name=True)

    reservation_id: Annotated[
        str,
        Field(
            ...,
            alias='ReservationId',
            description='Unique reservation ID, e.g. \u00271234567\u0027',
        ),
    ]


class DeleteScheduleRequest(BaseModel):
    """Placeholder documentation for DeleteScheduleRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='Id of the channel whose schedule is being deleted.',
        ),
    ]


class DeleteScheduleResponse(BaseModel):
    """Placeholder documentation for DeleteScheduleResponse."""

    model_config = ConfigDict(populate_by_name=True)


class DeleteSdiSourceRequest(BaseModel):
    """Placeholder documentation for DeleteSdiSourceRequest."""

    model_config = ConfigDict(populate_by_name=True)

    sdi_source_id: Annotated[
        str,
        Field(
            ...,
            alias='SdiSourceId',
            description='The ID of the SdiSource.',
        ),
    ]


class DeleteSignalMapRequest(BaseModel):
    """Placeholder documentation for DeleteSignalMapRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class DeleteTagsRequest(BaseModel):
    """Placeholder documentation for DeleteTagsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    resource_arn: Annotated[
        str,
        Field(
            ...,
            alias='ResourceArn',
            description='',
        ),
    ]

    tag_keys: Annotated[
        list[str],
        Field(
            ...,
            alias='TagKeys',
            description='An array of tag keys to delete',
        ),
    ]


class DescribeAnywhereSettings(BaseModel):
    """Elemental anywhere settings."""

    model_config = ConfigDict(populate_by_name=True)

    channel_placement_group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelPlacementGroupId',
            description='The ID of the channel placement group for the channel.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the cluster for the channel.',
        ),
    ]


class DescribeClusterRequest(BaseModel):
    """Placeholder documentation for DescribeClusterRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster.',
        ),
    ]


class DescribeInputDeviceRequest(BaseModel):
    """Placeholder documentation for DescribeInputDeviceRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of this input device. For example, hd-123456789abcdef.',
        ),
    ]


class DescribeInputDeviceThumbnailRequest(BaseModel):
    """Placeholder documentation for DescribeInputDeviceThumbnailRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of this input device. For example, hd-123456789abcdef.',
        ),
    ]

    accept: Annotated[
        AcceptHeader,
        Field(
            ...,
            alias='Accept',
            description='The HTTP Accept header. Indicates the requested type for the thumbnail.',
        ),
    ]


class DescribeInputDeviceThumbnailResponse(BaseModel):
    """Placeholder documentation for DescribeInputDeviceThumbnailResponse."""

    model_config = ConfigDict(populate_by_name=True)

    body: Annotated[
        Optional[bytes],
        Field(
            None,
            alias='Body',
            description='The binary data for the thumbnail that the Link device has most recently sent to MediaLive.',
        ),
    ]

    content_type: Annotated[
        Optional[ContentType],
        Field(
            None,
            alias='ContentType',
            description='Specifies the media type of the thumbnail.',
        ),
    ]

    content_length: Annotated[
        Optional[int],
        Field(
            None,
            alias='ContentLength',
            description='The length of the content.',
        ),
    ]

    e_tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='ETag',
            description='The unique, cacheable version of this thumbnail.',
        ),
    ]

    last_modified: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastModified',
            description='The date and time the thumbnail was last updated at the device.',
        ),
    ]


class DescribeInputRequest(BaseModel):
    """Placeholder documentation for DescribeInputRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_id: Annotated[
        str,
        Field(
            ...,
            alias='InputId',
            description='Unique ID of the input',
        ),
    ]


class DescribeInputSecurityGroupRequest(BaseModel):
    """Placeholder documentation for DescribeInputSecurityGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_security_group_id: Annotated[
        str,
        Field(
            ...,
            alias='InputSecurityGroupId',
            description='The id of the Input Security Group to describe',
        ),
    ]


class DescribeMultiplexProgramRequest(BaseModel):
    """Placeholder documentation for DescribeMultiplexProgramRequest."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='The ID of the multiplex that the program belongs to.',
        ),
    ]

    program_name: Annotated[
        str,
        Field(
            ...,
            alias='ProgramName',
            description='The name of the program.',
        ),
    ]


class DescribeMultiplexRequest(BaseModel):
    """Placeholder documentation for DescribeMultiplexRequest."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='The ID of the multiplex.',
        ),
    ]


class DescribeNetworkRequest(BaseModel):
    """Placeholder documentation for DescribeNetworkRequest."""

    model_config = ConfigDict(populate_by_name=True)

    network_id: Annotated[
        str,
        Field(
            ...,
            alias='NetworkId',
            description='The ID of the network.',
        ),
    ]


class DescribeNodeRequest(BaseModel):
    """Placeholder documentation for DescribeNodeRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster',
        ),
    ]

    node_id: Annotated[
        str,
        Field(
            ...,
            alias='NodeId',
            description='The ID of the node.',
        ),
    ]


class DescribeOfferingRequest(BaseModel):
    """Placeholder documentation for DescribeOfferingRequest."""

    model_config = ConfigDict(populate_by_name=True)

    offering_id: Annotated[
        str,
        Field(
            ...,
            alias='OfferingId',
            description='Unique offering ID, e.g. \u002787654321\u0027',
        ),
    ]


class DescribeReservationRequest(BaseModel):
    """Placeholder documentation for DescribeReservationRequest."""

    model_config = ConfigDict(populate_by_name=True)

    reservation_id: Annotated[
        str,
        Field(
            ...,
            alias='ReservationId',
            description='Unique reservation ID, e.g. \u00271234567\u0027',
        ),
    ]


class DescribeScheduleRequest(BaseModel):
    """Placeholder documentation for DescribeScheduleRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='Id of the channel whose schedule is being updated.',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class DescribeSdiSourceRequest(BaseModel):
    """Placeholder documentation for DescribeSdiSourceRequest."""

    model_config = ConfigDict(populate_by_name=True)

    sdi_source_id: Annotated[
        str,
        Field(
            ...,
            alias='SdiSourceId',
            description='Get details about an SdiSource.',
        ),
    ]


class DescribeThumbnailsRequest(BaseModel):
    """Placeholder documentation for DescribeThumbnailsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        str,
        Field(
            ...,
            alias='ChannelId',
            description='Unique ID of the channel',
        ),
    ]

    pipeline_id: Annotated[
        str,
        Field(
            ...,
            alias='PipelineId',
            description='Pipeline ID ("0" or "1")',
        ),
    ]

    thumbnail_type: Annotated[
        str,
        Field(
            ...,
            alias='ThumbnailType',
            description='thumbnail type',
        ),
    ]


class DvbNitSettings(BaseModel):
    """DVB Network Information Table (NIT)."""

    model_config = ConfigDict(populate_by_name=True)

    network_id: Annotated[
        int,
        Field(
            ...,
            alias='NetworkId',
            description='The numeric value placed in the Network Information Table (NIT).',
        ),
    ]

    network_name: Annotated[
        str,
        Field(
            ...,
            alias='NetworkName',
            description='The network name text placed in the networkNameDescriptor inside the Network Information Table. Maximum length is 256 characters.',
        ),
    ]

    rep_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='RepInterval',
            description='The number of milliseconds between instances of this table in the output transport stream.',
        ),
    ]


class DvbSdtSettings(BaseModel):
    """DVB Service Description Table (SDT)."""

    model_config = ConfigDict(populate_by_name=True)

    output_sdt: Annotated[
        Optional[DvbSdtOutputSdt],
        Field(
            None,
            alias='OutputSdt',
            description='Selects method of inserting SDT information into output stream. The sdtFollow setting copies SDT information from input stream to output stream. The sdtFollowIfPresent setting copies SDT information from input stream to output stream if SDT information is present in the input, otherwise it will fall back on the user-defined values. The sdtManual setting means user will enter the SDT information. The sdtNone setting means output stream will not contain SDT information.',
        ),
    ]

    rep_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='RepInterval',
            description='The number of milliseconds between instances of this table in the output transport stream.',
        ),
    ]

    service_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ServiceName',
            description='The service name placed in the serviceDescriptor in the Service Description Table. Maximum length is 256 characters.',
        ),
    ]

    service_provider_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ServiceProviderName',
            description='The service provider name placed in the serviceDescriptor in the Service Description Table. Maximum length is 256 characters.',
        ),
    ]


class DvbSubSourceSettings(BaseModel):
    """Dvb Sub Source Settings."""

    model_config = ConfigDict(populate_by_name=True)

    ocr_language: Annotated[
        Optional[DvbSubOcrLanguage],
        Field(
            None,
            alias='OcrLanguage',
            description='If you will configure a WebVTT caption description that references this caption selector, use this field to provide the language to consider when translating the image-based source to text.',
        ),
    ]

    pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='Pid',
            description='When using DVB-Sub with Burn-In or SMPTE-TT, use this PID for the source content. Unused for DVB-Sub passthrough. All DVB-Sub content is passed through, regardless of selectors.',
        ),
    ]


class DvbTdtSettings(BaseModel):
    """DVB Time and Date Table (SDT)."""

    model_config = ConfigDict(populate_by_name=True)

    rep_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='RepInterval',
            description='The number of milliseconds between instances of this table in the output transport stream.',
        ),
    ]


class Eac3AtmosSettings(BaseModel):
    """Eac3 Atmos Settings."""

    model_config = ConfigDict(populate_by_name=True)

    bitrate: Annotated[
        Optional[float],
        Field(
            None,
            alias='Bitrate',
            description='Average bitrate in bits/second. Valid bitrates depend on the coding mode.',
        ),
    ]

    coding_mode: Annotated[
        Optional[Eac3AtmosCodingMode],
        Field(
            None,
            alias='CodingMode',
            description='Dolby Digital Plus with Dolby Atmos coding mode. Determines number of channels.',
        ),
    ]

    dialnorm: Annotated[
        Optional[int],
        Field(
            None,
            alias='Dialnorm',
            description='Sets the dialnorm for the output. Default 23.',
        ),
    ]

    drc_line: Annotated[
        Optional[Eac3AtmosDrcLine],
        Field(
            None,
            alias='DrcLine',
            description='Sets the Dolby dynamic range compression profile.',
        ),
    ]

    drc_rf: Annotated[
        Optional[Eac3AtmosDrcRf],
        Field(
            None,
            alias='DrcRf',
            description='Sets the profile for heavy Dolby dynamic range compression, ensures that the instantaneous signal peaks do not exceed specified levels.',
        ),
    ]

    height_trim: Annotated[
        Optional[float],
        Field(
            None,
            alias='HeightTrim',
            description='Height dimensional trim. Sets the maximum amount to attenuate the height channels when the downstream player isn??t configured to handle Dolby Digital Plus with Dolby Atmos and must remix the channels.',
        ),
    ]

    surround_trim: Annotated[
        Optional[float],
        Field(
            None,
            alias='SurroundTrim',
            description='Surround dimensional trim. Sets the maximum amount to attenuate the surround channels when the downstream player isn\u0027t configured to handle Dolby Digital Plus with Dolby Atmos and must remix the channels.',
        ),
    ]


class Eac3Settings(BaseModel):
    """Eac3 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    attenuation_control: Annotated[
        Optional[Eac3AttenuationControl],
        Field(
            None,
            alias='AttenuationControl',
            description='When set to attenuate3Db, applies a 3 dB attenuation to the surround channels. Only used for 3/2 coding mode.',
        ),
    ]

    bitrate: Annotated[
        Optional[float],
        Field(
            None,
            alias='Bitrate',
            description='Average bitrate in bits/second. Valid bitrates depend on the coding mode.',
        ),
    ]

    bitstream_mode: Annotated[
        Optional[Eac3BitstreamMode],
        Field(
            None,
            alias='BitstreamMode',
            description='Specifies the bitstream mode (bsmod) for the emitted E-AC-3 stream. See ATSC A/52-2012 (Annex E) for background on these values.',
        ),
    ]

    coding_mode: Annotated[
        Optional[Eac3CodingMode],
        Field(
            None,
            alias='CodingMode',
            description='Dolby Digital Plus coding mode. Determines number of channels.',
        ),
    ]

    dc_filter: Annotated[
        Optional[Eac3DcFilter],
        Field(
            None,
            alias='DcFilter',
            description='When set to enabled, activates a DC highpass filter for all input channels.',
        ),
    ]

    dialnorm: Annotated[
        Optional[int],
        Field(
            None,
            alias='Dialnorm',
            description='Sets the dialnorm for the output. If blank and input audio is Dolby Digital Plus, dialnorm will be passed through.',
        ),
    ]

    drc_line: Annotated[
        Optional[Eac3DrcLine],
        Field(
            None,
            alias='DrcLine',
            description='Sets the Dolby dynamic range compression profile.',
        ),
    ]

    drc_rf: Annotated[
        Optional[Eac3DrcRf],
        Field(
            None,
            alias='DrcRf',
            description='Sets the profile for heavy Dolby dynamic range compression, ensures that the instantaneous signal peaks do not exceed specified levels.',
        ),
    ]

    lfe_control: Annotated[
        Optional[Eac3LfeControl],
        Field(
            None,
            alias='LfeControl',
            description='When encoding 3/2 audio, setting to lfe enables the LFE channel',
        ),
    ]

    lfe_filter: Annotated[
        Optional[Eac3LfeFilter],
        Field(
            None,
            alias='LfeFilter',
            description='When set to enabled, applies a 120Hz lowpass filter to the LFE channel prior to encoding. Only valid with codingMode32 coding mode.',
        ),
    ]

    lo_ro_center_mix_level: Annotated[
        Optional[float],
        Field(
            None,
            alias='LoRoCenterMixLevel',
            description='Left only/Right only center mix level. Only used for 3/2 coding mode.',
        ),
    ]

    lo_ro_surround_mix_level: Annotated[
        Optional[float],
        Field(
            None,
            alias='LoRoSurroundMixLevel',
            description='Left only/Right only surround mix level. Only used for 3/2 coding mode.',
        ),
    ]

    lt_rt_center_mix_level: Annotated[
        Optional[float],
        Field(
            None,
            alias='LtRtCenterMixLevel',
            description='Left total/Right total center mix level. Only used for 3/2 coding mode.',
        ),
    ]

    lt_rt_surround_mix_level: Annotated[
        Optional[float],
        Field(
            None,
            alias='LtRtSurroundMixLevel',
            description='Left total/Right total surround mix level. Only used for 3/2 coding mode.',
        ),
    ]

    metadata_control: Annotated[
        Optional[Eac3MetadataControl],
        Field(
            None,
            alias='MetadataControl',
            description='When set to followInput, encoder metadata will be sourced from the DD, DD+, or DolbyE decoder that supplied this audio data. If audio was not supplied from one of these streams, then the static metadata settings will be used.',
        ),
    ]

    passthrough_control: Annotated[
        Optional[Eac3PassthroughControl],
        Field(
            None,
            alias='PassthroughControl',
            description='When set to whenPossible, input DD+ audio will be passed through if it is present on the input. This detection is dynamic over the life of the transcode. Inputs that alternate between DD+ and non-DD+ content will have a consistent DD+ output as the system alternates between passthrough and encoding.',
        ),
    ]

    phase_control: Annotated[
        Optional[Eac3PhaseControl],
        Field(
            None,
            alias='PhaseControl',
            description='When set to shift90Degrees, applies a 90-degree phase shift to the surround channels. Only used for 3/2 coding mode.',
        ),
    ]

    stereo_downmix: Annotated[
        Optional[Eac3StereoDownmix],
        Field(
            None,
            alias='StereoDownmix',
            description='Stereo downmix preference. Only used for 3/2 coding mode.',
        ),
    ]

    surround_ex_mode: Annotated[
        Optional[Eac3SurroundExMode],
        Field(
            None,
            alias='SurroundExMode',
            description='When encoding 3/2 audio, sets whether an extra center back surround channel is matrix encoded into the left and right surround channels.',
        ),
    ]

    surround_mode: Annotated[
        Optional[Eac3SurroundMode],
        Field(
            None,
            alias='SurroundMode',
            description='When encoding 2/0 audio, sets whether Dolby Surround is matrix encoded into the two channels.',
        ),
    ]


class EbuTtDDestinationSettings(BaseModel):
    """Ebu Tt DDestination Settings."""

    model_config = ConfigDict(populate_by_name=True)

    copyright_holder: Annotated[
        Optional[str],
        Field(
            None,
            alias='CopyrightHolder',
            description='Complete this field if you want to include the name of the copyright holder in the copyright tag in the captions metadata.',
        ),
    ]

    fill_line_gap: Annotated[
        Optional[EbuTtDFillLineGapControl],
        Field(
            None,
            alias='FillLineGap',
            description='Specifies how to handle the gap between the lines (in multi-line captions). ENABLED: Fill with the captions background color (as specified in the input captions). DISABLED: Leave the gap unfilled',
        ),
    ]

    font_family: Annotated[
        Optional[str],
        Field(
            None,
            alias='FontFamily',
            description='Specifies the font family to include in the font data attached to the EBU-TT captions. Valid only if style_control is set to include. (If style_control is set to exclude, the font family is always set to monospaced.) Enter a list of font families, as a comma-separated list of font names, in order of preference. The name can be a font family (such as Arial), or a generic font family (such as serif), or default (to let the downstream player choose the font). Or leave blank to set the family to monospace. Note that you can specify only the font family. All other style information (color, bold, position and so on) is copied from the input captions. The size is always set to 100% to allow the downstream player to choose the size.',
        ),
    ]

    style_control: Annotated[
        Optional[EbuTtDDestinationStyleControl],
        Field(
            None,
            alias='StyleControl',
            description='Specifies the style information to include in the font data that is attached to the EBU-TT captions. INCLUDE: Take the style information from the source captions and include that information in the font data attached to the EBU-TT captions. This option is valid only if the source captions are Embedded or Teletext. EXCLUDE: Set the font family to monospaced. Do not include any other style information.',
        ),
    ]

    default_font_size: Annotated[
        Optional[int],
        Field(
            None,
            alias='DefaultFontSize',
            description='Specifies the default font size as a percentage of the computed cell size. Valid only if the defaultLineHeight is also set. If you leave this field empty, the default font size is 80% of the cell size.',
        ),
    ]

    default_line_height: Annotated[
        Optional[int],
        Field(
            None,
            alias='DefaultLineHeight',
            description='Documentation update needed',
        ),
    ]


class EmbeddedDestinationSettings(BaseModel):
    """Embedded Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)


class EmbeddedPlusScte20DestinationSettings(BaseModel):
    """Embedded Plus Scte20 Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)


class EmbeddedSourceSettings(BaseModel):
    """Embedded Source Settings."""

    model_config = ConfigDict(populate_by_name=True)

    convert608_to708: Annotated[
        Optional[EmbeddedConvert608To708],
        Field(
            None,
            alias='Convert608To708',
            description='If upconvert, 608 data is both passed through via the "608 compatibility bytes" fields of the 708 wrapper as well as translated into 708. 708 data present in the source content will be discarded.',
        ),
    ]

    scte20_detection: Annotated[
        Optional[EmbeddedScte20Detection],
        Field(
            None,
            alias='Scte20Detection',
            description='Set to "auto" to handle streams with intermittent and/or non-aligned SCTE-20 and Embedded captions.',
        ),
    ]

    source608_channel_number: Annotated[
        Optional[int],
        Field(
            None,
            alias='Source608ChannelNumber',
            description='Specifies the 608/708 channel number within the video track from which to extract captions. Unused for passthrough.',
        ),
    ]

    source608_track_number: Annotated[
        Optional[int],
        Field(
            None,
            alias='Source608TrackNumber',
            description='This field is unused and deprecated.',
        ),
    ]


class Empty(BaseModel):
    """Placeholder documentation for Empty."""

    model_config = ConfigDict(populate_by_name=True)


class CreateEventBridgeRuleTemplateRequest(BaseModel):
    """Placeholder documentation for CreateEventBridgeRuleTemplateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
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

    group_identifier: Annotated[
        str,
        Field(
            ...,
            alias='GroupIdentifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateEventBridgeRuleTemplateRequestContent(BaseModel):
    """Placeholder documentation for CreateEventBridgeRuleTemplateRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
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

    group_identifier: Annotated[
        str,
        Field(
            ...,
            alias='GroupIdentifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
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

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]


class CreateEventBridgeRuleTemplateResponse(BaseModel):
    """Placeholder documentation for CreateEventBridgeRuleTemplateResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='An eventbridge rule template\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
        ),
    ]

    event_type: Annotated[
        Optional[EventBridgeRuleTemplateEventType],
        Field(
            None,
            alias='EventType',
            description='',
        ),
    ]

    group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupId',
            description='An eventbridge rule template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class CreateEventBridgeRuleTemplateResponseContent(BaseModel):
    """Placeholder documentation for CreateEventBridgeRuleTemplateResponseContent."""

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

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
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


class ForbiddenException(BaseModel):
    """Placeholder documentation for ForbiddenException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class ForbiddenExceptionResponseContent(BaseModel):
    """User does not have sufficient access to perform this action."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='Exception error message.',
        ),
    ]


class GatewayTimeoutException(BaseModel):
    """Placeholder documentation for GatewayTimeoutException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class GetCloudWatchAlarmTemplateGroupRequest(BaseModel):
    """Placeholder documentation for GetCloudWatchAlarmTemplateGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class GetCloudWatchAlarmTemplateGroupResponse(BaseModel):
    """Placeholder documentation for GetCloudWatchAlarmTemplateGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A cloudwatch alarm template group\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class GetCloudWatchAlarmTemplateGroupResponseContent(BaseModel):
    """Placeholder documentation for GetCloudWatchAlarmTemplateGroupResponseContent."""

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


class GetCloudWatchAlarmTemplateRequest(BaseModel):
    """Placeholder documentation for GetCloudWatchAlarmTemplateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A cloudwatch alarm template\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class GetCloudWatchAlarmTemplateResponse(BaseModel):
    """Placeholder documentation for GetCloudWatchAlarmTemplateResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A cloudwatch alarm template\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    comparison_operator: Annotated[
        Optional[CloudWatchAlarmTemplateComparisonOperator],
        Field(
            None,
            alias='ComparisonOperator',
            description='',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[int],
        Field(
            None,
            alias='EvaluationPeriods',
            description='The number of periods over which data is compared to the specified threshold.',
        ),
    ]

    group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupId',
            description='A cloudwatch alarm template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='A cloudwatch alarm template\u0027s id. AWS provided templates have ids that start with `aws-`',
        ),
    ]

    metric_name: Annotated[
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    period: Annotated[
        Optional[int],
        Field(
            None,
            alias='Period',
            description='The period, in seconds, over which the specified statistic is applied.',
        ),
    ]

    statistic: Annotated[
        Optional[CloudWatchAlarmTemplateStatistic],
        Field(
            None,
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
        Optional[CloudWatchAlarmTemplateTargetResourceType],
        Field(
            None,
            alias='TargetResourceType',
            description='',
        ),
    ]

    threshold: Annotated[
        Optional[float],
        Field(
            None,
            alias='Threshold',
            description='The threshold value to compare with the specified statistic.',
        ),
    ]

    treat_missing_data: Annotated[
        Optional[CloudWatchAlarmTemplateTreatMissingData],
        Field(
            None,
            alias='TreatMissingData',
            description='',
        ),
    ]


class GetCloudWatchAlarmTemplateResponseContent(BaseModel):
    """Placeholder documentation for GetCloudWatchAlarmTemplateResponseContent."""

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


class GetEventBridgeRuleTemplateGroupRequest(BaseModel):
    """Placeholder documentation for GetEventBridgeRuleTemplateGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class GetEventBridgeRuleTemplateGroupResponse(BaseModel):
    """Placeholder documentation for GetEventBridgeRuleTemplateGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='An eventbridge rule template group\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class GetEventBridgeRuleTemplateGroupResponseContent(BaseModel):
    """Placeholder documentation for GetEventBridgeRuleTemplateGroupResponseContent."""

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


class GetEventBridgeRuleTemplateRequest(BaseModel):
    """Placeholder documentation for GetEventBridgeRuleTemplateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='An eventbridge rule template\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class GetEventBridgeRuleTemplateResponse(BaseModel):
    """Placeholder documentation for GetEventBridgeRuleTemplateResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='An eventbridge rule template\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
        ),
    ]

    event_type: Annotated[
        Optional[EventBridgeRuleTemplateEventType],
        Field(
            None,
            alias='EventType',
            description='',
        ),
    ]

    group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupId',
            description='An eventbridge rule template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class GetEventBridgeRuleTemplateResponseContent(BaseModel):
    """Placeholder documentation for GetEventBridgeRuleTemplateResponseContent."""

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

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
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


class GetSignalMapRequest(BaseModel):
    """Placeholder documentation for GetSignalMapRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class HtmlMotionGraphicsSettings(BaseModel):
    """Html Motion Graphics Settings."""

    model_config = ConfigDict(populate_by_name=True)


class AudioChannelMapping(BaseModel):
    """Audio Channel Mapping."""

    model_config = ConfigDict(populate_by_name=True)

    input_channel_levels: Annotated[
        list[InputChannelLevel],
        Field(
            ...,
            alias='InputChannelLevels',
            description='Indices and gain values for each input channel that should be remixed into this output channel.',
        ),
    ]

    output_channel: Annotated[
        int,
        Field(
            ...,
            alias='OutputChannel',
            description='The index of the output channel being produced.',
        ),
    ]


class DescribeInputDeviceResponse(BaseModel):
    """Placeholder documentation for DescribeInputDeviceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique ARN of the input device.',
        ),
    ]

    connection_state: Annotated[
        Optional[InputDeviceConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The state of the connection between the input device and AWS.',
        ),
    ]

    device_settings_sync_state: Annotated[
        Optional[DeviceSettingsSyncState],
        Field(
            None,
            alias='DeviceSettingsSyncState',
            description='The status of the action to synchronize the device configuration. If you change the configuration of the input device (for example, the maximum bitrate), MediaLive sends the new data to the device. The device might not update itself immediately. SYNCED means the device has updated its configuration. SYNCING means that it has not updated its configuration.',
        ),
    ]

    device_update_status: Annotated[
        Optional[DeviceUpdateStatus],
        Field(
            None,
            alias='DeviceUpdateStatus',
            description='The status of software on the input device.',
        ),
    ]

    hd_device_settings: Annotated[
        Optional[InputDeviceHdSettings],
        Field(
            None,
            alias='HdDeviceSettings',
            description='Settings that describe an input device that is type HD.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the input device.',
        ),
    ]

    mac_address: Annotated[
        Optional[str],
        Field(
            None,
            alias='MacAddress',
            description='The network MAC address of the input device.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A name that you specify for the input device.',
        ),
    ]

    network_settings: Annotated[
        Optional[InputDeviceNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='The network settings for the input device.',
        ),
    ]

    serial_number: Annotated[
        Optional[str],
        Field(
            None,
            alias='SerialNumber',
            description='The unique serial number of the input device.',
        ),
    ]

    type: Annotated[
        Optional[InputDeviceType],
        Field(
            None,
            alias='Type',
            description='The type of the input device.',
        ),
    ]

    uhd_device_settings: Annotated[
        Optional[InputDeviceUhdSettings],
        Field(
            None,
            alias='UhdDeviceSettings',
            description='Settings that describe an input device that is type UHD.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    availability_zone: Annotated[
        Optional[str],
        Field(
            None,
            alias='AvailabilityZone',
            description='The Availability Zone associated with this input device.',
        ),
    ]

    medialive_input_arns: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='MedialiveInputArns',
            description='An array of the ARNs for the MediaLive inputs attached to the device. Returned only if the outputType is MEDIALIVE_INPUT.',
        ),
    ]

    output_type: Annotated[
        Optional[InputDeviceOutputType],
        Field(
            None,
            alias='OutputType',
            description='The output attachment type of the input device. Specifies MEDIACONNECT_FLOW if this device is the source for a MediaConnect flow. Specifies MEDIALIVE_INPUT if this device is the source for a MediaLive input.',
        ),
    ]


class AudioOnlyHlsSettings(BaseModel):
    """Audio Only Hls Settings."""

    model_config = ConfigDict(populate_by_name=True)

    audio_group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='AudioGroupId',
            description='Specifies the group to which the audio Rendition belongs.',
        ),
    ]

    audio_only_image: Annotated[
        Optional[InputLocation],
        Field(
            None,
            alias='AudioOnlyImage',
            description='Optional. Specifies the .jpg or .png image to use as the cover art for an audio-only output. We recommend a low bit-size file because the image increases the output audio bandwidth. The image is attached to the audio as an ID3 tag, frame type APIC, picture type 0x10, as per the "ID3 tag version 2.4.0 - Native Frames" standard.',
        ),
    ]

    audio_track_type: Annotated[
        Optional[AudioOnlyHlsTrackType],
        Field(
            None,
            alias='AudioTrackType',
            description='Four types of audio-only tracks are supported: Audio-Only Variant Stream The client can play back this audio-only stream instead of video in low-bandwidth scenarios. Represented as an EXT-X-STREAM-INF in the HLS manifest. Alternate Audio, Auto Select, Default Alternate rendition that the client should try to play back by default. Represented as an EXT-X-MEDIA in the HLS manifest with DEFAULT=YES, AUTOSELECT=YES Alternate Audio, Auto Select, Not Default Alternate rendition that the client may try to play back by default. Represented as an EXT-X-MEDIA in the HLS manifest with DEFAULT=NO, AUTOSELECT=YES Alternate Audio, not Auto Select Alternate rendition that the client will not try to play back by default. Represented as an EXT-X-MEDIA in the HLS manifest with DEFAULT=NO, AUTOSELECT=NO',
        ),
    ]

    segment_type: Annotated[
        Optional[AudioOnlyHlsSegmentType],
        Field(
            None,
            alias='SegmentType',
            description='Specifies the segment type.',
        ),
    ]


class BurnInDestinationSettings(BaseModel):
    """Burn In Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)

    alignment: Annotated[
        Optional[BurnInAlignment],
        Field(
            None,
            alias='Alignment',
            description='If no explicit xPosition or yPosition is provided, setting alignment to centered will place the captions at the bottom center of the output. Similarly, setting a left alignment will align captions to the bottom left of the output. If x and y positions are given in conjunction with the alignment parameter, the font will be justified (either left or centered) relative to those coordinates. Selecting "smart" justification will left-justify live subtitles and center-justify pre-recorded subtitles. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    background_color: Annotated[
        Optional[BurnInBackgroundColor],
        Field(
            None,
            alias='BackgroundColor',
            description='Specifies the color of the rectangle behind the captions. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    background_opacity: Annotated[
        Optional[int],
        Field(
            None,
            alias='BackgroundOpacity',
            description='Specifies the opacity of the background rectangle. 255 is opaque; 0 is transparent. Leaving this parameter out is equivalent to setting it to 0 (transparent). All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font: Annotated[
        Optional[InputLocation],
        Field(
            None,
            alias='Font',
            description='External font file used for caption burn-in. File extension must be \u0027ttf\u0027 or \u0027tte\u0027. Although the user can select output fonts for many different types of input captions, embedded, STL and teletext sources use a strict grid system. Using external fonts with these caption sources could cause unexpected display of proportional fonts. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font_color: Annotated[
        Optional[BurnInFontColor],
        Field(
            None,
            alias='FontColor',
            description='Specifies the color of the burned-in captions. This option is not valid for source captions that are STL, 608/embedded or teletext. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font_opacity: Annotated[
        Optional[int],
        Field(
            None,
            alias='FontOpacity',
            description='Specifies the opacity of the burned-in captions. 255 is opaque; 0 is transparent. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font_resolution: Annotated[
        Optional[int],
        Field(
            None,
            alias='FontResolution',
            description='Font resolution in DPI (dots per inch); default is 96 dpi. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font_size: Annotated[
        Optional[str],
        Field(
            None,
            alias='FontSize',
            description='When set to \u0027auto\u0027 fontSize will scale depending on the size of the output. Giving a positive integer will specify the exact font size in points. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    outline_color: Annotated[
        Optional[BurnInOutlineColor],
        Field(
            None,
            alias='OutlineColor',
            description='Specifies font outline color. This option is not valid for source captions that are either 608/embedded or teletext. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    outline_size: Annotated[
        Optional[int],
        Field(
            None,
            alias='OutlineSize',
            description='Specifies font outline size in pixels. This option is not valid for source captions that are either 608/embedded or teletext. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    shadow_color: Annotated[
        Optional[BurnInShadowColor],
        Field(
            None,
            alias='ShadowColor',
            description='Specifies the color of the shadow cast by the captions. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    shadow_opacity: Annotated[
        Optional[int],
        Field(
            None,
            alias='ShadowOpacity',
            description='Specifies the opacity of the shadow. 255 is opaque; 0 is transparent. Leaving this parameter out is equivalent to setting it to 0 (transparent). All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    shadow_x_offset: Annotated[
        Optional[int],
        Field(
            None,
            alias='ShadowXOffset',
            description='Specifies the horizontal offset of the shadow relative to the captions in pixels. A value of -2 would result in a shadow offset 2 pixels to the left. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    shadow_y_offset: Annotated[
        Optional[int],
        Field(
            None,
            alias='ShadowYOffset',
            description='Specifies the vertical offset of the shadow relative to the captions in pixels. A value of -2 would result in a shadow offset 2 pixels above the text. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    teletext_grid_control: Annotated[
        Optional[BurnInTeletextGridControl],
        Field(
            None,
            alias='TeletextGridControl',
            description='Controls whether a fixed grid size will be used to generate the output subtitles bitmap. Only applicable for Teletext inputs and DVB-Sub/Burn-in outputs.',
        ),
    ]

    x_position: Annotated[
        Optional[int],
        Field(
            None,
            alias='XPosition',
            description='Specifies the horizontal position of the caption relative to the left side of the output in pixels. A value of 10 would result in the captions starting 10 pixels from the left of the output. If no explicit xPosition is provided, the horizontal caption position will be determined by the alignment parameter. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    y_position: Annotated[
        Optional[int],
        Field(
            None,
            alias='YPosition',
            description='Specifies the vertical position of the caption relative to the top of the output in pixels. A value of 10 would result in the captions starting 10 pixels from the top of the output. If no explicit yPosition is provided, the caption will be positioned towards the bottom of the output. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    subtitle_rows: Annotated[
        Optional[BurnInDestinationSubtitleRows],
        Field(
            None,
            alias='SubtitleRows',
            description='Applies only when the input captions are Teletext and the output captions are DVB-Sub or Burn-In. Choose the number of lines for the captions bitmap. The captions bitmap is 700 wide \u00d7 576 high and will be laid over the video. For example, a value of 16 divides the bitmap into 16 lines, with each line 36 pixels high (16 \u00d7 36 = 576). The default is 24 (24 pixels high). Enter the same number in every encode in every output that converts the same Teletext source to DVB-Sub or Burn-in.',
        ),
    ]


class DvbSubDestinationSettings(BaseModel):
    """Dvb Sub Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)

    alignment: Annotated[
        Optional[DvbSubDestinationAlignment],
        Field(
            None,
            alias='Alignment',
            description='If no explicit xPosition or yPosition is provided, setting alignment to centered will place the captions at the bottom center of the output. Similarly, setting a left alignment will align captions to the bottom left of the output. If x and y positions are given in conjunction with the alignment parameter, the font will be justified (either left or centered) relative to those coordinates. Selecting "smart" justification will left-justify live subtitles and center-justify pre-recorded subtitles. This option is not valid for source captions that are STL or 608/embedded. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    background_color: Annotated[
        Optional[DvbSubDestinationBackgroundColor],
        Field(
            None,
            alias='BackgroundColor',
            description='Specifies the color of the rectangle behind the captions. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    background_opacity: Annotated[
        Optional[int],
        Field(
            None,
            alias='BackgroundOpacity',
            description='Specifies the opacity of the background rectangle. 255 is opaque; 0 is transparent. Leaving this parameter blank is equivalent to setting it to 0 (transparent). All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font: Annotated[
        Optional[InputLocation],
        Field(
            None,
            alias='Font',
            description='External font file used for caption burn-in. File extension must be \u0027ttf\u0027 or \u0027tte\u0027. Although the user can select output fonts for many different types of input captions, embedded, STL and teletext sources use a strict grid system. Using external fonts with these caption sources could cause unexpected display of proportional fonts. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font_color: Annotated[
        Optional[DvbSubDestinationFontColor],
        Field(
            None,
            alias='FontColor',
            description='Specifies the color of the burned-in captions. This option is not valid for source captions that are STL, 608/embedded or teletext. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font_opacity: Annotated[
        Optional[int],
        Field(
            None,
            alias='FontOpacity',
            description='Specifies the opacity of the burned-in captions. 255 is opaque; 0 is transparent. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font_resolution: Annotated[
        Optional[int],
        Field(
            None,
            alias='FontResolution',
            description='Font resolution in DPI (dots per inch); default is 96 dpi. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    font_size: Annotated[
        Optional[str],
        Field(
            None,
            alias='FontSize',
            description='When set to auto fontSize will scale depending on the size of the output. Giving a positive integer will specify the exact font size in points. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    outline_color: Annotated[
        Optional[DvbSubDestinationOutlineColor],
        Field(
            None,
            alias='OutlineColor',
            description='Specifies font outline color. This option is not valid for source captions that are either 608/embedded or teletext. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    outline_size: Annotated[
        Optional[int],
        Field(
            None,
            alias='OutlineSize',
            description='Specifies font outline size in pixels. This option is not valid for source captions that are either 608/embedded or teletext. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    shadow_color: Annotated[
        Optional[DvbSubDestinationShadowColor],
        Field(
            None,
            alias='ShadowColor',
            description='Specifies the color of the shadow cast by the captions. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    shadow_opacity: Annotated[
        Optional[int],
        Field(
            None,
            alias='ShadowOpacity',
            description='Specifies the opacity of the shadow. 255 is opaque; 0 is transparent. Leaving this parameter blank is equivalent to setting it to 0 (transparent). All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    shadow_x_offset: Annotated[
        Optional[int],
        Field(
            None,
            alias='ShadowXOffset',
            description='Specifies the horizontal offset of the shadow relative to the captions in pixels. A value of -2 would result in a shadow offset 2 pixels to the left. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    shadow_y_offset: Annotated[
        Optional[int],
        Field(
            None,
            alias='ShadowYOffset',
            description='Specifies the vertical offset of the shadow relative to the captions in pixels. A value of -2 would result in a shadow offset 2 pixels above the text. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    teletext_grid_control: Annotated[
        Optional[DvbSubDestinationTeletextGridControl],
        Field(
            None,
            alias='TeletextGridControl',
            description='Controls whether a fixed grid size will be used to generate the output subtitles bitmap. Only applicable for Teletext inputs and DVB-Sub/Burn-in outputs.',
        ),
    ]

    x_position: Annotated[
        Optional[int],
        Field(
            None,
            alias='XPosition',
            description='Specifies the horizontal position of the caption relative to the left side of the output in pixels. A value of 10 would result in the captions starting 10 pixels from the left of the output. If no explicit xPosition is provided, the horizontal caption position will be determined by the alignment parameter. This option is not valid for source captions that are STL, 608/embedded or teletext. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    y_position: Annotated[
        Optional[int],
        Field(
            None,
            alias='YPosition',
            description='Specifies the vertical position of the caption relative to the top of the output in pixels. A value of 10 would result in the captions starting 10 pixels from the top of the output. If no explicit yPosition is provided, the caption will be positioned towards the bottom of the output. This option is not valid for source captions that are STL, 608/embedded or teletext. These source settings are already pre-defined by the caption stream. All burn-in and DVB-Sub font settings must match.',
        ),
    ]

    subtitle_rows: Annotated[
        Optional[DvbSubDestinationSubtitleRows],
        Field(
            None,
            alias='SubtitleRows',
            description='Applies only when the input captions are Teletext and the output captions are DVB-Sub or Burn-In. Choose the number of lines for the captions bitmap. The captions bitmap is 700 wide \u00d7 576 high and will be laid over the video. For example, a value of 16 divides the bitmap into 16 lines, with each line 36 pixels high (16 \u00d7 36 = 576). The default is 24 (24 pixels high). Enter the same number in every encode in every output that converts the same Teletext source to DVB-Sub or Burn-in.',
        ),
    ]


class DescribeInputSecurityGroupResponse(BaseModel):
    """Placeholder documentation for DescribeInputSecurityGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='Unique ARN of Input Security Group',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The Id of the Input Security Group',
        ),
    ]

    inputs: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='Inputs',
            description='The list of inputs currently using this Input Security Group.',
        ),
    ]

    state: Annotated[
        Optional[InputSecurityGroupState],
        Field(
            None,
            alias='State',
            description='The current state of the Input Security Group.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    whitelist_rules: Annotated[
        Optional[list[InputWhitelistRule]],
        Field(
            None,
            alias='WhitelistRules',
            description='Whitelist rules and their sync status',
        ),
    ]


class CreateInputSecurityGroupResponse(BaseModel):
    """Placeholder documentation for CreateInputSecurityGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    security_group: Annotated[
        Optional[InputSecurityGroup],
        Field(
            None,
            alias='SecurityGroup',
            description='',
        ),
    ]


class CreateInputSecurityGroupResultModel(BaseModel):
    """Placeholder documentation for CreateInputSecurityGroupResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    security_group: Annotated[
        Optional[InputSecurityGroup],
        Field(
            None,
            alias='SecurityGroup',
            description='',
        ),
    ]


class CreateInputSecurityGroupRequest(BaseModel):
    """The IPv4 CIDRs to whitelist for this Input Security Group."""

    model_config = ConfigDict(populate_by_name=True)

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    whitelist_rules: Annotated[
        Optional[list[InputWhitelistRuleCidr]],
        Field(
            None,
            alias='WhitelistRules',
            description='List of IPv4 CIDR addresses to whitelist',
        ),
    ]


class InterfaceMapping(BaseModel):
    """Used in ClusterNetworkSettings."""

    model_config = ConfigDict(populate_by_name=True)

    logical_interface_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='LogicalInterfaceName',
            description='The logical name for one interface (on every Node) that handles a specific type of traffic. We recommend that the name hints at the physical interface it applies to. For example, it could refer to the traffic that the physical interface handles. For example, my-Inputs-Interface.',
        ),
    ]

    network_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='NetworkId',
            description='The ID of the network that you want to connect to the specified logicalInterfaceName.',
        ),
    ]


class CreateClusterResponse(BaseModel):
    """Placeholder documentation for CreateClusterResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Cluster. It is automatically assigned when the Cluster is created.',
        ),
    ]

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='',
        ),
    ]

    cluster_type: Annotated[
        Optional[ClusterType],
        Field(
            None,
            alias='ClusterType',
            description='The hardware type for the Cluster',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Cluster. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceRoleArn',
            description='The ARN of the IAM role for the Node in this Cluster. Any Nodes that are associated with this Cluster assume this role. The role gives permissions to the operations that you expect these Node to perform.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Cluster.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='Network settings that connect the Nodes in the Cluster to one or more of the Networks that the Cluster is associated with.',
        ),
    ]

    state: Annotated[
        Optional[ClusterState],
        Field(
            None,
            alias='State',
            description='The current state of the Cluster.',
        ),
    ]


class DeleteClusterResponse(BaseModel):
    """Placeholder documentation for DeleteClusterResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Cluster. It is automatically assigned when the Cluster is created.',
        ),
    ]

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='',
        ),
    ]

    cluster_type: Annotated[
        Optional[ClusterType],
        Field(
            None,
            alias='ClusterType',
            description='The hardware type for the Cluster',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Cluster. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceRoleArn',
            description='The ARN of the IAM role for the Node in this Cluster. Any Nodes that are associated with this Cluster assume this role. The role gives permissions to the operations that you expect these Node to perform.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Cluster.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='Network settings that connect the Nodes in the Cluster to one or more of the Networks that the Cluster is associated with.',
        ),
    ]

    state: Annotated[
        Optional[ClusterState],
        Field(
            None,
            alias='State',
            description='The current state of the Cluster.',
        ),
    ]


class DescribeClusterResponse(BaseModel):
    """Placeholder documentation for DescribeClusterResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Cluster. It is automatically assigned when the Cluster is created.',
        ),
    ]

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='',
        ),
    ]

    cluster_type: Annotated[
        Optional[ClusterType],
        Field(
            None,
            alias='ClusterType',
            description='The hardware type for the Cluster',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Cluster. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceRoleArn',
            description='The ARN of the IAM role for the Node in this Cluster. Any Nodes that are associated with this Cluster assume this role. The role gives permissions to the operations that you expect these Node to perform.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Cluster.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='Network settings that connect the Nodes in the Cluster to one or more of the Networks that the Cluster is associated with.',
        ),
    ]

    state: Annotated[
        Optional[ClusterState],
        Field(
            None,
            alias='State',
            description='The current state of the Cluster.',
        ),
    ]


class DescribeClusterResult(BaseModel):
    """Contains the response for CreateCluster, DescribeCluster, DeleteCluster, UpdateCluster."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Cluster. It is automatically assigned when the Cluster is created.',
        ),
    ]

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='',
        ),
    ]

    cluster_type: Annotated[
        Optional[ClusterType],
        Field(
            None,
            alias='ClusterType',
            description='The hardware type for the Cluster',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Cluster. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceRoleArn',
            description='The ARN of the IAM role for the Node in this Cluster. Any Nodes that are associated with this Cluster assume this role. The role gives permissions to the operations that you expect these Node to perform.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Cluster.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='Network settings that connect the Nodes in the Cluster to one or more of the Networks that the Cluster is associated with.',
        ),
    ]

    state: Annotated[
        Optional[ClusterState],
        Field(
            None,
            alias='State',
            description='The current state of the Cluster.',
        ),
    ]


class DescribeClusterSummary(BaseModel):
    """Used in ListClustersResult."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Cluster. It is automatically assigned when the Cluster is created.',
        ),
    ]

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='An array of the IDs of the Channels that are associated with this Cluster. One Channel is associated with the Cluster as follows: A Channel belongs to a ChannelPlacementGroup. A ChannelPlacementGroup is attached to a Node. A Node belongs to a Cluster.',
        ),
    ]

    cluster_type: Annotated[
        Optional[ClusterType],
        Field(
            None,
            alias='ClusterType',
            description='The hardware type for the Cluster.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Cluster. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceRoleArn',
            description='The ARN of the IAM role for the Node in this Cluster. Any Nodes that are associated with this Cluster assume this role. The role gives permissions to the operations that you expect these Node to perform.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Cluster.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='Network settings that connect the Nodes in the Cluster to one or more of the Networks that the Cluster is associated with.',
        ),
    ]

    state: Annotated[
        Optional[ClusterState],
        Field(
            None,
            alias='State',
            description='The current state of the Cluster.',
        ),
    ]


class InterfaceMappingCreateRequest(BaseModel):
    """Used in ClusterNetworkSettingsCreateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    logical_interface_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='LogicalInterfaceName',
            description='The logical name for one interface (on every Node) that handles a specific type of traffic. We recommend that the name hints at the physical interface it applies to. For example, it could refer to the traffic that the physical interface handles. For example, my-Inputs-Interface.',
        ),
    ]

    network_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='NetworkId',
            description='The ID of the network that you want to connect to the specified logicalInterfaceName.',
        ),
    ]


class CreateClusterRequest(BaseModel):
    """Create as many Clusters as you want, but create at least one. Each Cluster groups together Nodes that you want to treat as a collection. Within the Cluster, you will set up some Nodes as active Nodes, and some as backup Nodes, for Node failover purposes. Each Node can belong to only one Cluster."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_type: Annotated[
        Optional[ClusterType],
        Field(
            None,
            alias='ClusterType',
            description='Specify a type. All the Nodes that you later add to this Cluster must be this type of hardware. One Cluster instance can\u0027t contain different hardware types. You won\u0027t be able to change this parameter after you create the Cluster.',
        ),
    ]

    instance_role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceRoleArn',
            description='The ARN of the IAM role for the Node in this Cluster. The role must include all the operations that you expect these Node to perform. If necessary, create a role in IAM, then attach it here.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Specify a name that is unique in the AWS account. We recommend that you assign a name that hints at the types of Nodes in the Cluster. Names are case-sensitive.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettingsCreateRequest],
        Field(
            None,
            alias='NetworkSettings',
            description='Network settings that connect the Nodes in the Cluster to one or more of the Networks that the Cluster is associated with.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='The unique ID of the request.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class InterfaceMappingUpdateRequest(BaseModel):
    """Placeholder documentation for InterfaceMappingUpdateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    logical_interface_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='LogicalInterfaceName',
            description='The logical name for one interface (on every Node) that handles a specific type of traffic. We recommend that the name hints at the physical interface it applies to. For example, it could refer to the traffic that the physical interface handles. For example, my-Inputs-Interface.',
        ),
    ]

    network_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='NetworkId',
            description='The ID of the network that you want to connect to the specified logicalInterfaceName. You can use the ListNetworks operation to discover all the IDs.',
        ),
    ]


class InternalServerErrorException(BaseModel):
    """Placeholder documentation for InternalServerErrorException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class InternalServerErrorExceptionResponseContent(BaseModel):
    """Unexpected error during processing of request."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='Exception error message.',
        ),
    ]


class InternalServiceError(BaseModel):
    """Placeholder documentation for InternalServiceError."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class InvalidRequest(BaseModel):
    """Placeholder documentation for InvalidRequest."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class IpPool(BaseModel):
    """Used in DescribeNetworkResult, DescribeNetworkSummary, UpdateNetworkResult."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='A CIDR block of IP addresses that are reserved for MediaLive Anywhere.',
        ),
    ]


class IpPoolCreateRequest(BaseModel):
    """Used in CreateNetworkRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='A CIDR block of IP addresses to reserve for MediaLive Anywhere.',
        ),
    ]


class IpPoolUpdateRequest(BaseModel):
    """Used in UpdateNetworkRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='A CIDR block of IP addresses to reserve for MediaLive Anywhere.',
        ),
    ]


class LimitExceeded(BaseModel):
    """Placeholder documentation for LimitExceeded."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class ListCloudWatchAlarmTemplateGroupsRequest(BaseModel):
    """Placeholder documentation for ListCloudWatchAlarmTemplateGroupsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]

    scope: Annotated[
        Optional[str],
        Field(
            None,
            alias='Scope',
            description='Represents the scope of a resource, with options for all scopes, AWS provided resources, or local resources.',
        ),
    ]

    signal_map_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='SignalMapIdentifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class ListCloudWatchAlarmTemplateGroupsResponse(BaseModel):
    """Placeholder documentation for ListCloudWatchAlarmTemplateGroupsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_template_groups: Annotated[
        Optional[list[CloudWatchAlarmTemplateGroupSummary]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroups',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListCloudWatchAlarmTemplateGroupsResponseContent(BaseModel):
    """Placeholder documentation for ListCloudWatchAlarmTemplateGroupsResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_template_groups: Annotated[
        list[CloudWatchAlarmTemplateGroupSummary],
        Field(
            ...,
            alias='CloudWatchAlarmTemplateGroups',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListCloudWatchAlarmTemplatesRequest(BaseModel):
    """Placeholder documentation for ListCloudWatchAlarmTemplatesRequest."""

    model_config = ConfigDict(populate_by_name=True)

    group_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupIdentifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]

    scope: Annotated[
        Optional[str],
        Field(
            None,
            alias='Scope',
            description='Represents the scope of a resource, with options for all scopes, AWS provided resources, or local resources.',
        ),
    ]

    signal_map_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='SignalMapIdentifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class ListCloudWatchAlarmTemplatesResponse(BaseModel):
    """Placeholder documentation for ListCloudWatchAlarmTemplatesResponse."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_templates: Annotated[
        Optional[list[CloudWatchAlarmTemplateSummary]],
        Field(
            None,
            alias='CloudWatchAlarmTemplates',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListCloudWatchAlarmTemplatesResponseContent(BaseModel):
    """Placeholder documentation for ListCloudWatchAlarmTemplatesResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_templates: Annotated[
        list[CloudWatchAlarmTemplateSummary],
        Field(
            ...,
            alias='CloudWatchAlarmTemplates',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListClustersRequest(BaseModel):
    """Placeholder documentation for ListClustersRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of items to return.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The token to retrieve the next page of results.',
        ),
    ]


class ListClustersResponse(BaseModel):
    """Placeholder documentation for ListClustersResponse."""

    model_config = ConfigDict(populate_by_name=True)

    clusters: Annotated[
        Optional[list[DescribeClusterSummary]],
        Field(
            None,
            alias='Clusters',
            description='A list of the Clusters that exist in your AWS account.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next result.',
        ),
    ]


class ListClustersResult(BaseModel):
    """Contains the response for ListClusters."""

    model_config = ConfigDict(populate_by_name=True)

    clusters: Annotated[
        Optional[list[DescribeClusterSummary]],
        Field(
            None,
            alias='Clusters',
            description='A list of the Clusters that exist in your AWS account.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next result.',
        ),
    ]


class ListEventBridgeRuleTemplateGroupsRequest(BaseModel):
    """Placeholder documentation for ListEventBridgeRuleTemplateGroupsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]

    signal_map_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='SignalMapIdentifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class ListEventBridgeRuleTemplateGroupsResponse(BaseModel):
    """Placeholder documentation for ListEventBridgeRuleTemplateGroupsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    event_bridge_rule_template_groups: Annotated[
        Optional[list[EventBridgeRuleTemplateGroupSummary]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroups',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListEventBridgeRuleTemplateGroupsResponseContent(BaseModel):
    """Placeholder documentation for ListEventBridgeRuleTemplateGroupsResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    event_bridge_rule_template_groups: Annotated[
        list[EventBridgeRuleTemplateGroupSummary],
        Field(
            ...,
            alias='EventBridgeRuleTemplateGroups',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListEventBridgeRuleTemplatesRequest(BaseModel):
    """Placeholder documentation for ListEventBridgeRuleTemplatesRequest."""

    model_config = ConfigDict(populate_by_name=True)

    group_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupIdentifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]

    signal_map_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='SignalMapIdentifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class ListEventBridgeRuleTemplatesResponse(BaseModel):
    """Placeholder documentation for ListEventBridgeRuleTemplatesResponse."""

    model_config = ConfigDict(populate_by_name=True)

    event_bridge_rule_templates: Annotated[
        Optional[list[EventBridgeRuleTemplateSummary]],
        Field(
            None,
            alias='EventBridgeRuleTemplates',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListEventBridgeRuleTemplatesResponseContent(BaseModel):
    """Placeholder documentation for ListEventBridgeRuleTemplatesResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    event_bridge_rule_templates: Annotated[
        list[EventBridgeRuleTemplateSummary],
        Field(
            ...,
            alias='EventBridgeRuleTemplates',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListInputDeviceTransfersRequest(BaseModel):
    """Placeholder documentation for ListInputDeviceTransfersRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]

    transfer_type: Annotated[
        str,
        Field(
            ...,
            alias='TransferType',
            description='',
        ),
    ]


class ListInputDevicesRequest(BaseModel):
    """Placeholder documentation for ListInputDevicesRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class ListInputDevicesResponse(BaseModel):
    """Placeholder documentation for ListInputDevicesResponse."""

    model_config = ConfigDict(populate_by_name=True)

    input_devices: Annotated[
        Optional[list[InputDeviceSummary]],
        Field(
            None,
            alias='InputDevices',
            description='The list of input devices.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token to get additional list results.',
        ),
    ]


class ListInputDevicesResultModel(BaseModel):
    """The list of input devices owned by the AWS account."""

    model_config = ConfigDict(populate_by_name=True)

    input_devices: Annotated[
        Optional[list[InputDeviceSummary]],
        Field(
            None,
            alias='InputDevices',
            description='The list of input devices.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token to get additional list results.',
        ),
    ]


class ListInputSecurityGroupsRequest(BaseModel):
    """Placeholder documentation for ListInputSecurityGroupsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class ListInputSecurityGroupsResponse(BaseModel):
    """Placeholder documentation for ListInputSecurityGroupsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    input_security_groups: Annotated[
        Optional[list[InputSecurityGroup]],
        Field(
            None,
            alias='InputSecurityGroups',
            description='List of input security groups',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class ListInputSecurityGroupsResultModel(BaseModel):
    """Result of input security group list request."""

    model_config = ConfigDict(populate_by_name=True)

    input_security_groups: Annotated[
        Optional[list[InputSecurityGroup]],
        Field(
            None,
            alias='InputSecurityGroups',
            description='List of input security groups',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class ListInputsRequest(BaseModel):
    """Placeholder documentation for ListInputsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class ListMultiplexProgramsRequest(BaseModel):
    """Placeholder documentation for ListMultiplexProgramsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of items to return.',
        ),
    ]

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='The ID of the multiplex that the programs belong to.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The token to retrieve the next page of results.',
        ),
    ]


class ListMultiplexesRequest(BaseModel):
    """Placeholder documentation for ListMultiplexesRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of items to return.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The token to retrieve the next page of results.',
        ),
    ]


class ListNetworksRequest(BaseModel):
    """Placeholder documentation for ListNetworksRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of items to return.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The token to retrieve the next page of results.',
        ),
    ]


class ListNodesRequest(BaseModel):
    """Placeholder documentation for ListNodesRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of items to return.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The token to retrieve the next page of results.',
        ),
    ]


class ListOfferingsRequest(BaseModel):
    """Placeholder documentation for ListOfferingsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_class: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelClass',
            description='Filter by channel class, \u0027STANDARD\u0027 or \u0027SINGLE_PIPELINE\u0027',
        ),
    ]

    channel_configuration: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelConfiguration',
            description='Filter to offerings that match the configuration of an existing channel, e.g. \u00272345678\u0027 (a channel ID)',
        ),
    ]

    codec: Annotated[
        Optional[str],
        Field(
            None,
            alias='Codec',
            description='Filter by codec, \u0027AVC\u0027, \u0027HEVC\u0027, \u0027MPEG2\u0027, \u0027AUDIO\u0027, \u0027LINK\u0027, or \u0027AV1\u0027',
        ),
    ]

    duration: Annotated[
        Optional[str],
        Field(
            None,
            alias='Duration',
            description='Filter by offering duration, e.g. \u002712\u0027',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    maximum_bitrate: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaximumBitrate',
            description='Filter by bitrate, \u0027MAX_10_MBPS\u0027, \u0027MAX_20_MBPS\u0027, or \u0027MAX_50_MBPS\u0027',
        ),
    ]

    maximum_framerate: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaximumFramerate',
            description='Filter by framerate, \u0027MAX_30_FPS\u0027 or \u0027MAX_60_FPS\u0027',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]

    resolution: Annotated[
        Optional[str],
        Field(
            None,
            alias='Resolution',
            description='Filter by resolution, \u0027SD\u0027, \u0027HD\u0027, \u0027FHD\u0027, or \u0027UHD\u0027',
        ),
    ]

    resource_type: Annotated[
        Optional[str],
        Field(
            None,
            alias='ResourceType',
            description='Filter by resource type, \u0027INPUT\u0027, \u0027OUTPUT\u0027, \u0027MULTIPLEX\u0027, or \u0027CHANNEL\u0027',
        ),
    ]

    special_feature: Annotated[
        Optional[str],
        Field(
            None,
            alias='SpecialFeature',
            description='Filter by special feature, \u0027ADVANCED_AUDIO\u0027 or \u0027AUDIO_NORMALIZATION\u0027',
        ),
    ]

    video_quality: Annotated[
        Optional[str],
        Field(
            None,
            alias='VideoQuality',
            description='Filter by video quality, \u0027STANDARD\u0027, \u0027ENHANCED\u0027, or \u0027PREMIUM\u0027',
        ),
    ]


class ListReservationsRequest(BaseModel):
    """Placeholder documentation for ListReservationsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    channel_class: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelClass',
            description='Filter by channel class, \u0027STANDARD\u0027 or \u0027SINGLE_PIPELINE\u0027',
        ),
    ]

    codec: Annotated[
        Optional[str],
        Field(
            None,
            alias='Codec',
            description='Filter by codec, \u0027AVC\u0027, \u0027HEVC\u0027, \u0027MPEG2\u0027, \u0027AUDIO\u0027, \u0027LINK\u0027, or \u0027AV1\u0027',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    maximum_bitrate: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaximumBitrate',
            description='Filter by bitrate, \u0027MAX_10_MBPS\u0027, \u0027MAX_20_MBPS\u0027, or \u0027MAX_50_MBPS\u0027',
        ),
    ]

    maximum_framerate: Annotated[
        Optional[str],
        Field(
            None,
            alias='MaximumFramerate',
            description='Filter by framerate, \u0027MAX_30_FPS\u0027 or \u0027MAX_60_FPS\u0027',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]

    resolution: Annotated[
        Optional[str],
        Field(
            None,
            alias='Resolution',
            description='Filter by resolution, \u0027SD\u0027, \u0027HD\u0027, \u0027FHD\u0027, or \u0027UHD\u0027',
        ),
    ]

    resource_type: Annotated[
        Optional[str],
        Field(
            None,
            alias='ResourceType',
            description='Filter by resource type, \u0027INPUT\u0027, \u0027OUTPUT\u0027, \u0027MULTIPLEX\u0027, or \u0027CHANNEL\u0027',
        ),
    ]

    special_feature: Annotated[
        Optional[str],
        Field(
            None,
            alias='SpecialFeature',
            description='Filter by special feature, \u0027ADVANCED_AUDIO\u0027 or \u0027AUDIO_NORMALIZATION\u0027',
        ),
    ]

    video_quality: Annotated[
        Optional[str],
        Field(
            None,
            alias='VideoQuality',
            description='Filter by video quality, \u0027STANDARD\u0027, \u0027ENHANCED\u0027, or \u0027PREMIUM\u0027',
        ),
    ]


class ListSdiSourcesRequest(BaseModel):
    """Placeholder documentation for ListSdiSourcesRequest."""

    model_config = ConfigDict(populate_by_name=True)

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='The maximum number of items to return.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The token to retrieve the next page of results.',
        ),
    ]


class ListSignalMapsRequest(BaseModel):
    """Placeholder documentation for ListSignalMapsRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_template_group_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIdentifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    event_bridge_rule_template_group_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIdentifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    max_results: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxResults',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]


class ListVersionsRequest(BaseModel):
    """Placeholder documentation for ListVersionsRequest."""

    model_config = ConfigDict(populate_by_name=True)


class ListVersionsResponse(BaseModel):
    """Placeholder documentation for ListVersionsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    versions: Annotated[
        Optional[list[ChannelEngineVersionResponse]],
        Field(
            None,
            alias='Versions',
            description='List of engine versions that are available for this AWS account.',
        ),
    ]


class MediaConnectFlow(BaseModel):
    """The settings for a MediaConnect Flow."""

    model_config = ConfigDict(populate_by_name=True)

    flow_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='FlowArn',
            description='The unique ARN of the MediaConnect Flow being used as a source.',
        ),
    ]


class MediaConnectFlowRequest(BaseModel):
    """The settings for a MediaConnect Flow."""

    model_config = ConfigDict(populate_by_name=True)

    flow_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='FlowArn',
            description='The ARN of the MediaConnect Flow that you want to use as a source.',
        ),
    ]


class MediaResourceNeighbor(BaseModel):
    """A direct source or destination neighbor to an AWS media resource."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='The ARN of a resource used in AWS media workflows.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The logical name of an AWS media resource.',
        ),
    ]


class MediaResource(BaseModel):
    """An AWS resource used in media workflows."""

    model_config = ConfigDict(populate_by_name=True)

    destinations: Annotated[
        Optional[list[MediaResourceNeighbor]],
        Field(
            None,
            alias='Destinations',
            description='',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The logical name of an AWS media resource.',
        ),
    ]

    sources: Annotated[
        Optional[list[MediaResourceNeighbor]],
        Field(
            None,
            alias='Sources',
            description='',
        ),
    ]


class MonitorDeployment(BaseModel):
    """Represents the latest monitor deployment of a signal map."""

    model_config = ConfigDict(populate_by_name=True)

    details_uri: Annotated[
        Optional[str],
        Field(
            None,
            alias='DetailsUri',
            description='URI associated with a signal map\u0027s monitor deployment.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed monitor deployment of a signal map.',
        ),
    ]

    status: Annotated[
        SignalMapMonitorDeploymentStatus,
        Field(
            ...,
            alias='Status',
            description='',
        ),
    ]


class Mp2Settings(BaseModel):
    """Mp2 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    bitrate: Annotated[
        Optional[float],
        Field(
            None,
            alias='Bitrate',
            description='Average bitrate in bits/second.',
        ),
    ]

    coding_mode: Annotated[
        Optional[Mp2CodingMode],
        Field(
            None,
            alias='CodingMode',
            description='The MPEG2 Audio coding mode. Valid values are codingMode10 (for mono) or codingMode20 (for stereo).',
        ),
    ]

    sample_rate: Annotated[
        Optional[float],
        Field(
            None,
            alias='SampleRate',
            description='Sample rate in Hz.',
        ),
    ]


class ListMultiplexProgramsResponse(BaseModel):
    """Placeholder documentation for ListMultiplexProgramsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_programs: Annotated[
        Optional[list[MultiplexProgramSummary]],
        Field(
            None,
            alias='MultiplexPrograms',
            description='List of multiplex programs.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next ListMultiplexProgram request.',
        ),
    ]


class ListMultiplexProgramsResultModel(BaseModel):
    """Placeholder documentation for ListMultiplexProgramsResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_programs: Annotated[
        Optional[list[MultiplexProgramSummary]],
        Field(
            None,
            alias='MultiplexPrograms',
            description='List of multiplex programs.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next ListMultiplexProgram request.',
        ),
    ]


class CreateMultiplex(BaseModel):
    """Placeholder documentation for CreateMultiplex."""

    model_config = ConfigDict(populate_by_name=True)

    availability_zones: Annotated[
        list[str],
        Field(
            ...,
            alias='AvailabilityZones',
            description='A list of availability zones for the multiplex. You must specify exactly two.',
        ),
    ]

    multiplex_settings: Annotated[
        MultiplexSettings,
        Field(
            ...,
            alias='MultiplexSettings',
            description='Configuration for a multiplex event.',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='Name of multiplex.',
        ),
    ]

    request_id: Annotated[
        str,
        Field(
            ...,
            alias='RequestId',
            description='Unique request ID. This prevents retries from creating multiple resources.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class CreateMultiplexRequest(BaseModel):
    """A request to create a multiplex."""

    model_config = ConfigDict(populate_by_name=True)

    availability_zones: Annotated[
        list[str],
        Field(
            ...,
            alias='AvailabilityZones',
            description='A list of availability zones for the multiplex. You must specify exactly two.',
        ),
    ]

    multiplex_settings: Annotated[
        MultiplexSettings,
        Field(
            ...,
            alias='MultiplexSettings',
            description='Configuration for a multiplex event.',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='Name of multiplex.',
        ),
    ]

    request_id: Annotated[
        str,
        Field(
            ...,
            alias='RequestId',
            description='Unique request ID. This prevents retries from creating multiple resources.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class DeleteMultiplexResponse(BaseModel):
    """Placeholder documentation for DeleteMultiplexResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the multiplex.',
        ),
    ]

    availability_zones: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AvailabilityZones',
            description='A list of availability zones for the multiplex.',
        ),
    ]

    destinations: Annotated[
        Optional[list[MultiplexOutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of the multiplex output destinations.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the multiplex.',
        ),
    ]

    multiplex_settings: Annotated[
        Optional[MultiplexSettings],
        Field(
            None,
            alias='MultiplexSettings',
            description='Configuration for a multiplex event.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the multiplex.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    program_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramCount',
            description='The number of programs in the multiplex.',
        ),
    ]

    state: Annotated[
        Optional[MultiplexState],
        Field(
            None,
            alias='State',
            description='The current state of the multiplex.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class DescribeMultiplexResponse(BaseModel):
    """Placeholder documentation for DescribeMultiplexResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the multiplex.',
        ),
    ]

    availability_zones: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AvailabilityZones',
            description='A list of availability zones for the multiplex.',
        ),
    ]

    destinations: Annotated[
        Optional[list[MultiplexOutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of the multiplex output destinations.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the multiplex.',
        ),
    ]

    multiplex_settings: Annotated[
        Optional[MultiplexSettings],
        Field(
            None,
            alias='MultiplexSettings',
            description='Configuration for a multiplex event.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the multiplex.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    program_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramCount',
            description='The number of programs in the multiplex.',
        ),
    ]

    state: Annotated[
        Optional[MultiplexState],
        Field(
            None,
            alias='State',
            description='The current state of the multiplex.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class CreateMultiplexResponse(BaseModel):
    """Placeholder documentation for CreateMultiplexResponse."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex: Annotated[
        Optional[Multiplex],
        Field(
            None,
            alias='Multiplex',
            description='The newly created multiplex.',
        ),
    ]


class CreateMultiplexResultModel(BaseModel):
    """Placeholder documentation for CreateMultiplexResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex: Annotated[
        Optional[Multiplex],
        Field(
            None,
            alias='Multiplex',
            description='The newly created multiplex.',
        ),
    ]


class ListMultiplexesResponse(BaseModel):
    """Placeholder documentation for ListMultiplexesResponse."""

    model_config = ConfigDict(populate_by_name=True)

    multiplexes: Annotated[
        Optional[list[MultiplexSummary]],
        Field(
            None,
            alias='Multiplexes',
            description='List of multiplexes.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next ListMultiplexes request.',
        ),
    ]


class ListMultiplexesResultModel(BaseModel):
    """Placeholder documentation for ListMultiplexesResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    multiplexes: Annotated[
        Optional[list[MultiplexSummary]],
        Field(
            None,
            alias='Multiplexes',
            description='List of multiplexes.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next ListMultiplexes request.',
        ),
    ]


class CreateMultiplexProgram(BaseModel):
    """Placeholder documentation for CreateMultiplexProgram."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_program_settings: Annotated[
        MultiplexProgramSettings,
        Field(
            ...,
            alias='MultiplexProgramSettings',
            description='The settings for this multiplex program.',
        ),
    ]

    program_name: Annotated[
        str,
        Field(
            ...,
            alias='ProgramName',
            description='Name of multiplex program.',
        ),
    ]

    request_id: Annotated[
        str,
        Field(
            ...,
            alias='RequestId',
            description='Unique request ID. This prevents retries from creating multiple resources.',
        ),
    ]


class CreateMultiplexProgramRequest(BaseModel):
    """A request to create a program in a multiplex."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='ID of the multiplex where the program is to be created.',
        ),
    ]

    multiplex_program_settings: Annotated[
        MultiplexProgramSettings,
        Field(
            ...,
            alias='MultiplexProgramSettings',
            description='The settings for this multiplex program.',
        ),
    ]

    program_name: Annotated[
        str,
        Field(
            ...,
            alias='ProgramName',
            description='Name of multiplex program.',
        ),
    ]

    request_id: Annotated[
        str,
        Field(
            ...,
            alias='RequestId',
            description='Unique request ID. This prevents retries from creating multiple resources.',
        ),
    ]


class DeleteMultiplexProgramResponse(BaseModel):
    """Placeholder documentation for DeleteMultiplexProgramResponse."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelId',
            description='The MediaLive channel associated with the program.',
        ),
    ]

    multiplex_program_settings: Annotated[
        Optional[MultiplexProgramSettings],
        Field(
            None,
            alias='MultiplexProgramSettings',
            description='The settings for this multiplex program.',
        ),
    ]

    packet_identifiers_map: Annotated[
        Optional[MultiplexProgramPacketIdentifiersMap],
        Field(
            None,
            alias='PacketIdentifiersMap',
            description='The packet identifier map for this multiplex program.',
        ),
    ]

    pipeline_details: Annotated[
        Optional[list[MultiplexProgramPipelineDetail]],
        Field(
            None,
            alias='PipelineDetails',
            description='Contains information about the current sources for the specified program in the specified multiplex. Keep in mind that each multiplex pipeline connects to both pipelines in a given source channel (the channel identified by the program). But only one of those channel pipelines is ever active at one time.',
        ),
    ]

    program_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ProgramName',
            description='The name of the multiplex program.',
        ),
    ]


class DescribeMultiplexProgramResponse(BaseModel):
    """Placeholder documentation for DescribeMultiplexProgramResponse."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelId',
            description='The MediaLive channel associated with the program.',
        ),
    ]

    multiplex_program_settings: Annotated[
        Optional[MultiplexProgramSettings],
        Field(
            None,
            alias='MultiplexProgramSettings',
            description='The settings for this multiplex program.',
        ),
    ]

    packet_identifiers_map: Annotated[
        Optional[MultiplexProgramPacketIdentifiersMap],
        Field(
            None,
            alias='PacketIdentifiersMap',
            description='The packet identifier map for this multiplex program.',
        ),
    ]

    pipeline_details: Annotated[
        Optional[list[MultiplexProgramPipelineDetail]],
        Field(
            None,
            alias='PipelineDetails',
            description='Contains information about the current sources for the specified program in the specified multiplex. Keep in mind that each multiplex pipeline connects to both pipelines in a given source channel (the channel identified by the program). But only one of those channel pipelines is ever active at one time.',
        ),
    ]

    program_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ProgramName',
            description='The name of the multiplex program.',
        ),
    ]


class CreateMultiplexProgramResponse(BaseModel):
    """Placeholder documentation for CreateMultiplexProgramResponse."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_program: Annotated[
        Optional[MultiplexProgram],
        Field(
            None,
            alias='MultiplexProgram',
            description='The newly created multiplex program.',
        ),
    ]


class CreateMultiplexProgramResultModel(BaseModel):
    """Placeholder documentation for CreateMultiplexProgramResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_program: Annotated[
        Optional[MultiplexProgram],
        Field(
            None,
            alias='MultiplexProgram',
            description='The newly created multiplex program.',
        ),
    ]


class AudioWatermarkSettings(BaseModel):
    """Audio Watermark Settings."""

    model_config = ConfigDict(populate_by_name=True)

    nielsen_watermarks_settings: Annotated[
        Optional[NielsenWatermarksSettings],
        Field(
            None,
            alias='NielsenWatermarksSettings',
            description='Settings to configure Nielsen Watermarks in the audio encode',
        ),
    ]


class CreateNodeRegistrationScriptRequest(BaseModel):
    """A request to create a new node registration script."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='If you\u0027re generating a re-registration script for an already existing node, this is where you provide the id.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Specify a pattern for MediaLive Anywhere to use to assign a name to each Node in the Cluster. The pattern can include the variables $hn (hostname of the node hardware) and $ts for the date and time that the Node is created, in UTC (for example, 2024-08-20T23:35:12Z).',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMapping]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]


class CreateNodeRequest(BaseModel):
    """A request to create a node."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The user-specified name of the Node to be created.',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMappingCreateRequest]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class NotFoundException(BaseModel):
    """Placeholder documentation for NotFoundException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class NotFoundExceptionResponseContent(BaseModel):
    """Request references a resource which does not exist."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='Exception error message.',
        ),
    ]


class AdditionalDestinations(BaseModel):
    """Additional output destinations for a CMAF Ingest output group."""

    model_config = ConfigDict(populate_by_name=True)

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='The destination location',
        ),
    ]


class PassThroughSettings(BaseModel):
    """Pass Through Settings."""

    model_config = ConfigDict(populate_by_name=True)


class RemixSettings(BaseModel):
    """Remix Settings."""

    model_config = ConfigDict(populate_by_name=True)

    channel_mappings: Annotated[
        list[AudioChannelMapping],
        Field(
            ...,
            alias='ChannelMappings',
            description='Mapping of input channels to output channels, with appropriate gain adjustments.',
        ),
    ]

    channels_in: Annotated[
        Optional[int],
        Field(
            None,
            alias='ChannelsIn',
            description='Number of input channels to be used.',
        ),
    ]

    channels_out: Annotated[
        Optional[int],
        Field(
            None,
            alias='ChannelsOut',
            description='Number of output channels to be produced. Valid values: 1, 2, 4, 6, 8',
        ),
    ]


class RenewalSettings(BaseModel):
    """The Renewal settings for Reservations."""

    model_config = ConfigDict(populate_by_name=True)

    automatic_renewal: Annotated[
        Optional[ReservationAutomaticRenewal],
        Field(
            None,
            alias='AutomaticRenewal',
            description='Automatic renewal status for the reservation',
        ),
    ]

    renewal_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='RenewalCount',
            description='Count for the reservation renewal',
        ),
    ]


class DeleteReservationResponse(BaseModel):
    """Placeholder documentation for DeleteReservationResponse."""

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


class DescribeOfferingResponse(BaseModel):
    """Placeholder documentation for DescribeOfferingResponse."""

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


class DescribeReservationResponse(BaseModel):
    """Placeholder documentation for DescribeReservationResponse."""

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


class ListOfferingsResponse(BaseModel):
    """Placeholder documentation for ListOfferingsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token to retrieve the next page of results',
        ),
    ]

    offerings: Annotated[
        Optional[list[Offering]],
        Field(
            None,
            alias='Offerings',
            description='List of offerings',
        ),
    ]


class ListOfferingsResultModel(BaseModel):
    """ListOfferings response."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token to retrieve the next page of results',
        ),
    ]

    offerings: Annotated[
        Optional[list[Offering]],
        Field(
            None,
            alias='Offerings',
            description='List of offerings',
        ),
    ]


class ListReservationsResponse(BaseModel):
    """Placeholder documentation for ListReservationsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token to retrieve the next page of results',
        ),
    ]

    reservations: Annotated[
        Optional[list[Reservation]],
        Field(
            None,
            alias='Reservations',
            description='List of reservations',
        ),
    ]


class ListReservationsResultModel(BaseModel):
    """ListReservations response."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token to retrieve the next page of results',
        ),
    ]

    reservations: Annotated[
        Optional[list[Reservation]],
        Field(
            None,
            alias='Reservations',
            description='List of reservations',
        ),
    ]


class ResourceConflict(BaseModel):
    """Placeholder documentation for ResourceConflict."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class ResourceNotFound(BaseModel):
    """Placeholder documentation for ResourceNotFound."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class Route(BaseModel):
    """Used in DescribeNetworkResult, DescribeNetworkSummary, UpdateNetworkResult."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='A CIDR block for one Route.',
        ),
    ]

    gateway: Annotated[
        Optional[str],
        Field(
            None,
            alias='Gateway',
            description='The IP address of the Gateway for this route, if applicable.',
        ),
    ]


class CreateNetworkResponse(BaseModel):
    """Placeholder documentation for CreateNetworkResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Network. It is automatically assigned when the Network is created.',
        ),
    ]

    associated_cluster_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AssociatedClusterIds',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Network. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    ip_pools: Annotated[
        Optional[list[IpPool]],
        Field(
            None,
            alias='IpPools',
            description='An array of IpPools in your organization\u0027s network that identify a collection of IP addresses in this network that are reserved for use in MediaLive Anywhere. MediaLive Anywhere uses these IP addresses for Push inputs (in both Bridge and NAT networks) and for output destinations (only in Bridge networks). Each IpPool specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Network.',
        ),
    ]

    routes: Annotated[
        Optional[list[Route]],
        Field(
            None,
            alias='Routes',
            description='An array of routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]

    state: Annotated[
        Optional[NetworkState],
        Field(
            None,
            alias='State',
            description='The current state of the Network. Only MediaLive Anywhere can change the state.',
        ),
    ]


class DeleteNetworkResponse(BaseModel):
    """Placeholder documentation for DeleteNetworkResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Network. It is automatically assigned when the Network is created.',
        ),
    ]

    associated_cluster_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AssociatedClusterIds',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Network. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    ip_pools: Annotated[
        Optional[list[IpPool]],
        Field(
            None,
            alias='IpPools',
            description='An array of IpPools in your organization\u0027s network that identify a collection of IP addresses in this network that are reserved for use in MediaLive Anywhere. MediaLive Anywhere uses these IP addresses for Push inputs (in both Bridge and NAT networks) and for output destinations (only in Bridge networks). Each IpPool specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Network.',
        ),
    ]

    routes: Annotated[
        Optional[list[Route]],
        Field(
            None,
            alias='Routes',
            description='An array of routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]

    state: Annotated[
        Optional[NetworkState],
        Field(
            None,
            alias='State',
            description='The current state of the Network. Only MediaLive Anywhere can change the state.',
        ),
    ]


class DescribeNetworkResponse(BaseModel):
    """Placeholder documentation for DescribeNetworkResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Network. It is automatically assigned when the Network is created.',
        ),
    ]

    associated_cluster_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AssociatedClusterIds',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Network. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    ip_pools: Annotated[
        Optional[list[IpPool]],
        Field(
            None,
            alias='IpPools',
            description='An array of IpPools in your organization\u0027s network that identify a collection of IP addresses in this network that are reserved for use in MediaLive Anywhere. MediaLive Anywhere uses these IP addresses for Push inputs (in both Bridge and NAT networks) and for output destinations (only in Bridge networks). Each IpPool specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Network.',
        ),
    ]

    routes: Annotated[
        Optional[list[Route]],
        Field(
            None,
            alias='Routes',
            description='An array of routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]

    state: Annotated[
        Optional[NetworkState],
        Field(
            None,
            alias='State',
            description='The current state of the Network. Only MediaLive Anywhere can change the state.',
        ),
    ]


class DescribeNetworkResult(BaseModel):
    """Contains the response for CreateNetwork, DescribeNetwork, DeleteNetwork, UpdateNetwork."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Network. It is automatically assigned when the Network is created.',
        ),
    ]

    associated_cluster_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AssociatedClusterIds',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Network. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    ip_pools: Annotated[
        Optional[list[IpPool]],
        Field(
            None,
            alias='IpPools',
            description='An array of IpPools in your organization\u0027s network that identify a collection of IP addresses in this network that are reserved for use in MediaLive Anywhere. MediaLive Anywhere uses these IP addresses for Push inputs (in both Bridge and NAT networks) and for output destinations (only in Bridge networks). Each IpPool specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Network.',
        ),
    ]

    routes: Annotated[
        Optional[list[Route]],
        Field(
            None,
            alias='Routes',
            description='An array of routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]

    state: Annotated[
        Optional[NetworkState],
        Field(
            None,
            alias='State',
            description='The current state of the Network. Only MediaLive Anywhere can change the state.',
        ),
    ]


class DescribeNetworkSummary(BaseModel):
    """Used in ListNetworksResult."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Network. It is automatically assigned when the Network is created.',
        ),
    ]

    associated_cluster_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AssociatedClusterIds',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Network. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    ip_pools: Annotated[
        Optional[list[IpPool]],
        Field(
            None,
            alias='IpPools',
            description='An array of IpPools in your organization\u0027s network that identify a collection of IP addresses in your organization\u0027s network that are reserved for use in MediaLive Anywhere. MediaLive Anywhere uses these IP addresses for Push inputs (in both Bridge and NAT networks) and for output destinations (only in Bridge networks). Each IpPool specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for this Network.',
        ),
    ]

    routes: Annotated[
        Optional[list[Route]],
        Field(
            None,
            alias='Routes',
            description='An array of routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]

    state: Annotated[
        Optional[NetworkState],
        Field(
            None,
            alias='State',
            description='The current state of the Network. Only MediaLive Anywhere can change the state.',
        ),
    ]


class ListNetworksResponse(BaseModel):
    """Placeholder documentation for ListNetworksResponse."""

    model_config = ConfigDict(populate_by_name=True)

    networks: Annotated[
        Optional[list[DescribeNetworkSummary]],
        Field(
            None,
            alias='Networks',
            description='An array of networks that you have created.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next ListNetworks request.',
        ),
    ]


class ListNetworksResult(BaseModel):
    """Contains the response for ListNetworks."""

    model_config = ConfigDict(populate_by_name=True)

    networks: Annotated[
        Optional[list[DescribeNetworkSummary]],
        Field(
            None,
            alias='Networks',
            description='An array of networks that you have created.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next ListNetworks request.',
        ),
    ]


class RouteCreateRequest(BaseModel):
    """Used in CreateNetworkRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='A CIDR block for one Route.',
        ),
    ]

    gateway: Annotated[
        Optional[str],
        Field(
            None,
            alias='Gateway',
            description='The IP address of the Gateway for this route, if applicable.',
        ),
    ]


class CreateNetworkRequest(BaseModel):
    """A request to create a Network."""

    model_config = ConfigDict(populate_by_name=True)

    ip_pools: Annotated[
        Optional[list[IpPoolCreateRequest]],
        Field(
            None,
            alias='IpPools',
            description='An array of IpPoolCreateRequests that identify a collection of IP addresses in your network that you want to reserve for use in MediaLive Anywhere. MediaLiveAnywhere uses these IP addresses for Push inputs (in both Bridge and NATnetworks) and for output destinations (only in Bridge networks). EachIpPoolUpdateRequest specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Specify a name that is unique in the AWS account. We recommend that you assign a name that hints at the type of traffic on the network. Names are case-sensitive.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='An ID that you assign to a create request. This ID ensures idempotency when creating resources.',
        ),
    ]

    routes: Annotated[
        Optional[list[RouteCreateRequest]],
        Field(
            None,
            alias='Routes',
            description='An array of routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class RouteUpdateRequest(BaseModel):
    """Used in UpdateNetworkRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='A CIDR block for one Route.',
        ),
    ]

    gateway: Annotated[
        Optional[str],
        Field(
            None,
            alias='Gateway',
            description='The IP address of the Gateway for this route, if applicable.',
        ),
    ]


class CreateSdiSourceResponse(BaseModel):
    """Placeholder documentation for CreateSdiSourceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    sdi_source: Annotated[
        Optional[SdiSource],
        Field(
            None,
            alias='SdiSource',
            description='Settings for the SDI source.',
        ),
    ]


class DeleteSdiSourceResponse(BaseModel):
    """Placeholder documentation for DeleteSdiSourceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    sdi_source: Annotated[
        Optional[SdiSource],
        Field(
            None,
            alias='SdiSource',
            description='Settings for the SDI source.',
        ),
    ]


class DescribeSdiSourceResponse(BaseModel):
    """Placeholder documentation for DescribeSdiSourceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    sdi_source: Annotated[
        Optional[SdiSource],
        Field(
            None,
            alias='SdiSource',
            description='Settings for the SDI source.',
        ),
    ]


class CreateNodeResponse(BaseModel):
    """Placeholder documentation for CreateNodeResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Node. It is automatically assigned when the Node is created.',
        ),
    ]

    channel_placement_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of IDs. Each ID is one ChannelPlacementGroup that is associated with this Node. Empty if the Node is not yet associated with any groups.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    connection_state: Annotated[
        Optional[NodeConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The current connection state of the Node.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Node. Unique in the Cluster. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceArn',
            description='The ARN of the EC2 instance hosting the Node.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Node.',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMapping]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role current role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    state: Annotated[
        Optional[NodeState],
        Field(
            None,
            alias='State',
            description='The current state of the Node.',
        ),
    ]

    sdi_source_mappings: Annotated[
        Optional[list[SdiSourceMapping]],
        Field(
            None,
            alias='SdiSourceMappings',
            description='An array of SDI source mappings. Each mapping connects one logical SdiSource to the physical SDI card and port that the physical SDI source uses.',
        ),
    ]


class DeleteNodeResponse(BaseModel):
    """Placeholder documentation for DeleteNodeResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Node. It is automatically assigned when the Node is created.',
        ),
    ]

    channel_placement_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of IDs. Each ID is one ChannelPlacementGroup that is associated with this Node. Empty if the Node is not yet associated with any groups.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    connection_state: Annotated[
        Optional[NodeConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The current connection state of the Node.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Node. Unique in the Cluster. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceArn',
            description='The ARN of the EC2 instance hosting the Node.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Node.',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMapping]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role current role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    state: Annotated[
        Optional[NodeState],
        Field(
            None,
            alias='State',
            description='The current state of the Node.',
        ),
    ]

    sdi_source_mappings: Annotated[
        Optional[list[SdiSourceMapping]],
        Field(
            None,
            alias='SdiSourceMappings',
            description='An array of SDI source mappings. Each mapping connects one logical SdiSource to the physical SDI card and port that the physical SDI source uses.',
        ),
    ]


class DescribeNodeResponse(BaseModel):
    """Placeholder documentation for DescribeNodeResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Node. It is automatically assigned when the Node is created.',
        ),
    ]

    channel_placement_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of IDs. Each ID is one ChannelPlacementGroup that is associated with this Node. Empty if the Node is not yet associated with any groups.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    connection_state: Annotated[
        Optional[NodeConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The current connection state of the Node.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Node. Unique in the Cluster. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceArn',
            description='The ARN of the EC2 instance hosting the Node.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Node.',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMapping]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role current role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    state: Annotated[
        Optional[NodeState],
        Field(
            None,
            alias='State',
            description='The current state of the Node.',
        ),
    ]

    sdi_source_mappings: Annotated[
        Optional[list[SdiSourceMapping]],
        Field(
            None,
            alias='SdiSourceMappings',
            description='An array of SDI source mappings. Each mapping connects one logical SdiSource to the physical SDI card and port that the physical SDI source uses.',
        ),
    ]


class DescribeNodeResult(BaseModel):
    """Contains the response for CreateNode, DescribeNode, DeleteNode, UpdateNode."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Node. It is automatically assigned when the Node is created.',
        ),
    ]

    channel_placement_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of IDs. Each ID is one ChannelPlacementGroup that is associated with this Node. Empty if the Node is not yet associated with any groups.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    connection_state: Annotated[
        Optional[NodeConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The current connection state of the Node.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Node. Unique in the Cluster. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceArn',
            description='The ARN of the EC2 instance hosting the Node.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Node.',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMapping]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role current role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    state: Annotated[
        Optional[NodeState],
        Field(
            None,
            alias='State',
            description='The current state of the Node.',
        ),
    ]

    sdi_source_mappings: Annotated[
        Optional[list[SdiSourceMapping]],
        Field(
            None,
            alias='SdiSourceMappings',
            description='An array of SDI source mappings. Each mapping connects one logical SdiSource to the physical SDI card and port that the physical SDI source uses.',
        ),
    ]


class DescribeNodeSummary(BaseModel):
    """Placeholder documentation for DescribeNodeSummary."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Node. It is automatically assigned when the Node is created.',
        ),
    ]

    channel_placement_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of IDs. Each ID is one ChannelPlacementGroup that is associated with this Node. Empty if the Node is not yet associated with any groups.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    connection_state: Annotated[
        Optional[NodeConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The current connection state of the Node.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Node. Unique in the Cluster. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceArn',
            description='The EC2 ARN of the Instance associated with the Node.',
        ),
    ]

    managed_instance_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ManagedInstanceId',
            description='At the routing layer will get it from the callerId/context for use with bring your own device.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Node.',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMapping]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role current role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    state: Annotated[
        Optional[NodeState],
        Field(
            None,
            alias='State',
            description='The current state of the Node.',
        ),
    ]

    sdi_source_mappings: Annotated[
        Optional[list[SdiSourceMapping]],
        Field(
            None,
            alias='SdiSourceMappings',
            description='An array of SDI source mappings. Each mapping connects one logical SdiSource to the physical SDI card and port that the physical SDI source uses.',
        ),
    ]


class ListNodesResponse(BaseModel):
    """Placeholder documentation for ListNodesResponse."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next result.',
        ),
    ]

    nodes: Annotated[
        Optional[list[DescribeNodeSummary]],
        Field(
            None,
            alias='Nodes',
            description='An array of Nodes that exist in the Cluster.',
        ),
    ]


class ListNodesResult(BaseModel):
    """Contains the response for ListNodes."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='Token for the next result.',
        ),
    ]

    nodes: Annotated[
        Optional[list[DescribeNodeSummary]],
        Field(
            None,
            alias='Nodes',
            description='An array of Nodes that exist in the Cluster.',
        ),
    ]


class ListSdiSourcesResponse(BaseModel):
    """Placeholder documentation for ListSdiSourcesResponse."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]

    sdi_sources: Annotated[
        Optional[list[SdiSourceSummary]],
        Field(
            None,
            alias='SdiSources',
            description='',
        ),
    ]


class ListSignalMapsResponse(BaseModel):
    """Placeholder documentation for ListSignalMapsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]

    signal_maps: Annotated[
        Optional[list[SignalMapSummary]],
        Field(
            None,
            alias='SignalMaps',
            description='',
        ),
    ]


class ListSignalMapsResponseContent(BaseModel):
    """Placeholder documentation for ListSignalMapsResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token used to retrieve the next set of results in paginated list responses.',
        ),
    ]

    signal_maps: Annotated[
        list[SignalMapSummary],
        Field(
            ...,
            alias='SignalMaps',
            description='',
        ),
    ]


class SmpteTtDestinationSettings(BaseModel):
    """Smpte Tt Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)


class DescribeInputResponse(BaseModel):
    """Placeholder documentation for DescribeInputResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The Unique ARN of the input (generated, immutable).',
        ),
    ]

    attached_channels: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AttachedChannels',
            description='A list of channel IDs that that input is attached to (currently an input can only be attached to one channel).',
        ),
    ]

    destinations: Annotated[
        Optional[list[InputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of the destinations of the input (PUSH-type).',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The generated ID of the input (unique for user account, immutable).',
        ),
    ]

    input_class: Annotated[
        Optional[InputClass],
        Field(
            None,
            alias='InputClass',
            description='STANDARD - MediaLive expects two sources to be connected to this input. If the channel is also STANDARD, both sources will be ingested. If the channel is SINGLE_PIPELINE, only the first source will be ingested; the second source will always be ignored, even if the first source fails. SINGLE_PIPELINE - You can connect only one source to this input. If the ChannelClass is also SINGLE_PIPELINE, this value is valid. If the ChannelClass is STANDARD, this value is not valid because the channel requires two sources in the input.',
        ),
    ]

    input_devices: Annotated[
        Optional[list[InputDeviceSettings]],
        Field(
            None,
            alias='InputDevices',
            description='Settings for the input devices.',
        ),
    ]

    input_partner_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputPartnerIds',
            description='A list of IDs for all Inputs which are partners of this one.',
        ),
    ]

    input_source_type: Annotated[
        Optional[InputSourceType],
        Field(
            None,
            alias='InputSourceType',
            description='Certain pull input sources can be dynamic, meaning that they can have their URL\u0027s dynamically changes during input switch actions. Presently, this functionality only works with MP4_FILE and TS_FILE inputs.',
        ),
    ]

    media_connect_flows: Annotated[
        Optional[list[MediaConnectFlow]],
        Field(
            None,
            alias='MediaConnectFlows',
            description='A list of MediaConnect Flows for this input.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The user-assigned name (This is a mutable value).',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role this input assumes during and after creation.',
        ),
    ]

    security_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SecurityGroups',
            description='A list of IDs for all the Input Security Groups attached to the input.',
        ),
    ]

    sources: Annotated[
        Optional[list[InputSource]],
        Field(
            None,
            alias='Sources',
            description='A list of the sources of the input (PULL-type).',
        ),
    ]

    state: Annotated[
        Optional[InputState],
        Field(
            None,
            alias='State',
            description='',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    type: Annotated[
        Optional[InputType],
        Field(
            None,
            alias='Type',
            description='',
        ),
    ]

    srt_settings: Annotated[
        Optional[SrtSettings],
        Field(
            None,
            alias='SrtSettings',
            description='The settings associated with an SRT input.',
        ),
    ]

    input_network_location: Annotated[
        Optional[InputNetworkLocation],
        Field(
            None,
            alias='InputNetworkLocation',
            description='The location of this input. AWS, for an input existing in the AWS Cloud, On-Prem for an input in a customer network.',
        ),
    ]

    multicast_settings: Annotated[
        Optional[MulticastSettings],
        Field(
            None,
            alias='MulticastSettings',
            description='Multicast Input settings.',
        ),
    ]

    smpte2110_receiver_group_settings: Annotated[
        Optional[Smpte2110ReceiverGroupSettings],
        Field(
            None,
            alias='Smpte2110ReceiverGroupSettings',
            description='Include this parameter if the input is a SMPTE 2110 input, to identify the stream sources for this input.',
        ),
    ]

    sdi_sources: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SdiSources',
            description='',
        ),
    ]


class CreateInputResponse(BaseModel):
    """Placeholder documentation for CreateInputResponse."""

    model_config = ConfigDict(populate_by_name=True)

    input: Annotated[
        Optional[Input],
        Field(
            None,
            alias='Input',
            description='',
        ),
    ]


class CreateInputResultModel(BaseModel):
    """Placeholder documentation for CreateInputResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    input: Annotated[
        Optional[Input],
        Field(
            None,
            alias='Input',
            description='',
        ),
    ]


class CreatePartnerInputResponse(BaseModel):
    """Placeholder documentation for CreatePartnerInputResponse."""

    model_config = ConfigDict(populate_by_name=True)

    input: Annotated[
        Optional[Input],
        Field(
            None,
            alias='Input',
            description='',
        ),
    ]


class CreatePartnerInputResultModel(BaseModel):
    """Placeholder documentation for CreatePartnerInputResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    input: Annotated[
        Optional[Input],
        Field(
            None,
            alias='Input',
            description='',
        ),
    ]


class ListInputsResponse(BaseModel):
    """Placeholder documentation for ListInputsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    inputs: Annotated[
        Optional[list[Input]],
        Field(
            None,
            alias='Inputs',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class ListInputsResultModel(BaseModel):
    """Placeholder documentation for ListInputsResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    inputs: Annotated[
        Optional[list[Input]],
        Field(
            None,
            alias='Inputs',
            description='',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='',
        ),
    ]


class CreateInput(BaseModel):
    """Placeholder documentation for CreateInput."""

    model_config = ConfigDict(populate_by_name=True)

    destinations: Annotated[
        Optional[list[InputDestinationRequest]],
        Field(
            None,
            alias='Destinations',
            description='Destination settings for PUSH type inputs.',
        ),
    ]

    input_devices: Annotated[
        Optional[list[InputDeviceSettings]],
        Field(
            None,
            alias='InputDevices',
            description='Settings for the devices.',
        ),
    ]

    input_security_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputSecurityGroups',
            description='A list of security groups referenced by IDs to attach to the input.',
        ),
    ]

    media_connect_flows: Annotated[
        Optional[list[MediaConnectFlowRequest]],
        Field(
            None,
            alias='MediaConnectFlows',
            description='A list of the MediaConnect Flows that you want to use in this input. You can specify as few as one Flow and presently, as many as two. The only requirement is when you have more than one is that each Flow is in a separate Availability Zone as this ensures your EML input is redundant to AZ issues.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of the input.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='Unique identifier of the request to ensure the request is handled exactly once in case of retries.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role this input assumes during and after creation.',
        ),
    ]

    sources: Annotated[
        Optional[list[InputSourceRequest]],
        Field(
            None,
            alias='Sources',
            description='The source URLs for a PULL-type input. Every PULL type input needs exactly two source URLs for redundancy. Only specify sources for PULL type Inputs. Leave Destinations empty.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    type: Annotated[
        Optional[InputType],
        Field(
            None,
            alias='Type',
            description='',
        ),
    ]

    vpc: Annotated[
        Optional[InputVpcRequest],
        Field(
            None,
            alias='Vpc',
            description='',
        ),
    ]

    srt_settings: Annotated[
        Optional[SrtSettingsRequest],
        Field(
            None,
            alias='SrtSettings',
            description='The settings associated with an SRT input.',
        ),
    ]

    input_network_location: Annotated[
        Optional[InputNetworkLocation],
        Field(
            None,
            alias='InputNetworkLocation',
            description='The location of this input. AWS, for an input existing in the AWS Cloud, On-Prem for an input in a customer network.',
        ),
    ]

    multicast_settings: Annotated[
        Optional[MulticastSettingsCreateRequest],
        Field(
            None,
            alias='MulticastSettings',
            description='Multicast Input settings.',
        ),
    ]

    smpte2110_receiver_group_settings: Annotated[
        Optional[Smpte2110ReceiverGroupSettings],
        Field(
            None,
            alias='Smpte2110ReceiverGroupSettings',
            description='Include this parameter if the input is a SMPTE 2110 input, to identify the stream sources for this input.',
        ),
    ]

    sdi_sources: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SdiSources',
            description='',
        ),
    ]


class CreateInputRequest(BaseModel):
    """The name of the input."""

    model_config = ConfigDict(populate_by_name=True)

    destinations: Annotated[
        Optional[list[InputDestinationRequest]],
        Field(
            None,
            alias='Destinations',
            description='Destination settings for PUSH type inputs.',
        ),
    ]

    input_devices: Annotated[
        Optional[list[InputDeviceSettings]],
        Field(
            None,
            alias='InputDevices',
            description='Settings for the devices.',
        ),
    ]

    input_security_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputSecurityGroups',
            description='A list of security groups referenced by IDs to attach to the input.',
        ),
    ]

    media_connect_flows: Annotated[
        Optional[list[MediaConnectFlowRequest]],
        Field(
            None,
            alias='MediaConnectFlows',
            description='A list of the MediaConnect Flows that you want to use in this input. You can specify as few as one Flow and presently, as many as two. The only requirement is when you have more than one is that each Flow is in a separate Availability Zone as this ensures your EML input is redundant to AZ issues.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of the input.',
        ),
    ]

    request_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='RequestId',
            description='Unique identifier of the request to ensure the request is handled exactly once in case of retries.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role this input assumes during and after creation.',
        ),
    ]

    sources: Annotated[
        Optional[list[InputSourceRequest]],
        Field(
            None,
            alias='Sources',
            description='The source URLs for a PULL-type input. Every PULL type input needs exactly two source URLs for redundancy. Only specify sources for PULL type Inputs. Leave Destinations empty.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    type: Annotated[
        Optional[InputType],
        Field(
            None,
            alias='Type',
            description='',
        ),
    ]

    vpc: Annotated[
        Optional[InputVpcRequest],
        Field(
            None,
            alias='Vpc',
            description='',
        ),
    ]

    srt_settings: Annotated[
        Optional[SrtSettingsRequest],
        Field(
            None,
            alias='SrtSettings',
            description='The settings associated with an SRT input.',
        ),
    ]

    input_network_location: Annotated[
        Optional[InputNetworkLocation],
        Field(
            None,
            alias='InputNetworkLocation',
            description='The location of this input. AWS, for an input existing in the AWS Cloud, On-Prem for an input in a customer network.',
        ),
    ]

    multicast_settings: Annotated[
        Optional[MulticastSettingsCreateRequest],
        Field(
            None,
            alias='MulticastSettings',
            description='Multicast Input settings.',
        ),
    ]

    smpte2110_receiver_group_settings: Annotated[
        Optional[Smpte2110ReceiverGroupSettings],
        Field(
            None,
            alias='Smpte2110ReceiverGroupSettings',
            description='Include this parameter if the input is a SMPTE 2110 input, to identify the stream sources for this input.',
        ),
    ]

    sdi_sources: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SdiSources',
            description='',
        ),
    ]


class StandardHlsSettings(BaseModel):
    """Standard Hls Settings."""

    model_config = ConfigDict(populate_by_name=True)

    audio_rendition_sets: Annotated[
        Optional[str],
        Field(
            None,
            alias='AudioRenditionSets',
            description='List all the audio groups that are used with the video output stream. Input all the audio GROUP-IDs that are associated to the video, separate by \u0027,\u0027.',
        ),
    ]

    m3u8_settings: Annotated[
        M3u8Settings,
        Field(
            ...,
            alias='M3u8Settings',
            description='',
        ),
    ]


class StartDeleteMonitorDeploymentRequest(BaseModel):
    """Placeholder documentation for StartDeleteMonitorDeploymentRequest."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class StartInputDeviceMaintenanceWindowRequest(BaseModel):
    """Placeholder documentation for StartInputDeviceMaintenanceWindowRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of the input device to start a maintenance window for. For example, hd-123456789abcdef.',
        ),
    ]


class StartInputDeviceMaintenanceWindowResponse(BaseModel):
    """Placeholder documentation for StartInputDeviceMaintenanceWindowResponse."""

    model_config = ConfigDict(populate_by_name=True)


class StartInputDeviceRequest(BaseModel):
    """Placeholder documentation for StartInputDeviceRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of the input device to start. For example, hd-123456789abcdef.',
        ),
    ]


class StartInputDeviceResponse(BaseModel):
    """Placeholder documentation for StartInputDeviceResponse."""

    model_config = ConfigDict(populate_by_name=True)


class StartMonitorDeploymentRequest(BaseModel):
    """Placeholder documentation for StartMonitorDeploymentRequest."""

    model_config = ConfigDict(populate_by_name=True)

    dry_run: Annotated[
        Optional[bool],
        Field(
            None,
            alias='DryRun',
            description='',
        ),
    ]

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class StartMonitorDeploymentRequestContent(BaseModel):
    """Placeholder documentation for StartMonitorDeploymentRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    dry_run: Annotated[
        Optional[bool],
        Field(
            None,
            alias='DryRun',
            description='',
        ),
    ]


class StartMultiplexRequest(BaseModel):
    """Placeholder documentation for StartMultiplexRequest."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='The ID of the multiplex.',
        ),
    ]


class StartMultiplexResponse(BaseModel):
    """Placeholder documentation for StartMultiplexResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the multiplex.',
        ),
    ]

    availability_zones: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AvailabilityZones',
            description='A list of availability zones for the multiplex.',
        ),
    ]

    destinations: Annotated[
        Optional[list[MultiplexOutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of the multiplex output destinations.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the multiplex.',
        ),
    ]

    multiplex_settings: Annotated[
        Optional[MultiplexSettings],
        Field(
            None,
            alias='MultiplexSettings',
            description='Configuration for a multiplex event.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the multiplex.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    program_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramCount',
            description='The number of programs in the multiplex.',
        ),
    ]

    state: Annotated[
        Optional[MultiplexState],
        Field(
            None,
            alias='State',
            description='The current state of the multiplex.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class StartTimecode(BaseModel):
    """Settings to identify the start of the clip."""

    model_config = ConfigDict(populate_by_name=True)

    timecode: Annotated[
        Optional[str],
        Field(
            None,
            alias='Timecode',
            description='The timecode for the frame where you want to start the clip. Optional; if not specified, the clip starts at first frame in the file. Enter the timecode as HH:MM:SS:FF or HH:MM:SS;FF.',
        ),
    ]


class StartUpdateSignalMapRequest(BaseModel):
    """Placeholder documentation for StartUpdateSignalMapRequest."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_template_group_identifiers: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIdentifiers',
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

    discovery_entry_point_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    event_bridge_rule_template_group_identifiers: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIdentifiers',
            description='',
        ),
    ]

    force_rediscovery: Annotated[
        Optional[bool],
        Field(
            None,
            alias='ForceRediscovery',
            description='If true, will force a rediscovery of a signal map if an unchanged discoveryEntryPointArn is provided.',
        ),
    ]

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A signal map\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]


class StartUpdateSignalMapRequestContent(BaseModel):
    """Placeholder documentation for StartUpdateSignalMapRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    cloud_watch_alarm_template_group_identifiers: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIdentifiers',
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

    discovery_entry_point_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    event_bridge_rule_template_group_identifiers: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIdentifiers',
            description='',
        ),
    ]

    force_rediscovery: Annotated[
        Optional[bool],
        Field(
            None,
            alias='ForceRediscovery',
            description='If true, will force a rediscovery of a signal map if an unchanged discoveryEntryPointArn is provided.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]


class StopInputDeviceRequest(BaseModel):
    """Placeholder documentation for StopInputDeviceRequest."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of the input device to stop. For example, hd-123456789abcdef.',
        ),
    ]


class StopInputDeviceResponse(BaseModel):
    """Placeholder documentation for StopInputDeviceResponse."""

    model_config = ConfigDict(populate_by_name=True)


class StopMultiplexRequest(BaseModel):
    """Placeholder documentation for StopMultiplexRequest."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='The ID of the multiplex.',
        ),
    ]


class StopMultiplexResponse(BaseModel):
    """Placeholder documentation for StopMultiplexResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique arn of the multiplex.',
        ),
    ]

    availability_zones: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AvailabilityZones',
            description='A list of availability zones for the multiplex.',
        ),
    ]

    destinations: Annotated[
        Optional[list[MultiplexOutputDestination]],
        Field(
            None,
            alias='Destinations',
            description='A list of the multiplex output destinations.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the multiplex.',
        ),
    ]

    multiplex_settings: Annotated[
        Optional[MultiplexSettings],
        Field(
            None,
            alias='MultiplexSettings',
            description='Configuration for a multiplex event.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name of the multiplex.',
        ),
    ]

    pipelines_running_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='PipelinesRunningCount',
            description='The number of currently healthy pipelines.',
        ),
    ]

    program_count: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramCount',
            description='The number of programs in the multiplex.',
        ),
    ]

    state: Annotated[
        Optional[MultiplexState],
        Field(
            None,
            alias='State',
            description='The current state of the multiplex.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]


class StopTimecode(BaseModel):
    """Settings to identify the end of the clip."""

    model_config = ConfigDict(populate_by_name=True)

    last_frame_clipping_behavior: Annotated[
        Optional[LastFrameClippingBehavior],
        Field(
            None,
            alias='LastFrameClippingBehavior',
            description='If you specify a StopTimecode in an input (in order to clip the file), you can specify if you want the clip to exclude (the default) or include the frame specified by the timecode.',
        ),
    ]

    timecode: Annotated[
        Optional[str],
        Field(
            None,
            alias='Timecode',
            description='The timecode for the frame where you want to stop the clip. Optional; if not specified, the clip continues to the end of the file. Enter the timecode as HH:MM:SS:FF or HH:MM:SS;FF.',
        ),
    ]


class SuccessfulMonitorDeployment(BaseModel):
    """Represents the latest successful monitor deployment of a signal map."""

    model_config = ConfigDict(populate_by_name=True)

    details_uri: Annotated[
        str,
        Field(
            ...,
            alias='DetailsUri',
            description='URI associated with a signal map\u0027s monitor deployment.',
        ),
    ]

    status: Annotated[
        SignalMapMonitorDeploymentStatus,
        Field(
            ...,
            alias='Status',
            description='',
        ),
    ]


class CreateSignalMapResponse(BaseModel):
    """Placeholder documentation for CreateSignalMapResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
            description='',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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

    discovery_entry_point_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='A signal map\u0027s id.',
        ),
    ]

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        Optional[bool],
        Field(
            None,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
            description='',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    status: Annotated[
        Optional[SignalMapStatus],
        Field(
            None,
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


class CreateSignalMapResponseContent(BaseModel):
    """Placeholder documentation for CreateSignalMapResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
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

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    discovery_entry_point_arn: Annotated[
        str,
        Field(
            ...,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
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

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        bool,
        Field(
            ...,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
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


class GetSignalMapResponse(BaseModel):
    """Placeholder documentation for GetSignalMapResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
            description='',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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

    discovery_entry_point_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='A signal map\u0027s id.',
        ),
    ]

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        Optional[bool],
        Field(
            None,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
            description='',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    status: Annotated[
        Optional[SignalMapStatus],
        Field(
            None,
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


class GetSignalMapResponseContent(BaseModel):
    """Placeholder documentation for GetSignalMapResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
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

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    discovery_entry_point_arn: Annotated[
        str,
        Field(
            ...,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
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

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        bool,
        Field(
            ...,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
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


class StartDeleteMonitorDeploymentResponse(BaseModel):
    """Placeholder documentation for StartDeleteMonitorDeploymentResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
            description='',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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

    discovery_entry_point_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='A signal map\u0027s id.',
        ),
    ]

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        Optional[bool],
        Field(
            None,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
            description='',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    status: Annotated[
        Optional[SignalMapStatus],
        Field(
            None,
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


class StartDeleteMonitorDeploymentResponseContent(BaseModel):
    """Placeholder documentation for StartDeleteMonitorDeploymentResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
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

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    discovery_entry_point_arn: Annotated[
        str,
        Field(
            ...,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
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

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        bool,
        Field(
            ...,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
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


class StartMonitorDeploymentResponse(BaseModel):
    """Placeholder documentation for StartMonitorDeploymentResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
            description='',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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

    discovery_entry_point_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='A signal map\u0027s id.',
        ),
    ]

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        Optional[bool],
        Field(
            None,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
            description='',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    status: Annotated[
        Optional[SignalMapStatus],
        Field(
            None,
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


class StartMonitorDeploymentResponseContent(BaseModel):
    """Placeholder documentation for StartMonitorDeploymentResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
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

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    discovery_entry_point_arn: Annotated[
        str,
        Field(
            ...,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
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

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        bool,
        Field(
            ...,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
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


class StartUpdateSignalMapResponse(BaseModel):
    """Placeholder documentation for StartUpdateSignalMapResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
            description='',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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

    discovery_entry_point_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='A signal map\u0027s id.',
        ),
    ]

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        Optional[bool],
        Field(
            None,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
            description='',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    status: Annotated[
        Optional[SignalMapStatus],
        Field(
            None,
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


class StartUpdateSignalMapResponseContent(BaseModel):
    """Placeholder documentation for StartUpdateSignalMapResponseContent."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        str,
        Field(
            ...,
            alias='Arn',
            description='A signal map\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    cloud_watch_alarm_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CloudWatchAlarmTemplateGroupIds',
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

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    discovery_entry_point_arn: Annotated[
        str,
        Field(
            ...,
            alias='DiscoveryEntryPointArn',
            description='A top-level supported AWS resource ARN to discovery a signal map from.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='Error message associated with a failed creation or failed update attempt of a signal map.',
        ),
    ]

    event_bridge_rule_template_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='EventBridgeRuleTemplateGroupIds',
            description='',
        ),
    ]

    failed_media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='FailedMediaResourceMap',
            description='',
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

    last_discovered_at: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='LastDiscoveredAt',
            description='',
        ),
    ]

    last_successful_monitor_deployment: Annotated[
        Optional[SuccessfulMonitorDeployment],
        Field(
            None,
            alias='LastSuccessfulMonitorDeployment',
            description='',
        ),
    ]

    media_resource_map: Annotated[
        Optional[dict[str, MediaResource]],
        Field(
            None,
            alias='MediaResourceMap',
            description='',
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

    monitor_changes_pending_deployment: Annotated[
        bool,
        Field(
            ...,
            alias='MonitorChangesPendingDeployment',
            description='If true, there are pending monitor changes for this signal map that can be deployed.',
        ),
    ]

    monitor_deployment: Annotated[
        Optional[MonitorDeployment],
        Field(
            None,
            alias='MonitorDeployment',
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


class TeletextDestinationSettings(BaseModel):
    """Teletext Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)


class TeletextSourceSettings(BaseModel):
    """Teletext Source Settings."""

    model_config = ConfigDict(populate_by_name=True)

    output_rectangle: Annotated[
        Optional[CaptionRectangle],
        Field(
            None,
            alias='OutputRectangle',
            description='Optionally defines a region where TTML style captions will be displayed',
        ),
    ]

    page_number: Annotated[
        Optional[str],
        Field(
            None,
            alias='PageNumber',
            description='Specifies the teletext page number within the data stream from which to extract captions. Range of 0x100 (256) to 0x8FF (2303). Unused for passthrough. Should be specified as a hexadecimal string with no "0x" prefix.',
        ),
    ]


class CaptionSelectorSettings(BaseModel):
    """Caption Selector Settings."""

    model_config = ConfigDict(populate_by_name=True)

    ancillary_source_settings: Annotated[
        Optional[AncillarySourceSettings],
        Field(
            None,
            alias='AncillarySourceSettings',
            description='',
        ),
    ]

    arib_source_settings: Annotated[
        Optional[AribSourceSettings],
        Field(
            None,
            alias='AribSourceSettings',
            description='',
        ),
    ]

    dvb_sub_source_settings: Annotated[
        Optional[DvbSubSourceSettings],
        Field(
            None,
            alias='DvbSubSourceSettings',
            description='',
        ),
    ]

    embedded_source_settings: Annotated[
        Optional[EmbeddedSourceSettings],
        Field(
            None,
            alias='EmbeddedSourceSettings',
            description='',
        ),
    ]

    scte20_source_settings: Annotated[
        Optional[Scte20SourceSettings],
        Field(
            None,
            alias='Scte20SourceSettings',
            description='',
        ),
    ]

    scte27_source_settings: Annotated[
        Optional[Scte27SourceSettings],
        Field(
            None,
            alias='Scte27SourceSettings',
            description='',
        ),
    ]

    teletext_source_settings: Annotated[
        Optional[TeletextSourceSettings],
        Field(
            None,
            alias='TeletextSourceSettings',
            description='',
        ),
    ]


class CaptionSelector(BaseModel):
    """Caption Selector."""

    model_config = ConfigDict(populate_by_name=True)

    language_code: Annotated[
        Optional[str],
        Field(
            None,
            alias='LanguageCode',
            description='When specified this field indicates the three letter language code of the caption track to extract from the source.',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='Name identifier for a caption selector. This name is used to associate this caption selector with one or more caption descriptions. Names must be unique within an event.',
        ),
    ]

    selector_settings: Annotated[
        Optional[CaptionSelectorSettings],
        Field(
            None,
            alias='SelectorSettings',
            description='Caption selector settings.',
        ),
    ]


class DescribeThumbnailsResponse(BaseModel):
    """Placeholder documentation for DescribeThumbnailsResponse."""

    model_config = ConfigDict(populate_by_name=True)

    thumbnail_details: Annotated[
        Optional[list[ThumbnailDetail]],
        Field(
            None,
            alias='ThumbnailDetails',
            description='',
        ),
    ]


class DescribeThumbnailsResultModel(BaseModel):
    """Thumbnail details for all the pipelines of a running channel."""

    model_config = ConfigDict(populate_by_name=True)

    thumbnail_details: Annotated[
        Optional[list[ThumbnailDetail]],
        Field(
            None,
            alias='ThumbnailDetails',
            description='',
        ),
    ]


class TimedMetadataScheduleActionSettings(BaseModel):
    """Settings for the action to insert ID3 metadata (as a one-time action) in applicable output groups."""

    model_config = ConfigDict(populate_by_name=True)

    id3: Annotated[
        str,
        Field(
            ...,
            alias='Id3',
            description='Enter a base64 string that contains one or more fully formed ID3 tags.See the ID3 specification: http://id3.org/id3v2.4.0-structure',
        ),
    ]


class BatchScheduleActionCreateRequest(BaseModel):
    """A list of schedule actions to create (in a request) or that have been created (in a response)."""

    model_config = ConfigDict(populate_by_name=True)

    schedule_actions: Annotated[
        list[ScheduleAction],
        Field(
            ...,
            alias='ScheduleActions',
            description='A list of schedule actions to create.',
        ),
    ]


class BatchScheduleActionCreateResult(BaseModel):
    """List of actions that have been created in the schedule."""

    model_config = ConfigDict(populate_by_name=True)

    schedule_actions: Annotated[
        list[ScheduleAction],
        Field(
            ...,
            alias='ScheduleActions',
            description='List of actions that have been created in the schedule.',
        ),
    ]


class BatchScheduleActionDeleteResult(BaseModel):
    """List of actions that have been deleted from the schedule."""

    model_config = ConfigDict(populate_by_name=True)

    schedule_actions: Annotated[
        list[ScheduleAction],
        Field(
            ...,
            alias='ScheduleActions',
            description='List of actions that have been deleted from the schedule.',
        ),
    ]


class DescribeScheduleResponse(BaseModel):
    """Placeholder documentation for DescribeScheduleResponse."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='The next token; for use in pagination.',
        ),
    ]

    schedule_actions: Annotated[
        Optional[list[ScheduleAction]],
        Field(
            None,
            alias='ScheduleActions',
            description='The list of actions in the schedule.',
        ),
    ]


class TooManyRequestsException(BaseModel):
    """Placeholder documentation for TooManyRequestsException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='',
        ),
    ]


class TooManyRequestsExceptionResponseContent(BaseModel):
    """Request was denied due to request throttling."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='Exception error message.',
        ),
    ]


class ListInputDeviceTransfersResponse(BaseModel):
    """Placeholder documentation for ListInputDeviceTransfersResponse."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_transfers: Annotated[
        Optional[list[TransferringInputDeviceSummary]],
        Field(
            None,
            alias='InputDeviceTransfers',
            description='The list of devices that you are transferring or are being transferred to you.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token to get additional list results.',
        ),
    ]


class ListInputDeviceTransfersResultModel(BaseModel):
    """The list of input devices in the transferred state. The recipient hasn't yet accepted or rejected the transfer."""

    model_config = ConfigDict(populate_by_name=True)

    input_device_transfers: Annotated[
        Optional[list[TransferringInputDeviceSummary]],
        Field(
            None,
            alias='InputDeviceTransfers',
            description='The list of devices that you are transferring or are being transferred to you.',
        ),
    ]

    next_token: Annotated[
        Optional[str],
        Field(
            None,
            alias='NextToken',
            description='A token to get additional list results.',
        ),
    ]


class TtmlDestinationSettings(BaseModel):
    """Ttml Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)

    style_control: Annotated[
        Optional[TtmlDestinationStyleControl],
        Field(
            None,
            alias='StyleControl',
            description='This field is not currently supported and will not affect the output styling. Leave the default value.',
        ),
    ]


class UpdateAccountConfigurationRequest(BaseModel):
    """List of account configuration parameters to update."""

    model_config = ConfigDict(populate_by_name=True)

    account_configuration: Annotated[
        Optional[AccountConfiguration],
        Field(
            None,
            alias='AccountConfiguration',
            description='',
        ),
    ]


class UpdateAccountConfigurationRequestModel(BaseModel):
    """The desired new account configuration."""

    model_config = ConfigDict(populate_by_name=True)

    account_configuration: Annotated[
        Optional[AccountConfiguration],
        Field(
            None,
            alias='AccountConfiguration',
            description='',
        ),
    ]


class UpdateAccountConfigurationResponse(BaseModel):
    """Placeholder documentation for UpdateAccountConfigurationResponse."""

    model_config = ConfigDict(populate_by_name=True)

    account_configuration: Annotated[
        Optional[AccountConfiguration],
        Field(
            None,
            alias='AccountConfiguration',
            description='',
        ),
    ]


class UpdateAccountConfigurationResultModel(BaseModel):
    """The account's updated configuration."""

    model_config = ConfigDict(populate_by_name=True)

    account_configuration: Annotated[
        Optional[AccountConfiguration],
        Field(
            None,
            alias='AccountConfiguration',
            description='',
        ),
    ]


class UpdateCloudWatchAlarmTemplateGroupRequest(BaseModel):
    """Placeholder documentation for UpdateCloudWatchAlarmTemplateGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class UpdateCloudWatchAlarmTemplateGroupRequestContent(BaseModel):
    """Placeholder documentation for UpdateCloudWatchAlarmTemplateGroupRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]


class UpdateCloudWatchAlarmTemplateGroupResponse(BaseModel):
    """Placeholder documentation for UpdateCloudWatchAlarmTemplateGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A cloudwatch alarm template group\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class UpdateCloudWatchAlarmTemplateGroupResponseContent(BaseModel):
    """Placeholder documentation for UpdateCloudWatchAlarmTemplateGroupResponseContent."""

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


class UpdateCloudWatchAlarmTemplateRequest(BaseModel):
    """Placeholder documentation for UpdateCloudWatchAlarmTemplateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    comparison_operator: Annotated[
        Optional[CloudWatchAlarmTemplateComparisonOperator],
        Field(
            None,
            alias='ComparisonOperator',
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
        Optional[int],
        Field(
            None,
            alias='EvaluationPeriods',
            description='The number of periods over which data is compared to the specified threshold.',
        ),
    ]

    group_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupIdentifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='A cloudwatch alarm template\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    metric_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='MetricName',
            description='The name of the metric associated with the alarm. Must be compatible with targetResourceType.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    period: Annotated[
        Optional[int],
        Field(
            None,
            alias='Period',
            description='The period, in seconds, over which the specified statistic is applied.',
        ),
    ]

    statistic: Annotated[
        Optional[CloudWatchAlarmTemplateStatistic],
        Field(
            None,
            alias='Statistic',
            description='',
        ),
    ]

    target_resource_type: Annotated[
        Optional[CloudWatchAlarmTemplateTargetResourceType],
        Field(
            None,
            alias='TargetResourceType',
            description='',
        ),
    ]

    threshold: Annotated[
        Optional[float],
        Field(
            None,
            alias='Threshold',
            description='The threshold value to compare with the specified statistic.',
        ),
    ]

    treat_missing_data: Annotated[
        Optional[CloudWatchAlarmTemplateTreatMissingData],
        Field(
            None,
            alias='TreatMissingData',
            description='',
        ),
    ]


class UpdateCloudWatchAlarmTemplateRequestContent(BaseModel):
    """Placeholder documentation for UpdateCloudWatchAlarmTemplateRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    comparison_operator: Annotated[
        Optional[CloudWatchAlarmTemplateComparisonOperator],
        Field(
            None,
            alias='ComparisonOperator',
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
        Optional[int],
        Field(
            None,
            alias='EvaluationPeriods',
            description='The number of periods over which data is compared to the specified threshold.',
        ),
    ]

    group_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupIdentifier',
            description='A cloudwatch alarm template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    metric_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='MetricName',
            description='The name of the metric associated with the alarm. Must be compatible with targetResourceType.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    period: Annotated[
        Optional[int],
        Field(
            None,
            alias='Period',
            description='The period, in seconds, over which the specified statistic is applied.',
        ),
    ]

    statistic: Annotated[
        Optional[CloudWatchAlarmTemplateStatistic],
        Field(
            None,
            alias='Statistic',
            description='',
        ),
    ]

    target_resource_type: Annotated[
        Optional[CloudWatchAlarmTemplateTargetResourceType],
        Field(
            None,
            alias='TargetResourceType',
            description='',
        ),
    ]

    threshold: Annotated[
        Optional[float],
        Field(
            None,
            alias='Threshold',
            description='The threshold value to compare with the specified statistic.',
        ),
    ]

    treat_missing_data: Annotated[
        Optional[CloudWatchAlarmTemplateTreatMissingData],
        Field(
            None,
            alias='TreatMissingData',
            description='',
        ),
    ]


class UpdateCloudWatchAlarmTemplateResponse(BaseModel):
    """Placeholder documentation for UpdateCloudWatchAlarmTemplateResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='A cloudwatch alarm template\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    comparison_operator: Annotated[
        Optional[CloudWatchAlarmTemplateComparisonOperator],
        Field(
            None,
            alias='ComparisonOperator',
            description='',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[int],
        Field(
            None,
            alias='EvaluationPeriods',
            description='The number of periods over which data is compared to the specified threshold.',
        ),
    ]

    group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupId',
            description='A cloudwatch alarm template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='A cloudwatch alarm template\u0027s id. AWS provided templates have ids that start with `aws-`',
        ),
    ]

    metric_name: Annotated[
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]

    period: Annotated[
        Optional[int],
        Field(
            None,
            alias='Period',
            description='The period, in seconds, over which the specified statistic is applied.',
        ),
    ]

    statistic: Annotated[
        Optional[CloudWatchAlarmTemplateStatistic],
        Field(
            None,
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
        Optional[CloudWatchAlarmTemplateTargetResourceType],
        Field(
            None,
            alias='TargetResourceType',
            description='',
        ),
    ]

    threshold: Annotated[
        Optional[float],
        Field(
            None,
            alias='Threshold',
            description='The threshold value to compare with the specified statistic.',
        ),
    ]

    treat_missing_data: Annotated[
        Optional[CloudWatchAlarmTemplateTreatMissingData],
        Field(
            None,
            alias='TreatMissingData',
            description='',
        ),
    ]


class UpdateCloudWatchAlarmTemplateResponseContent(BaseModel):
    """Placeholder documentation for UpdateCloudWatchAlarmTemplateResponseContent."""

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


class UpdateClusterRequest(BaseModel):
    """A request to update the cluster."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Include this parameter only if you want to change the current name of the Cluster. Specify a name that is unique in the AWS account. You can\u0027t change the name. Names are case-sensitive.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettingsUpdateRequest],
        Field(
            None,
            alias='NetworkSettings',
            description='Include this property only if you want to change the current connections between the Nodes in the Cluster and the Networks the Cluster is associated with.',
        ),
    ]


class UpdateClusterResponse(BaseModel):
    """Placeholder documentation for UpdateClusterResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Cluster.',
        ),
    ]

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='An array of the IDs of the Channels that are associated with this Cluster. One Channel is associated with the Cluster as follows: A Channel belongs to a ChannelPlacementGroup. A ChannelPlacementGroup is attached to a Node. A Node belongs to a Cluster.',
        ),
    ]

    cluster_type: Annotated[
        Optional[ClusterType],
        Field(
            None,
            alias='ClusterType',
            description='The hardware type for the Cluster',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Cluster.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The user-specified name of the Cluster.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='Network settings that connect the Nodes in the Cluster to one or more of the Networks that the Cluster is associated with.',
        ),
    ]

    state: Annotated[
        Optional[ClusterState],
        Field(
            None,
            alias='State',
            description='The current state of the Cluster.',
        ),
    ]


class UpdateClusterResult(BaseModel):
    """The name that you specified for the Cluster."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Cluster.',
        ),
    ]

    channel_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelIds',
            description='An array of the IDs of the Channels that are associated with this Cluster. One Channel is associated with the Cluster as follows: A Channel belongs to a ChannelPlacementGroup. A ChannelPlacementGroup is attached to a Node. A Node belongs to a Cluster.',
        ),
    ]

    cluster_type: Annotated[
        Optional[ClusterType],
        Field(
            None,
            alias='ClusterType',
            description='The hardware type for the Cluster',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Cluster.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The user-specified name of the Cluster.',
        ),
    ]

    network_settings: Annotated[
        Optional[ClusterNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='Network settings that connect the Nodes in the Cluster to one or more of the Networks that the Cluster is associated with.',
        ),
    ]

    state: Annotated[
        Optional[ClusterState],
        Field(
            None,
            alias='State',
            description='The current state of the Cluster.',
        ),
    ]


class UpdateEventBridgeRuleTemplateGroupRequest(BaseModel):
    """Placeholder documentation for UpdateEventBridgeRuleTemplateGroupRequest."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]


class UpdateEventBridgeRuleTemplateGroupRequestContent(BaseModel):
    """Placeholder documentation for UpdateEventBridgeRuleTemplateGroupRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]


class UpdateEventBridgeRuleTemplateGroupResponse(BaseModel):
    """Placeholder documentation for UpdateEventBridgeRuleTemplateGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='An eventbridge rule template group\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class UpdateEventBridgeRuleTemplateGroupResponseContent(BaseModel):
    """Placeholder documentation for UpdateEventBridgeRuleTemplateGroupResponseContent."""

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


class UpdateEventBridgeRuleTemplateRequest(BaseModel):
    """Placeholder documentation for UpdateEventBridgeRuleTemplateRequest."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
        ),
    ]

    event_type: Annotated[
        Optional[EventBridgeRuleTemplateEventType],
        Field(
            None,
            alias='EventType',
            description='',
        ),
    ]

    group_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupIdentifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    identifier: Annotated[
        str,
        Field(
            ...,
            alias='Identifier',
            description='An eventbridge rule template\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]


class UpdateEventBridgeRuleTemplateRequestContent(BaseModel):
    """Placeholder documentation for UpdateEventBridgeRuleTemplateRequestContent."""

    model_config = ConfigDict(populate_by_name=True)

    description: Annotated[
        Optional[str],
        Field(
            None,
            alias='Description',
            description='A resource\u0027s optional description.',
        ),
    ]

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
        ),
    ]

    event_type: Annotated[
        Optional[EventBridgeRuleTemplateEventType],
        Field(
            None,
            alias='EventType',
            description='',
        ),
    ]

    group_identifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupIdentifier',
            description='An eventbridge rule template group\u0027s identifier. Can be either be its id or current name.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A resource\u0027s name. Names must be unique within the scope of a resource type in a specific region.',
        ),
    ]


class UpdateEventBridgeRuleTemplateResponse(BaseModel):
    """Placeholder documentation for UpdateEventBridgeRuleTemplateResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='An eventbridge rule template\u0027s ARN (Amazon Resource Name)',
        ),
    ]

    created_at: Annotated[
        Optional[datetime],
        Field(
            None,
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

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
        ),
    ]

    event_type: Annotated[
        Optional[EventBridgeRuleTemplateEventType],
        Field(
            None,
            alias='EventType',
            description='',
        ),
    ]

    group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='GroupId',
            description='An eventbridge rule template group\u0027s id. AWS provided template groups have ids that start with `aws-`',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
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
        Optional[str],
        Field(
            None,
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


class UpdateEventBridgeRuleTemplateResponseContent(BaseModel):
    """Placeholder documentation for UpdateEventBridgeRuleTemplateResponseContent."""

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

    event_targets: Annotated[
        Optional[list[EventBridgeRuleTemplateTarget]],
        Field(
            None,
            alias='EventTargets',
            description='',
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


class UpdateInput(BaseModel):
    """Placeholder documentation for UpdateInput."""

    model_config = ConfigDict(populate_by_name=True)

    destinations: Annotated[
        Optional[list[InputDestinationRequest]],
        Field(
            None,
            alias='Destinations',
            description='Destination settings for PUSH type inputs.',
        ),
    ]

    input_devices: Annotated[
        Optional[list[InputDeviceRequest]],
        Field(
            None,
            alias='InputDevices',
            description='Settings for the devices.',
        ),
    ]

    input_security_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputSecurityGroups',
            description='A list of security groups referenced by IDs to attach to the input.',
        ),
    ]

    media_connect_flows: Annotated[
        Optional[list[MediaConnectFlowRequest]],
        Field(
            None,
            alias='MediaConnectFlows',
            description='A list of the MediaConnect Flow ARNs that you want to use as the source of the input. You can specify as few as one Flow and presently, as many as two. The only requirement is when you have more than one is that each Flow is in a separate Availability Zone as this ensures your EML input is redundant to AZ issues.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of the input.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role this input assumes during and after creation.',
        ),
    ]

    sources: Annotated[
        Optional[list[InputSourceRequest]],
        Field(
            None,
            alias='Sources',
            description='The source URLs for a PULL-type input. Every PULL type input needs exactly two source URLs for redundancy. Only specify sources for PULL type Inputs. Leave Destinations empty.',
        ),
    ]

    srt_settings: Annotated[
        Optional[SrtSettingsRequest],
        Field(
            None,
            alias='SrtSettings',
            description='The settings associated with an SRT input.',
        ),
    ]

    multicast_settings: Annotated[
        Optional[MulticastSettingsUpdateRequest],
        Field(
            None,
            alias='MulticastSettings',
            description='Multicast Input settings.',
        ),
    ]

    smpte2110_receiver_group_settings: Annotated[
        Optional[Smpte2110ReceiverGroupSettings],
        Field(
            None,
            alias='Smpte2110ReceiverGroupSettings',
            description='Include this parameter if the input is a SMPTE 2110 input, to identify the stream sources for this input.',
        ),
    ]

    sdi_sources: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SdiSources',
            description='',
        ),
    ]


class UpdateInputDevice(BaseModel):
    """Updates an input device."""

    model_config = ConfigDict(populate_by_name=True)

    hd_device_settings: Annotated[
        Optional[InputDeviceConfigurableSettings],
        Field(
            None,
            alias='HdDeviceSettings',
            description='The settings that you want to apply to the HD input device.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you assigned to this input device (not the unique ID).',
        ),
    ]

    uhd_device_settings: Annotated[
        Optional[InputDeviceConfigurableSettings],
        Field(
            None,
            alias='UhdDeviceSettings',
            description='The settings that you want to apply to the UHD input device.',
        ),
    ]

    availability_zone: Annotated[
        Optional[str],
        Field(
            None,
            alias='AvailabilityZone',
            description='The Availability Zone you want associated with this input device.',
        ),
    ]


class UpdateInputDeviceRequest(BaseModel):
    """A request to update an input device."""

    model_config = ConfigDict(populate_by_name=True)

    hd_device_settings: Annotated[
        Optional[InputDeviceConfigurableSettings],
        Field(
            None,
            alias='HdDeviceSettings',
            description='The settings that you want to apply to the HD input device.',
        ),
    ]

    input_device_id: Annotated[
        str,
        Field(
            ...,
            alias='InputDeviceId',
            description='The unique ID of the input device. For example, hd-123456789abcdef.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you assigned to this input device (not the unique ID).',
        ),
    ]

    uhd_device_settings: Annotated[
        Optional[InputDeviceConfigurableSettings],
        Field(
            None,
            alias='UhdDeviceSettings',
            description='The settings that you want to apply to the UHD input device.',
        ),
    ]

    availability_zone: Annotated[
        Optional[str],
        Field(
            None,
            alias='AvailabilityZone',
            description='The Availability Zone you want associated with this input device.',
        ),
    ]


class UpdateInputDeviceResponse(BaseModel):
    """Placeholder documentation for UpdateInputDeviceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The unique ARN of the input device.',
        ),
    ]

    connection_state: Annotated[
        Optional[InputDeviceConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The state of the connection between the input device and AWS.',
        ),
    ]

    device_settings_sync_state: Annotated[
        Optional[DeviceSettingsSyncState],
        Field(
            None,
            alias='DeviceSettingsSyncState',
            description='The status of the action to synchronize the device configuration. If you change the configuration of the input device (for example, the maximum bitrate), MediaLive sends the new data to the device. The device might not update itself immediately. SYNCED means the device has updated its configuration. SYNCING means that it has not updated its configuration.',
        ),
    ]

    device_update_status: Annotated[
        Optional[DeviceUpdateStatus],
        Field(
            None,
            alias='DeviceUpdateStatus',
            description='The status of software on the input device.',
        ),
    ]

    hd_device_settings: Annotated[
        Optional[InputDeviceHdSettings],
        Field(
            None,
            alias='HdDeviceSettings',
            description='Settings that describe an input device that is type HD.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the input device.',
        ),
    ]

    mac_address: Annotated[
        Optional[str],
        Field(
            None,
            alias='MacAddress',
            description='The network MAC address of the input device.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='A name that you specify for the input device.',
        ),
    ]

    network_settings: Annotated[
        Optional[InputDeviceNetworkSettings],
        Field(
            None,
            alias='NetworkSettings',
            description='The network settings for the input device.',
        ),
    ]

    serial_number: Annotated[
        Optional[str],
        Field(
            None,
            alias='SerialNumber',
            description='The unique serial number of the input device.',
        ),
    ]

    type: Annotated[
        Optional[InputDeviceType],
        Field(
            None,
            alias='Type',
            description='The type of the input device.',
        ),
    ]

    uhd_device_settings: Annotated[
        Optional[InputDeviceUhdSettings],
        Field(
            None,
            alias='UhdDeviceSettings',
            description='Settings that describe an input device that is type UHD.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    availability_zone: Annotated[
        Optional[str],
        Field(
            None,
            alias='AvailabilityZone',
            description='The Availability Zone associated with this input device.',
        ),
    ]

    medialive_input_arns: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='MedialiveInputArns',
            description='An array of the ARNs for the MediaLive inputs attached to the device. Returned only if the outputType is MEDIALIVE_INPUT.',
        ),
    ]

    output_type: Annotated[
        Optional[InputDeviceOutputType],
        Field(
            None,
            alias='OutputType',
            description='The output attachment type of the input device. Specifies MEDIACONNECT_FLOW if this device is the source for a MediaConnect flow. Specifies MEDIALIVE_INPUT if this device is the source for a MediaLive input.',
        ),
    ]


class UpdateInputRequest(BaseModel):
    """A request to update an input."""

    model_config = ConfigDict(populate_by_name=True)

    destinations: Annotated[
        Optional[list[InputDestinationRequest]],
        Field(
            None,
            alias='Destinations',
            description='Destination settings for PUSH type inputs.',
        ),
    ]

    input_devices: Annotated[
        Optional[list[InputDeviceRequest]],
        Field(
            None,
            alias='InputDevices',
            description='Settings for the devices.',
        ),
    ]

    input_id: Annotated[
        str,
        Field(
            ...,
            alias='InputId',
            description='Unique ID of the input.',
        ),
    ]

    input_security_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='InputSecurityGroups',
            description='A list of security groups referenced by IDs to attach to the input.',
        ),
    ]

    media_connect_flows: Annotated[
        Optional[list[MediaConnectFlowRequest]],
        Field(
            None,
            alias='MediaConnectFlows',
            description='A list of the MediaConnect Flow ARNs that you want to use as the source of the input. You can specify as few as one Flow and presently, as many as two. The only requirement is when you have more than one is that each Flow is in a separate Availability Zone as this ensures your EML input is redundant to AZ issues.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of the input.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The Amazon Resource Name (ARN) of the role this input assumes during and after creation.',
        ),
    ]

    sources: Annotated[
        Optional[list[InputSourceRequest]],
        Field(
            None,
            alias='Sources',
            description='The source URLs for a PULL-type input. Every PULL type input needs exactly two source URLs for redundancy. Only specify sources for PULL type Inputs. Leave Destinations empty.',
        ),
    ]

    srt_settings: Annotated[
        Optional[SrtSettingsRequest],
        Field(
            None,
            alias='SrtSettings',
            description='The settings associated with an SRT input.',
        ),
    ]

    multicast_settings: Annotated[
        Optional[MulticastSettingsUpdateRequest],
        Field(
            None,
            alias='MulticastSettings',
            description='Multicast Input settings.',
        ),
    ]

    smpte2110_receiver_group_settings: Annotated[
        Optional[Smpte2110ReceiverGroupSettings],
        Field(
            None,
            alias='Smpte2110ReceiverGroupSettings',
            description='Include this parameter if the input is a SMPTE 2110 input, to identify the stream sources for this input.',
        ),
    ]

    sdi_sources: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SdiSources',
            description='',
        ),
    ]


class UpdateInputResponse(BaseModel):
    """Placeholder documentation for UpdateInputResponse."""

    model_config = ConfigDict(populate_by_name=True)

    input: Annotated[
        Optional[Input],
        Field(
            None,
            alias='Input',
            description='',
        ),
    ]


class UpdateInputResultModel(BaseModel):
    """Placeholder documentation for UpdateInputResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    input: Annotated[
        Optional[Input],
        Field(
            None,
            alias='Input',
            description='',
        ),
    ]


class UpdateInputSecurityGroupRequest(BaseModel):
    """The request to update some combination of the Input Security Group name and the IPv4 CIDRs the Input Security Group should allow."""

    model_config = ConfigDict(populate_by_name=True)

    input_security_group_id: Annotated[
        str,
        Field(
            ...,
            alias='InputSecurityGroupId',
            description='The id of the Input Security Group to update.',
        ),
    ]

    tags: Annotated[
        Optional[dict[str, str]],
        Field(
            None,
            alias='Tags',
            description='A collection of key-value pairs.',
        ),
    ]

    whitelist_rules: Annotated[
        Optional[list[InputWhitelistRuleCidr]],
        Field(
            None,
            alias='WhitelistRules',
            description='List of IPv4 CIDR addresses to whitelist',
        ),
    ]


class UpdateInputSecurityGroupResponse(BaseModel):
    """Placeholder documentation for UpdateInputSecurityGroupResponse."""

    model_config = ConfigDict(populate_by_name=True)

    security_group: Annotated[
        Optional[InputSecurityGroup],
        Field(
            None,
            alias='SecurityGroup',
            description='',
        ),
    ]


class UpdateInputSecurityGroupResultModel(BaseModel):
    """Placeholder documentation for UpdateInputSecurityGroupResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    security_group: Annotated[
        Optional[InputSecurityGroup],
        Field(
            None,
            alias='SecurityGroup',
            description='',
        ),
    ]


class UpdateMultiplex(BaseModel):
    """Placeholder documentation for UpdateMultiplex."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_settings: Annotated[
        Optional[MultiplexSettings],
        Field(
            None,
            alias='MultiplexSettings',
            description='The new settings for a multiplex.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of the multiplex.',
        ),
    ]

    packet_identifiers_mapping: Annotated[
        Optional[dict[str, MultiplexProgramPacketIdentifiersMap]],
        Field(
            None,
            alias='PacketIdentifiersMapping',
            description='',
        ),
    ]


class UpdateMultiplexProgram(BaseModel):
    """Placeholder documentation for UpdateMultiplexProgram."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_program_settings: Annotated[
        Optional[MultiplexProgramSettings],
        Field(
            None,
            alias='MultiplexProgramSettings',
            description='The new settings for a multiplex program.',
        ),
    ]


class UpdateMultiplexProgramRequest(BaseModel):
    """A request to update a program in a multiplex."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='The ID of the multiplex of the program to update.',
        ),
    ]

    multiplex_program_settings: Annotated[
        Optional[MultiplexProgramSettings],
        Field(
            None,
            alias='MultiplexProgramSettings',
            description='The new settings for a multiplex program.',
        ),
    ]

    program_name: Annotated[
        str,
        Field(
            ...,
            alias='ProgramName',
            description='The name of the program to update.',
        ),
    ]


class UpdateMultiplexProgramResponse(BaseModel):
    """Placeholder documentation for UpdateMultiplexProgramResponse."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_program: Annotated[
        Optional[MultiplexProgram],
        Field(
            None,
            alias='MultiplexProgram',
            description='The updated multiplex program.',
        ),
    ]


class UpdateMultiplexProgramResultModel(BaseModel):
    """Placeholder documentation for UpdateMultiplexProgramResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_program: Annotated[
        Optional[MultiplexProgram],
        Field(
            None,
            alias='MultiplexProgram',
            description='The updated multiplex program.',
        ),
    ]


class UpdateMultiplexRequest(BaseModel):
    """A request to update a multiplex."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        str,
        Field(
            ...,
            alias='MultiplexId',
            description='ID of the multiplex to update.',
        ),
    ]

    multiplex_settings: Annotated[
        Optional[MultiplexSettings],
        Field(
            None,
            alias='MultiplexSettings',
            description='The new settings for a multiplex.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of the multiplex.',
        ),
    ]

    packet_identifiers_mapping: Annotated[
        Optional[dict[str, MultiplexProgramPacketIdentifiersMap]],
        Field(
            None,
            alias='PacketIdentifiersMapping',
            description='',
        ),
    ]


class UpdateMultiplexResponse(BaseModel):
    """Placeholder documentation for UpdateMultiplexResponse."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex: Annotated[
        Optional[Multiplex],
        Field(
            None,
            alias='Multiplex',
            description='The updated multiplex.',
        ),
    ]


class UpdateMultiplexResultModel(BaseModel):
    """Placeholder documentation for UpdateMultiplexResultModel."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex: Annotated[
        Optional[Multiplex],
        Field(
            None,
            alias='Multiplex',
            description='The updated multiplex.',
        ),
    ]


class UpdateNetworkRequest(BaseModel):
    """A request to update the network."""

    model_config = ConfigDict(populate_by_name=True)

    ip_pools: Annotated[
        Optional[list[IpPoolUpdateRequest]],
        Field(
            None,
            alias='IpPools',
            description='Include this parameter only if you want to change the pool of IP addresses in the network. An array of IpPoolCreateRequests that identify a collection of IP addresses in this network that you want to reserve for use in MediaLive Anywhere. MediaLive Anywhere uses these IP addresses for Push inputs (in both Bridge and NAT networks) and for output destinations (only in Bridge networks). Each IpPoolUpdateRequest specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Include this parameter only if you want to change the name of the Network. Specify a name that is unique in the AWS account. Names are case-sensitive.',
        ),
    ]

    network_id: Annotated[
        str,
        Field(
            ...,
            alias='NetworkId',
            description='The ID of the network',
        ),
    ]

    routes: Annotated[
        Optional[list[RouteUpdateRequest]],
        Field(
            None,
            alias='Routes',
            description='Include this parameter only if you want to change or add routes in the Network. An array of Routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]


class UpdateNetworkResponse(BaseModel):
    """Placeholder documentation for UpdateNetworkResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Network. It is automatically assigned when the Network is created.',
        ),
    ]

    associated_cluster_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AssociatedClusterIds',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Network. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    ip_pools: Annotated[
        Optional[list[IpPool]],
        Field(
            None,
            alias='IpPools',
            description='An array of IpPools in your organization\u0027s network that identify a collection of IP addresses in this network that are reserved for use in MediaLive Anywhere. MediaLive Anywhere uses these IP addresses for Push inputs (in both Bridge and NAT networks) and for output destinations (only in Bridge networks). Each IpPool specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Network.',
        ),
    ]

    routes: Annotated[
        Optional[list[Route]],
        Field(
            None,
            alias='Routes',
            description='An array of Routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]

    state: Annotated[
        Optional[NetworkState],
        Field(
            None,
            alias='State',
            description='The current state of the Network. Only MediaLive Anywhere can change the state.',
        ),
    ]


class UpdateNetworkResult(BaseModel):
    """Contains the response for the UpdateNetwork."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of this Network. It is automatically assigned when the Network is created.',
        ),
    ]

    associated_cluster_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AssociatedClusterIds',
            description='',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The ID of the Network. Unique in the AWS account. The ID is the resource-id portion of the ARN.',
        ),
    ]

    ip_pools: Annotated[
        Optional[list[IpPool]],
        Field(
            None,
            alias='IpPools',
            description='An array of IpPools in your organization\u0027s network that identify a collection of IP addresses in this network that are reserved for use in MediaLive Anywhere. MediaLive Anywhere uses these IP addresses for Push inputs (in both Bridge and NAT networks) and for output destinations (only in Bridge networks). Each IpPool specifies one CIDR block.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Network.',
        ),
    ]

    routes: Annotated[
        Optional[list[Route]],
        Field(
            None,
            alias='Routes',
            description='An array of Routes that MediaLive Anywhere needs to know about in order to route encoding traffic.',
        ),
    ]

    state: Annotated[
        Optional[NetworkState],
        Field(
            None,
            alias='State',
            description='The current state of the Network. Only MediaLive Anywhere can change the state.',
        ),
    ]


class UpdateNodeRequest(BaseModel):
    """A request to update the node."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Include this parameter only if you want to change the current name of the Node. Specify a name that is unique in the Cluster. You can\u0027t change the name. Names are case-sensitive.',
        ),
    ]

    node_id: Annotated[
        str,
        Field(
            ...,
            alias='NodeId',
            description='The ID of the node.',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    sdi_source_mappings: Annotated[
        Optional[list[SdiSourceMappingUpdateRequest]],
        Field(
            None,
            alias='SdiSourceMappings',
            description='The mappings of a SDI capture card port to a logical SDI data stream',
        ),
    ]


class UpdateNodeResponse(BaseModel):
    """Placeholder documentation for UpdateNodeResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Node. It is automatically assigned when the Node is created.',
        ),
    ]

    channel_placement_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of IDs. Each ID is one ChannelPlacementGroup that is associated with this Node. Empty if the Node is not yet associated with any groups.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    connection_state: Annotated[
        Optional[NodeConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The current connection state of the Node.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Node. Unique in the Cluster. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceArn',
            description='The ARN of the EC2 instance hosting the Node.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Node.',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMapping]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role current role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    state: Annotated[
        Optional[NodeState],
        Field(
            None,
            alias='State',
            description='The current state of the Node.',
        ),
    ]

    sdi_source_mappings: Annotated[
        Optional[list[SdiSourceMapping]],
        Field(
            None,
            alias='SdiSourceMappings',
            description='An array of SDI source mappings. Each mapping connects one logical SdiSource to the physical SDI card and port that the physical SDI source uses.',
        ),
    ]


class UpdateNodeStateRequest(BaseModel):
    """A request to update the state of a node."""

    model_config = ConfigDict(populate_by_name=True)

    cluster_id: Annotated[
        str,
        Field(
            ...,
            alias='ClusterId',
            description='The ID of the cluster',
        ),
    ]

    node_id: Annotated[
        str,
        Field(
            ...,
            alias='NodeId',
            description='The ID of the node.',
        ),
    ]

    state: Annotated[
        Optional[UpdateNodeState],
        Field(
            None,
            alias='State',
            description='The state to apply to the Node. Set to ACTIVE (COMMISSIONED) to indicate that the Node is deployable. MediaLive Anywhere will consider this node it needs a Node to run a Channel on, or when it needs a Node to promote from a backup node to an active node. Set to DRAINING to isolate the Node so that MediaLive Anywhere won\u0027t use it.',
        ),
    ]


class UpdateNodeStateResponse(BaseModel):
    """Placeholder documentation for UpdateNodeStateResponse."""

    model_config = ConfigDict(populate_by_name=True)

    arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='Arn',
            description='The ARN of the Node. It is automatically assigned when the Node is created.',
        ),
    ]

    channel_placement_groups: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='ChannelPlacementGroups',
            description='An array of IDs. Each ID is one ChannelPlacementGroup that is associated with this Node. Empty if the Node is not yet associated with any groups.',
        ),
    ]

    cluster_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ClusterId',
            description='The ID of the Cluster that the Node belongs to.',
        ),
    ]

    connection_state: Annotated[
        Optional[NodeConnectionState],
        Field(
            None,
            alias='ConnectionState',
            description='The current connection state of the Node.',
        ),
    ]

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID of the Node. Unique in the Cluster. The ID is the resource-id portion of the ARN.',
        ),
    ]

    instance_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='InstanceArn',
            description='The ARN of the EC2 instance hosting the Node.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='The name that you specified for the Node.',
        ),
    ]

    node_interface_mappings: Annotated[
        Optional[list[NodeInterfaceMapping]],
        Field(
            None,
            alias='NodeInterfaceMappings',
            description='Documentation update needed',
        ),
    ]

    role: Annotated[
        Optional[NodeRole],
        Field(
            None,
            alias='Role',
            description='The initial role current role of the Node in the Cluster. ACTIVE means the Node is available for encoding. BACKUP means the Node is a redundant Node and might get used if an ACTIVE Node fails.',
        ),
    ]

    state: Annotated[
        Optional[NodeState],
        Field(
            None,
            alias='State',
            description='The current state of the Node.',
        ),
    ]

    sdi_source_mappings: Annotated[
        Optional[list[SdiSourceMapping]],
        Field(
            None,
            alias='SdiSourceMappings',
            description='An array of SDI source mappings. Each mapping connects one logical SdiSource to the physical SDI card and port that the physical SDI source uses.',
        ),
    ]


class UpdateReservation(BaseModel):
    """UpdateReservation request."""

    model_config = ConfigDict(populate_by_name=True)

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of the reservation',
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


class UpdateReservationRequest(BaseModel):
    """Request to update a reservation."""

    model_config = ConfigDict(populate_by_name=True)

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Name of the reservation',
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
        str,
        Field(
            ...,
            alias='ReservationId',
            description='Unique reservation ID, e.g. \u00271234567\u0027',
        ),
    ]


class UpdateReservationResponse(BaseModel):
    """Placeholder documentation for UpdateReservationResponse."""

    model_config = ConfigDict(populate_by_name=True)

    reservation: Annotated[
        Optional[Reservation],
        Field(
            None,
            alias='Reservation',
            description='',
        ),
    ]


class UpdateReservationResultModel(BaseModel):
    """UpdateReservation response."""

    model_config = ConfigDict(populate_by_name=True)

    reservation: Annotated[
        Optional[Reservation],
        Field(
            None,
            alias='Reservation',
            description='',
        ),
    ]


class UpdateSdiSourceRequest(BaseModel):
    """A request to update the SdiSource."""

    model_config = ConfigDict(populate_by_name=True)

    mode: Annotated[
        Optional[SdiSourceMode],
        Field(
            None,
            alias='Mode',
            description='Include this parameter only if you want to change the name of the SdiSource. Specify a name that is unique in the AWS account. We recommend you assign a name that describes the source, for example curling-cameraA. Names are case-sensitive.',
        ),
    ]

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Include this parameter only if you want to change the name of the SdiSource. Specify a name that is unique in the AWS account. We recommend you assign a name that describes the source, for example curling-cameraA. Names are case-sensitive.',
        ),
    ]

    sdi_source_id: Annotated[
        str,
        Field(
            ...,
            alias='SdiSourceId',
            description='The ID of the SdiSource',
        ),
    ]

    type: Annotated[
        Optional[SdiSourceType],
        Field(
            None,
            alias='Type',
            description='Include this parameter only if you want to change the mode. Specify the type of the SDI source: SINGLE: The source is a single-link source. QUAD: The source is one part of a quad-link source.',
        ),
    ]


class UpdateSdiSourceResponse(BaseModel):
    """Placeholder documentation for UpdateSdiSourceResponse."""

    model_config = ConfigDict(populate_by_name=True)

    sdi_source: Annotated[
        Optional[SdiSource],
        Field(
            None,
            alias='SdiSource',
            description='Settings for the SDI source.',
        ),
    ]


class ValidationError(BaseModel):
    """Placeholder documentation for ValidationError."""

    model_config = ConfigDict(populate_by_name=True)

    element_path: Annotated[
        Optional[str],
        Field(
            None,
            alias='ElementPath',
            description='Path to the source of the error.',
        ),
    ]

    error_message: Annotated[
        Optional[str],
        Field(
            None,
            alias='ErrorMessage',
            description='The error message.',
        ),
    ]


class UnprocessableEntityException(BaseModel):
    """Placeholder documentation for UnprocessableEntityException."""

    model_config = ConfigDict(populate_by_name=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            alias='Message',
            description='The error message.',
        ),
    ]

    validation_errors: Annotated[
        Optional[list[ValidationError]],
        Field(
            None,
            alias='ValidationErrors',
            description='A collection of validation error responses.',
        ),
    ]


class WavSettings(BaseModel):
    """Wav Settings."""

    model_config = ConfigDict(populate_by_name=True)

    bit_depth: Annotated[
        Optional[float],
        Field(
            None,
            alias='BitDepth',
            description='Bits per sample.',
        ),
    ]

    coding_mode: Annotated[
        Optional[WavCodingMode],
        Field(
            None,
            alias='CodingMode',
            description='The audio coding mode for the WAV audio. The mode determines the number of channels in the audio.',
        ),
    ]

    sample_rate: Annotated[
        Optional[float],
        Field(
            None,
            alias='SampleRate',
            description='Sample rate in Hz.',
        ),
    ]


class AudioCodecSettings(BaseModel):
    """Audio Codec Settings."""

    model_config = ConfigDict(populate_by_name=True)

    aac_settings: Annotated[
        Optional[AacSettings],
        Field(
            None,
            alias='AacSettings',
            description='',
        ),
    ]

    ac3_settings: Annotated[
        Optional[Ac3Settings],
        Field(
            None,
            alias='Ac3Settings',
            description='',
        ),
    ]

    eac3_atmos_settings: Annotated[
        Optional[Eac3AtmosSettings],
        Field(
            None,
            alias='Eac3AtmosSettings',
            description='',
        ),
    ]

    eac3_settings: Annotated[
        Optional[Eac3Settings],
        Field(
            None,
            alias='Eac3Settings',
            description='',
        ),
    ]

    mp2_settings: Annotated[
        Optional[Mp2Settings],
        Field(
            None,
            alias='Mp2Settings',
            description='',
        ),
    ]

    pass_through_settings: Annotated[
        Optional[PassThroughSettings],
        Field(
            None,
            alias='PassThroughSettings',
            description='',
        ),
    ]

    wav_settings: Annotated[
        Optional[WavSettings],
        Field(
            None,
            alias='WavSettings',
            description='',
        ),
    ]


class AudioDescription(BaseModel):
    """Audio Description."""

    model_config = ConfigDict(populate_by_name=True)

    audio_normalization_settings: Annotated[
        Optional[AudioNormalizationSettings],
        Field(
            None,
            alias='AudioNormalizationSettings',
            description='Advanced audio normalization settings.',
        ),
    ]

    audio_selector_name: Annotated[
        str,
        Field(
            ...,
            alias='AudioSelectorName',
            description='The name of the AudioSelector used as the source for this AudioDescription.',
        ),
    ]

    audio_type: Annotated[
        Optional[AudioType],
        Field(
            None,
            alias='AudioType',
            description='Applies only if audioTypeControl is useConfigured. The values for audioType are defined in ISO-IEC 13818-1.',
        ),
    ]

    audio_type_control: Annotated[
        Optional[AudioDescriptionAudioTypeControl],
        Field(
            None,
            alias='AudioTypeControl',
            description='Determines how audio type is determined. followInput: If the input contains an ISO 639 audioType, then that value is passed through to the output. If the input contains no ISO 639 audioType, the value in Audio Type is included in the output. useConfigured: The value in Audio Type is included in the output. Note that this field and audioType are both ignored if inputType is broadcasterMixedAd.',
        ),
    ]

    audio_watermarking_settings: Annotated[
        Optional[AudioWatermarkSettings],
        Field(
            None,
            alias='AudioWatermarkingSettings',
            description='Settings to configure one or more solutions that insert audio watermarks in the audio encode',
        ),
    ]

    codec_settings: Annotated[
        Optional[AudioCodecSettings],
        Field(
            None,
            alias='CodecSettings',
            description='Audio codec settings.',
        ),
    ]

    language_code: Annotated[
        Optional[str],
        Field(
            None,
            alias='LanguageCode',
            description='RFC 5646 language code representing the language of the audio output track. Only used if languageControlMode is useConfigured, or there is no ISO 639 language code specified in the input.',
        ),
    ]

    language_code_control: Annotated[
        Optional[AudioDescriptionLanguageCodeControl],
        Field(
            None,
            alias='LanguageCodeControl',
            description='Choosing followInput will cause the ISO 639 language code of the output to follow the ISO 639 language code of the input. The languageCode will be used when useConfigured is set, or when followInput is selected but there is no ISO 639 language code specified by the input.',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='The name of this AudioDescription. Outputs will use this name to uniquely identify this AudioDescription. Description names should be unique within this Live Event.',
        ),
    ]

    remix_settings: Annotated[
        Optional[RemixSettings],
        Field(
            None,
            alias='RemixSettings',
            description='Settings that control how input audio channels are remixed into the output audio channels.',
        ),
    ]

    stream_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='StreamName',
            description='Used for MS Smooth and Apple HLS outputs. Indicates the name displayed by the player (eg. English, or Director Commentary).',
        ),
    ]

    audio_dash_roles: Annotated[
        Optional[list[DashRoleAudio]],
        Field(
            None,
            alias='AudioDashRoles',
            description='Identifies the DASH roles to assign to this audio output. Applies only when the audio output is configured for DVB DASH accessibility signaling.',
        ),
    ]

    dvb_dash_accessibility: Annotated[
        Optional[DvbDashAccessibility],
        Field(
            None,
            alias='DvbDashAccessibility',
            description='Identifies DVB DASH accessibility signaling in this audio output. Used in Microsoft Smooth Streaming outputs to signal accessibility information to packagers.',
        ),
    ]


class WebvttDestinationSettings(BaseModel):
    """Webvtt Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)

    style_control: Annotated[
        Optional[WebvttDestinationStyleControl],
        Field(
            None,
            alias='StyleControl',
            description='Controls whether the color and position of the source captions is passed through to the WebVTT output captions. PASSTHROUGH - Valid only if the source captions are EMBEDDED or TELETEXT. NO_STYLE_DATA - Don\u0027t pass through the style. The output captions will not contain any font styling information.',
        ),
    ]


class CaptionDestinationSettings(BaseModel):
    """Caption Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)

    arib_destination_settings: Annotated[
        Optional[AribDestinationSettings],
        Field(
            None,
            alias='AribDestinationSettings',
            description='',
        ),
    ]

    burn_in_destination_settings: Annotated[
        Optional[BurnInDestinationSettings],
        Field(
            None,
            alias='BurnInDestinationSettings',
            description='',
        ),
    ]

    dvb_sub_destination_settings: Annotated[
        Optional[DvbSubDestinationSettings],
        Field(
            None,
            alias='DvbSubDestinationSettings',
            description='',
        ),
    ]

    ebu_tt_d_destination_settings: Annotated[
        Optional[EbuTtDDestinationSettings],
        Field(
            None,
            alias='EbuTtDDestinationSettings',
            description='',
        ),
    ]

    embedded_destination_settings: Annotated[
        Optional[EmbeddedDestinationSettings],
        Field(
            None,
            alias='EmbeddedDestinationSettings',
            description='',
        ),
    ]

    embedded_plus_scte20_destination_settings: Annotated[
        Optional[EmbeddedPlusScte20DestinationSettings],
        Field(
            None,
            alias='EmbeddedPlusScte20DestinationSettings',
            description='',
        ),
    ]

    rtmp_caption_info_destination_settings: Annotated[
        Optional[RtmpCaptionInfoDestinationSettings],
        Field(
            None,
            alias='RtmpCaptionInfoDestinationSettings',
            description='',
        ),
    ]

    scte20_plus_embedded_destination_settings: Annotated[
        Optional[Scte20PlusEmbeddedDestinationSettings],
        Field(
            None,
            alias='Scte20PlusEmbeddedDestinationSettings',
            description='',
        ),
    ]

    scte27_destination_settings: Annotated[
        Optional[Scte27DestinationSettings],
        Field(
            None,
            alias='Scte27DestinationSettings',
            description='',
        ),
    ]

    smpte_tt_destination_settings: Annotated[
        Optional[SmpteTtDestinationSettings],
        Field(
            None,
            alias='SmpteTtDestinationSettings',
            description='',
        ),
    ]

    teletext_destination_settings: Annotated[
        Optional[TeletextDestinationSettings],
        Field(
            None,
            alias='TeletextDestinationSettings',
            description='',
        ),
    ]

    ttml_destination_settings: Annotated[
        Optional[TtmlDestinationSettings],
        Field(
            None,
            alias='TtmlDestinationSettings',
            description='',
        ),
    ]

    webvtt_destination_settings: Annotated[
        Optional[WebvttDestinationSettings],
        Field(
            None,
            alias='WebvttDestinationSettings',
            description='',
        ),
    ]


class CaptionDescription(BaseModel):
    """Caption Description."""

    model_config = ConfigDict(populate_by_name=True)

    accessibility: Annotated[
        Optional[AccessibilityType],
        Field(
            None,
            alias='Accessibility',
            description='Indicates whether the caption track implements accessibility features such as written descriptions of spoken dialog, music, and sounds. This signaling is added to HLS output group and MediaPackage output group.',
        ),
    ]

    caption_selector_name: Annotated[
        str,
        Field(
            ...,
            alias='CaptionSelectorName',
            description='Specifies which input caption selector to use as a caption source when generating output captions. This field should match a captionSelector name.',
        ),
    ]

    destination_settings: Annotated[
        Optional[CaptionDestinationSettings],
        Field(
            None,
            alias='DestinationSettings',
            description='Additional settings for captions destination that depend on the destination type.',
        ),
    ]

    language_code: Annotated[
        Optional[str],
        Field(
            None,
            alias='LanguageCode',
            description='ISO 639-2 three-digit code: http://www.loc.gov/standards/iso639-2/',
        ),
    ]

    language_description: Annotated[
        Optional[str],
        Field(
            None,
            alias='LanguageDescription',
            description='Human readable information to indicate captions available for players (eg. English, or Spanish).',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='Name of the caption description. Used to associate a caption description with an output. Names must be unique within an event.',
        ),
    ]

    caption_dash_roles: Annotated[
        Optional[list[DashRoleCaption]],
        Field(
            None,
            alias='CaptionDashRoles',
            description='Identifies the DASH roles to assign to this captions output. Applies only when the captions output is configured for DVB DASH accessibility signaling.',
        ),
    ]

    dvb_dash_accessibility: Annotated[
        Optional[DvbDashAccessibility],
        Field(
            None,
            alias='DvbDashAccessibility',
            description='Identifies DVB DASH accessibility signaling in this captions output. Used in Microsoft Smooth Streaming outputs to signal accessibility information to packagers.',
        ),
    ]
