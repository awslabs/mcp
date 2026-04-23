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

"""Encoding-related Pydantic models — video codecs (H.264/H.265/AV1/MPEG-2), filters, color space."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    AfdSignaling,
    Av1GopSizeUnits,
    Av1Level,
    Av1LookAheadRateControl,
    Av1RateControlMode,
    Av1SceneChangeDetect,
    AvailBlankingState,
    BandwidthReductionFilterStrength,
    BandwidthReductionPostFilterSharpening,
    BlackoutSlateNetworkEndBlackout,
    BlackoutSlateState,
    ColorSpace,
    FeatureActivationsInputPrepareScheduleActions,
    FeatureActivationsOutputStaticImageOverlayScheduleActions,
    FixedAfd,
    FrameCaptureIntervalUnit,
    GlobalConfigurationInputEndAction,
    GlobalConfigurationLowFramerateInputs,
    GlobalConfigurationOutputLockingMode,
    GlobalConfigurationOutputTimingSource,
    H264AdaptiveQuantization,
    H264ColorMetadata,
    H264EntropyEncoding,
    H264FlickerAq,
    H264ForceFieldPictures,
    H264FramerateControl,
    H264GopBReference,
    H264GopSizeUnits,
    H264Level,
    H264LookAheadRateControl,
    H264ParControl,
    H264Profile,
    H264QualityLevel,
    H264RateControlMode,
    H264ScanType,
    H264SceneChangeDetect,
    H264SpatialAq,
    H264SubGopLength,
    H264Syntax,
    H264TemporalAq,
    H264TimecodeInsertionBehavior,
    H265AdaptiveQuantization,
    H265AlternativeTransferFunction,
    H265ColorMetadata,
    H265Deblocking,
    H265FlickerAq,
    H265GopBReference,
    H265GopSizeUnits,
    H265Level,
    H265LookAheadRateControl,
    H265MvOverPictureBoundaries,
    H265MvTemporalPredictor,
    H265Profile,
    H265RateControlMode,
    H265ScanType,
    H265SceneChangeDetect,
    H265SubGopLength,
    H265Tier,
    H265TilePadding,
    H265TimecodeInsertionBehavior,
    H265TreeblockSize,
    Mpeg2AdaptiveQuantization,
    Mpeg2ColorMetadata,
    Mpeg2ColorSpace,
    Mpeg2DisplayRatio,
    Mpeg2GopSizeUnits,
    Mpeg2ScanType,
    Mpeg2SubGopLength,
    Mpeg2TimecodeInsertionBehavior,
    S3CannedAcl,
    Scte35SegmentationScope,
    TemporalFilterPostFilterSharpening,
    TemporalFilterStrength,
    ThumbnailState,
    ThumbnailType,
    TimecodeBurninFontSize,
    TimecodeBurninPosition,
    TimecodeConfigSource,
    VideoDescriptionRespondToAfd,
    VideoDescriptionScalingBehavior,
    VideoSelectorColorSpace,
    VideoSelectorColorSpaceUsage,
)
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.input import (
        InputLocation,
        InputLossBehavior,
    )
    from awslabs.amazon_medialive_mcp_server.models.output import (
        OutputLocationRef,
        OutputLockingSettings,
    )
    from awslabs.amazon_medialive_mcp_server.models.schedule import (
        Scte35SpliceInsert,
        Scte35TimeSignalApos,
    )


class BandwidthReductionFilterSettings(BaseModel):
    """Bandwidth Reduction Filter Settings."""

    model_config = ConfigDict(populate_by_name=True)

    post_filter_sharpening: Annotated[
        Optional[BandwidthReductionPostFilterSharpening],
        Field(
            None,
            alias='PostFilterSharpening',
            description='Configures the sharpening control, which is available when the bandwidth reduction filter is enabled. This control sharpens edges and contours, which produces a specific artistic effect that you might want. We recommend that you test each of the values (including DISABLED) to observe the sharpening effect on the content.',
        ),
    ]

    strength: Annotated[
        Optional[BandwidthReductionFilterStrength],
        Field(
            None,
            alias='Strength',
            description='Enables the bandwidth reduction filter. The filter strengths range from 1 to 4. We recommend that you always enable this filter and use AUTO, to let MediaLive apply the optimum filtering for the context.',
        ),
    ]


class ColorCorrection(BaseModel):
    """Property of ColorCorrectionSettings. Used for custom color space conversion. The object identifies one 3D LUT file and specifies the input/output color space combination that the file will be used for."""

    model_config = ConfigDict(populate_by_name=True)

    input_color_space: Annotated[
        ColorSpace,
        Field(
            ...,
            alias='InputColorSpace',
            description='The color space of the input.',
        ),
    ]

    output_color_space: Annotated[
        ColorSpace,
        Field(
            ...,
            alias='OutputColorSpace',
            description='The color space of the output.',
        ),
    ]

    uri: Annotated[
        str,
        Field(
            ...,
            alias='Uri',
            description='The URI of the 3D LUT file. The protocol must be \u0027s3:\u0027 or \u0027s3ssl:\u0027:.',
        ),
    ]


class ColorCorrectionSettings(BaseModel):
    """Property of encoderSettings. Controls color conversion when you are using 3D LUT files to perform color conversion on video."""

    model_config = ConfigDict(populate_by_name=True)

    global_color_corrections: Annotated[
        list[ColorCorrection],
        Field(
            ...,
            alias='GlobalColorCorrections',
            description='An array of colorCorrections that applies when you are using 3D LUT files to perform color conversion on video. Each colorCorrection contains one 3D LUT file (that defines the color mapping for converting an input color space to an output color space), and the input/output combination that this 3D LUT file applies to. MediaLive reads the color space in the input metadata, determines the color space that you have specified for the output, and finds and uses the LUT file that applies to this combination.',
        ),
    ]


class ColorSpacePassthroughSettings(BaseModel):
    """Passthrough applies no color space conversion to the output."""

    model_config = ConfigDict(populate_by_name=True)


class DolbyVision81Settings(BaseModel):
    """Dolby Vision81 Settings."""

    model_config = ConfigDict(populate_by_name=True)


class Esam(BaseModel):
    """Esam."""

    model_config = ConfigDict(populate_by_name=True)

    acquisition_point_id: Annotated[
        str,
        Field(
            ...,
            alias='AcquisitionPointId',
            description='Sent as acquisitionPointIdentity to identify the MediaLive channel to the POIS.',
        ),
    ]

    ad_avail_offset: Annotated[
        Optional[int],
        Field(
            None,
            alias='AdAvailOffset',
            description='When specified, this offset (in milliseconds) is added to the input Ad Avail PTS time. This only applies to embedded SCTE 104/35 messages and does not apply to OOB messages.',
        ),
    ]

    password_param: Annotated[
        Optional[str],
        Field(
            None,
            alias='PasswordParam',
            description='Documentation update needed',
        ),
    ]

    pois_endpoint: Annotated[
        str,
        Field(
            ...,
            alias='PoisEndpoint',
            description='The URL of the signal conditioner endpoint on the Placement Opportunity Information System (POIS). MediaLive sends SignalProcessingEvents here when SCTE-35 messages are read.',
        ),
    ]

    username: Annotated[
        Optional[str],
        Field(
            None,
            alias='Username',
            description='Documentation update needed',
        ),
    ]

    zone_identity: Annotated[
        Optional[str],
        Field(
            None,
            alias='ZoneIdentity',
            description='Optional data sent as zoneIdentity to identify the MediaLive channel to the POIS.',
        ),
    ]


class FeatureActivations(BaseModel):
    """Feature Activations."""

    model_config = ConfigDict(populate_by_name=True)

    input_prepare_schedule_actions: Annotated[
        Optional[FeatureActivationsInputPrepareScheduleActions],
        Field(
            None,
            alias='InputPrepareScheduleActions',
            description='Enables the Input Prepare feature. You can create Input Prepare actions in the schedule only if this feature is enabled. If you disable the feature on an existing schedule, make sure that you first delete all input prepare actions from the schedule.',
        ),
    ]

    output_static_image_overlay_schedule_actions: Annotated[
        Optional[FeatureActivationsOutputStaticImageOverlayScheduleActions],
        Field(
            None,
            alias='OutputStaticImageOverlayScheduleActions',
            description='Enables the output static image overlay feature. Enabling this feature allows you to send channel schedule updates to display/clear/modify image overlays on an output-by-output bases.',
        ),
    ]


class FrameCaptureHlsSettings(BaseModel):
    """Frame Capture Hls Settings."""

    model_config = ConfigDict(populate_by_name=True)


class FrameCaptureOutputSettings(BaseModel):
    """Frame Capture Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='NameModifier',
            description='Required if the output group contains more than one output. This modifier forms part of the output file name.',
        ),
    ]


