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

"""Output-related Pydantic models — output groups, HLS/DASH/CMAF/RTMP/UDP packaging."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    AuthenticationScheme,
    CmafId3Behavior,
    CmafIngestSegmentLengthUnits,
    CmafKLVBehavior,
    CmafNielsenId3Behavior,
    CmafTimedMetadataId3Frame,
    CmafTimedMetadataPassthrough,
    FecOutputIncludeFec,
    Fmp4NielsenId3Behavior,
    Fmp4TimedMetadataBehavior,
    HlsAutoSelect,
    HlsDefault,
    IncludeFillerNalUnits,
    InputLossActionForMsSmoothOut,
    InputLossActionForRtmpOut,
    InputLossActionForUdpOut,
    M2tsAbsentInputAudioBehavior,
    M2tsArib,
    M2tsAribCaptionsPidControl,
    M2tsAudioBufferModel,
    M2tsAudioInterval,
    M2tsAudioStreamType,
    M2tsBufferModel,
    M2tsCcDescriptor,
    M2tsEbifControl,
    M2tsEbpPlacement,
    M2tsEsRateInPes,
    M2tsKlv,
    M2tsNielsenId3Behavior,
    M2tsPcrControl,
    M2tsRateMode,
    M2tsScte35Control,
    M2tsSegmentationMarkers,
    M2tsSegmentationStyle,
    M2tsTimedMetadataBehavior,
    M3u8KlvBehavior,
    M3u8NielsenId3Behavior,
    M3u8PcrControl,
    M3u8Scte35Behavior,
    M3u8TimedMetadataBehavior,
    MsSmoothH265PackagingType,
    RtmpAdMarkers,
    RtmpCacheFullBehavior,
    RtmpCaptionData,
    RtmpOutputCertificateMode,
    S3CannedAcl,
    Scte35Type,
    SmoothGroupAudioOnlyTimecodeControl,
    SmoothGroupCertificateMode,
    SmoothGroupEventIdMode,
    SmoothGroupEventStopBehavior,
    SmoothGroupSegmentationMode,
    SmoothGroupSparseTrackType,
    SmoothGroupStreamManifestBehavior,
    SmoothGroupTimestampOffsetMode,
    UdpTimedMetadataId3Frame,
)
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.channel import PipelineLockingSettings
    from awslabs.amazon_medialive_mcp_server.models.common import (
        AdditionalDestinations,
        CaptionLanguageMapping,
        DvbNitSettings,
        DvbSdtSettings,
        DvbTdtSettings,
    )
    from awslabs.amazon_medialive_mcp_server.models.encoding import (
        FrameCaptureGroupSettings,
        FrameCaptureOutputSettings,
    )
    from awslabs.amazon_medialive_mcp_server.models.input import (
        HlsGroupSettings,
        HlsOutputSettings,
        InputLocation,
        SrtGroupSettings,
        SrtOutputDestinationSettings,
        SrtOutputSettings,
    )
    from awslabs.amazon_medialive_mcp_server.models.multiplex import (
        MultiplexGroupSettings,
        MultiplexOutputSettings,
        MultiplexProgramChannelDestinationSettings,
    )


class ArchiveS3Settings(BaseModel):
    """Archive S3 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    canned_acl: Annotated[
        Optional[S3CannedAcl],
        Field(
            None,
            alias='CannedAcl',
            description='Specify the canned ACL to apply to each S3 request. Defaults to none.',
        ),
    ]


class ArchiveCdnSettings(BaseModel):
    """Archive Cdn Settings."""

    model_config = ConfigDict(populate_by_name=True)

    archive_s3_settings: Annotated[
        Optional[ArchiveS3Settings],
        Field(
            None,
            alias='ArchiveS3Settings',
            description='',
        ),
    ]


class CmafIngestCaptionLanguageMapping(BaseModel):
    """Add an array item for each language. Follow the order of the caption descriptions. For example, if the first caption description is for German, then the first array item must be for German, and its caption channel must be set to 1. The second array item must be 2, and so on."""

    model_config = ConfigDict(populate_by_name=True)

    caption_channel: Annotated[
        int,
        Field(
            ...,
            alias='CaptionChannel',
            description='A number for the channel for this caption, 1 to 4.',
        ),
    ]

    language_code: Annotated[
        str,
        Field(
            ...,
            alias='LanguageCode',
            description='Language code for the language of the caption in this channel. For example, ger/deu. See http://www.loc.gov/standards/iso639-2',
        ),
    ]


class CmafIngestOutputSettings(BaseModel):
    """Cmaf Ingest Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='NameModifier',
            description='String concatenated to the end of the destination filename. Required for multiple outputs of the same type.',
        ),
    ]


class EpochLockingSettings(BaseModel):
    """Epoch Locking Settings."""

    model_config = ConfigDict(populate_by_name=True)

    custom_epoch: Annotated[
        Optional[str],
        Field(
            None,
            alias='CustomEpoch',
            description='Optional. Enter a value here to use a custom epoch, instead of the standard epoch (which started at 1970-01-01T00:00:00 UTC). Specify the start time of the custom epoch, in YYYY-MM-DDTHH:MM:SS in UTC. The time must be 2000-01-01T00:00:00 or later. Always set the MM:SS portion to 00:00.',
        ),
    ]

    jam_sync_time: Annotated[
        Optional[str],
        Field(
            None,
            alias='JamSyncTime',
            description='Optional. Enter a time for the jam sync. The default is midnight UTC. When epoch locking is enabled, MediaLive performs a daily jam sync on every output encode to ensure timecodes don\u2019t diverge from the wall clock. The jam sync applies only to encodes with frame rate of 29.97 or 59.94 FPS. To override, enter a time in HH:MM:SS in UTC. Always set the MM:SS portion to 00:00.',
        ),
    ]


class FecOutputSettings(BaseModel):
    """Fec Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    column_depth: Annotated[
        Optional[int],
        Field(
            None,
            alias='ColumnDepth',
            description='Parameter D from SMPTE 2022-1. The height of the FEC protection matrix. The number of transport stream packets per column error correction packet. Must be between 4 and 20, inclusive.',
        ),
    ]

    include_fec: Annotated[
        Optional[FecOutputIncludeFec],
        Field(
            None,
            alias='IncludeFec',
            description='Enables column only or column and row based FEC',
        ),
    ]

    row_length: Annotated[
        Optional[int],
        Field(
            None,
            alias='RowLength',
            description='Parameter L from SMPTE 2022-1. The width of the FEC protection matrix. Must be between 1 and 20, inclusive. If only Column FEC is used, then larger values increase robustness. If Row FEC is used, then this is the number of transport stream packets per row error correction packet, and the value must be between 4 and 20, inclusive, if includeFec is columnAndRow. If includeFec is column, this value must be 1 to 20, inclusive.',
        ),
    ]


