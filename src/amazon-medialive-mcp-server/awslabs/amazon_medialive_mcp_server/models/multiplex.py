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

"""Multiplex-related Pydantic models — multiplex and multiplex program management."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    M2tsAbsentInputAudioBehavior,
    M2tsArib,
    M2tsAudioBufferModel,
    M2tsAudioStreamType,
    M2tsCcDescriptor,
    M2tsEbifControl,
    M2tsEsRateInPes,
    M2tsKlv,
    M2tsNielsenId3Behavior,
    M2tsPcrControl,
    M2tsScte35Control,
    MultiplexState,
    PreferredChannelPipeline,
)
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.common import ValidationError
    from awslabs.amazon_medialive_mcp_server.models.output import (
        OutputLocationRef,
    )


class MultiplexGroupSettings(BaseModel):
    """Multiplex Group Settings."""

    model_config = ConfigDict(populate_by_name=True)


class MultiplexM2tsSettings(BaseModel):
    """Multiplex M2ts Settings."""

    model_config = ConfigDict(populate_by_name=True)

    absent_input_audio_behavior: Annotated[
        Optional[M2tsAbsentInputAudioBehavior],
        Field(
            None,
            alias='AbsentInputAudioBehavior',
            description='When set to drop, output audio streams will be removed from the program if the selected input audio stream is removed from the input. This allows the output audio configuration to dynamically change based on input configuration. If this is set to encodeSilence, all output audio streams will output encoded silence when not connected to an active input stream.',
        ),
    ]

    arib: Annotated[
        Optional[M2tsArib],
        Field(
            None,
            alias='Arib',
            description='When set to enabled, uses ARIB-compliant field muxing and removes video descriptor.',
        ),
    ]

    audio_buffer_model: Annotated[
        Optional[M2tsAudioBufferModel],
        Field(
            None,
            alias='AudioBufferModel',
            description='When set to dvb, uses DVB buffer model for Dolby Digital audio. When set to atsc, the ATSC model is used.',
        ),
    ]

    audio_frames_per_pes: Annotated[
        Optional[int],
        Field(
            None,
            alias='AudioFramesPerPes',
            description='The number of audio frames to insert for each PES packet.',
        ),
    ]

    audio_stream_type: Annotated[
        Optional[M2tsAudioStreamType],
        Field(
            None,
            alias='AudioStreamType',
            description='When set to atsc, uses stream type = 0x81 for AC3 and stream type = 0x87 for EAC3. When set to dvb, uses stream type = 0x06.',
        ),
    ]

    cc_descriptor: Annotated[
        Optional[M2tsCcDescriptor],
        Field(
            None,
            alias='CcDescriptor',
            description='When set to enabled, generates captionServiceDescriptor in PMT.',
        ),
    ]

    ebif: Annotated[
        Optional[M2tsEbifControl],
        Field(
            None,
            alias='Ebif',
            description='If set to passthrough, passes any EBIF data from the input source to this output.',
        ),
    ]

    es_rate_in_pes: Annotated[
        Optional[M2tsEsRateInPes],
        Field(
            None,
            alias='EsRateInPes',
            description='Include or exclude the ES Rate field in the PES header.',
        ),
    ]

    klv: Annotated[
        Optional[M2tsKlv],
        Field(
            None,
            alias='Klv',
            description='If set to passthrough, passes any KLV data from the input source to this output.',
        ),
    ]

    nielsen_id3_behavior: Annotated[
        Optional[M2tsNielsenId3Behavior],
        Field(
            None,
            alias='NielsenId3Behavior',
            description='If set to passthrough, Nielsen inaudible tones for media tracking will be detected in the input audio and an equivalent ID3 tag will be inserted in the output.',
        ),
    ]

    pcr_control: Annotated[
        Optional[M2tsPcrControl],
        Field(
            None,
            alias='PcrControl',
            description='When set to pcrEveryPesPacket, a Program Clock Reference value is inserted for every Packetized Elementary Stream (PES) header. This parameter is effective only when the PCR PID is the same as the video or audio elementary stream.',
        ),
    ]

    pcr_period: Annotated[
        Optional[int],
        Field(
            None,
            alias='PcrPeriod',
            description='Maximum time in milliseconds between Program Clock Reference (PCRs) inserted into the transport stream.',
        ),
    ]

    scte35_control: Annotated[
        Optional[M2tsScte35Control],
        Field(
            None,
            alias='Scte35Control',
            description='Optionally pass SCTE-35 signals from the input source to this output.',
        ),
    ]

    scte35_preroll_pullup_milliseconds: Annotated[
        Optional[float],
        Field(
            None,
            alias='Scte35PrerollPullupMilliseconds',
            description='Defines the amount SCTE-35 preroll will be increased (in milliseconds) on the output. Preroll is the amount of time between the presence of a SCTE-35 indication in a transport stream and the PTS of the video frame it references. Zero means don\u0027t add pullup (it doesn\u0027t mean set the preroll to zero). Negative pullup is not supported, which means that you can\u0027t make the preroll shorter. Be aware that latency in the output will increase by the pullup amount.',
        ),
    ]


class MultiplexContainerSettings(BaseModel):
    """Multiplex Container Settings."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_m2ts_settings: Annotated[
        Optional[MultiplexM2tsSettings],
        Field(
            None,
            alias='MultiplexM2tsSettings',
            description='',
        ),
    ]


