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

"""Schedule-related Pydantic models — schedule actions, SCTE-35, input switching."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    FollowPoint,
    MotionGraphicsInsertion,
    Scte20Convert608To708,
    Scte27OcrLanguage,
    Scte35AposNoRegionalBlackoutBehavior,
    Scte35AposWebDeliveryAllowedBehavior,
    Scte35ArchiveAllowedFlag,
    Scte35DeviceRestrictions,
    Scte35InputMode,
    Scte35NoRegionalBlackoutFlag,
    Scte35SegmentationCancelIndicator,
    Scte35SpliceInsertNoRegionalBlackoutBehavior,
    Scte35SpliceInsertWebDeliveryAllowedBehavior,
    Scte35WebDeliveryAllowedFlag,
)
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.channel import PipelinePauseStateSettings
    from awslabs.amazon_medialive_mcp_server.models.common import (
        HtmlMotionGraphicsSettings,
        TimedMetadataScheduleActionSettings,
    )
    from awslabs.amazon_medialive_mcp_server.models.input import (
        HlsId3SegmentTaggingScheduleActionSettings,
        HlsTimedMetadataScheduleActionSettings,
        InputLocation,
        InputPrepareScheduleActionSettings,
        InputSwitchScheduleActionSettings,
    )


class FixedModeScheduleActionStartSettings(BaseModel):
    """Start time for the action."""

    model_config = ConfigDict(populate_by_name=True)

    time: Annotated[
        str,
        Field(
            ...,
            alias='Time',
            description='Start time for the action to start in the channel. (Not the time for the action to be added to the schedule: actions are always added to the schedule immediately.) UTC format: yyyy-mm-ddThh:mm:ss.nnnZ. All the letters are digits (for example, mm might be 01) except for the two constants "T" for time and "Z" for "UTC format".',
        ),
    ]


class FollowModeScheduleActionStartSettings(BaseModel):
    """Settings to specify if an action follows another."""

    model_config = ConfigDict(populate_by_name=True)

    follow_point: Annotated[
        FollowPoint,
        Field(
            ...,
            alias='FollowPoint',
            description='Identifies whether this action starts relative to the start or relative to the end of the reference action.',
        ),
    ]

    reference_action_name: Annotated[
        str,
        Field(
            ...,
            alias='ReferenceActionName',
            description='The action name of another action that this one refers to.',
        ),
    ]


class Id3SegmentTaggingScheduleActionSettings(BaseModel):
    """Settings for the action to insert ID3 metadata in every segment, in applicable output groups."""

    model_config = ConfigDict(populate_by_name=True)

    id3: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id3',
            description='Complete this parameter if you want to specify the entire ID3 metadata. Enter a base64 string that contains one or more fully formed ID3 tags, according to the ID3 specification: http://id3.org/id3v2.4.0-structure',
        ),
    ]

    tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='Tag',
            description='Complete this parameter if you want to specify only the metadata, not the entire frame. MediaLive will insert the metadata in a TXXX frame. Enter the value as plain text. You can include standard MediaLive variable data such as the current segment number.',
        ),
    ]


class ImmediateModeScheduleActionStartSettings(BaseModel):
    """Settings to configure an action so that it occurs as soon as possible."""

    model_config = ConfigDict(populate_by_name=True)


class MotionGraphicsActivateScheduleActionSettings(BaseModel):
    """Settings to specify the rendering of motion graphics into the video stream."""

    model_config = ConfigDict(populate_by_name=True)

    duration: Annotated[
        Optional[int],
        Field(
            None,
            alias='Duration',
            description='Duration (in milliseconds) that motion graphics should render on to the video stream. Leaving out this property or setting to 0 will result in rendering continuing until a deactivate action is processed.',
        ),
    ]

    password_param: Annotated[
        Optional[str],
        Field(
            None,
            alias='PasswordParam',
            description='Key used to extract the password from EC2 Parameter store',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='URI of the HTML5 content to be rendered into the live stream.',
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


class MotionGraphicsDeactivateScheduleActionSettings(BaseModel):
    """Settings to specify the ending of rendering motion graphics into the video stream."""

    model_config = ConfigDict(populate_by_name=True)


class MotionGraphicsSettings(BaseModel):
    """Motion Graphics Settings."""

    model_config = ConfigDict(populate_by_name=True)

    html_motion_graphics_settings: Annotated[
        Optional[HtmlMotionGraphicsSettings],
        Field(
            None,
            alias='HtmlMotionGraphicsSettings',
            description='',
        ),
    ]


class MotionGraphicsConfiguration(BaseModel):
    """Motion Graphics Configuration."""

    model_config = ConfigDict(populate_by_name=True)

    motion_graphics_insertion: Annotated[
        Optional[MotionGraphicsInsertion],
        Field(
            None,
            alias='MotionGraphicsInsertion',
            description='',
        ),
    ]

    motion_graphics_settings: Annotated[
        MotionGraphicsSettings,
        Field(
            ...,
            alias='MotionGraphicsSettings',
            description='Motion Graphics Settings',
        ),
    ]


class PauseStateScheduleActionSettings(BaseModel):
    """Settings for the action to set pause state of a channel."""

    model_config = ConfigDict(populate_by_name=True)

    pipelines: Annotated[
        Optional[list[PipelinePauseStateSettings]],
        Field(
            None,
            alias='Pipelines',
            description='',
        ),
    ]


class ScheduleActionStartSettings(BaseModel):
    """Settings to specify when an action should occur. Only one of the options must be selected."""

    model_config = ConfigDict(populate_by_name=True)

    fixed_mode_schedule_action_start_settings: Annotated[
        Optional[FixedModeScheduleActionStartSettings],
        Field(
            None,
            alias='FixedModeScheduleActionStartSettings',
            description='Option for specifying the start time for an action.',
        ),
    ]

    follow_mode_schedule_action_start_settings: Annotated[
        Optional[FollowModeScheduleActionStartSettings],
        Field(
            None,
            alias='FollowModeScheduleActionStartSettings',
            description='Option for specifying an action as relative to another action.',
        ),
    ]

    immediate_mode_schedule_action_start_settings: Annotated[
        Optional[ImmediateModeScheduleActionStartSettings],
        Field(
            None,
            alias='ImmediateModeScheduleActionStartSettings',
            description='Option for specifying an action that should be applied immediately.',
        ),
    ]


class ScheduleDeleteResultModel(BaseModel):
    """Result of a schedule deletion."""

    model_config = ConfigDict(populate_by_name=True)


class Scte20PlusEmbeddedDestinationSettings(BaseModel):
    """Scte20 Plus Embedded Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)