class Fmp4HlsSettings(BaseModel):
    """Fmp4 Hls Settings."""

    model_config = ConfigDict(populate_by_name=True)

    audio_rendition_sets: Annotated[
        Optional[str],
        Field(
            None,
            alias='AudioRenditionSets',
            description='List all the audio groups that are used with the video output stream. Input all the audio GROUP-IDs that are associated to the video, separate by \u0027,\u0027.',
        ),
    ]

    nielsen_id3_behavior: Annotated[
        Optional[Fmp4NielsenId3Behavior],
        Field(
            None,
            alias='NielsenId3Behavior',
            description='If set to passthrough, Nielsen inaudible tones for media tracking will be detected in the input audio and an equivalent ID3 tag will be inserted in the output.',
        ),
    ]

    timed_metadata_behavior: Annotated[
        Optional[Fmp4TimedMetadataBehavior],
        Field(
            None,
            alias='TimedMetadataBehavior',
            description='Set to PASSTHROUGH to enable ID3 metadata insertion. To include metadata, you configure other parameters in the output group or individual outputs, or you add an ID3 action to the channel schedule.',
        ),
    ]


class M2tsSettings(BaseModel):
    """M2ts Settings."""

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

    arib_captions_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='AribCaptionsPid',
            description='Packet Identifier (PID) for ARIB Captions in the transport stream. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    arib_captions_pid_control: Annotated[
        Optional[M2tsAribCaptionsPidControl],
        Field(
            None,
            alias='AribCaptionsPidControl',
            description='If set to auto, pid number used for ARIB Captions will be auto-selected from unused pids. If set to useConfigured, ARIB Captions will be on the configured pid number.',
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

    audio_pids: Annotated[
        Optional[str],
        Field(
            None,
            alias='AudioPids',
            description='Packet Identifier (PID) of the elementary audio stream(s) in the transport stream. Multiple values are accepted, and can be entered in ranges and/or by comma separation. Can be entered as decimal or hexadecimal values. Each PID specified must be in the range of 32 (or 0x20)..8182 (or 0x1ff6).',
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

    bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='Bitrate',
            description='The output bitrate of the transport stream in bits per second. Setting to 0 lets the muxer automatically determine the appropriate bitrate.',
        ),
    ]

    buffer_model: Annotated[
        Optional[M2tsBufferModel],
        Field(
            None,
            alias='BufferModel',
            description='Controls the timing accuracy for output network traffic. Leave as MULTIPLEX to ensure accurate network packet timing. Or set to NONE, which might result in lower latency but will result in more variability in output network packet timing. This variability might cause interruptions, jitter, or bursty behavior in your playback or receiving devices.',
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

    dvb_nit_settings: Annotated[
        Optional[DvbNitSettings],
        Field(
            None,
            alias='DvbNitSettings',
            description='Inserts DVB Network Information Table (NIT) at the specified table repetition interval.',
        ),
    ]

    dvb_sdt_settings: Annotated[
        Optional[DvbSdtSettings],
        Field(
            None,
            alias='DvbSdtSettings',
            description='Inserts DVB Service Description Table (SDT) at the specified table repetition interval.',
        ),
    ]

    dvb_sub_pids: Annotated[
        Optional[str],
        Field(
            None,
            alias='DvbSubPids',
            description='Packet Identifier (PID) for input source DVB Subtitle data to this output. Multiple values are accepted, and can be entered in ranges and/or by comma separation. Can be entered as decimal or hexadecimal values. Each PID specified must be in the range of 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    dvb_tdt_settings: Annotated[
        Optional[DvbTdtSettings],
        Field(
            None,
            alias='DvbTdtSettings',
            description='Inserts DVB Time and Date Table (TDT) at the specified table repetition interval.',
        ),
    ]

    dvb_teletext_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='DvbTeletextPid',
            description='Packet Identifier (PID) for input source DVB Teletext data to this output. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
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

    ebp_audio_interval: Annotated[
        Optional[M2tsAudioInterval],
        Field(
            None,
            alias='EbpAudioInterval',
            description='When videoAndFixedIntervals is selected, audio EBP markers will be added to partitions 3 and 4. The interval between these additional markers will be fixed, and will be slightly shorter than the video EBP marker interval. Only available when EBP Cablelabs segmentation markers are selected. Partitions 1 and 2 will always follow the video interval.',
        ),
    ]

    ebp_lookahead_ms: Annotated[
        Optional[int],
        Field(
            None,
            alias='EbpLookaheadMs',
            description='When set, enforces that Encoder Boundary Points do not come within the specified time interval of each other by looking ahead at input video. If another EBP is going to come in within the specified time interval, the current EBP is not emitted, and the segment is "stretched" to the next marker. The lookahead value does not add latency to the system. The Live Event must be configured elsewhere to create sufficient latency to make the lookahead accurate.',
        ),
    ]

    ebp_placement: Annotated[
        Optional[M2tsEbpPlacement],
        Field(
            None,
            alias='EbpPlacement',
            description='Controls placement of EBP on Audio PIDs. If set to videoAndAudioPids, EBP markers will be placed on the video PID and all audio PIDs. If set to videoPid, EBP markers will be placed on only the video PID.',
        ),
    ]

    ecm_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='EcmPid',
            description='This field is unused and deprecated.',
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

    etv_platform_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='EtvPlatformPid',
            description='Packet Identifier (PID) for input source ETV Platform data to this output. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    etv_signal_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='EtvSignalPid',
            description='Packet Identifier (PID) for input source ETV Signal data to this output. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    fragment_time: Annotated[
        Optional[float],
        Field(
            None,
            alias='FragmentTime',
            description='The length in seconds of each fragment. Only used with EBP markers.',
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

    klv_data_pids: Annotated[
        Optional[str],
        Field(
            None,
            alias='KlvDataPids',
            description='Packet Identifier (PID) for input source KLV data to this output. Multiple values are accepted, and can be entered in ranges and/or by comma separation. Can be entered as decimal or hexadecimal values. Each PID specified must be in the range of 32 (or 0x20)..8182 (or 0x1ff6).',
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

    null_packet_bitrate: Annotated[
        Optional[float],
        Field(
            None,
            alias='NullPacketBitrate',
            description='Value in bits per second of extra null packets to insert into the transport stream. This can be used if a downstream encryption system requires periodic null packets.',
        ),
    ]

    pat_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='PatInterval',
            description='The number of milliseconds between instances of this table in the output transport stream. Valid values are 0, 10..1000.',
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

    pcr_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='PcrPid',
            description='Packet Identifier (PID) of the Program Clock Reference (PCR) in the transport stream. When no value is given, the encoder will assign the same value as the Video PID. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    pmt_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='PmtInterval',
            description='The number of milliseconds between instances of this table in the output transport stream. Valid values are 0, 10..1000.',
        ),
    ]

    pmt_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='PmtPid',
            description='Packet Identifier (PID) for the Program Map Table (PMT) in the transport stream. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    program_num: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramNum',
            description='The value of the program number field in the Program Map Table.',
        ),
    ]

    rate_mode: Annotated[
        Optional[M2tsRateMode],
        Field(
            None,
            alias='RateMode',
            description='When vbr, does not insert null packets into transport stream to fill specified bitrate. The bitrate setting acts as the maximum bitrate when vbr is set.',
        ),
    ]

    scte27_pids: Annotated[
        Optional[str],
        Field(
            None,
            alias='Scte27Pids',
            description='Packet Identifier (PID) for input source SCTE-27 data to this output. Multiple values are accepted, and can be entered in ranges and/or by comma separation. Can be entered as decimal or hexadecimal values. Each PID specified must be in the range of 32 (or 0x20)..8182 (or 0x1ff6).',
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

    scte35_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='Scte35Pid',
            description='Packet Identifier (PID) of the SCTE-35 stream in the transport stream. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    segmentation_markers: Annotated[
        Optional[M2tsSegmentationMarkers],
        Field(
            None,
            alias='SegmentationMarkers',
            description='Inserts segmentation markers at each segmentationTime period. raiSegstart sets the Random Access Indicator bit in the adaptation field. raiAdapt sets the RAI bit and adds the current timecode in the private data bytes. psiSegstart inserts PAT and PMT tables at the start of segments. ebp adds Encoder Boundary Point information to the adaptation field as per OpenCable specification OC-SP-EBP-I01-130118. ebpLegacy adds Encoder Boundary Point information to the adaptation field using a legacy proprietary format.',
        ),
    ]

    segmentation_style: Annotated[
        Optional[M2tsSegmentationStyle],
        Field(
            None,
            alias='SegmentationStyle',
            description='The segmentation style parameter controls how segmentation markers are inserted into the transport stream. With avails, it is possible that segments may be truncated, which can influence where future segmentation markers are inserted. When a segmentation style of "resetCadence" is selected and a segment is truncated due to an avail, we will reset the segmentation cadence. This means the subsequent segment will have a duration of $segmentationTime seconds. When a segmentation style of "maintainCadence" is selected and a segment is truncated due to an avail, we will not reset the segmentation cadence. This means the subsequent segment will likely be truncated as well. However, all segments after that will have a duration of $segmentationTime seconds. Note that EBP lookahead is a slight exception to this rule.',
        ),
    ]

    segmentation_time: Annotated[
        Optional[float],
        Field(
            None,
            alias='SegmentationTime',
            description='The length in seconds of each segment. Required unless markers is set to _none_.',
        ),
    ]

    timed_metadata_behavior: Annotated[
        Optional[M2tsTimedMetadataBehavior],
        Field(
            None,
            alias='TimedMetadataBehavior',
            description='When set to passthrough, timed metadata will be passed through from input to output.',
        ),
    ]

    timed_metadata_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='TimedMetadataPid',
            description='Packet Identifier (PID) of the timed metadata stream in the transport stream. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    transport_stream_id: Annotated[
        Optional[int],
        Field(
            None,
            alias='TransportStreamId',
            description='The value of the transport stream ID field in the Program Map Table.',
        ),
    ]

    video_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='VideoPid',
            description='Packet Identifier (PID) of the elementary video stream in the transport stream. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
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


class M3u8Settings(BaseModel):
    """Settings information for the .m3u8 container."""

    model_config = ConfigDict(populate_by_name=True)

    audio_frames_per_pes: Annotated[
        Optional[int],
        Field(
            None,
            alias='AudioFramesPerPes',
            description='The number of audio frames to insert for each PES packet.',
        ),
    ]

    audio_pids: Annotated[
        Optional[str],
        Field(
            None,
            alias='AudioPids',
            description='Packet Identifier (PID) of the elementary audio stream(s) in the transport stream. Multiple values are accepted, and can be entered in ranges and/or by comma separation. Can be entered as decimal or hexadecimal values.',
        ),
    ]

    ecm_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='EcmPid',
            description='This parameter is unused and deprecated.',
        ),
    ]

    nielsen_id3_behavior: Annotated[
        Optional[M3u8NielsenId3Behavior],
        Field(
            None,
            alias='NielsenId3Behavior',
            description='If set to passthrough, Nielsen inaudible tones for media tracking will be detected in the input audio and an equivalent ID3 tag will be inserted in the output.',
        ),
    ]

    pat_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='PatInterval',
            description='The number of milliseconds between instances of this table in the output transport stream. A value of \\"0\\" writes out the PMT once per segment file.',
        ),
    ]

    pcr_control: Annotated[
        Optional[M3u8PcrControl],
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
            description='Maximum time in milliseconds between Program Clock References (PCRs) inserted into the transport stream.',
        ),
    ]

    pcr_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='PcrPid',
            description='Packet Identifier (PID) of the Program Clock Reference (PCR) in the transport stream. When no value is given, the encoder will assign the same value as the Video PID. Can be entered as a decimal or hexadecimal value.',
        ),
    ]

    pmt_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='PmtInterval',
            description='The number of milliseconds between instances of this table in the output transport stream. A value of \\"0\\" writes out the PMT once per segment file.',
        ),
    ]

    pmt_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='PmtPid',
            description='Packet Identifier (PID) for the Program Map Table (PMT) in the transport stream. Can be entered as a decimal or hexadecimal value.',
        ),
    ]

    program_num: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramNum',
            description='The value of the program number field in the Program Map Table.',
        ),
    ]

    scte35_behavior: Annotated[
        Optional[M3u8Scte35Behavior],
        Field(
            None,
            alias='Scte35Behavior',
            description='If set to passthrough, passes any SCTE-35 signals from the input source to this output.',
        ),
    ]

    scte35_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='Scte35Pid',
            description='Packet Identifier (PID) of the SCTE-35 stream in the transport stream. Can be entered as a decimal or hexadecimal value.',
        ),
    ]

    timed_metadata_behavior: Annotated[
        Optional[M3u8TimedMetadataBehavior],
        Field(
            None,
            alias='TimedMetadataBehavior',
            description='Set to PASSTHROUGH to enable ID3 metadata insertion. To include metadata, you configure other parameters in the output group or individual outputs, or you add an ID3 action to the channel schedule.',
        ),
    ]

    timed_metadata_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='TimedMetadataPid',
            description='Packet Identifier (PID) of the timed metadata stream in the transport stream. Can be entered as a decimal or hexadecimal value. Valid values are 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]

    transport_stream_id: Annotated[
        Optional[int],
        Field(
            None,
            alias='TransportStreamId',
            description='The value of the transport stream ID field in the Program Map Table.',
        ),
    ]

    video_pid: Annotated[
        Optional[str],
        Field(
            None,
            alias='VideoPid',
            description='Packet Identifier (PID) of the elementary video stream in the transport stream. Can be entered as a decimal or hexadecimal value.',
        ),
    ]

    klv_behavior: Annotated[
        Optional[M3u8KlvBehavior],
        Field(
            None,
            alias='KlvBehavior',
            description='If set to passthrough, passes any KLV data from the input source to this output.',
        ),
    ]

    klv_data_pids: Annotated[
        Optional[str],
        Field(
            None,
            alias='KlvDataPids',
            description='Packet Identifier (PID) for input source KLV data to this output. Multiple values are accepted, and can be entered in ranges and/or by comma separation. Can be entered as decimal or hexadecimal values. Each PID specified must be in the range of 32 (or 0x20)..8182 (or 0x1ff6).',
        ),
    ]