class FrameCaptureS3Settings(BaseModel):
    """Frame Capture S3 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    canned_acl: Annotated[
        Optional[S3CannedAcl],
        Field(
            None,
            alias='CannedAcl',
            description='Specify the canned ACL to apply to each S3 request. Defaults to none.',
        ),
    ]


class FrameCaptureCdnSettings(BaseModel):
    """Frame Capture Cdn Settings."""

    model_config = ConfigDict(populate_by_name=True)

    frame_capture_s3_settings: Annotated[
        Optional[FrameCaptureS3Settings],
        Field(
            None,
            alias='FrameCaptureS3Settings',
            description='',
        ),
    ]


class Hdr10Settings(BaseModel):
    """Hdr10 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    max_cll: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxCll',
            description='Maximum Content Light Level An integer metadata value defining the maximum light level, in nits, of any single pixel within an encoded HDR video stream or file.',
        ),
    ]

    max_fall: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxFall',
            description='Maximum Frame Average Light Level An integer metadata value defining the maximum average light level, in nits, for any single frame within an encoded HDR video stream or file.',
        ),
    ]


class AvailBlanking(BaseModel):
    """Avail Blanking."""

    model_config = ConfigDict(populate_by_name=True)

    avail_blanking_image: Annotated[
        Optional[InputLocation],
        Field(
            None,
            alias='AvailBlankingImage',
            description='Blanking image to be used. Leave empty for solid black. Only bmp and png images are supported.',
        ),
    ]

    state: Annotated[
        Optional[AvailBlankingState],
        Field(
            None,
            alias='State',
            description='When set to enabled, causes video, audio and captions to be blanked when insertion metadata is added.',
        ),
    ]


class BlackoutSlate(BaseModel):
    """Blackout Slate."""

    model_config = ConfigDict(populate_by_name=True)

    blackout_slate_image: Annotated[
        Optional[InputLocation],
        Field(
            None,
            alias='BlackoutSlateImage',
            description='Blackout slate image to be used. Leave empty for solid black. Only bmp and png images are supported.',
        ),
    ]

    network_end_blackout: Annotated[
        Optional[BlackoutSlateNetworkEndBlackout],
        Field(
            None,
            alias='NetworkEndBlackout',
            description='Setting to enabled causes the encoder to blackout the video, audio, and captions, and raise the "Network Blackout Image" slate when an SCTE104/35 Network End Segmentation Descriptor is encountered. The blackout will be lifted when the Network Start Segmentation Descriptor is encountered. The Network End and Network Start descriptors must contain a network ID that matches the value entered in "Network ID".',
        ),
    ]

    network_end_blackout_image: Annotated[
        Optional[InputLocation],
        Field(
            None,
            alias='NetworkEndBlackoutImage',
            description='Path to local file to use as Network End Blackout image. Image will be scaled to fill the entire output raster.',
        ),
    ]

    network_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='NetworkId',
            description='Provides Network ID that matches EIDR ID format (e.g., "10.XXXX/XXXX-XXXX-XXXX-XXXX-XXXX-C").',
        ),
    ]

    state: Annotated[
        Optional[BlackoutSlateState],
        Field(
            None,
            alias='State',
            description='When set to enabled, causes video, audio and captions to be blanked when indicated by program metadata.',
        ),
    ]