class MultiplexMediaConnectOutputDestinationSettings(BaseModel):
    """Multiplex MediaConnect output destination settings."""

    model_config = ConfigDict(populate_by_name=True)

    entitlement_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='EntitlementArn',
            description='The MediaConnect entitlement ARN available as a Flow source.',
        ),
    ]


class MultiplexOutputDestination(BaseModel):
    """Multiplex output destination settings."""

    model_config = ConfigDict(populate_by_name=True)

    media_connect_settings: Annotated[
        Optional[MultiplexMediaConnectOutputDestinationSettings],
        Field(
            None,
            alias='MediaConnectSettings',
            description='Multiplex MediaConnect output destination settings.',
        ),
    ]


class MultiplexProgramChannelDestinationSettings(BaseModel):
    """Multiplex Program Input Destination Settings for outputting a Channel to a Multiplex."""

    model_config = ConfigDict(populate_by_name=True)

    multiplex_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='MultiplexId',
            description='The ID of the Multiplex that the encoder is providing output to. You do not need to specify the individual inputs to the Multiplex; MediaLive will handle the connection of the two MediaLive pipelines to the two Multiplex instances. The Multiplex must be in the same region as the Channel.',
        ),
    ]

    program_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ProgramName',
            description='The program name of the Multiplex program that the encoder is providing output to.',
        ),
    ]


class MultiplexProgramPacketIdentifiersMap(BaseModel):
    """Packet identifiers map for a given Multiplex program."""

    model_config = ConfigDict(populate_by_name=True)

    audio_pids: Annotated[
        Optional[list[int]],
        Field(
            None,
            alias='AudioPids',
            description='',
        ),
    ]

    dvb_sub_pids: Annotated[
        Optional[list[int]],
        Field(
            None,
            alias='DvbSubPids',
            description='',
        ),
    ]

    dvb_teletext_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='DvbTeletextPid',
            description='',
        ),
    ]

    etv_platform_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='EtvPlatformPid',
            description='',
        ),
    ]

    etv_signal_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='EtvSignalPid',
            description='',
        ),
    ]

    klv_data_pids: Annotated[
        Optional[list[int]],
        Field(
            None,
            alias='KlvDataPids',
            description='',
        ),
    ]

    pcr_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='PcrPid',
            description='',
        ),
    ]

    pmt_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='PmtPid',
            description='',
        ),
    ]

    private_metadata_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='PrivateMetadataPid',
            description='',
        ),
    ]

    scte27_pids: Annotated[
        Optional[list[int]],
        Field(
            None,
            alias='Scte27Pids',
            description='',
        ),
    ]

    scte35_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='Scte35Pid',
            description='',
        ),
    ]

    timed_metadata_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='TimedMetadataPid',
            description='',
        ),
    ]

    video_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='VideoPid',
            description='',
        ),
    ]

    arib_captions_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='AribCaptionsPid',
            description='',
        ),
    ]

    dvb_teletext_pids: Annotated[
        Optional[list[int]],
        Field(
            None,
            alias='DvbTeletextPids',
            description='',
        ),
    ]

    ecm_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='EcmPid',
            description='',
        ),
    ]

    smpte2038_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='Smpte2038Pid',
            description='',
        ),
    ]


class MultiplexProgramPipelineDetail(BaseModel):
    """The current source for one of the pipelines in the multiplex."""

    model_config = ConfigDict(populate_by_name=True)

    active_channel_pipeline: Annotated[
        Optional[str],
        Field(
            None,
            alias='ActiveChannelPipeline',
            description='Identifies the channel pipeline that is currently active for the pipeline (identified by PipelineId) in the multiplex.',
        ),
    ]

    pipeline_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='PipelineId',
            description='Identifies a specific pipeline in the multiplex.',
        ),
    ]