class MediaPackageOutputDestinationSettings(BaseModel):
    """MediaPackage Output Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)

    channel_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelId',
            description='ID of the channel in MediaPackage that is the destination for this output group. You do not need to specify the individual inputs in MediaPackage; MediaLive will handle the connection of the two MediaLive pipelines to the two MediaPackage inputs. The MediaPackage channel and MediaLive channel must be in the same region.',
        ),
    ]

    channel_group: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelGroup',
            description='Name of the channel group in MediaPackageV2. Only use if you are sending CMAF Ingest output to a CMAF ingest endpoint on a MediaPackage channel that uses MediaPackage v2.',
        ),
    ]

    channel_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='ChannelName',
            description='Name of the channel in MediaPackageV2. Only use if you are sending CMAF Ingest output to a CMAF ingest endpoint on a MediaPackage channel that uses MediaPackage v2.',
        ),
    ]


class MediaPackageV2DestinationSettings(BaseModel):
    """Media Package V2 Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)

    audio_group_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='AudioGroupId',
            description='Applies only to an output that contains audio. If you want to put several audio encodes into one audio rendition group, decide on a name (ID) for the group. Then in every audio output that you want to belong to that group, enter that ID in this field. Note that this information is part of the HLS specification (not the CMAF specification), but if you include it then MediaPackage will include it in the manifest it creates for the video player.',
        ),
    ]

    audio_rendition_sets: Annotated[
        Optional[str],
        Field(
            None,
            alias='AudioRenditionSets',
            description='Applies only to an output that contains video, and only if you want to associate one or more audio groups to this video. In this field you assign the groups that you create (in the Group ID fields in the various audio outputs). Enter one group ID, or enter a comma-separated list of group IDs. Note that this information is part of the HLS specification (not the CMAF specification), but if you include it then MediaPackage will include it in the manifest it creates for the video player.',
        ),
    ]

    hls_auto_select: Annotated[
        Optional[HlsAutoSelect],
        Field(
            None,
            alias='HlsAutoSelect',
            description='Specifies whether MediaPackage should set this output as the auto-select rendition in the HLS manifest. YES means this must be the auto-select. NO means this should never be the auto-select. OMIT means MediaPackage decides what to set on this rendition. When you consider all the renditions, follow these guidelines. You can set zero or one renditions to YES. You can set zero or more renditions to NO, but you can\u0027t set all renditions to NO. You can set zero, some, or all to OMIT.',
        ),
    ]

    hls_default: Annotated[
        Optional[HlsDefault],
        Field(
            None,
            alias='HlsDefault',
            description='Specifies whether MediaPackage should set this output as the default rendition in the HLS manifest. YES means this must be the default. NO means this should never be the default. OMIT means MediaPackage decides what to set on this rendition. When you consider all the renditions, follow these guidelines. You can set zero or one renditions to YES. You can set zero or more renditions to NO, but you can\u0027t set all renditions to NO. You can set zero, some, or all to OMIT.',
        ),
    ]