class Scte20SourceSettings(BaseModel):
    """Scte20 Source Settings."""

    model_config = ConfigDict(populate_by_name=True)

    convert608_to708: Annotated[
        Optional[Scte20Convert608To708],
        Field(
            None,
            alias='Convert608To708',
            description='If upconvert, 608 data is both passed through via the "608 compatibility bytes" fields of the 708 wrapper as well as translated into 708. 708 data present in the source content will be discarded.',
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


class Scte27DestinationSettings(BaseModel):
    """Scte27 Destination Settings."""

    model_config = ConfigDict(populate_by_name=True)


class Scte27SourceSettings(BaseModel):
    """Scte27 Source Settings."""

    model_config = ConfigDict(populate_by_name=True)

    ocr_language: Annotated[
        Optional[Scte27OcrLanguage],
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
            description='The pid field is used in conjunction with the caption selector languageCode field as follows: - Specify PID and Language: Extracts captions from that PID; the language is "informational". - Specify PID and omit Language: Extracts the specified PID. - Omit PID and specify Language: Extracts the specified language, whichever PID that happens to be. - Omit PID and omit Language: Valid only if source is DVB-Sub that is being passed through; all languages will be passed through.',
        ),
    ]


class Scte35DeliveryRestrictions(BaseModel):
    """Corresponds to SCTE-35 delivery_not_restricted_flag parameter. To declare delivery restrictions, include this element and its four "restriction" flags. To declare that there are no restrictions, omit this element."""

    model_config = ConfigDict(populate_by_name=True)

    archive_allowed_flag: Annotated[
        Scte35ArchiveAllowedFlag,
        Field(
            ...,
            alias='ArchiveAllowedFlag',
            description='Corresponds to SCTE-35 archive_allowed_flag.',
        ),
    ]

    device_restrictions: Annotated[
        Scte35DeviceRestrictions,
        Field(
            ...,
            alias='DeviceRestrictions',
            description='Corresponds to SCTE-35 device_restrictions parameter.',
        ),
    ]

    no_regional_blackout_flag: Annotated[
        Scte35NoRegionalBlackoutFlag,
        Field(
            ...,
            alias='NoRegionalBlackoutFlag',
            description='Corresponds to SCTE-35 no_regional_blackout_flag parameter.',
        ),
    ]

    web_delivery_allowed_flag: Annotated[
        Scte35WebDeliveryAllowedFlag,
        Field(
            ...,
            alias='WebDeliveryAllowedFlag',
            description='Corresponds to SCTE-35 web_delivery_allowed_flag parameter.',
        ),
    ]


class Scte35InputScheduleActionSettings(BaseModel):
    """Scte35Input Schedule Action Settings."""

    model_config = ConfigDict(populate_by_name=True)

    input_attachment_name_reference: Annotated[
        Optional[str],
        Field(
            None,
            alias='InputAttachmentNameReference',
            description='In fixed mode, enter the name of the input attachment that you want to use as a SCTE-35 input. (Don\u0027t enter the ID of the input.)"',
        ),
    ]

    mode: Annotated[
        Scte35InputMode,
        Field(
            ...,
            alias='Mode',
            description='Whether the SCTE-35 input should be the active input or a fixed input.',
        ),
    ]


class Scte35ReturnToNetworkScheduleActionSettings(BaseModel):
    """Settings for a SCTE-35 return_to_network message."""

    model_config = ConfigDict(populate_by_name=True)

    splice_event_id: Annotated[
        int,
        Field(
            ...,
            alias='SpliceEventId',
            description='The splice_event_id for the SCTE-35 splice_insert, as defined in SCTE-35.',
        ),
    ]


class Scte35SegmentationDescriptor(BaseModel):
    """Corresponds to SCTE-35 segmentation_descriptor."""

    model_config = ConfigDict(populate_by_name=True)

    delivery_restrictions: Annotated[
        Optional[Scte35DeliveryRestrictions],
        Field(
            None,
            alias='DeliveryRestrictions',
            description='Holds the four SCTE-35 delivery restriction parameters.',
        ),
    ]

    segment_num: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentNum',
            description='Corresponds to SCTE-35 segment_num. A value that is valid for the specified segmentation_type_id.',
        ),
    ]

    segmentation_cancel_indicator: Annotated[
        Scte35SegmentationCancelIndicator,
        Field(
            ...,
            alias='SegmentationCancelIndicator',
            description='Corresponds to SCTE-35 segmentation_event_cancel_indicator.',
        ),
    ]

    segmentation_duration: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentationDuration',
            description='Corresponds to SCTE-35 segmentation_duration. Optional. The duration for the time_signal, in 90 KHz ticks. To convert seconds to ticks, multiple the seconds by 90,000. Enter time in 90 KHz clock ticks. If you do not enter a duration, the time_signal will continue until you insert a cancellation message.',
        ),
    ]

    segmentation_event_id: Annotated[
        int,
        Field(
            ...,
            alias='SegmentationEventId',
            description='Corresponds to SCTE-35 segmentation_event_id.',
        ),
    ]

    segmentation_type_id: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentationTypeId',
            description='Corresponds to SCTE-35 segmentation_type_id. One of the segmentation_type_id values listed in the SCTE-35 specification. On the console, enter the ID in decimal (for example, "52"). In the CLI, API, or an SDK, enter the ID in hex (for example, "0x34") or decimal (for example, "52").',
        ),
    ]

    segmentation_upid: Annotated[
        Optional[str],
        Field(
            None,
            alias='SegmentationUpid',
            description='Corresponds to SCTE-35 segmentation_upid. Enter a string containing the hexadecimal representation of the characters that make up the SCTE-35 segmentation_upid value. Must contain an even number of hex characters. Do not include spaces between each hex pair. For example, the ASCII "ADS Information" becomes hex "41445320496e666f726d6174696f6e.',
        ),
    ]

    segmentation_upid_type: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentationUpidType',
            description='Corresponds to SCTE-35 segmentation_upid_type. On the console, enter one of the types listed in the SCTE-35 specification, converted to a decimal. For example, "0x0C" hex from the specification is "12" in decimal. In the CLI, API, or an SDK, enter one of the types listed in the SCTE-35 specification, in either hex (for example, "0x0C" ) or in decimal (for example, "12").',
        ),
    ]

    segments_expected: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentsExpected',
            description='Corresponds to SCTE-35 segments_expected. A value that is valid for the specified segmentation_type_id.',
        ),
    ]

    sub_segment_num: Annotated[
        Optional[int],
        Field(
            None,
            alias='SubSegmentNum',
            description='Corresponds to SCTE-35 sub_segment_num. A value that is valid for the specified segmentation_type_id.',
        ),
    ]

    sub_segments_expected: Annotated[
        Optional[int],
        Field(
            None,
            alias='SubSegmentsExpected',
            description='Corresponds to SCTE-35 sub_segments_expected. A value that is valid for the specified segmentation_type_id.',
        ),
    ]