class FrameCaptureGroupSettings(BaseModel):
    """Frame Capture Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='The destination for the frame capture files. Either the URI for an Amazon S3 bucket and object, plus a file name prefix (for example, s3ssl://sportsDelivery/highlights/20180820/curling-) or the URI for a MediaStore container, plus a file name prefix (for example, mediastoressl://sportsDelivery/20180820/curling-). The final file names consist of the prefix from the destination field (for example, "curling-") + name modifier + the counter (5 digits, starting from 00001) + extension (which is always .jpg). For example, curling-low.00001.jpg',
        ),
    ]

    frame_capture_cdn_settings: Annotated[
        Optional[FrameCaptureCdnSettings],
        Field(
            None,
            alias='FrameCaptureCdnSettings',
            description='Parameters that control interactions with the CDN.',
        ),
    ]


class GlobalConfiguration(BaseModel):
    """Global Configuration."""

    model_config = ConfigDict(populate_by_name=True)

    initial_audio_gain: Annotated[
        Optional[int],
        Field(
            None,
            alias='InitialAudioGain',
            description='Value to set the initial audio gain for the Live Event.',
        ),
    ]

    input_end_action: Annotated[
        Optional[GlobalConfigurationInputEndAction],
        Field(
            None,
            alias='InputEndAction',
            description='Indicates the action to take when the current input completes (e.g. end-of-file). When switchAndLoopInputs is configured the encoder will restart at the beginning of the first input. When "none" is configured the encoder will transcode either black, a solid color, or a user specified slate images per the "Input Loss Behavior" configuration until the next input switch occurs (which is controlled through the Channel Schedule API).',
        ),
    ]

    input_loss_behavior: Annotated[
        Optional[InputLossBehavior],
        Field(
            None,
            alias='InputLossBehavior',
            description='Settings for system actions when input is lost.',
        ),
    ]

    output_locking_mode: Annotated[
        Optional[GlobalConfigurationOutputLockingMode],
        Field(
            None,
            alias='OutputLockingMode',
            description='Indicates how MediaLive pipelines are synchronized. PIPELINE_LOCKING - MediaLive will attempt to synchronize the output of each pipeline to the other. EPOCH_LOCKING - MediaLive will attempt to synchronize the output of each pipeline to the Unix epoch. DISABLED - MediaLive will not attempt to synchronize the output of pipelines. We advise against disabling output locking because it has negative side effects in most workflows. For more information, see the section about output locking (pipeline locking) in the Medialive user guide.',
        ),
    ]

    output_timing_source: Annotated[
        Optional[GlobalConfigurationOutputTimingSource],
        Field(
            None,
            alias='OutputTimingSource',
            description='Indicates whether the rate of frames emitted by the Live encoder should be paced by its system clock (which optionally may be locked to another source via NTP) or should be locked to the clock of the source that is providing the input stream.',
        ),
    ]

    support_low_framerate_inputs: Annotated[
        Optional[GlobalConfigurationLowFramerateInputs],
        Field(
            None,
            alias='SupportLowFramerateInputs',
            description='Adjusts video input buffer for streams with very low video framerates. This is commonly set to enabled for music channels with less than one video frame per second.',
        ),
    ]

    output_locking_settings: Annotated[
        Optional[OutputLockingSettings],
        Field(
            None,
            alias='OutputLockingSettings',
            description='Advanced output locking settings',
        ),
    ]


class Rec601Settings(BaseModel):
    """Rec601 Settings."""

    model_config = ConfigDict(populate_by_name=True)


class Rec709Settings(BaseModel):
    """Rec709 Settings."""

    model_config = ConfigDict(populate_by_name=True)


class Av1ColorSpaceSettings(BaseModel):
    """Av1 Color Space Settings."""

    model_config = ConfigDict(populate_by_name=True)

    color_space_passthrough_settings: Annotated[
        Optional[ColorSpacePassthroughSettings],
        Field(
            None,
            alias='ColorSpacePassthroughSettings',
            description='',
        ),
    ]

    hdr10_settings: Annotated[
        Optional[Hdr10Settings],
        Field(
            None,
            alias='Hdr10Settings',
            description='',
        ),
    ]

    rec601_settings: Annotated[
        Optional[Rec601Settings],
        Field(
            None,
            alias='Rec601Settings',
            description='',
        ),
    ]

    rec709_settings: Annotated[
        Optional[Rec709Settings],
        Field(
            None,
            alias='Rec709Settings',
            description='',
        ),
    ]


class H264ColorSpaceSettings(BaseModel):
    """H264 Color Space Settings."""

    model_config = ConfigDict(populate_by_name=True)

    color_space_passthrough_settings: Annotated[
        Optional[ColorSpacePassthroughSettings],
        Field(
            None,
            alias='ColorSpacePassthroughSettings',
            description='',
        ),
    ]

    rec601_settings: Annotated[
        Optional[Rec601Settings],
        Field(
            None,
            alias='Rec601Settings',
            description='',
        ),
    ]

    rec709_settings: Annotated[
        Optional[Rec709Settings],
        Field(
            None,
            alias='Rec709Settings',
            description='',
        ),
    ]


class H265ColorSpaceSettings(BaseModel):
    """H265 Color Space Settings."""

    model_config = ConfigDict(populate_by_name=True)

    color_space_passthrough_settings: Annotated[
        Optional[ColorSpacePassthroughSettings],
        Field(
            None,
            alias='ColorSpacePassthroughSettings',
            description='',
        ),
    ]

    dolby_vision81_settings: Annotated[
        Optional[DolbyVision81Settings],
        Field(
            None,
            alias='DolbyVision81Settings',
            description='',
        ),
    ]

    hdr10_settings: Annotated[
        Optional[Hdr10Settings],
        Field(
            None,
            alias='Hdr10Settings',
            description='',
        ),
    ]

    rec601_settings: Annotated[
        Optional[Rec601Settings],
        Field(
            None,
            alias='Rec601Settings',
            description='',
        ),
    ]

    rec709_settings: Annotated[
        Optional[Rec709Settings],
        Field(
            None,
            alias='Rec709Settings',
            description='',
        ),
    ]


class AvailSettings(BaseModel):
    """Avail Settings."""

    model_config = ConfigDict(populate_by_name=True)

    esam: Annotated[
        Optional[Esam],
        Field(
            None,
            alias='Esam',
            description='',
        ),
    ]

    scte35_splice_insert: Annotated[
        Optional[Scte35SpliceInsert],
        Field(
            None,
            alias='Scte35SpliceInsert',
            description='',
        ),
    ]

    scte35_time_signal_apos: Annotated[
        Optional[Scte35TimeSignalApos],
        Field(
            None,
            alias='Scte35TimeSignalApos',
            description='',
        ),
    ]


class AvailConfiguration(BaseModel):
    """Avail Configuration."""

    model_config = ConfigDict(populate_by_name=True)

    avail_settings: Annotated[
        Optional[AvailSettings],
        Field(
            None,
            alias='AvailSettings',
            description='Controls how SCTE-35 messages create cues. Splice Insert mode treats all segmentation signals traditionally. With Time Signal APOS mode only Time Signal Placement Opportunity and Break messages create segment breaks. With ESAM mode, signals are forwarded to an ESAM server for possible update.',
        ),
    ]

    scte35_segmentation_scope: Annotated[
        Optional[Scte35SegmentationScope],
        Field(
            None,
            alias='Scte35SegmentationScope',
            description='Configures whether SCTE 35 passthrough triggers segment breaks in all output groups that use segmented outputs. Insertion of a SCTE 35 message typically results in a segment break, in addition to the regular cadence of breaks. The segment breaks appear in video outputs, audio outputs, and captions outputs (if any). ALL_OUTPUT_GROUPS: Default. Insert the segment break in in all output groups that have segmented outputs. This is the legacy behavior. SCTE35_ENABLED_OUTPUT_GROUPS: Insert the segment break only in output groups that have SCTE 35 passthrough enabled. This is the recommended value, because it reduces unnecessary segment breaks.',
        ),
    ]


class TemporalFilterSettings(BaseModel):
    """Temporal Filter Settings."""

    model_config = ConfigDict(populate_by_name=True)

    post_filter_sharpening: Annotated[
        Optional[TemporalFilterPostFilterSharpening],
        Field(
            None,
            alias='PostFilterSharpening',
            description='If you enable this filter, the results are the following: - If the source content is noisy (it contains excessive digital artifacts), the filter cleans up the source. - If the source content is already clean, the filter tends to decrease the bitrate, especially when the rate control mode is QVBR.',
        ),
    ]

    strength: Annotated[
        Optional[TemporalFilterStrength],
        Field(
            None,
            alias='Strength',
            description='Choose a filter strength. We recommend a strength of 1 or 2. A higher strength might take out good information, resulting in an image that is overly soft.',
        ),
    ]


class H264FilterSettings(BaseModel):
    """H264 Filter Settings."""

    model_config = ConfigDict(populate_by_name=True)

    temporal_filter_settings: Annotated[
        Optional[TemporalFilterSettings],
        Field(
            None,
            alias='TemporalFilterSettings',
            description='',
        ),
    ]

    bandwidth_reduction_filter_settings: Annotated[
        Optional[BandwidthReductionFilterSettings],
        Field(
            None,
            alias='BandwidthReductionFilterSettings',
            description='',
        ),
    ]


class H265FilterSettings(BaseModel):
    """H265 Filter Settings."""

    model_config = ConfigDict(populate_by_name=True)

    temporal_filter_settings: Annotated[
        Optional[TemporalFilterSettings],
        Field(
            None,
            alias='TemporalFilterSettings',
            description='',
        ),
    ]

    bandwidth_reduction_filter_settings: Annotated[
        Optional[BandwidthReductionFilterSettings],
        Field(
            None,
            alias='BandwidthReductionFilterSettings',
            description='',
        ),
    ]


class Mpeg2FilterSettings(BaseModel):
    """Mpeg2 Filter Settings."""

    model_config = ConfigDict(populate_by_name=True)

    temporal_filter_settings: Annotated[
        Optional[TemporalFilterSettings],
        Field(
            None,
            alias='TemporalFilterSettings',
            description='',
        ),
    ]


class Thumbnail(BaseModel):
    """Details of a single thumbnail."""

    model_config = ConfigDict(populate_by_name=True)

    body: Annotated[
        Optional[str],
        Field(
            None,
            alias='Body',
            description='The binary data for the latest thumbnail.',
        ),
    ]

    content_type: Annotated[
        Optional[str],
        Field(
            None,
            alias='ContentType',
            description='The content type for the latest thumbnail.',
        ),
    ]

    thumbnail_type: Annotated[
        Optional[ThumbnailType],
        Field(
            None,
            alias='ThumbnailType',
            description='Thumbnail Type',
        ),
    ]

    time_stamp: Annotated[
        Optional[datetime],
        Field(
            None,
            alias='TimeStamp',
            description='Time stamp for the latest thumbnail.',
        ),
    ]


class ThumbnailConfiguration(BaseModel):
    """Thumbnail Configuration."""

    model_config = ConfigDict(populate_by_name=True)

    state: Annotated[
        ThumbnailState,
        Field(
            ...,
            alias='State',
            description='Enables the thumbnail feature. The feature generates thumbnails of the incoming video in each pipeline in the channel. AUTO turns the feature on, DISABLE turns the feature off.',
        ),
    ]


class ThumbnailData(BaseModel):
    """The binary data for the thumbnail that the Link device has most recently sent to MediaLive."""

    model_config = ConfigDict(populate_by_name=True)

    body: Annotated[
        Optional[str],
        Field(
            None,
            alias='Body',
            description='The binary data for the thumbnail that the Link device has most recently sent to MediaLive.',
        ),
    ]


class ThumbnailDetail(BaseModel):
    """Thumbnail details for one pipeline of a running channel."""

    model_config = ConfigDict(populate_by_name=True)

    pipeline_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='PipelineId',
            description='Pipeline ID',
        ),
    ]

    thumbnails: Annotated[
        Optional[list[Thumbnail]],
        Field(
            None,
            alias='Thumbnails',
            description='thumbnails of a single pipeline',
        ),
    ]


class ThumbnailNoData(BaseModel):
    """Response when thumbnail has no data. It should have no message."""

    model_config = ConfigDict(populate_by_name=True)


class TimecodeBurninSettings(BaseModel):
    """Timecode Burnin Settings."""

    model_config = ConfigDict(populate_by_name=True)

    font_size: Annotated[
        TimecodeBurninFontSize,
        Field(
            ...,
            alias='FontSize',
            description='Choose a timecode burn-in font size',
        ),
    ]

    position: Annotated[
        TimecodeBurninPosition,
        Field(
            ...,
            alias='Position',
            description='Choose a timecode burn-in output position',
        ),
    ]

    prefix: Annotated[
        Optional[str],
        Field(
            None,
            alias='Prefix',
            description='Create a timecode burn-in prefix (optional)',
        ),
    ]


class Av1Settings(BaseModel):
    """Av1 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    afd_signaling: Annotated[
        Optional[AfdSignaling],
        Field(
            None,
            alias='AfdSignaling',
            description='Configures whether MediaLive will write AFD values into the video. AUTO: MediaLive will try to preserve the input AFD value (in cases where multiple AFD values are valid). FIXED: the AFD value will be the value configured in the fixedAfd parameter. NONE: MediaLive won\u0027t write AFD into the video',
        ),
    ]

    buf_size: Annotated[
        Optional[int],
        Field(
            None,
            alias='BufSize',
            description='The size of the buffer (HRD buffer model) in bits.',
        ),
    ]

    color_space_settings: Annotated[
        Optional[Av1ColorSpaceSettings],
        Field(
            None,
            alias='ColorSpaceSettings',
            description='Specify the type of color space to apply or choose to pass through. The default is to pass through the color space that is in the source.',
        ),
    ]

    fixed_afd: Annotated[
        Optional[FixedAfd],
        Field(
            None,
            alias='FixedAfd',
            description='Complete this property only if you set the afdSignaling property to FIXED. Choose the AFD value (4 bits) to write on all frames of the video encode.',
        ),
    ]

    framerate_denominator: Annotated[
        int,
        Field(
            ...,
            alias='FramerateDenominator',
            description='The denominator for the framerate. Framerate is a fraction, for example, 24000 / 1001.',
        ),
    ]

    framerate_numerator: Annotated[
        int,
        Field(
            ...,
            alias='FramerateNumerator',
            description='The numerator for the framerate. Framerate is a fraction, for example, 24000 / 1001.',
        ),
    ]

    gop_size: Annotated[
        Optional[float],
        Field(
            None,
            alias='GopSize',
            description='The GOP size (keyframe interval). If GopSizeUnits is frames, GopSize must be a whole number and must be greater than or equal to 1. If GopSizeUnits is seconds, GopSize must be greater than 0, but it can be a decimal.',
        ),
    ]

    gop_size_units: Annotated[
        Optional[Av1GopSizeUnits],
        Field(
            None,
            alias='GopSizeUnits',
            description='Choose the units for the GOP size: FRAMES or SECONDS. For SECONDS, MediaLive converts the size into a frame count at run time.',
        ),
    ]

    level: Annotated[
        Optional[Av1Level],
        Field(
            None,
            alias='Level',
            description='Sets the level. This parameter is one of the properties of the encoding scheme for AV1.',
        ),
    ]

    look_ahead_rate_control: Annotated[
        Optional[Av1LookAheadRateControl],
        Field(
            None,
            alias='LookAheadRateControl',
            description='Sets the amount of lookahead. A value of LOW can decrease latency and memory usage. A value of HIGH can produce better quality for certain content.',
        ),
    ]

    max_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxBitrate',
            description='The maximum bitrate to assign. For recommendations, see the description for qvbrQualityLevel.',
        ),
    ]

    min_i_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinIInterval',
            description='Applies only if you enable SceneChangeDetect. Sets the interval between frames. This property ensures a minimum separation between repeated (cadence) I-frames and any I-frames inserted by scene change detection (SCD frames). Enter a number for the interval, measured in number of frames. If an SCD frame and a cadence frame are closer than the specified number of frames, MediaLive shrinks or stretches the GOP to include the SCD frame. Then normal cadence resumes in the next GOP. For GOP stretch to succeed, you must enable LookAheadRateControl. Note that the maximum GOP stretch = (GOP size) + (Minimum I-interval) - 1',
        ),
    ]

    par_denominator: Annotated[
        Optional[int],
        Field(
            None,
            alias='ParDenominator',
            description='The denominator for the output pixel aspect ratio (PAR).',
        ),
    ]

    par_numerator: Annotated[
        Optional[int],
        Field(
            None,
            alias='ParNumerator',
            description='The numerator for the output pixel aspect ratio (PAR).',
        ),
    ]

    qvbr_quality_level: Annotated[
        Optional[int],
        Field(
            None,
            alias='QvbrQualityLevel',
            description='Controls the target quality for the video encode. With QVBR rate control mode, the final quality is the target quality, constrained by the maxBitrate. Set values for the qvbrQualityLevel property and maxBitrate property that suit your most important viewing devices. To let MediaLive set the quality level (AUTO mode), leave the qvbrQualityLevel field empty. In this case, MediaLive uses the maximum bitrate, and the quality follows from that: more complex content might have a lower quality. Or set a target quality level and a maximum bitrate. With more complex content, MediaLive will try to achieve the target quality, but it won\u0027t exceed the maximum bitrate. With less complex content, This option will use only the bitrate needed to reach the target quality. Recommended values are: Primary screen: qvbrQualityLevel: Leave empty. maxBitrate: 4,000,000 PC or tablet: qvbrQualityLevel: Leave empty. maxBitrate: 1,500,000 to 3,000,000 Smartphone: qvbrQualityLevel: Leave empty. maxBitrate: 1,000,000 to 1,500,000',
        ),
    ]

    scene_change_detect: Annotated[
        Optional[Av1SceneChangeDetect],
        Field(
            None,
            alias='SceneChangeDetect',
            description='Controls whether MediaLive inserts I-frames when it detects a scene change. ENABLED or DISABLED.',
        ),
    ]

    timecode_burnin_settings: Annotated[
        Optional[TimecodeBurninSettings],
        Field(
            None,
            alias='TimecodeBurninSettings',
            description='Configures the timecode burn-in feature. If you enable this feature, the timecode will become part of the video.',
        ),
    ]

    bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='Bitrate',
            description='Average bitrate in bits/second. Required when the rate control mode is CBR. Not used for QVBR.',
        ),
    ]

    rate_control_mode: Annotated[
        Optional[Av1RateControlMode],
        Field(
            None,
            alias='RateControlMode',
            description='Rate control mode. QVBR: Quality will match the specified quality level except when it is constrained by the maximum bitrate. Recommended if you or your viewers pay for bandwidth. CBR: Quality varies, depending on the video complexity. Recommended only if you distribute your assets to devices that cannot handle variable bitrates.',
        ),
    ]

    min_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinBitrate',
            description='Used for QVBR rate control mode only. Optional. Enter a minimum bitrate if you want to keep the output bitrate about a threshold, in order to prevent the downstream system from de-allocating network bandwidth for this output.',
        ),
    ]