class MediaPackageOutputSettings(BaseModel):
    """Media Package Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    media_package_v2_destination_settings: Annotated[
        Optional[MediaPackageV2DestinationSettings],
        Field(
            None,
            alias='MediaPackageV2DestinationSettings',
            description='Optional settings for MediaPackage V2 destinations',
        ),
    ]


class MediaPackageV2GroupSettings(BaseModel):
    """Media Package V2 Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    caption_language_mappings: Annotated[
        Optional[list[CaptionLanguageMapping]],
        Field(
            None,
            alias='CaptionLanguageMappings',
            description='Mapping of up to 4 caption channels to caption languages.',
        ),
    ]

    id3_behavior: Annotated[
        Optional[CmafId3Behavior],
        Field(
            None,
            alias='Id3Behavior',
            description='Set to ENABLED to enable ID3 metadata insertion. To include metadata, you configure other parameters in the output group, or you add an ID3 action to the channel schedule.',
        ),
    ]

    klv_behavior: Annotated[
        Optional[CmafKLVBehavior],
        Field(
            None,
            alias='KlvBehavior',
            description='If set to passthrough, passes any KLV data from the input source to this output.',
        ),
    ]

    nielsen_id3_behavior: Annotated[
        Optional[CmafNielsenId3Behavior],
        Field(
            None,
            alias='NielsenId3Behavior',
            description='If set to passthrough, Nielsen inaudible tones for media tracking will be detected in the input audio and an equivalent ID3 tag will be inserted in the output.',
        ),
    ]

    scte35_type: Annotated[
        Optional[Scte35Type],
        Field(
            None,
            alias='Scte35Type',
            description='Type of scte35 track to add. none or scte35WithoutSegmentation',
        ),
    ]

    segment_length: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentLength',
            description='The nominal duration of segments. The units are specified in SegmentLengthUnits. The segments will end on the next keyframe after the specified duration, so the actual segment length might be longer, and it might be a fraction of the units.',
        ),
    ]

    segment_length_units: Annotated[
        Optional[CmafIngestSegmentLengthUnits],
        Field(
            None,
            alias='SegmentLengthUnits',
            description='Time unit for segment length parameter.',
        ),
    ]

    timed_metadata_id3_frame: Annotated[
        Optional[CmafTimedMetadataId3Frame],
        Field(
            None,
            alias='TimedMetadataId3Frame',
            description='Set to none if you don\u0027t want to insert a timecode in the output. Otherwise choose the frame type for the timecode.',
        ),
    ]

    timed_metadata_id3_period: Annotated[
        Optional[int],
        Field(
            None,
            alias='TimedMetadataId3Period',
            description='If you set up to insert a timecode in the output, specify the frequency for the frame, in seconds.',
        ),
    ]

    timed_metadata_passthrough: Annotated[
        Optional[CmafTimedMetadataPassthrough],
        Field(
            None,
            alias='TimedMetadataPassthrough',
            description='Set to enabled to pass through ID3 metadata from the input sources.',
        ),
    ]