class Scte35DescriptorSettings(BaseModel):
    """SCTE-35 Descriptor settings."""

    model_config = ConfigDict(populate_by_name=True)

    segmentation_descriptor_scte35_descriptor_settings: Annotated[
        Scte35SegmentationDescriptor,
        Field(
            ...,
            alias='SegmentationDescriptorScte35DescriptorSettings',
            description='SCTE-35 Segmentation Descriptor.',
        ),
    ]


class Scte35Descriptor(BaseModel):
    """Holds one set of SCTE-35 Descriptor Settings."""

    model_config = ConfigDict(populate_by_name=True)

    scte35_descriptor_settings: Annotated[
        Scte35DescriptorSettings,
        Field(
            ...,
            alias='Scte35DescriptorSettings',
            description='SCTE-35 Descriptor Settings.',
        ),
    ]


class Scte35SpliceInsert(BaseModel):
    """Typical configuration that applies breaks on splice inserts in addition to time signal placement opportunities, breaks, and advertisements."""

    model_config = ConfigDict(populate_by_name=True)

    ad_avail_offset: Annotated[
        Optional[int],
        Field(
            None,
            alias='AdAvailOffset',
            description='When specified, this offset (in milliseconds) is added to the input Ad Avail PTS time. This only applies to embedded SCTE 104/35 messages and does not apply to OOB messages.',
        ),
    ]

    no_regional_blackout_flag: Annotated[
        Optional[Scte35SpliceInsertNoRegionalBlackoutBehavior],
        Field(
            None,
            alias='NoRegionalBlackoutFlag',
            description='When set to ignore, Segment Descriptors with noRegionalBlackoutFlag set to 0 will no longer trigger blackouts or Ad Avail slates',
        ),
    ]

    web_delivery_allowed_flag: Annotated[
        Optional[Scte35SpliceInsertWebDeliveryAllowedBehavior],
        Field(
            None,
            alias='WebDeliveryAllowedFlag',
            description='When set to ignore, Segment Descriptors with webDeliveryAllowedFlag set to 0 will no longer trigger blackouts or Ad Avail slates',
        ),
    ]