class FrameCaptureSettings(BaseModel):
    """Frame Capture Settings."""

    model_config = ConfigDict(populate_by_name=True)

    capture_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='CaptureInterval',
            description='The frequency at which to capture frames for inclusion in the output. May be specified in either seconds or milliseconds, as specified by captureIntervalUnits.',
        ),
    ]

    capture_interval_units: Annotated[
        Optional[FrameCaptureIntervalUnit],
        Field(
            None,
            alias='CaptureIntervalUnits',
            description='Unit for the frame capture interval.',
        ),
    ]

    timecode_burnin_settings: Annotated[
        Optional[TimecodeBurninSettings],
        Field(
            None,
            alias='TimecodeBurninSettings',
            description='Timecode burn-in settings',
        ),
    ]


class H264Settings(BaseModel):
    """H264 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    adaptive_quantization: Annotated[
        Optional[H264AdaptiveQuantization],
        Field(
            None,
            alias='AdaptiveQuantization',
            description='Enables or disables adaptive quantization (AQ), which is a technique MediaLive can apply to video on a frame-by-frame basis to produce more compression without losing quality. There are three types of adaptive quantization: spatial, temporal, and flicker. We recommend that you set the field to Auto. For more information about all the options, see the topic about video adaptive quantization in the MediaLive user guide.',
        ),
    ]

    afd_signaling: Annotated[
        Optional[AfdSignaling],
        Field(
            None,
            alias='AfdSignaling',
            description='Indicates that AFD values will be written into the output stream. If afdSignaling is "auto", the system will try to preserve the input AFD value (in cases where multiple AFD values are valid). If set to "fixed", the AFD value will be the value configured in the fixedAfd parameter.',
        ),
    ]

    bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='Bitrate',
            description='Average bitrate in bits/second. Required when the rate control mode is VBR or CBR. Not used for QVBR. In an MS Smooth output group, each output must have a unique value when its bitrate is rounded down to the nearest multiple of 1000.',
        ),
    ]

    buf_fill_pct: Annotated[
        Optional[int],
        Field(
            None,
            alias='BufFillPct',
            description='Percentage of the buffer that should initially be filled (HRD buffer model).',
        ),
    ]

    buf_size: Annotated[
        Optional[int],
        Field(
            None,
            alias='BufSize',
            description='Size of buffer (HRD buffer model) in bits.',
        ),
    ]

    color_metadata: Annotated[
        Optional[H264ColorMetadata],
        Field(
            None,
            alias='ColorMetadata',
            description='Includes colorspace metadata in the output.',
        ),
    ]

    color_space_settings: Annotated[
        Optional[H264ColorSpaceSettings],
        Field(
            None,
            alias='ColorSpaceSettings',
            description='Specify the type of color space to apply or choose to pass through. The default is to pass through the color space that is in the source.',
        ),
    ]

    entropy_encoding: Annotated[
        Optional[H264EntropyEncoding],
        Field(
            None,
            alias='EntropyEncoding',
            description='Entropy encoding mode. Use cabac (must be in Main or High profile) or cavlc.',
        ),
    ]

    filter_settings: Annotated[
        Optional[H264FilterSettings],
        Field(
            None,
            alias='FilterSettings',
            description='Optional. Both filters reduce bandwidth by removing imperceptible details. You can enable one of the filters. We recommend that you try both filters and observe the results to decide which one to use. The Temporal Filter reduces bandwidth by removing imperceptible details in the content. It combines perceptual filtering and motion compensated temporal filtering (MCTF). It operates independently of the compression level. The Bandwidth Reduction filter is a perceptual filter located within the encoding loop. It adapts to the current compression level to filter imperceptible signals. This filter works only when the resolution is 1080p or lower.',
        ),
    ]

    fixed_afd: Annotated[
        Optional[FixedAfd],
        Field(
            None,
            alias='FixedAfd',
            description='Four bit AFD value to write on all frames of video in the output stream. Only valid when afdSignaling is set to \u0027Fixed\u0027.',
        ),
    ]

    flicker_aq: Annotated[
        Optional[H264FlickerAq],
        Field(
            None,
            alias='FlickerAq',
            description='Flicker AQ makes adjustments within each frame to reduce flicker or \u0027pop\u0027 on I-frames. The value to enter in this field depends on the value in the Adaptive quantization field. For more information, see the topic about video adaptive quantization in the MediaLive user guide.',
        ),
    ]

    force_field_pictures: Annotated[
        Optional[H264ForceFieldPictures],
        Field(
            None,
            alias='ForceFieldPictures',
            description='This setting applies only when scan type is "interlaced." It controls whether coding is performed on a field basis or on a frame basis. (When the video is progressive, the coding is always performed on a frame basis.) enabled: Force MediaLive to code on a field basis, so that odd and even sets of fields are coded separately. disabled: Code the two sets of fields separately (on a field basis) or together (on a frame basis using PAFF), depending on what is most appropriate for the content.',
        ),
    ]

    framerate_control: Annotated[
        Optional[H264FramerateControl],
        Field(
            None,
            alias='FramerateControl',
            description='This field indicates how the output video frame rate is specified. If "specified" is selected then the output video frame rate is determined by framerateNumerator and framerateDenominator, else if "initializeFromSource" is selected then the output video frame rate will be set equal to the input video frame rate of the first input.',
        ),
    ]

    framerate_denominator: Annotated[
        Optional[int],
        Field(
            None,
            alias='FramerateDenominator',
            description='Framerate denominator.',
        ),
    ]

    framerate_numerator: Annotated[
        Optional[int],
        Field(
            None,
            alias='FramerateNumerator',
            description='Framerate numerator - framerate is a fraction, e.g. 24000 / 1001 = 23.976 fps.',
        ),
    ]

    gop_b_reference: Annotated[
        Optional[H264GopBReference],
        Field(
            None,
            alias='GopBReference',
            description='Documentation update needed',
        ),
    ]

    gop_closed_cadence: Annotated[
        Optional[int],
        Field(
            None,
            alias='GopClosedCadence',
            description='Frequency of closed GOPs. In streaming applications, it is recommended that this be set to 1 so a decoder joining mid-stream will receive an IDR frame as quickly as possible. Setting this value to 0 will break output segmenting.',
        ),
    ]

    gop_num_b_frames: Annotated[
        Optional[int],
        Field(
            None,
            alias='GopNumBFrames',
            description='Number of B-frames between reference frames.',
        ),
    ]

    gop_size: Annotated[
        Optional[float],
        Field(
            None,
            alias='GopSize',
            description='GOP size (keyframe interval) in units of either frames or seconds per gopSizeUnits. If gopSizeUnits is frames, gopSize must be an integer and must be greater than or equal to 1. If gopSizeUnits is seconds, gopSize must be greater than 0, but need not be an integer.',
        ),
    ]

    gop_size_units: Annotated[
        Optional[H264GopSizeUnits],
        Field(
            None,
            alias='GopSizeUnits',
            description='Indicates if the gopSize is specified in frames or seconds. If seconds the system will convert the gopSize into a frame count at run time.',
        ),
    ]

    level: Annotated[
        Optional[H264Level],
        Field(
            None,
            alias='Level',
            description='H.264 Level.',
        ),
    ]

    look_ahead_rate_control: Annotated[
        Optional[H264LookAheadRateControl],
        Field(
            None,
            alias='LookAheadRateControl',
            description='Amount of lookahead. A value of low can decrease latency and memory usage, while high can produce better quality for certain content.',
        ),
    ]

    max_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxBitrate',
            description='For QVBR: See the tooltip for Quality level For VBR: Set the maximum bitrate in order to accommodate expected spikes in the complexity of the video.',
        ),
    ]

    min_i_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinIInterval',
            description='Only meaningful if sceneChangeDetect is set to enabled. Defaults to 5 if multiplex rate control is used. Enforces separation between repeated (cadence) I-frames and I-frames inserted by Scene Change Detection. If a scene change I-frame is within I-interval frames of a cadence I-frame, the GOP is shrunk and/or stretched to the scene change I-frame. GOP stretch requires enabling lookahead as well as setting I-interval. The normal cadence resumes for the next GOP. Note: Maximum GOP stretch = GOP size + Min-I-interval - 1',
        ),
    ]

    num_ref_frames: Annotated[
        Optional[int],
        Field(
            None,
            alias='NumRefFrames',
            description='Number of reference frames to use. The encoder may use more than requested if using B-frames and/or interlaced encoding.',
        ),
    ]

    par_control: Annotated[
        Optional[H264ParControl],
        Field(
            None,
            alias='ParControl',
            description='This field indicates how the output pixel aspect ratio is specified. If "specified" is selected then the output video pixel aspect ratio is determined by parNumerator and parDenominator, else if "initializeFromSource" is selected then the output pixsel aspect ratio will be set equal to the input video pixel aspect ratio of the first input.',
        ),
    ]

    par_denominator: Annotated[
        Optional[int],
        Field(
            None,
            alias='ParDenominator',
            description='Pixel Aspect Ratio denominator.',
        ),
    ]

    par_numerator: Annotated[
        Optional[int],
        Field(
            None,
            alias='ParNumerator',
            description='Pixel Aspect Ratio numerator.',
        ),
    ]

    profile: Annotated[
        Optional[H264Profile],
        Field(
            None,
            alias='Profile',
            description='H.264 Profile.',
        ),
    ]

    quality_level: Annotated[
        Optional[H264QualityLevel],
        Field(
            None,
            alias='QualityLevel',
            description='Leave as STANDARD_QUALITY or choose a different value (which might result in additional costs to run the channel). - ENHANCED_QUALITY: Produces a slightly better video quality without an increase in the bitrate. Has an effect only when the Rate control mode is QVBR or CBR. If this channel is in a MediaLive multiplex, the value must be ENHANCED_QUALITY. - STANDARD_QUALITY: Valid for any Rate control mode.',
        ),
    ]

    qvbr_quality_level: Annotated[
        Optional[int],
        Field(
            None,
            alias='QvbrQualityLevel',
            description='Controls the target quality for the video encode. Applies only when the rate control mode is QVBR. You can set a target quality or you can let MediaLive determine the best quality. To set a target quality, enter values in the QVBR quality level field and the Max bitrate field. Enter values that suit your most important viewing devices. Recommended values are: - Primary screen: Quality level: 8 to 10. Max bitrate: 4M - PC or tablet: Quality level: 7. Max bitrate: 1.5M to 3M - Smartphone: Quality level: 6. Max bitrate: 1M to 1.5M To let MediaLive decide, leave the QVBR quality level field empty, and in Max bitrate enter the maximum rate you want in the video. For more information, see the section called "Video - rate control mode" in the MediaLive user guide',
        ),
    ]

    rate_control_mode: Annotated[
        Optional[H264RateControlMode],
        Field(
            None,
            alias='RateControlMode',
            description='Rate control mode. QVBR: Quality will match the specified quality level except when it is constrained by the maximum bitrate. Recommended if you or your viewers pay for bandwidth. VBR: Quality and bitrate vary, depending on the video complexity. Recommended instead of QVBR if you want to maintain a specific average bitrate over the duration of the channel. CBR: Quality varies, depending on the video complexity. Recommended only if you distribute your assets to devices that cannot handle variable bitrates. Multiplex: This rate control mode is only supported (and is required) when the video is being delivered to a MediaLive Multiplex in which case the rate control configuration is controlled by the properties within the Multiplex Program.',
        ),
    ]

    scan_type: Annotated[
        Optional[H264ScanType],
        Field(
            None,
            alias='ScanType',
            description='Sets the scan type of the output to progressive or top-field-first interlaced.',
        ),
    ]

    scene_change_detect: Annotated[
        Optional[H264SceneChangeDetect],
        Field(
            None,
            alias='SceneChangeDetect',
            description='Scene change detection. - On: inserts I-frames when scene change is detected. - Off: does not force an I-frame when scene change is detected.',
        ),
    ]

    slices: Annotated[
        Optional[int],
        Field(
            None,
            alias='Slices',
            description='Number of slices per picture. Must be less than or equal to the number of macroblock rows for progressive pictures, and less than or equal to half the number of macroblock rows for interlaced pictures. This field is optional; when no value is specified the encoder will choose the number of slices based on encode resolution.',
        ),
    ]

    softness: Annotated[
        Optional[int],
        Field(
            None,
            alias='Softness',
            description='Softness. Selects quantizer matrix, larger values reduce high-frequency content in the encoded image. If not set to zero, must be greater than 15.',
        ),
    ]

    spatial_aq: Annotated[
        Optional[H264SpatialAq],
        Field(
            None,
            alias='SpatialAq',
            description='Spatial AQ makes adjustments within each frame based on spatial variation of content complexity. The value to enter in this field depends on the value in the Adaptive quantization field. For more information, see the topic about video adaptive quantization in the MediaLive user guide.',
        ),
    ]

    subgop_length: Annotated[
        Optional[H264SubGopLength],
        Field(
            None,
            alias='SubgopLength',
            description='If set to fixed, use gopNumBFrames B-frames per sub-GOP. If set to dynamic, optimize the number of B-frames used for each sub-GOP to improve visual quality.',
        ),
    ]

    syntax: Annotated[
        Optional[H264Syntax],
        Field(
            None,
            alias='Syntax',
            description='Produces a bitstream compliant with SMPTE RP-2027.',
        ),
    ]

    temporal_aq: Annotated[
        Optional[H264TemporalAq],
        Field(
            None,
            alias='TemporalAq',
            description='Temporal makes adjustments within each frame based on variations in content complexity over time. The value to enter in this field depends on the value in the Adaptive quantization field. For more information, see the topic about video adaptive quantization in the MediaLive user guide.',
        ),
    ]

    timecode_insertion: Annotated[
        Optional[H264TimecodeInsertionBehavior],
        Field(
            None,
            alias='TimecodeInsertion',
            description='Determines how timecodes should be inserted into the video elementary stream. - \u0027disabled\u0027: Do not include timecodes - \u0027picTimingSei\u0027: Pass through picture timing SEI messages from the source specified in Timecode Config',
        ),
    ]

    timecode_burnin_settings: Annotated[
        Optional[TimecodeBurninSettings],
        Field(
            None,
            alias='TimecodeBurninSettings',
            description='Timecode burn-in settings',
        ),
    ]

    min_qp: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinQp',
            description='Sets the minimum QP. If you aren\u0027t familiar with quantization adjustment, leave the field empty. MediaLive will apply an appropriate value.',
        ),
    ]

    min_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinBitrate',
            description='Used for QVBR rate control mode only. Optional. Enter a minimum bitrate if you want to keep the output bitrate about a threshold, in order to prevent the downstream system from de-allocating network bandwidth for this output.',
        ),
    ]


class H265Settings(BaseModel):
    """H265 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    adaptive_quantization: Annotated[
        Optional[H265AdaptiveQuantization],
        Field(
            None,
            alias='AdaptiveQuantization',
            description='Enables or disables adaptive quantization (AQ), which is a technique MediaLive can apply to video on a frame-by-frame basis to produce more compression without losing quality. There are three types of adaptive quantization: spatial, temporal, and flicker. Flicker is the only type that you can customize. We recommend that you set the field to Auto. For more information about all the options, see the topic about video adaptive quantization in the MediaLive user guide.',
        ),
    ]

    afd_signaling: Annotated[
        Optional[AfdSignaling],
        Field(
            None,
            alias='AfdSignaling',
            description='Indicates that AFD values will be written into the output stream. If afdSignaling is "auto", the system will try to preserve the input AFD value (in cases where multiple AFD values are valid). If set to "fixed", the AFD value will be the value configured in the fixedAfd parameter.',
        ),
    ]

    alternative_transfer_function: Annotated[
        Optional[H265AlternativeTransferFunction],
        Field(
            None,
            alias='AlternativeTransferFunction',
            description='Whether or not EML should insert an Alternative Transfer Function SEI message to support backwards compatibility with non-HDR decoders and displays.',
        ),
    ]

    bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='Bitrate',
            description='Average bitrate in bits/second. Required when the rate control mode is VBR or CBR. Not used for QVBR. In an MS Smooth output group, each output must have a unique value when its bitrate is rounded down to the nearest multiple of 1000.',
        ),
    ]

    buf_size: Annotated[
        Optional[int],
        Field(
            None,
            alias='BufSize',
            description='Size of buffer (HRD buffer model) in bits.',
        ),
    ]

    color_metadata: Annotated[
        Optional[H265ColorMetadata],
        Field(
            None,
            alias='ColorMetadata',
            description='Includes colorspace metadata in the output.',
        ),
    ]

    color_space_settings: Annotated[
        Optional[H265ColorSpaceSettings],
        Field(
            None,
            alias='ColorSpaceSettings',
            description='Specify the type of color space to apply or choose to pass through. The default is to pass through the color space that is in the source.',
        ),
    ]

    filter_settings: Annotated[
        Optional[H265FilterSettings],
        Field(
            None,
            alias='FilterSettings',
            description='Optional. Both filters reduce bandwidth by removing imperceptible details. You can enable one of the filters. We recommend that you try both filters and observe the results to decide which one to use. The Temporal Filter reduces bandwidth by removing imperceptible details in the content. It combines perceptual filtering and motion compensated temporal filtering (MCTF). It operates independently of the compression level. The Bandwidth Reduction filter is a perceptual filter located within the encoding loop. It adapts to the current compression level to filter imperceptible signals. This filter works only when the resolution is 1080p or lower.',
        ),
    ]

    fixed_afd: Annotated[
        Optional[FixedAfd],
        Field(
            None,
            alias='FixedAfd',
            description='Four bit AFD value to write on all frames of video in the output stream. Only valid when afdSignaling is set to \u0027Fixed\u0027.',
        ),
    ]

    flicker_aq: Annotated[
        Optional[H265FlickerAq],
        Field(
            None,
            alias='FlickerAq',
            description='Flicker AQ makes adjustments within each frame to reduce flicker or \u0027pop\u0027 on I-frames. The value to enter in this field depends on the value in the Adaptive quantization field. For more information, see the topic about video adaptive quantization in the MediaLive user guide.',
        ),
    ]

    framerate_denominator: Annotated[
        int,
        Field(
            ...,
            alias='FramerateDenominator',
            description='Framerate denominator.',
        ),
    ]

    framerate_numerator: Annotated[
        int,
        Field(
            ...,
            alias='FramerateNumerator',
            description='Framerate numerator - framerate is a fraction, e.g. 24000 / 1001 = 23.976 fps.',
        ),
    ]

    gop_closed_cadence: Annotated[
        Optional[int],
        Field(
            None,
            alias='GopClosedCadence',
            description='Frequency of closed GOPs. In streaming applications, it is recommended that this be set to 1 so a decoder joining mid-stream will receive an IDR frame as quickly as possible. Setting this value to 0 will break output segmenting.',
        ),
    ]

    gop_size: Annotated[
        Optional[float],
        Field(
            None,
            alias='GopSize',
            description='GOP size (keyframe interval) in units of either frames or seconds per gopSizeUnits. If gopSizeUnits is frames, gopSize must be an integer and must be greater than or equal to 1. If gopSizeUnits is seconds, gopSize must be greater than 0, but need not be an integer.',
        ),
    ]

    gop_size_units: Annotated[
        Optional[H265GopSizeUnits],
        Field(
            None,
            alias='GopSizeUnits',
            description='Indicates if the gopSize is specified in frames or seconds. If seconds the system will convert the gopSize into a frame count at run time.',
        ),
    ]

    level: Annotated[
        Optional[H265Level],
        Field(
            None,
            alias='Level',
            description='H.265 Level.',
        ),
    ]

    look_ahead_rate_control: Annotated[
        Optional[H265LookAheadRateControl],
        Field(
            None,
            alias='LookAheadRateControl',
            description='Amount of lookahead. A value of low can decrease latency and memory usage, while high can produce better quality for certain content.',
        ),
    ]

    max_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxBitrate',
            description='For QVBR: See the tooltip for Quality level',
        ),
    ]

    min_i_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinIInterval',
            description='Only meaningful if sceneChangeDetect is set to enabled. Defaults to 5 if multiplex rate control is used. Enforces separation between repeated (cadence) I-frames and I-frames inserted by Scene Change Detection. If a scene change I-frame is within I-interval frames of a cadence I-frame, the GOP is shrunk and/or stretched to the scene change I-frame. GOP stretch requires enabling lookahead as well as setting I-interval. The normal cadence resumes for the next GOP. Note: Maximum GOP stretch = GOP size + Min-I-interval - 1',
        ),
    ]

    par_denominator: Annotated[
        Optional[int],
        Field(
            None,
            alias='ParDenominator',
            description='Pixel Aspect Ratio denominator.',
        ),
    ]

    par_numerator: Annotated[
        Optional[int],
        Field(
            None,
            alias='ParNumerator',
            description='Pixel Aspect Ratio numerator.',
        ),
    ]

    profile: Annotated[
        Optional[H265Profile],
        Field(
            None,
            alias='Profile',
            description='H.265 Profile.',
        ),
    ]

    qvbr_quality_level: Annotated[
        Optional[int],
        Field(
            None,
            alias='QvbrQualityLevel',
            description='Controls the target quality for the video encode. Applies only when the rate control mode is QVBR. Set values for the QVBR quality level field and Max bitrate field that suit your most important viewing devices. Recommended values are: - Primary screen: Quality level: 8 to 10. Max bitrate: 4M - PC or tablet: Quality level: 7. Max bitrate: 1.5M to 3M - Smartphone: Quality level: 6. Max bitrate: 1M to 1.5M',
        ),
    ]

    rate_control_mode: Annotated[
        Optional[H265RateControlMode],
        Field(
            None,
            alias='RateControlMode',
            description='Rate control mode. QVBR: Quality will match the specified quality level except when it is constrained by the maximum bitrate. Recommended if you or your viewers pay for bandwidth. CBR: Quality varies, depending on the video complexity. Recommended only if you distribute your assets to devices that cannot handle variable bitrates. Multiplex: This rate control mode is only supported (and is required) when the video is being delivered to a MediaLive Multiplex in which case the rate control configuration is controlled by the properties within the Multiplex Program.',
        ),
    ]

    scan_type: Annotated[
        Optional[H265ScanType],
        Field(
            None,
            alias='ScanType',
            description='Sets the scan type of the output to progressive or top-field-first interlaced.',
        ),
    ]

    scene_change_detect: Annotated[
        Optional[H265SceneChangeDetect],
        Field(
            None,
            alias='SceneChangeDetect',
            description='Scene change detection.',
        ),
    ]

    slices: Annotated[
        Optional[int],
        Field(
            None,
            alias='Slices',
            description='Number of slices per picture. Must be less than or equal to the number of macroblock rows for progressive pictures, and less than or equal to half the number of macroblock rows for interlaced pictures. This field is optional; when no value is specified the encoder will choose the number of slices based on encode resolution.',
        ),
    ]

    tier: Annotated[
        Optional[H265Tier],
        Field(
            None,
            alias='Tier',
            description='H.265 Tier.',
        ),
    ]

    timecode_insertion: Annotated[
        Optional[H265TimecodeInsertionBehavior],
        Field(
            None,
            alias='TimecodeInsertion',
            description='Determines how timecodes should be inserted into the video elementary stream. - \u0027disabled\u0027: Do not include timecodes - \u0027picTimingSei\u0027: Pass through picture timing SEI messages from the source specified in Timecode Config',
        ),
    ]

    timecode_burnin_settings: Annotated[
        Optional[TimecodeBurninSettings],
        Field(
            None,
            alias='TimecodeBurninSettings',
            description='Timecode burn-in settings',
        ),
    ]

    mv_over_picture_boundaries: Annotated[
        Optional[H265MvOverPictureBoundaries],
        Field(
            None,
            alias='MvOverPictureBoundaries',
            description='If you are setting up the picture as a tile, you must set this to "disabled". In all other configurations, you typically enter "enabled".',
        ),
    ]

    mv_temporal_predictor: Annotated[
        Optional[H265MvTemporalPredictor],
        Field(
            None,
            alias='MvTemporalPredictor',
            description='If you are setting up the picture as a tile, you must set this to "disabled". In other configurations, you typically enter "enabled".',
        ),
    ]

    tile_height: Annotated[
        Optional[int],
        Field(
            None,
            alias='TileHeight',
            description='Set this field to set up the picture as a tile. You must also set tileWidth. The tile height must result in 22 or fewer rows in the frame. The tile width must result in 20 or fewer columns in the frame. And finally, the product of the column count and row count must be 64 of less. If the tile width and height are specified, MediaLive will override the video codec slices field with a value that MediaLive calculates',
        ),
    ]

    tile_padding: Annotated[
        Optional[H265TilePadding],
        Field(
            None,
            alias='TilePadding',
            description='Set to "padded" to force MediaLive to add padding to the frame, to obtain a frame that is a whole multiple of the tile size. If you are setting up the picture as a tile, you must enter "padded". In all other configurations, you typically enter "none".',
        ),
    ]

    tile_width: Annotated[
        Optional[int],
        Field(
            None,
            alias='TileWidth',
            description='Set this field to set up the picture as a tile. See tileHeight for more information.',
        ),
    ]

    treeblock_size: Annotated[
        Optional[H265TreeblockSize],
        Field(
            None,
            alias='TreeblockSize',
            description='Select the tree block size used for encoding. If you enter "auto", the encoder will pick the best size. If you are setting up the picture as a tile, you must set this to 32x32. In all other configurations, you typically enter "auto".',
        ),
    ]

    min_qp: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinQp',
            description='Sets the minimum QP. If you aren\u0027t familiar with quantization adjustment, leave the field empty. MediaLive will apply an appropriate value.',
        ),
    ]

    deblocking: Annotated[
        Optional[H265Deblocking],
        Field(
            None,
            alias='Deblocking',
            description='Enable or disable the deblocking filter for this codec. The filter reduces blocking artifacts at block boundaries, which improves overall video quality. If the filter is disabled, visible block edges might appear in the output, especially at lower bitrates.',
        ),
    ]

    gop_b_reference: Annotated[
        Optional[H265GopBReference],
        Field(
            None,
            alias='GopBReference',
            description='Allows the encoder to use a B-Frame as a reference frame as well. ENABLED: B-frames will also serve as reference frames. DISABLED: B-frames won\u0027t be reference frames. Must be DISABLED if resolution is greater than 1080p or when using tiled hevc encoding.',
        ),
    ]

    gop_num_b_frames: Annotated[
        Optional[int],
        Field(
            None,
            alias='GopNumBFrames',
            description='Sets the number of B-frames between reference frames. Set to 2 if resolution is greater than 1080p or when using tiled hevc encoding.',
        ),
    ]

    min_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinBitrate',
            description='Used for QVBR rate control mode only. Optional. Enter a minimum bitrate if you want to keep the output bitrate about a threshold, in order to prevent the downstream system from de-allocating network bandwidth for this output.',
        ),
    ]

    subgop_length: Annotated[
        Optional[H265SubGopLength],
        Field(
            None,
            alias='SubgopLength',
            description='Sets the number of B-frames in each sub-GOP. FIXED: Use the value in Num B-frames. DYNAMIC: Optimizes the number of B-frames in each sub-GOP to improve visual quality. Must be FIXED if resolution is greater than 1080p or when using tiled hevc encoding.',
        ),
    ]