class MsSmoothOutputSettings(BaseModel):
    """Ms Smooth Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    h265_packaging_type: Annotated[
        Optional[MsSmoothH265PackagingType],
        Field(
            None,
            alias='H265PackagingType',
            description='Only applicable when this output is referencing an H.265 video description. Specifies whether MP4 segments should be packaged as HEV1 or HVC1.',
        ),
    ]

    name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='NameModifier',
            description='String concatenated to the end of the destination filename. Required for multiple outputs of the same type.',
        ),
    ]


class OutputDestinationSettings(BaseModel):
    """Placeholder documentation for OutputDestinationSettings."""

    model_config = ConfigDict(populate_by_name=True)

    password_param: Annotated[
        Optional[str],
        Field(
            None,
            alias='PasswordParam',
            description='key used to extract the password from EC2 Parameter store',
        ),
    ]

    stream_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='StreamName',
            description='Stream name for RTMP destinations (URLs of type rtmp://)',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='A URL specifying a destination',
        ),
    ]

    username: Annotated[
        Optional[str],
        Field(
            None,
            alias='Username',
            description='username for destination',
        ),
    ]


class OutputLocationRef(BaseModel):
    """Reference to an OutputDestination ID defined in the channel."""

    model_config = ConfigDict(populate_by_name=True)

    destination_ref_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='DestinationRefId',
            description='',
        ),
    ]


class ArchiveGroupSettings(BaseModel):
    """Archive Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    archive_cdn_settings: Annotated[
        Optional[ArchiveCdnSettings],
        Field(
            None,
            alias='ArchiveCdnSettings',
            description='Parameters that control interactions with the CDN.',
        ),
    ]

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='A directory and base filename where archive files should be written.',
        ),
    ]

    rollover_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='RolloverInterval',
            description='Number of seconds to write to archive file before closing and starting a new one.',
        ),
    ]


class CmafIngestGroupSettings(BaseModel):
    """Cmaf Ingest Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='A HTTP destination for the tracks',
        ),
    ]

    nielsen_id3_behavior: Annotated[
        Optional[CmafNielsenId3Behavior],
        Field(
            None,
            alias='NielsenId3Behavior',
            description='If set to passthrough, Nielsen inaudible tones for media tracking will be detected in the input audio and an equivalent ID3 tag will be inserted in the output.',
        ),
    ]

    scte35_type: Annotated[
        Optional[Scte35Type],
        Field(
            None,
            alias='Scte35Type',
            description='Type of scte35 track to add. none or scte35WithoutSegmentation',
        ),
    ]

    segment_length: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentLength',
            description='The nominal duration of segments. The units are specified in SegmentLengthUnits. The segments will end on the next keyframe after the specified duration, so the actual segment length might be longer, and it might be a fraction of the units.',
        ),
    ]

    segment_length_units: Annotated[
        Optional[CmafIngestSegmentLengthUnits],
        Field(
            None,
            alias='SegmentLengthUnits',
            description='Time unit for segment length parameter.',
        ),
    ]

    send_delay_ms: Annotated[
        Optional[int],
        Field(
            None,
            alias='SendDelayMs',
            description='Number of milliseconds to delay the output from the second pipeline.',
        ),
    ]

    klv_behavior: Annotated[
        Optional[CmafKLVBehavior],
        Field(
            None,
            alias='KlvBehavior',
            description='If set to passthrough, passes any KLV data from the input source to this output.',
        ),
    ]

    klv_name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='KlvNameModifier',
            description='Change the modifier that MediaLive automatically adds to the Streams() name that identifies a KLV track. The default is "klv", which means the default name will be Streams(klv.cmfm). Any string you enter here will replace the "klv" string.\\nThe modifier can only contain: numbers, letters, plus (+), minus (-), underscore (_) and period (.) and has a maximum length of 100 characters.',
        ),
    ]

    nielsen_id3_name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='NielsenId3NameModifier',
            description='Change the modifier that MediaLive automatically adds to the Streams() name that identifies a Nielsen ID3 track. The default is "nid3", which means the default name will be Streams(nid3.cmfm). Any string you enter here will replace the "nid3" string.\\nThe modifier can only contain: numbers, letters, plus (+), minus (-), underscore (_) and period (.) and has a maximum length of 100 characters.',
        ),
    ]

    scte35_name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='Scte35NameModifier',
            description='Change the modifier that MediaLive automatically adds to the Streams() name for a SCTE 35 track. The default is "scte", which means the default name will be Streams(scte.cmfm). Any string you enter here will replace the "scte" string.\\nThe modifier can only contain: numbers, letters, plus (+), minus (-), underscore (_) and period (.) and has a maximum length of 100 characters.',
        ),
    ]

    id3_behavior: Annotated[
        Optional[CmafId3Behavior],
        Field(
            None,
            alias='Id3Behavior',
            description='Set to ENABLED to enable ID3 metadata insertion. To include metadata, you configure other parameters in the output group, or you add an ID3 action to the channel schedule.',
        ),
    ]

    id3_name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id3NameModifier',
            description='Change the modifier that MediaLive automatically adds to the Streams() name that identifies an ID3 track. The default is "id3", which means the default name will be Streams(id3.cmfm). Any string you enter here will replace the "id3" string.\\nThe modifier can only contain: numbers, letters, plus (+), minus (-), underscore (_) and period (.) and has a maximum length of 100 characters.',
        ),
    ]

    caption_language_mappings: Annotated[
        Optional[list[CmafIngestCaptionLanguageMapping]],
        Field(
            None,
            alias='CaptionLanguageMappings',
            description='An array that identifies the languages in the four caption channels in the embedded captions.',
        ),
    ]

    timed_metadata_id3_frame: Annotated[
        Optional[CmafTimedMetadataId3Frame],
        Field(
            None,
            alias='TimedMetadataId3Frame',
            description='Set to none if you don\u0027t want to insert a timecode in the output. Otherwise choose the frame type for the timecode.',
        ),
    ]

    timed_metadata_id3_period: Annotated[
        Optional[int],
        Field(
            None,
            alias='TimedMetadataId3Period',
            description='If you set up to insert a timecode in the output, specify the frequency for the frame, in seconds.',
        ),
    ]

    timed_metadata_passthrough: Annotated[
        Optional[CmafTimedMetadataPassthrough],
        Field(
            None,
            alias='TimedMetadataPassthrough',
            description='Set to enabled to pass through ID3 metadata from the input sources.',
        ),
    ]

    additional_destinations: Annotated[
        Optional[list[AdditionalDestinations]],
        Field(
            None,
            alias='AdditionalDestinations',
            description='Optional an array of additional destinational HTTP destinations for the OutputGroup outputs',
        ),
    ]


class MediaPackageGroupSettings(BaseModel):
    """Media Package Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='MediaPackage channel destination.',
        ),
    ]

    mediapackage_v2_group_settings: Annotated[
        Optional[MediaPackageV2GroupSettings],
        Field(
            None,
            alias='MediapackageV2GroupSettings',
            description='Parameters that apply only if the destination parameter (for the output group) specifies a channelGroup and channelName. Use of these two paramters indicates that the output group is for MediaPackage V2 (CMAF Ingest).',
        ),
    ]