class Scte35SpliceInsertScheduleActionSettings(BaseModel):
    """Settings for a SCTE-35 splice_insert message."""

    model_config = ConfigDict(populate_by_name=True)

    duration: Annotated[
        Optional[int],
        Field(
            None,
            alias='Duration',
            description='Optional, the duration for the splice_insert, in 90 KHz ticks. To convert seconds to ticks, multiple the seconds by 90,000. If you enter a duration, there is an expectation that the downstream system can read the duration and cue in at that time. If you do not enter a duration, the splice_insert will continue indefinitely and there is an expectation that you will enter a return_to_network to end the splice_insert at the appropriate time.',
        ),
    ]

    splice_event_id: Annotated[
        int,
        Field(
            ...,
            alias='SpliceEventId',
            description='The splice_event_id for the SCTE-35 splice_insert, as defined in SCTE-35.',
        ),
    ]


class Scte35TimeSignalApos(BaseModel):
    """Atypical configuration that applies segment breaks only on SCTE-35 time signal placement opportunities and breaks."""

    model_config = ConfigDict(populate_by_name=True)

    ad_avail_offset: Annotated[
        Optional[int],
        Field(
            None,
            alias='AdAvailOffset',
            description='When specified, this offset (in milliseconds) is added to the input Ad Avail PTS time. This only applies to embedded SCTE 104/35 messages and does not apply to OOB messages.',
        ),
    ]

    no_regional_blackout_flag: Annotated[
        Optional[Scte35AposNoRegionalBlackoutBehavior],
        Field(
            None,
            alias='NoRegionalBlackoutFlag',
            description='When set to ignore, Segment Descriptors with noRegionalBlackoutFlag set to 0 will no longer trigger blackouts or Ad Avail slates',
        ),
    ]

    web_delivery_allowed_flag: Annotated[
        Optional[Scte35AposWebDeliveryAllowedBehavior],
        Field(
            None,
            alias='WebDeliveryAllowedFlag',
            description='When set to ignore, Segment Descriptors with webDeliveryAllowedFlag set to 0 will no longer trigger blackouts or Ad Avail slates',
        ),
    ]