class Mpeg2Settings(BaseModel):
    """Mpeg2 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    adaptive_quantization: Annotated[
        Optional[Mpeg2AdaptiveQuantization],
        Field(
            None,
            alias='AdaptiveQuantization',
            description='Choose Off to disable adaptive quantization. Or choose another value to enable the quantizer and set its strength. The strengths are: Auto, Off, Low, Medium, High. When you enable this field, MediaLive allows intra-frame quantizers to vary, which might improve visual quality.',
        ),
    ]

    afd_signaling: Annotated[
        Optional[AfdSignaling],
        Field(
            None,
            alias='AfdSignaling',
            description='Indicates the AFD values that MediaLive will write into the video encode. If you do not know what AFD signaling is, or if your downstream system has not given you guidance, choose AUTO. AUTO: MediaLive will try to preserve the input AFD value (in cases where multiple AFD values are valid). FIXED: MediaLive will use the value you specify in fixedAFD.',
        ),
    ]

    color_metadata: Annotated[
        Optional[Mpeg2ColorMetadata],
        Field(
            None,
            alias='ColorMetadata',
            description='Specifies whether to include the color space metadata. The metadata describes the color space that applies to the video (the colorSpace field). We recommend that you insert the metadata.',
        ),
    ]

    color_space: Annotated[
        Optional[Mpeg2ColorSpace],
        Field(
            None,
            alias='ColorSpace',
            description='Choose the type of color space conversion to apply to the output. For detailed information on setting up both the input and the output to obtain the desired color space in the output, see the section on \\"MediaLive Features - Video - color space\\" in the MediaLive User Guide. PASSTHROUGH: Keep the color space of the input content - do not convert it. AUTO:Convert all content that is SD to rec 601, and convert all content that is HD to rec 709.',
        ),
    ]

    display_aspect_ratio: Annotated[
        Optional[Mpeg2DisplayRatio],
        Field(
            None,
            alias='DisplayAspectRatio',
            description='Sets the pixel aspect ratio for the encode.',
        ),
    ]

    filter_settings: Annotated[
        Optional[Mpeg2FilterSettings],
        Field(
            None,
            alias='FilterSettings',
            description='Optionally specify a noise reduction filter, which can improve quality of compressed content. If you do not choose a filter, no filter will be applied. TEMPORAL: This filter is useful for both source content that is noisy (when it has excessive digital artifacts) and source content that is clean. When the content is noisy, the filter cleans up the source content before the encoding phase, with these two effects: First, it improves the output video quality because the content has been cleaned up. Secondly, it decreases the bandwidth because MediaLive does not waste bits on encoding noise. When the content is reasonably clean, the filter tends to decrease the bitrate.',
        ),
    ]

    fixed_afd: Annotated[
        Optional[FixedAfd],
        Field(
            None,
            alias='FixedAfd',
            description='Complete this field only when afdSignaling is set to FIXED. Enter the AFD value (4 bits) to write on all frames of the video encode.',
        ),
    ]

    framerate_denominator: Annotated[
        int,
        Field(
            ...,
            alias='FramerateDenominator',
            description='description": "The framerate denominator. For example, 1001. The framerate is the numerator divided by the denominator. For example, 24000 / 1001 = 23.976 FPS.',
        ),
    ]

    framerate_numerator: Annotated[
        int,
        Field(
            ...,
            alias='FramerateNumerator',
            description='The framerate numerator. For example, 24000. The framerate is the numerator divided by the denominator. For example, 24000 / 1001 = 23.976 FPS.',
        ),
    ]

    gop_closed_cadence: Annotated[
        Optional[int],
        Field(
            None,
            alias='GopClosedCadence',
            description='MPEG2: default is open GOP.',
        ),
    ]

    gop_num_b_frames: Annotated[
        Optional[int],
        Field(
            None,
            alias='GopNumBFrames',
            description='Relates to the GOP structure. The number of B-frames between reference frames. If you do not know what a B-frame is, use the default.',
        ),
    ]

    gop_size: Annotated[
        Optional[float],
        Field(
            None,
            alias='GopSize',
            description='Relates to the GOP structure. The GOP size (keyframe interval) in the units specified in gopSizeUnits. If you do not know what GOP is, use the default. If gopSizeUnits is frames, then the gopSize must be an integer and must be greater than or equal to 1. If gopSizeUnits is seconds, the gopSize must be greater than 0, but does not need to be an integer.',
        ),
    ]

    gop_size_units: Annotated[
        Optional[Mpeg2GopSizeUnits],
        Field(
            None,
            alias='GopSizeUnits',
            description='Relates to the GOP structure. Specifies whether the gopSize is specified in frames or seconds. If you do not plan to change the default gopSize, leave the default. If you specify SECONDS, MediaLive will internally convert the gop size to a frame count.',
        ),
    ]

    scan_type: Annotated[
        Optional[Mpeg2ScanType],
        Field(
            None,
            alias='ScanType',
            description='Set the scan type of the output to PROGRESSIVE or INTERLACED (top field first).',
        ),
    ]

    subgop_length: Annotated[
        Optional[Mpeg2SubGopLength],
        Field(
            None,
            alias='SubgopLength',
            description='Relates to the GOP structure. If you do not know what GOP is, use the default. FIXED: Set the number of B-frames in each sub-GOP to the value in gopNumBFrames. DYNAMIC: Let MediaLive optimize the number of B-frames in each sub-GOP, to improve visual quality.',
        ),
    ]

    timecode_insertion: Annotated[
        Optional[Mpeg2TimecodeInsertionBehavior],
        Field(
            None,
            alias='TimecodeInsertion',
            description='Determines how MediaLive inserts timecodes in the output video. For detailed information about setting up the input and the output for a timecode, see the section on \\"MediaLive Features - Timecode configuration\\" in the MediaLive User Guide. DISABLED: do not include timecodes. GOP_TIMECODE: Include timecode metadata in the GOP header.',
        ),
    ]

    timecode_burnin_settings: Annotated[
        Optional[TimecodeBurninSettings],
        Field(
            None,
            alias='TimecodeBurninSettings',
            description='Timecode burn-in settings',
        ),
    ]


class TimecodeConfig(BaseModel):
    """Timecode Config."""

    model_config = ConfigDict(populate_by_name=True)

    source: Annotated[
        TimecodeConfigSource,
        Field(
            ...,
            alias='Source',
            description='Identifies the source for the timecode that will be associated with the events outputs. -Embedded (embedded): Initialize the output timecode with timecode from the the source. If no embedded timecode is detected in the source, the system falls back to using "Start at 0" (zerobased). -System Clock (systemclock): Use the UTC time. -Start at 0 (zerobased): The time of the first frame of the event will be 00:00:00:00.',
        ),
    ]

    sync_threshold: Annotated[
        Optional[int],
        Field(
            None,
            alias='SyncThreshold',
            description='Threshold in frames beyond which output timecode is resynchronized to the input timecode. Discrepancies below this threshold are permitted to avoid unnecessary discontinuities in the output timecode. No timecode sync when this is not specified.',
        ),
    ]


class VideoCodecSettings(BaseModel):
    """Video Codec Settings."""

    model_config = ConfigDict(populate_by_name=True)

    frame_capture_settings: Annotated[
        Optional[FrameCaptureSettings],
        Field(
            None,
            alias='FrameCaptureSettings',
            description='',
        ),
    ]

    h264_settings: Annotated[
        Optional[H264Settings],
        Field(
            None,
            alias='H264Settings',
            description='',
        ),
    ]

    h265_settings: Annotated[
        Optional[H265Settings],
        Field(
            None,
            alias='H265Settings',
            description='',
        ),
    ]

    mpeg2_settings: Annotated[
        Optional[Mpeg2Settings],
        Field(
            None,
            alias='Mpeg2Settings',
            description='',
        ),
    ]

    av1_settings: Annotated[
        Optional[Av1Settings],
        Field(
            None,
            alias='Av1Settings',
            description='',
        ),
    ]


class VideoDescription(BaseModel):
    """Video settings for this stream."""

    model_config = ConfigDict(populate_by_name=True)

    codec_settings: Annotated[
        Optional[VideoCodecSettings],
        Field(
            None,
            alias='CodecSettings',
            description='Video codec settings.',
        ),
    ]

    height: Annotated[
        Optional[int],
        Field(
            None,
            alias='Height',
            description='Output video height, in pixels. Must be an even number. For most codecs, you can leave this field and width blank in order to use the height and width (resolution) from the source. Note, however, that leaving blank is not recommended. For the Frame Capture codec, height and width are required.',
        ),
    ]

    name: Annotated[
        str,
        Field(
            ...,
            alias='Name',
            description='The name of this VideoDescription. Outputs will use this name to uniquely identify this Description. Description names should be unique within this Live Event.',
        ),
    ]

    respond_to_afd: Annotated[
        Optional[VideoDescriptionRespondToAfd],
        Field(
            None,
            alias='RespondToAfd',
            description='Indicates how MediaLive will respond to the AFD values that might be in the input video. If you do not know what AFD signaling is, or if your downstream system has not given you guidance, choose PASSTHROUGH. RESPOND: MediaLive clips the input video using a formula that uses the AFD values (configured in afdSignaling ), the input display aspect ratio, and the output display aspect ratio. MediaLive also includes the AFD values in the output, unless the codec for this encode is FRAME_CAPTURE. PASSTHROUGH: MediaLive ignores the AFD values and does not clip the video. But MediaLive does include the values in the output. NONE: MediaLive does not clip the input video and does not include the AFD values in the output',
        ),
    ]

    scaling_behavior: Annotated[
        Optional[VideoDescriptionScalingBehavior],
        Field(
            None,
            alias='ScalingBehavior',
            description='STRETCH_TO_OUTPUT configures the output position to stretch the video to the specified output resolution (height and width). This option will override any position value. DEFAULT may insert black boxes (pillar boxes or letter boxes) around the video to provide the specified output resolution.',
        ),
    ]

    sharpness: Annotated[
        Optional[int],
        Field(
            None,
            alias='Sharpness',
            description='Changes the strength of the anti-alias filter used for scaling. 0 is the softest setting, 100 is the sharpest. A setting of 50 is recommended for most content.',
        ),
    ]

    width: Annotated[
        Optional[int],
        Field(
            None,
            alias='Width',
            description='Output video width, in pixels. Must be an even number. For most codecs, you can leave this field and height blank in order to use the height and width (resolution) from the source. Note, however, that leaving blank is not recommended. For the Frame Capture codec, height and width are required.',
        ),
    ]


class VideoSelectorColorSpaceSettings(BaseModel):
    """Video Selector Color Space Settings."""

    model_config = ConfigDict(populate_by_name=True)

    hdr10_settings: Annotated[
        Optional[Hdr10Settings],
        Field(
            None,
            alias='Hdr10Settings',
            description='',
        ),
    ]


class VideoSelectorPid(BaseModel):
    """Video Selector Pid."""

    model_config = ConfigDict(populate_by_name=True)

    pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='Pid',
            description='Selects a specific PID from within a video source.',
        ),
    ]


class VideoSelectorProgramId(BaseModel):
    """Video Selector Program Id."""

    model_config = ConfigDict(populate_by_name=True)

    program_id: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramId',
            description='Selects a specific program from within a multi-program transport stream. If the program doesn\u0027t exist, the first program within the transport stream will be selected by default.',
        ),
    ]


class VideoSelectorSettings(BaseModel):
    """Video Selector Settings."""

    model_config = ConfigDict(populate_by_name=True)

    video_selector_pid: Annotated[
        Optional[VideoSelectorPid],
        Field(
            None,
            alias='VideoSelectorPid',
            description='',
        ),
    ]

    video_selector_program_id: Annotated[
        Optional[VideoSelectorProgramId],
        Field(
            None,
            alias='VideoSelectorProgramId',
            description='',
        ),
    ]


class VideoSelector(BaseModel):
    """Specifies a particular video stream within an input source. An input may have only a single video selector."""

    model_config = ConfigDict(populate_by_name=True)

    color_space: Annotated[
        Optional[VideoSelectorColorSpace],
        Field(
            None,
            alias='ColorSpace',
            description='Controls how MediaLive will use the color space metadata from the source. Typically, choose FOLLOW, which means to use the color space metadata without changing it. Or choose another value (a standard). In this case, the handling is controlled by the colorspaceUsage property.',
        ),
    ]

    color_space_settings: Annotated[
        Optional[VideoSelectorColorSpaceSettings],
        Field(
            None,
            alias='ColorSpaceSettings',
            description='Choose HDR10 only if the following situation applies. Firstly, you specified HDR10 in ColorSpace. Secondly, the attached input is for AWS Elemental Link. Thirdly, you plan to convert the content to another color space. You need to specify the color space metadata that is missing from the source sent from AWS Elemental Link.',
        ),
    ]

    color_space_usage: Annotated[
        Optional[VideoSelectorColorSpaceUsage],
        Field(
            None,
            alias='ColorSpaceUsage',
            description='Applies only if colorSpace is a value other than follow. This field controls how the value in the colorSpace field will be used. fallback means that when the input does include color space data, that data will be used, but when the input has no color space data, the value in colorSpace will be used. Choose fallback if your input is sometimes missing color space data, but when it does have color space data, that data is correct. force means to always use the value in colorSpace. Choose force if your input usually has no color space data or might have unreliable color space data.',
        ),
    ]

    selector_settings: Annotated[
        Optional[VideoSelectorSettings],
        Field(
            None,
            alias='SelectorSettings',
            description='The video selector settings.',
        ),
    ]