class MsSmoothGroupSettings(BaseModel):
    """Ms Smooth Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    acquisition_point_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='AcquisitionPointId',
            description='The ID to include in each message in the sparse track. Ignored if sparseTrackType is NONE.',
        ),
    ]

    audio_only_timecode_control: Annotated[
        Optional[SmoothGroupAudioOnlyTimecodeControl],
        Field(
            None,
            alias='AudioOnlyTimecodeControl',
            description='If set to passthrough for an audio-only MS Smooth output, the fragment absolute time will be set to the current timecode. This option does not write timecodes to the audio elementary stream.',
        ),
    ]

    certificate_mode: Annotated[
        Optional[SmoothGroupCertificateMode],
        Field(
            None,
            alias='CertificateMode',
            description='If set to verifyAuthenticity, verify the https certificate chain to a trusted Certificate Authority (CA). This will cause https outputs to self-signed certificates to fail.',
        ),
    ]

    connection_retry_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='ConnectionRetryInterval',
            description='Number of seconds to wait before retrying connection to the IIS server if the connection is lost. Content will be cached during this time and the cache will be be delivered to the IIS server once the connection is re-established.',
        ),
    ]

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='Smooth Streaming publish point on an IIS server. Elemental Live acts as a "Push" encoder to IIS.',
        ),
    ]

    event_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='EventId',
            description='MS Smooth event ID to be sent to the IIS server. Should only be specified if eventIdMode is set to useConfigured.',
        ),
    ]

    event_id_mode: Annotated[
        Optional[SmoothGroupEventIdMode],
        Field(
            None,
            alias='EventIdMode',
            description='Specifies whether or not to send an event ID to the IIS server. If no event ID is sent and the same Live Event is used without changing the publishing point, clients might see cached video from the previous run. Options: - "useConfigured" - use the value provided in eventId - "useTimestamp" - generate and send an event ID based on the current timestamp - "noEventId" - do not send an event ID to the IIS server.',
        ),
    ]

    event_stop_behavior: Annotated[
        Optional[SmoothGroupEventStopBehavior],
        Field(
            None,
            alias='EventStopBehavior',
            description='When set to sendEos, send EOS signal to IIS server when stopping the event',
        ),
    ]

    filecache_duration: Annotated[
        Optional[int],
        Field(
            None,
            alias='FilecacheDuration',
            description='Size in seconds of file cache for streaming outputs.',
        ),
    ]

    fragment_length: Annotated[
        Optional[int],
        Field(
            None,
            alias='FragmentLength',
            description='Length of mp4 fragments to generate (in seconds). Fragment length must be compatible with GOP size and framerate.',
        ),
    ]

    input_loss_action: Annotated[
        Optional[InputLossActionForMsSmoothOut],
        Field(
            None,
            alias='InputLossAction',
            description='Parameter that control output group behavior on input loss.',
        ),
    ]

    num_retries: Annotated[
        Optional[int],
        Field(
            None,
            alias='NumRetries',
            description='Number of retry attempts.',
        ),
    ]

    restart_delay: Annotated[
        Optional[int],
        Field(
            None,
            alias='RestartDelay',
            description='Number of seconds before initiating a restart due to output failure, due to exhausting the numRetries on one segment, or exceeding filecacheDuration.',
        ),
    ]

    segmentation_mode: Annotated[
        Optional[SmoothGroupSegmentationMode],
        Field(
            None,
            alias='SegmentationMode',
            description='useInputSegmentation has been deprecated. The configured segment size is always used.',
        ),
    ]

    send_delay_ms: Annotated[
        Optional[int],
        Field(
            None,
            alias='SendDelayMs',
            description='Number of milliseconds to delay the output from the second pipeline.',
        ),
    ]

    sparse_track_type: Annotated[
        Optional[SmoothGroupSparseTrackType],
        Field(
            None,
            alias='SparseTrackType',
            description='Identifies the type of data to place in the sparse track: - SCTE35: Insert SCTE-35 messages from the source content. With each message, insert an IDR frame to start a new segment. - SCTE35_WITHOUT_SEGMENTATION: Insert SCTE-35 messages from the source content. With each message, insert an IDR frame but don\u0027t start a new segment. - NONE: Don\u0027t generate a sparse track for any outputs in this output group.',
        ),
    ]

    stream_manifest_behavior: Annotated[
        Optional[SmoothGroupStreamManifestBehavior],
        Field(
            None,
            alias='StreamManifestBehavior',
            description='When set to send, send stream manifest so publishing point doesn\u0027t start until all streams start.',
        ),
    ]

    timestamp_offset: Annotated[
        Optional[str],
        Field(
            None,
            alias='TimestampOffset',
            description='Timestamp offset for the event. Only used if timestampOffsetMode is set to useConfiguredOffset.',
        ),
    ]

    timestamp_offset_mode: Annotated[
        Optional[SmoothGroupTimestampOffsetMode],
        Field(
            None,
            alias='TimestampOffsetMode',
            description='Type of timestamp date offset to use. - useEventStartDate: Use the date the event was started as the offset - useConfiguredOffset: Use an explicitly configured date as the offset',
        ),
    ]


class OutputLockingSettings(BaseModel):
    """Output Locking Settings."""

    model_config = ConfigDict(populate_by_name=True)

    epoch_locking_settings: Annotated[
        Optional[EpochLockingSettings],
        Field(
            None,
            alias='EpochLockingSettings',
            description='',
        ),
    ]

    pipeline_locking_settings: Annotated[
        Optional[PipelineLockingSettings],
        Field(
            None,
            alias='PipelineLockingSettings',
            description='',
        ),
    ]


class RawSettings(BaseModel):
    """Raw Settings."""

    model_config = ConfigDict(populate_by_name=True)


class ArchiveContainerSettings(BaseModel):
    """Archive Container Settings."""

    model_config = ConfigDict(populate_by_name=True)

    m2ts_settings: Annotated[
        Optional[M2tsSettings],
        Field(
            None,
            alias='M2tsSettings',
            description='',
        ),
    ]

    raw_settings: Annotated[
        Optional[RawSettings],
        Field(
            None,
            alias='RawSettings',
            description='',
        ),
    ]


class ArchiveOutputSettings(BaseModel):
    """Archive Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    container_settings: Annotated[
        ArchiveContainerSettings,
        Field(
            ...,
            alias='ContainerSettings',
            description='Container for this output. Can be auto-detected from extension field.',
        ),
    ]

    extension: Annotated[
        Optional[str],
        Field(
            None,
            alias='Extension',
            description='Output file extension. If excluded, this will be auto-selected from the container type.',
        ),
    ]

    name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='NameModifier',
            description='String concatenated to the end of the destination filename. Required for multiple outputs of the same type.',
        ),
    ]