class Scte35TimeSignalScheduleActionSettings(BaseModel):
    """Settings for a SCTE-35 time_signal."""

    model_config = ConfigDict(populate_by_name=True)

    scte35_descriptors: Annotated[
        list[Scte35Descriptor],
        Field(
            ...,
            alias='Scte35Descriptors',
            description='The list of SCTE-35 descriptors accompanying the SCTE-35 time_signal.',
        ),
    ]


class StaticImageActivateScheduleActionSettings(BaseModel):
    """Settings for the action to activate a static image."""

    model_config = ConfigDict(populate_by_name=True)

    duration: Annotated[
        Optional[int],
        Field(
            None,
            alias='Duration',
            description='The duration in milliseconds for the image to remain on the video. If omitted or set to 0 the duration is unlimited and the image will remain until it is explicitly deactivated.',
        ),
    ]

    fade_in: Annotated[
        Optional[int],
        Field(
            None,
            alias='FadeIn',
            description='The time in milliseconds for the image to fade in. The fade-in starts at the start time of the overlay. Default is 0 (no fade-in).',
        ),
    ]

    fade_out: Annotated[
        Optional[int],
        Field(
            None,
            alias='FadeOut',
            description='Applies only if a duration is specified. The time in milliseconds for the image to fade out. The fade-out starts when the duration time is hit, so it effectively extends the duration. Default is 0 (no fade-out).',
        ),
    ]

    height: Annotated[
        Optional[int],
        Field(
            None,
            alias='Height',
            description='The height of the image when inserted into the video, in pixels. The overlay will be scaled up or down to the specified height. Leave blank to use the native height of the overlay.',
        ),
    ]

    image: Annotated[
        InputLocation,
        Field(
            ...,
            alias='Image',
            description='The location and filename of the image file to overlay on the video. The file must be a 32-bit BMP, PNG, or TGA file, and must not be larger (in pixels) than the input video.',
        ),
    ]

    image_x: Annotated[
        Optional[int],
        Field(
            None,
            alias='ImageX',
            description='Placement of the left edge of the overlay relative to the left edge of the video frame, in pixels. 0 (the default) is the left edge of the frame. If the placement causes the overlay to extend beyond the right edge of the underlying video, then the overlay is cropped on the right.',
        ),
    ]

    image_y: Annotated[
        Optional[int],
        Field(
            None,
            alias='ImageY',
            description='Placement of the top edge of the overlay relative to the top edge of the video frame, in pixels. 0 (the default) is the top edge of the frame. If the placement causes the overlay to extend beyond the bottom edge of the underlying video, then the overlay is cropped on the bottom.',
        ),
    ]

    layer: Annotated[
        Optional[int],
        Field(
            None,
            alias='Layer',
            description='The number of the layer, 0 to 7. There are 8 layers that can be overlaid on the video, each layer with a different image. The layers are in Z order, which means that overlays with higher values of layer are inserted on top of overlays with lower values of layer. Default is 0.',
        ),
    ]

    opacity: Annotated[
        Optional[int],
        Field(
            None,
            alias='Opacity',
            description='Opacity of image where 0 is transparent and 100 is fully opaque. Default is 100.',
        ),
    ]

    width: Annotated[
        Optional[int],
        Field(
            None,
            alias='Width',
            description='The width of the image when inserted into the video, in pixels. The overlay will be scaled up or down to the specified width. Leave blank to use the native width of the overlay.',
        ),
    ]