class MultiplexProgramServiceDescriptor(BaseModel):
    """Transport stream service descriptor configuration for the Multiplex program."""

    model_config = ConfigDict(populate_by_name=True)

    provider_name: Annotated[
        str,
        Field(
            ...,
            alias='ProviderName',
            description='Name of the provider.',
        ),
    ]

    service_name: Annotated[
        str,
        Field(
            ...,
            alias='ServiceName',
            description='Name of the service.',
        ),
    ]


class MultiplexProgramSummary(BaseModel):
    """Placeholder documentation for MultiplexProgramSummary."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelId',
            description='The MediaLive Channel associated with the program.',
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


class MultiplexSettings(BaseModel):
    """Contains configuration for a Multiplex event."""

    model_config = ConfigDict(populate_by_name=True)

    maximum_video_buffer_delay_milliseconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaximumVideoBufferDelayMilliseconds',
            description='Maximum video buffer delay in milliseconds.',
        ),
    ]

    transport_stream_bitrate: Annotated[
        int,
        Field(
            ...,
            alias='TransportStreamBitrate',
            description='Transport stream bit rate.',
        ),
    ]

    transport_stream_id: Annotated[
        int,
        Field(
            ...,
            alias='TransportStreamId',
            description='Transport stream ID.',
        ),
    ]

    transport_stream_reserved_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='TransportStreamReservedBitrate',
            description='Transport stream reserved bit rate.',
        ),
    ]


class Multiplex(BaseModel):
    """The multiplex object."""

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


class MultiplexSettingsSummary(BaseModel):
    """Contains summary configuration for a Multiplex event."""

    model_config = ConfigDict(populate_by_name=True)

    transport_stream_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='TransportStreamBitrate',
            description='Transport stream bit rate.',
        ),
    ]


class MultiplexStatmuxVideoSettings(BaseModel):
    """Statmux rate control settings."""

    model_config = ConfigDict(populate_by_name=True)

    maximum_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaximumBitrate',
            description='Maximum statmux bitrate.',
        ),
    ]

    minimum_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinimumBitrate',
            description='Minimum statmux bitrate.',
        ),
    ]

    priority: Annotated[
        Optional[int],
        Field(
            None,
            alias='Priority',
            description='The purpose of the priority is to use a combination of the\\nmultiplex rate control algorithm and the QVBR capability of the\\nencoder to prioritize the video quality of some channels in a\\nmultiplex over others. Channels that have a higher priority will\\nget higher video quality at the expense of the video quality of\\nother channels in the multiplex with lower priority.',
        ),
    ]


class MultiplexSummary(BaseModel):
    """Placeholder documentation for MultiplexSummary."""

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

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique id of the multiplex.',
        ),
    ]

    multiplex_settings: Annotated[
        Optional[MultiplexSettingsSummary],
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


class MultiplexVideoSettings(BaseModel):
    """The video configuration for each program in a multiplex."""

    model_config = ConfigDict(populate_by_name=True)

    constant_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='ConstantBitrate',
            description='The constant bitrate configuration for the video encode. When this field is defined, StatmuxSettings must be undefined.',
        ),
    ]

    statmux_settings: Annotated[
        Optional[MultiplexStatmuxVideoSettings],
        Field(
            None,
            alias='StatmuxSettings',
            description='Statmux rate control settings. When this field is defined, ConstantBitrate must be undefined.',
        ),
    ]


class MultiplexProgramSettings(BaseModel):
    """Multiplex Program settings configuration."""

    model_config = ConfigDict(populate_by_name=True)

    preferred_channel_pipeline: Annotated[
        Optional[PreferredChannelPipeline],
        Field(
            None,
            alias='PreferredChannelPipeline',
            description='Indicates which pipeline is preferred by the multiplex for program ingest.',
        ),
    ]

    program_number: Annotated[
        int,
        Field(
            ...,
            alias='ProgramNumber',
            description='Unique program number.',
        ),
    ]

    service_descriptor: Annotated[
        Optional[MultiplexProgramServiceDescriptor],
        Field(
            None,
            alias='ServiceDescriptor',
            description='Transport stream service descriptor configuration for the Multiplex program.',
        ),
    ]

    video_settings: Annotated[
        Optional[MultiplexVideoSettings],
        Field(
            None,
            alias='VideoSettings',
            description='Program video settings configuration.',
        ),
    ]


class MultiplexProgram(BaseModel):
    """The multiplex program object."""

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


class MultiplexOutputSettings(BaseModel):
    """Multiplex Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='Destination is a Multiplex.',
        ),
    ]

    container_settings: Annotated[
        Optional[MultiplexContainerSettings],
        Field(
            None,
            alias='ContainerSettings',
            description='',
        ),
    ]


class MultiplexConfigurationValidationError(BaseModel):
    """Placeholder documentation for MultiplexConfigurationValidationError."""

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