class RtmpCaptionInfoDestinationSettings(BaseModel):
    """Rtmp Caption Info Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)


class RtmpGroupSettings(BaseModel):
    """Rtmp Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    ad_markers: Annotated[
        Optional[list[RtmpAdMarkers]],
        Field(
            None,
            alias='AdMarkers',
            description='Choose the ad marker type for this output group. MediaLive will create a message based on the content of each SCTE-35 message, format it for that marker type, and insert it in the datastream.',
        ),
    ]

    authentication_scheme: Annotated[
        Optional[AuthenticationScheme],
        Field(
            None,
            alias='AuthenticationScheme',
            description='Authentication scheme to use when connecting with CDN',
        ),
    ]

    cache_full_behavior: Annotated[
        Optional[RtmpCacheFullBehavior],
        Field(
            None,
            alias='CacheFullBehavior',
            description='Controls behavior when content cache fills up. If remote origin server stalls the RTMP connection and does not accept content fast enough the \u0027Media Cache\u0027 will fill up. When the cache reaches the duration specified by cacheLength the cache will stop accepting new content. If set to disconnectImmediately, the RTMP output will force a disconnect. Clear the media cache, and reconnect after restartDelay seconds. If set to waitForServer, the RTMP output will wait up to 5 minutes to allow the origin server to begin accepting data again.',
        ),
    ]

    cache_length: Annotated[
        Optional[int],
        Field(
            None,
            alias='CacheLength',
            description='Cache length, in seconds, is used to calculate buffer size.',
        ),
    ]

    caption_data: Annotated[
        Optional[RtmpCaptionData],
        Field(
            None,
            alias='CaptionData',
            description='Controls the types of data that passes to onCaptionInfo outputs. If set to \u0027all\u0027 then 608 and 708 carried DTVCC data will be passed. If set to \u0027field1AndField2608\u0027 then DTVCC data will be stripped out, but 608 data from both fields will be passed. If set to \u0027field1608\u0027 then only the data carried in 608 from field 1 video will be passed.',
        ),
    ]

    input_loss_action: Annotated[
        Optional[InputLossActionForRtmpOut],
        Field(
            None,
            alias='InputLossAction',
            description='Controls the behavior of this RTMP group if input becomes unavailable. - emitOutput: Emit a slate until input returns. - pauseOutput: Stop transmitting data until input returns. This does not close the underlying RTMP connection.',
        ),
    ]

    restart_delay: Annotated[
        Optional[int],
        Field(
            None,
            alias='RestartDelay',
            description='If a streaming output fails, number of seconds to wait until a restart is initiated. A value of 0 means never restart.',
        ),
    ]

    include_filler_nal_units: Annotated[
        Optional[IncludeFillerNalUnits],
        Field(
            None,
            alias='IncludeFillerNalUnits',
            description='Applies only when the rate control mode (in the codec settings) is CBR (constant bit rate). Controls whether the RTMP output stream is padded (with FILL NAL units) in order to achieve a constant bit rate that is truly constant. When there is no padding, the bandwidth varies (up to the bitrate value in the codec settings). We recommend that you choose Auto.',
        ),
    ]


class RtmpOutputSettings(BaseModel):
    """Rtmp Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    certificate_mode: Annotated[
        Optional[RtmpOutputCertificateMode],
        Field(
            None,
            alias='CertificateMode',
            description='If set to verifyAuthenticity, verify the tls certificate chain to a trusted Certificate Authority (CA). This will cause rtmps outputs with self-signed certificates to fail.',
        ),
    ]

    connection_retry_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='ConnectionRetryInterval',
            description='Number of seconds to wait before retrying a connection to the Flash Media server if the connection is lost.',
        ),
    ]

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='The RTMP endpoint excluding the stream name (eg. rtmp://host/appname). For connection to Akamai, a username and password must be supplied. URI fields accept format identifiers.',
        ),
    ]

    num_retries: Annotated[
        Optional[int],
        Field(
            None,
            alias='NumRetries',
            description='Number of retry attempts.',
        ),
    ]


class OutputDestination(BaseModel):
    """Placeholder documentation for OutputDestination."""

    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='User-specified id. This is used in an output group or an output.',
        ),
    ]

    media_package_settings: Annotated[
        Optional[list[MediaPackageOutputDestinationSettings]],
        Field(
            None,
            alias='MediaPackageSettings',
            description='Destination settings for a MediaPackage output; one destination for both encoders.',
        ),
    ]

    multiplex_settings: Annotated[
        Optional[MultiplexProgramChannelDestinationSettings],
        Field(
            None,
            alias='MultiplexSettings',
            description='Destination settings for a Multiplex output; one destination for both encoders.',
        ),
    ]

    settings: Annotated[
        Optional[list[OutputDestinationSettings]],
        Field(
            None,
            alias='Settings',
            description='Destination settings for a standard output; one destination for each redundant encoder.',
        ),
    ]

    srt_settings: Annotated[
        Optional[list[SrtOutputDestinationSettings]],
        Field(
            None,
            alias='SrtSettings',
            description='SRT settings for an SRT output; one destination for each redundant encoder.',
        ),
    ]

    logical_interface_names: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='LogicalInterfaceNames',
            description='Optional assignment of an output to a logical interface on the Node. Only applies to on premises channels.',
        ),
    ]


class StaticKeySettings(BaseModel):
    """Static Key Settings."""

    model_config = ConfigDict(populate_by_name=True)

    key_provider_server: Annotated[
        Optional[InputLocation],
        Field(
            None,
            alias='KeyProviderServer',
            description='The URL of the license server used for protecting content.',
        ),
    ]

    static_key_value: Annotated[
        str,
        Field(
            ...,
            alias='StaticKeyValue',
            description='Static key value as a 32 character hexadecimal string.',
        ),
    ]


class KeyProviderSettings(BaseModel):
    """Key Provider Settings."""

    model_config = ConfigDict(populate_by_name=True)

    static_key_settings: Annotated[
        Optional[StaticKeySettings],
        Field(
            None,
            alias='StaticKeySettings',
            description='',
        ),
    ]


class UdpContainerSettings(BaseModel):
    """Udp Container Settings."""

    model_config = ConfigDict(populate_by_name=True)

    m2ts_settings: Annotated[
        Optional[M2tsSettings],
        Field(
            None,
            alias='M2tsSettings',
            description='',
        ),
    ]


class UdpGroupSettings(BaseModel):
    """Udp Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    input_loss_action: Annotated[
        Optional[InputLossActionForUdpOut],
        Field(
            None,
            alias='InputLossAction',
            description='Specifies behavior of last resort when input video is lost, and no more backup inputs are available. When dropTs is selected the entire transport stream will stop being emitted. When dropProgram is selected the program can be dropped from the transport stream (and replaced with null packets to meet the TS bitrate requirement). Or, when emitProgram is chosen the transport stream will continue to be produced normally with repeat frames, black frames, or slate frames substituted for the absent input video.',
        ),
    ]

    timed_metadata_id3_frame: Annotated[
        Optional[UdpTimedMetadataId3Frame],
        Field(
            None,
            alias='TimedMetadataId3Frame',
            description='Indicates ID3 frame that has the timecode.',
        ),
    ]

    timed_metadata_id3_period: Annotated[
        Optional[int],
        Field(
            None,
            alias='TimedMetadataId3Period',
            description='Timed Metadata interval in seconds.',
        ),
    ]