class StaticImageDeactivateScheduleActionSettings(BaseModel):
    """Settings for the action to deactivate the image in a specific layer."""

    model_config = ConfigDict(populate_by_name=True)

    fade_out: Annotated[
        Optional[int],
        Field(
            None,
            alias='FadeOut',
            description='The time in milliseconds for the image to fade out. Default is 0 (no fade-out).',
        ),
    ]

    layer: Annotated[
        Optional[int],
        Field(
            None,
            alias='Layer',
            description='The image overlay layer to deactivate, 0 to 7. Default is 0.',
        ),
    ]


class StaticImageOutputActivateScheduleActionSettings(BaseModel):
    """Settings for the action to activate a static image."""

    model_config = ConfigDict(populate_by_name=True)

    duration: Annotated[
        Optional[int],
        Field(
            None,
            alias='Duration',
            description='The duration in milliseconds for the image to remain on the video. If omitted or set to 0 the duration is unlimited and the image will remain until it is explicitly deactivated.',
        ),
    ]

    fade_in: Annotated[
        Optional[int],
        Field(
            None,
            alias='FadeIn',
            description='The time in milliseconds for the image to fade in. The fade-in starts at the start time of the overlay. Default is 0 (no fade-in).',
        ),
    ]

    fade_out: Annotated[
        Optional[int],
        Field(
            None,
            alias='FadeOut',
            description='Applies only if a duration is specified. The time in milliseconds for the image to fade out. The fade-out starts when the duration time is hit, so it effectively extends the duration. Default is 0 (no fade-out).',
        ),
    ]

    height: Annotated[
        Optional[int],
        Field(
            None,
            alias='Height',
            description='The height of the image when inserted into the video, in pixels. The overlay will be scaled up or down to the specified height. Leave blank to use the native height of the overlay.',
        ),
    ]

    image: Annotated[
        InputLocation,
        Field(
            ...,
            alias='Image',
            description='The location and filename of the image file to overlay on the video. The file must be a 32-bit BMP, PNG, or TGA file, and must not be larger (in pixels) than the input video.',
        ),
    ]

    image_x: Annotated[
        Optional[int],
        Field(
            None,
            alias='ImageX',
            description='Placement of the left edge of the overlay relative to the left edge of the video frame, in pixels. 0 (the default) is the left edge of the frame. If the placement causes the overlay to extend beyond the right edge of the underlying video, then the overlay is cropped on the right.',
        ),
    ]

    image_y: Annotated[
        Optional[int],
        Field(
            None,
            alias='ImageY',
            description='Placement of the top edge of the overlay relative to the top edge of the video frame, in pixels. 0 (the default) is the top edge of the frame. If the placement causes the overlay to extend beyond the bottom edge of the underlying video, then the overlay is cropped on the bottom.',
        ),
    ]

    layer: Annotated[
        Optional[int],
        Field(
            None,
            alias='Layer',
            description='The number of the layer, 0 to 7. There are 8 layers that can be overlaid on the video, each layer with a different image. The layers are in Z order, which means that overlays with higher values of layer are inserted on top of overlays with lower values of layer. Default is 0.',
        ),
    ]

    opacity: Annotated[
        Optional[int],
        Field(
            None,
            alias='Opacity',
            description='Opacity of image where 0 is transparent and 100 is fully opaque. Default is 100.',
        ),
    ]

    output_names: Annotated[
        list[str],
        Field(
            ...,
            alias='OutputNames',
            description='The name(s) of the output(s) the activation should apply to.',
        ),
    ]

    width: Annotated[
        Optional[int],
        Field(
            None,
            alias='Width',
            description='The width of the image when inserted into the video, in pixels. The overlay will be scaled up or down to the specified width. Leave blank to use the native width of the overlay.',
        ),
    ]


class StaticImageOutputDeactivateScheduleActionSettings(BaseModel):
    """Settings for the action to deactivate the image in a specific layer."""

    model_config = ConfigDict(populate_by_name=True)

    fade_out: Annotated[
        Optional[int],
        Field(
            None,
            alias='FadeOut',
            description='The time in milliseconds for the image to fade out. Default is 0 (no fade-out).',
        ),
    ]

    layer: Annotated[
        Optional[int],
        Field(
            None,
            alias='Layer',
            description='The image overlay layer to deactivate, 0 to 7. Default is 0.',
        ),
    ]

    output_names: Annotated[
        list[str],
        Field(
            ...,
            alias='OutputNames',
            description='The name(s) of the output(s) the deactivation should apply to.',
        ),
    ]


class ScheduleActionSettings(BaseModel):
    """Holds the settings for a single schedule action."""

    model_config = ConfigDict(populate_by_name=True)

    hls_id3_segment_tagging_settings: Annotated[
        Optional[HlsId3SegmentTaggingScheduleActionSettings],
        Field(
            None,
            alias='HlsId3SegmentTaggingSettings',
            description='Action to insert ID3 metadata in every segment, in HLS output groups',
        ),
    ]

    hls_timed_metadata_settings: Annotated[
        Optional[HlsTimedMetadataScheduleActionSettings],
        Field(
            None,
            alias='HlsTimedMetadataSettings',
            description='Action to insert ID3 metadata once, in HLS output groups',
        ),
    ]

    input_prepare_settings: Annotated[
        Optional[InputPrepareScheduleActionSettings],
        Field(
            None,
            alias='InputPrepareSettings',
            description='Action to prepare an input for a future immediate input switch',
        ),
    ]

    input_switch_settings: Annotated[
        Optional[InputSwitchScheduleActionSettings],
        Field(
            None,
            alias='InputSwitchSettings',
            description='Action to switch the input',
        ),
    ]

    motion_graphics_image_activate_settings: Annotated[
        Optional[MotionGraphicsActivateScheduleActionSettings],
        Field(
            None,
            alias='MotionGraphicsImageActivateSettings',
            description='Action to activate a motion graphics image overlay',
        ),
    ]

    motion_graphics_image_deactivate_settings: Annotated[
        Optional[MotionGraphicsDeactivateScheduleActionSettings],
        Field(
            None,
            alias='MotionGraphicsImageDeactivateSettings',
            description='Action to deactivate a motion graphics image overlay',
        ),
    ]

    pause_state_settings: Annotated[
        Optional[PauseStateScheduleActionSettings],
        Field(
            None,
            alias='PauseStateSettings',
            description='Action to pause or unpause one or both channel pipelines',
        ),
    ]

    scte35_input_settings: Annotated[
        Optional[Scte35InputScheduleActionSettings],
        Field(
            None,
            alias='Scte35InputSettings',
            description='Action to specify scte35 input',
        ),
    ]

    scte35_return_to_network_settings: Annotated[
        Optional[Scte35ReturnToNetworkScheduleActionSettings],
        Field(
            None,
            alias='Scte35ReturnToNetworkSettings',
            description='Action to insert SCTE-35 return_to_network message',
        ),
    ]

    scte35_splice_insert_settings: Annotated[
        Optional[Scte35SpliceInsertScheduleActionSettings],
        Field(
            None,
            alias='Scte35SpliceInsertSettings',
            description='Action to insert SCTE-35 splice_insert message',
        ),
    ]

    scte35_time_signal_settings: Annotated[
        Optional[Scte35TimeSignalScheduleActionSettings],
        Field(
            None,
            alias='Scte35TimeSignalSettings',
            description='Action to insert SCTE-35 time_signal message',
        ),
    ]

    static_image_activate_settings: Annotated[
        Optional[StaticImageActivateScheduleActionSettings],
        Field(
            None,
            alias='StaticImageActivateSettings',
            description='Action to activate a static image overlay',
        ),
    ]

    static_image_deactivate_settings: Annotated[
        Optional[StaticImageDeactivateScheduleActionSettings],
        Field(
            None,
            alias='StaticImageDeactivateSettings',
            description='Action to deactivate a static image overlay',
        ),
    ]

    static_image_output_activate_settings: Annotated[
        Optional[StaticImageOutputActivateScheduleActionSettings],
        Field(
            None,
            alias='StaticImageOutputActivateSettings',
            description='Action to activate a static image overlay in one or more specified outputs',
        ),
    ]

    static_image_output_deactivate_settings: Annotated[
        Optional[StaticImageOutputDeactivateScheduleActionSettings],
        Field(
            None,
            alias='StaticImageOutputDeactivateSettings',
            description='Action to deactivate a static image overlay in one or more specified outputs',
        ),
    ]

    id3_segment_tagging_settings: Annotated[
        Optional[Id3SegmentTaggingScheduleActionSettings],
        Field(
            None,
            alias='Id3SegmentTaggingSettings',
            description='Action to insert ID3 metadata in every segment, in applicable output groups',
        ),
    ]

    timed_metadata_settings: Annotated[
        Optional[TimedMetadataScheduleActionSettings],
        Field(
            None,
            alias='TimedMetadataSettings',
            description='Action to insert ID3 metadata once, in applicable output groups',
        ),
    ]


class ScheduleAction(BaseModel):
    """Contains information on a single schedule action."""

    model_config = ConfigDict(populate_by_name=True)

    action_name: Annotated[
        str,
        Field(
            ...,
            alias='ActionName',
            description='The name of the action, must be unique within the schedule. This name provides the main reference to an action once it is added to the schedule. A name is unique if it is no longer in the schedule. The schedule is automatically cleaned up to remove actions with a start time of more than 1 hour ago (approximately) so at that point a name can be reused.',
        ),
    ]

    schedule_action_settings: Annotated[
        ScheduleActionSettings,
        Field(
            ...,
            alias='ScheduleActionSettings',
            description='Settings for this schedule action.',
        ),
    ]

    schedule_action_start_settings: Annotated[
        ScheduleActionStartSettings,
        Field(
            ...,
            alias='ScheduleActionStartSettings',
            description='The time for the action to start in the channel.',
        ),
    ]


class ScheduleDescribeResultModel(BaseModel):
    """Results of a schedule describe."""

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
        list[ScheduleAction],
        Field(
            ...,
            alias='ScheduleActions',
            description='The list of actions in the schedule.',
        ),
    ]