class OutputGroupSettings(BaseModel):
    """Output Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    archive_group_settings: Annotated[
        Optional[ArchiveGroupSettings],
        Field(
            None,
            alias='ArchiveGroupSettings',
            description='',
        ),
    ]

    frame_capture_group_settings: Annotated[
        Optional[FrameCaptureGroupSettings],
        Field(
            None,
            alias='FrameCaptureGroupSettings',
            description='',
        ),
    ]

    hls_group_settings: Annotated[
        Optional[HlsGroupSettings],
        Field(
            None,
            alias='HlsGroupSettings',
            description='',
        ),
    ]

    media_package_group_settings: Annotated[
        Optional[MediaPackageGroupSettings],
        Field(
            None,
            alias='MediaPackageGroupSettings',
            description='',
        ),
    ]

    ms_smooth_group_settings: Annotated[
        Optional[MsSmoothGroupSettings],
        Field(
            None,
            alias='MsSmoothGroupSettings',
            description='',
        ),
    ]

    multiplex_group_settings: Annotated[
        Optional[MultiplexGroupSettings],
        Field(
            None,
            alias='MultiplexGroupSettings',
            description='',
        ),
    ]

    rtmp_group_settings: Annotated[
        Optional[RtmpGroupSettings],
        Field(
            None,
            alias='RtmpGroupSettings',
            description='',
        ),
    ]

    udp_group_settings: Annotated[
        Optional[UdpGroupSettings],
        Field(
            None,
            alias='UdpGroupSettings',
            description='',
        ),
    ]

    cmaf_ingest_group_settings: Annotated[
        Optional[CmafIngestGroupSettings],
        Field(
            None,
            alias='CmafIngestGroupSettings',
            description='',
        ),
    ]

    srt_group_settings: Annotated[
        Optional[SrtGroupSettings],
        Field(
            None,
            alias='SrtGroupSettings',
            description='',
        ),
    ]


class UdpOutputSettings(BaseModel):
    """Udp Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    buffer_msec: Annotated[
        Optional[int],
        Field(
            None,
            alias='BufferMsec',
            description='UDP output buffering in milliseconds. Larger values increase latency through the transcoder but simultaneously assist the transcoder in maintaining a constant, low-jitter UDP/RTP output while accommodating clock recovery, input switching, input disruptions, picture reordering, etc.',
        ),
    ]

    container_settings: Annotated[
        UdpContainerSettings,
        Field(
            ...,
            alias='ContainerSettings',
            description='',
        ),
    ]

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='Destination address and port number for RTP or UDP packets. Can be unicast or multicast RTP or UDP (eg. rtp://239.10.10.10:5001 or udp://10.100.100.100:5002).',
        ),
    ]

    fec_output_settings: Annotated[
        Optional[FecOutputSettings],
        Field(
            None,
            alias='FecOutputSettings',
            description='Settings for enabling and adjusting Forward Error Correction on UDP outputs.',
        ),
    ]


class OutputSettings(BaseModel):
    """Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    archive_output_settings: Annotated[
        Optional[ArchiveOutputSettings],
        Field(
            None,
            alias='ArchiveOutputSettings',
            description='',
        ),
    ]

    frame_capture_output_settings: Annotated[
        Optional[FrameCaptureOutputSettings],
        Field(
            None,
            alias='FrameCaptureOutputSettings',
            description='',
        ),
    ]

    hls_output_settings: Annotated[
        Optional[HlsOutputSettings],
        Field(
            None,
            alias='HlsOutputSettings',
            description='',
        ),
    ]

    media_package_output_settings: Annotated[
        Optional[MediaPackageOutputSettings],
        Field(
            None,
            alias='MediaPackageOutputSettings',
            description='',
        ),
    ]

    ms_smooth_output_settings: Annotated[
        Optional[MsSmoothOutputSettings],
        Field(
            None,
            alias='MsSmoothOutputSettings',
            description='',
        ),
    ]

    multiplex_output_settings: Annotated[
        Optional[MultiplexOutputSettings],
        Field(
            None,
            alias='MultiplexOutputSettings',
            description='',
        ),
    ]

    rtmp_output_settings: Annotated[
        Optional[RtmpOutputSettings],
        Field(
            None,
            alias='RtmpOutputSettings',
            description='',
        ),
    ]

    udp_output_settings: Annotated[
        Optional[UdpOutputSettings],
        Field(
            None,
            alias='UdpOutputSettings',
            description='',
        ),
    ]

    cmaf_ingest_output_settings: Annotated[
        Optional[CmafIngestOutputSettings],
        Field(
            None,
            alias='CmafIngestOutputSettings',
            description='',
        ),
    ]

    srt_output_settings: Annotated[
        Optional[SrtOutputSettings],
        Field(
            None,
            alias='SrtOutputSettings',
            description='',
        ),
    ]


class Output(BaseModel):
    """Output settings. There can be multiple outputs within a group."""

    model_config = ConfigDict(populate_by_name=True)

    audio_description_names: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='AudioDescriptionNames',
            description='The names of the AudioDescriptions used as audio sources for this output.',
        ),
    ]

    caption_description_names: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='CaptionDescriptionNames',
            description='The names of the CaptionDescriptions used as caption sources for this output.',
        ),
    ]

    output_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='OutputName',
            description='The name used to identify an output.',
        ),
    ]

    output_settings: Annotated[
        OutputSettings,
        Field(
            ...,
            alias='OutputSettings',
            description='Output type-specific settings.',
        ),
    ]

    video_description_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='VideoDescriptionName',
            description='The name of the VideoDescription used as the source for this output.',
        ),
    ]


class OutputGroup(BaseModel):
    """Output groups for this Live Event. Output groups contain information about where streams should be distributed."""

    model_config = ConfigDict(populate_by_name=True)

    name: Annotated[
        Optional[str],
        Field(
            None,
            alias='Name',
            description='Custom output group name optionally defined by the user.',
        ),
    ]

    output_group_settings: Annotated[
        OutputGroupSettings,
        Field(
            ...,
            alias='OutputGroupSettings',
            description='Settings associated with the output group.',
        ),
    ]

    outputs: Annotated[
        list[Output],
        Field(
            ...,
            alias='Outputs',
            description='',
        ),
    ]
