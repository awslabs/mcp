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

"""Auto-generated enum types from botocore service model.

DO NOT EDIT — this file is auto-generated from the botocore service model.
Generated from: MediaLive 2017-10-14
Botocore version: 1.40.49
"""

from enum import Enum


class AacCodingMode(str, Enum):
    """Aac Coding Mode."""

    AD_RECEIVER_MIX = 'AD_RECEIVER_MIX'
    CODING_MODE_1_0 = 'CODING_MODE_1_0'
    CODING_MODE_1_1 = 'CODING_MODE_1_1'
    CODING_MODE_2_0 = 'CODING_MODE_2_0'
    CODING_MODE_5_1 = 'CODING_MODE_5_1'


class AacInputType(str, Enum):
    """Aac Input Type."""

    BROADCASTER_MIXED_AD = 'BROADCASTER_MIXED_AD'
    NORMAL = 'NORMAL'


class AacProfile(str, Enum):
    """Aac Profile."""

    HEV1 = 'HEV1'
    HEV2 = 'HEV2'
    LC = 'LC'


class AacRateControlMode(str, Enum):
    """Aac Rate Control Mode."""

    CBR = 'CBR'
    VBR = 'VBR'


class AacRawFormat(str, Enum):
    """Aac Raw Format."""

    LATM_LOAS = 'LATM_LOAS'
    NONE = 'NONE'


class AacSpec(str, Enum):
    """Aac Spec."""

    MPEG2 = 'MPEG2'
    MPEG4 = 'MPEG4'


class AacVbrQuality(str, Enum):
    """Aac Vbr Quality."""

    HIGH = 'HIGH'
    LOW = 'LOW'
    MEDIUM_HIGH = 'MEDIUM_HIGH'
    MEDIUM_LOW = 'MEDIUM_LOW'


class Ac3AttenuationControl(str, Enum):
    """Ac3 Attenuation Control."""

    ATTENUATE_3_DB = 'ATTENUATE_3_DB'
    NONE = 'NONE'


class Ac3BitstreamMode(str, Enum):
    """Ac3 Bitstream Mode."""

    COMMENTARY = 'COMMENTARY'
    COMPLETE_MAIN = 'COMPLETE_MAIN'
    DIALOGUE = 'DIALOGUE'
    EMERGENCY = 'EMERGENCY'
    HEARING_IMPAIRED = 'HEARING_IMPAIRED'
    MUSIC_AND_EFFECTS = 'MUSIC_AND_EFFECTS'
    VISUALLY_IMPAIRED = 'VISUALLY_IMPAIRED'
    VOICE_OVER = 'VOICE_OVER'


class Ac3CodingMode(str, Enum):
    """Ac3 Coding Mode."""

    CODING_MODE_1_0 = 'CODING_MODE_1_0'
    CODING_MODE_1_1 = 'CODING_MODE_1_1'
    CODING_MODE_2_0 = 'CODING_MODE_2_0'
    CODING_MODE_3_2_LFE = 'CODING_MODE_3_2_LFE'


class Ac3DrcProfile(str, Enum):
    """Ac3 Drc Profile."""

    FILM_STANDARD = 'FILM_STANDARD'
    NONE = 'NONE'


class Ac3LfeFilter(str, Enum):
    """Ac3 Lfe Filter."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class Ac3MetadataControl(str, Enum):
    """Ac3 Metadata Control."""

    FOLLOW_INPUT = 'FOLLOW_INPUT'
    USE_CONFIGURED = 'USE_CONFIGURED'


class AccessibilityType(str, Enum):
    """Accessibility Type."""

    DOES_NOT_IMPLEMENT_ACCESSIBILITY_FEATURES = 'DOES_NOT_IMPLEMENT_ACCESSIBILITY_FEATURES'
    IMPLEMENTS_ACCESSIBILITY_FEATURES = 'IMPLEMENTS_ACCESSIBILITY_FEATURES'


class AfdSignaling(str, Enum):
    """Afd Signaling."""

    AUTO = 'AUTO'
    FIXED = 'FIXED'
    NONE = 'NONE'


class ArchiveS3LogUploads(str, Enum):
    """Archive S3 Log Uploads."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class AudioDescriptionAudioTypeControl(str, Enum):
    """Audio Description Audio Type Control."""

    FOLLOW_INPUT = 'FOLLOW_INPUT'
    USE_CONFIGURED = 'USE_CONFIGURED'


class AudioDescriptionLanguageCodeControl(str, Enum):
    """Audio Description Language Code Control."""

    FOLLOW_INPUT = 'FOLLOW_INPUT'
    USE_CONFIGURED = 'USE_CONFIGURED'


class AudioLanguageSelectionPolicy(str, Enum):
    """Audio Language Selection Policy."""

    LOOSE = 'LOOSE'
    STRICT = 'STRICT'


class AudioNormalizationAlgorithm(str, Enum):
    """Audio Normalization Algorithm."""

    ITU_1770_1 = 'ITU_1770_1'
    ITU_1770_2 = 'ITU_1770_2'


class AudioNormalizationAlgorithmControl(str, Enum):
    """Audio Normalization Algorithm Control."""

    CORRECT_AUDIO = 'CORRECT_AUDIO'


class AudioOnlyHlsSegmentType(str, Enum):
    """Audio Only Hls Segment Type."""

    AAC = 'AAC'
    FMP4 = 'FMP4'


class AudioOnlyHlsTrackType(str, Enum):
    """Audio Only Hls Track Type."""

    ALTERNATE_AUDIO_AUTO_SELECT = 'ALTERNATE_AUDIO_AUTO_SELECT'
    ALTERNATE_AUDIO_AUTO_SELECT_DEFAULT = 'ALTERNATE_AUDIO_AUTO_SELECT_DEFAULT'
    ALTERNATE_AUDIO_NOT_AUTO_SELECT = 'ALTERNATE_AUDIO_NOT_AUTO_SELECT'
    AUDIO_ONLY_VARIANT_STREAM = 'AUDIO_ONLY_VARIANT_STREAM'


class AudioType(str, Enum):
    """Audio Type."""

    CLEAN_EFFECTS = 'CLEAN_EFFECTS'
    HEARING_IMPAIRED = 'HEARING_IMPAIRED'
    UNDEFINED = 'UNDEFINED'
    VISUAL_IMPAIRED_COMMENTARY = 'VISUAL_IMPAIRED_COMMENTARY'


class AuthenticationScheme(str, Enum):
    """Authentication Scheme."""

    AKAMAI = 'AKAMAI'
    COMMON = 'COMMON'


class AvailBlankingState(str, Enum):
    """Avail Blanking State."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class BlackoutSlateNetworkEndBlackout(str, Enum):
    """Blackout Slate Network End Blackout."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class BlackoutSlateState(str, Enum):
    """Blackout Slate State."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class BurnInAlignment(str, Enum):
    """Burn In Alignment."""

    CENTERED = 'CENTERED'
    LEFT = 'LEFT'
    SMART = 'SMART'


class BurnInBackgroundColor(str, Enum):
    """Burn In Background Color."""

    BLACK = 'BLACK'
    NONE = 'NONE'
    WHITE = 'WHITE'


class BurnInFontColor(str, Enum):
    """Burn In Font Color."""

    BLACK = 'BLACK'
    BLUE = 'BLUE'
    GREEN = 'GREEN'
    RED = 'RED'
    WHITE = 'WHITE'
    YELLOW = 'YELLOW'


class BurnInOutlineColor(str, Enum):
    """Burn In Outline Color."""

    BLACK = 'BLACK'
    BLUE = 'BLUE'
    GREEN = 'GREEN'
    RED = 'RED'
    WHITE = 'WHITE'
    YELLOW = 'YELLOW'


class BurnInShadowColor(str, Enum):
    """Burn In Shadow Color."""

    BLACK = 'BLACK'
    NONE = 'NONE'
    WHITE = 'WHITE'


class BurnInTeletextGridControl(str, Enum):
    """Burn In Teletext Grid Control."""

    FIXED = 'FIXED'
    SCALED = 'SCALED'


class CdiInputResolution(str, Enum):
    """Maximum CDI input resolution; SD is 480i and 576i up to 30 frames-per-second (fps), HD is 720p up to 60 fps / 1080i up to 30 fps, FHD is 1080p up to 60 fps, UHD is 2160p up to 60 fps."""

    SD = 'SD'
    HD = 'HD'
    FHD = 'FHD'
    UHD = 'UHD'


class ChannelClass(str, Enum):
    """A standard channel has two encoding pipelines and a single pipeline channel only has one."""

    STANDARD = 'STANDARD'
    SINGLE_PIPELINE = 'SINGLE_PIPELINE'


class ChannelState(str, Enum):
    """Placeholder documentation for ChannelState."""

    CREATING = 'CREATING'
    CREATE_FAILED = 'CREATE_FAILED'
    IDLE = 'IDLE'
    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    RECOVERING = 'RECOVERING'
    STOPPING = 'STOPPING'
    DELETING = 'DELETING'
    DELETED = 'DELETED'
    UPDATING = 'UPDATING'
    UPDATE_FAILED = 'UPDATE_FAILED'


class ColorSpace(str, Enum):
    """Property of colorCorrections. When you are using 3D LUT files to perform color conversion on video, these are the supported color spaces."""

    HDR10 = 'HDR10'
    HLG_2020 = 'HLG_2020'
    REC_601 = 'REC_601'
    REC_709 = 'REC_709'


class DeviceSettingsSyncState(str, Enum):
    """The status of the action to synchronize the device configuration. If you change the configuration of the input device (for example, the maximum bitrate), MediaLive sends the new data to the device. The device might not update itself immediately. SYNCED means the device has updated its configuration. SYNCING means that it has not updated its configuration."""

    SYNCED = 'SYNCED'
    SYNCING = 'SYNCING'


class DeviceUpdateStatus(str, Enum):
    """The status of software on the input device."""

    UP_TO_DATE = 'UP_TO_DATE'
    NOT_UP_TO_DATE = 'NOT_UP_TO_DATE'
    UPDATING = 'UPDATING'


class DolbyEProgramSelection(str, Enum):
    """Dolby EProgram Selection."""

    ALL_CHANNELS = 'ALL_CHANNELS'
    PROGRAM_1 = 'PROGRAM_1'
    PROGRAM_2 = 'PROGRAM_2'
    PROGRAM_3 = 'PROGRAM_3'
    PROGRAM_4 = 'PROGRAM_4'
    PROGRAM_5 = 'PROGRAM_5'
    PROGRAM_6 = 'PROGRAM_6'
    PROGRAM_7 = 'PROGRAM_7'
    PROGRAM_8 = 'PROGRAM_8'


class DvbSdtOutputSdt(str, Enum):
    """Dvb Sdt Output Sdt."""

    SDT_FOLLOW = 'SDT_FOLLOW'
    SDT_FOLLOW_IF_PRESENT = 'SDT_FOLLOW_IF_PRESENT'
    SDT_MANUAL = 'SDT_MANUAL'
    SDT_NONE = 'SDT_NONE'


class DvbSubDestinationAlignment(str, Enum):
    """Dvb Sub Destination Alignment."""

    CENTERED = 'CENTERED'
    LEFT = 'LEFT'
    SMART = 'SMART'


class DvbSubDestinationBackgroundColor(str, Enum):
    """Dvb Sub Destination Background Color."""

    BLACK = 'BLACK'
    NONE = 'NONE'
    WHITE = 'WHITE'


class DvbSubDestinationFontColor(str, Enum):
    """Dvb Sub Destination Font Color."""

    BLACK = 'BLACK'
    BLUE = 'BLUE'
    GREEN = 'GREEN'
    RED = 'RED'
    WHITE = 'WHITE'
    YELLOW = 'YELLOW'


class DvbSubDestinationOutlineColor(str, Enum):
    """Dvb Sub Destination Outline Color."""

    BLACK = 'BLACK'
    BLUE = 'BLUE'
    GREEN = 'GREEN'
    RED = 'RED'
    WHITE = 'WHITE'
    YELLOW = 'YELLOW'


class DvbSubDestinationShadowColor(str, Enum):
    """Dvb Sub Destination Shadow Color."""

    BLACK = 'BLACK'
    NONE = 'NONE'
    WHITE = 'WHITE'


class DvbSubDestinationTeletextGridControl(str, Enum):
    """Dvb Sub Destination Teletext Grid Control."""

    FIXED = 'FIXED'
    SCALED = 'SCALED'


class DvbSubOcrLanguage(str, Enum):
    """Dvb Sub Ocr Language."""

    DEU = 'DEU'
    ENG = 'ENG'
    FRA = 'FRA'
    NLD = 'NLD'
    POR = 'POR'
    SPA = 'SPA'


class Eac3AtmosCodingMode(str, Enum):
    """Eac3 Atmos Coding Mode."""

    CODING_MODE_5_1_4 = 'CODING_MODE_5_1_4'
    CODING_MODE_7_1_4 = 'CODING_MODE_7_1_4'
    CODING_MODE_9_1_6 = 'CODING_MODE_9_1_6'


class Eac3AtmosDrcLine(str, Enum):
    """Eac3 Atmos Drc Line."""

    FILM_LIGHT = 'FILM_LIGHT'
    FILM_STANDARD = 'FILM_STANDARD'
    MUSIC_LIGHT = 'MUSIC_LIGHT'
    MUSIC_STANDARD = 'MUSIC_STANDARD'
    NONE = 'NONE'
    SPEECH = 'SPEECH'


class Eac3AtmosDrcRf(str, Enum):
    """Eac3 Atmos Drc Rf."""

    FILM_LIGHT = 'FILM_LIGHT'
    FILM_STANDARD = 'FILM_STANDARD'
    MUSIC_LIGHT = 'MUSIC_LIGHT'
    MUSIC_STANDARD = 'MUSIC_STANDARD'
    NONE = 'NONE'
    SPEECH = 'SPEECH'


class Eac3AttenuationControl(str, Enum):
    """Eac3 Attenuation Control."""

    ATTENUATE_3_DB = 'ATTENUATE_3_DB'
    NONE = 'NONE'


class Eac3BitstreamMode(str, Enum):
    """Eac3 Bitstream Mode."""

    COMMENTARY = 'COMMENTARY'
    COMPLETE_MAIN = 'COMPLETE_MAIN'
    EMERGENCY = 'EMERGENCY'
    HEARING_IMPAIRED = 'HEARING_IMPAIRED'
    VISUALLY_IMPAIRED = 'VISUALLY_IMPAIRED'


class Eac3CodingMode(str, Enum):
    """Eac3 Coding Mode."""

    CODING_MODE_1_0 = 'CODING_MODE_1_0'
    CODING_MODE_2_0 = 'CODING_MODE_2_0'
    CODING_MODE_3_2 = 'CODING_MODE_3_2'


class Eac3DcFilter(str, Enum):
    """Eac3 Dc Filter."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class Eac3DrcLine(str, Enum):
    """Eac3 Drc Line."""

    FILM_LIGHT = 'FILM_LIGHT'
    FILM_STANDARD = 'FILM_STANDARD'
    MUSIC_LIGHT = 'MUSIC_LIGHT'
    MUSIC_STANDARD = 'MUSIC_STANDARD'
    NONE = 'NONE'
    SPEECH = 'SPEECH'


class Eac3DrcRf(str, Enum):
    """Eac3 Drc Rf."""

    FILM_LIGHT = 'FILM_LIGHT'
    FILM_STANDARD = 'FILM_STANDARD'
    MUSIC_LIGHT = 'MUSIC_LIGHT'
    MUSIC_STANDARD = 'MUSIC_STANDARD'
    NONE = 'NONE'
    SPEECH = 'SPEECH'


class Eac3LfeControl(str, Enum):
    """Eac3 Lfe Control."""

    LFE = 'LFE'
    NO_LFE = 'NO_LFE'


class Eac3LfeFilter(str, Enum):
    """Eac3 Lfe Filter."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class Eac3MetadataControl(str, Enum):
    """Eac3 Metadata Control."""

    FOLLOW_INPUT = 'FOLLOW_INPUT'
    USE_CONFIGURED = 'USE_CONFIGURED'


class Eac3PassthroughControl(str, Enum):
    """Eac3 Passthrough Control."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    WHEN_POSSIBLE = 'WHEN_POSSIBLE'


class Eac3PhaseControl(str, Enum):
    """Eac3 Phase Control."""

    NO_SHIFT = 'NO_SHIFT'
    SHIFT_90_DEGREES = 'SHIFT_90_DEGREES'


class Eac3StereoDownmix(str, Enum):
    """Eac3 Stereo Downmix."""

    DPL2 = 'DPL2'
    LO_RO = 'LO_RO'
    LT_RT = 'LT_RT'
    NOT_INDICATED = 'NOT_INDICATED'


class Eac3SurroundExMode(str, Enum):
    """Eac3 Surround Ex Mode."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'
    NOT_INDICATED = 'NOT_INDICATED'


class Eac3SurroundMode(str, Enum):
    """Eac3 Surround Mode."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'
    NOT_INDICATED = 'NOT_INDICATED'


class EbuTtDDestinationStyleControl(str, Enum):
    """Ebu Tt DDestination Style Control."""

    EXCLUDE = 'EXCLUDE'
    INCLUDE = 'INCLUDE'


class EbuTtDFillLineGapControl(str, Enum):
    """Ebu Tt DFill Line Gap Control."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class EmbeddedConvert608To708(str, Enum):
    """Embedded Convert608 To708."""

    DISABLED = 'DISABLED'
    UPCONVERT = 'UPCONVERT'


class EmbeddedScte20Detection(str, Enum):
    """Embedded Scte20 Detection."""

    AUTO = 'AUTO'
    OFF = 'OFF'


class FeatureActivationsInputPrepareScheduleActions(str, Enum):
    """Feature Activations Input Prepare Schedule Actions."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class FeatureActivationsOutputStaticImageOverlayScheduleActions(str, Enum):
    """Feature Activations Output Static Image Overlay Schedule Actions."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class FecOutputIncludeFec(str, Enum):
    """Fec Output Include Fec."""

    COLUMN = 'COLUMN'
    COLUMN_AND_ROW = 'COLUMN_AND_ROW'


class FixedAfd(str, Enum):
    """Fixed Afd."""

    AFD_0000 = 'AFD_0000'
    AFD_0010 = 'AFD_0010'
    AFD_0011 = 'AFD_0011'
    AFD_0100 = 'AFD_0100'
    AFD_1000 = 'AFD_1000'
    AFD_1001 = 'AFD_1001'
    AFD_1010 = 'AFD_1010'
    AFD_1011 = 'AFD_1011'
    AFD_1101 = 'AFD_1101'
    AFD_1110 = 'AFD_1110'
    AFD_1111 = 'AFD_1111'


class Fmp4NielsenId3Behavior(str, Enum):
    """Fmp4 Nielsen Id3 Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class Fmp4TimedMetadataBehavior(str, Enum):
    """Fmp4 Timed Metadata Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class FollowPoint(str, Enum):
    """Follow reference point."""

    END = 'END'
    START = 'START'


class FrameCaptureIntervalUnit(str, Enum):
    """Frame Capture Interval Unit."""

    MILLISECONDS = 'MILLISECONDS'
    SECONDS = 'SECONDS'


class FrameCaptureS3LogUploads(str, Enum):
    """Frame Capture S3 Log Uploads."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class GlobalConfigurationInputEndAction(str, Enum):
    """Global Configuration Input End Action."""

    NONE = 'NONE'
    SWITCH_AND_LOOP_INPUTS = 'SWITCH_AND_LOOP_INPUTS'


class GlobalConfigurationLowFramerateInputs(str, Enum):
    """Global Configuration Low Framerate Inputs."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class GlobalConfigurationOutputLockingMode(str, Enum):
    """Global Configuration Output Locking Mode."""

    EPOCH_LOCKING = 'EPOCH_LOCKING'
    PIPELINE_LOCKING = 'PIPELINE_LOCKING'
    DISABLED = 'DISABLED'


class GlobalConfigurationOutputTimingSource(str, Enum):
    """Global Configuration Output Timing Source."""

    INPUT_CLOCK = 'INPUT_CLOCK'
    SYSTEM_CLOCK = 'SYSTEM_CLOCK'


class H264AdaptiveQuantization(str, Enum):
    """H264 Adaptive Quantization."""

    AUTO = 'AUTO'
    HIGH = 'HIGH'
    HIGHER = 'HIGHER'
    LOW = 'LOW'
    MAX = 'MAX'
    MEDIUM = 'MEDIUM'
    OFF = 'OFF'


class H264ColorMetadata(str, Enum):
    """H264 Color Metadata."""

    IGNORE = 'IGNORE'
    INSERT = 'INSERT'


class H264EntropyEncoding(str, Enum):
    """H264 Entropy Encoding."""

    CABAC = 'CABAC'
    CAVLC = 'CAVLC'


class H264FlickerAq(str, Enum):
    """H264 Flicker Aq."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H264ForceFieldPictures(str, Enum):
    """H264 Force Field Pictures."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H264FramerateControl(str, Enum):
    """H264 Framerate Control."""

    INITIALIZE_FROM_SOURCE = 'INITIALIZE_FROM_SOURCE'
    SPECIFIED = 'SPECIFIED'


class H264GopBReference(str, Enum):
    """H264 Gop BReference."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H264GopSizeUnits(str, Enum):
    """H264 Gop Size Units."""

    FRAMES = 'FRAMES'
    SECONDS = 'SECONDS'


class H264Level(str, Enum):
    """H264 Level."""

    H264_LEVEL_1 = 'H264_LEVEL_1'
    H264_LEVEL_1_1 = 'H264_LEVEL_1_1'
    H264_LEVEL_1_2 = 'H264_LEVEL_1_2'
    H264_LEVEL_1_3 = 'H264_LEVEL_1_3'
    H264_LEVEL_2 = 'H264_LEVEL_2'
    H264_LEVEL_2_1 = 'H264_LEVEL_2_1'
    H264_LEVEL_2_2 = 'H264_LEVEL_2_2'
    H264_LEVEL_3 = 'H264_LEVEL_3'
    H264_LEVEL_3_1 = 'H264_LEVEL_3_1'
    H264_LEVEL_3_2 = 'H264_LEVEL_3_2'
    H264_LEVEL_4 = 'H264_LEVEL_4'
    H264_LEVEL_4_1 = 'H264_LEVEL_4_1'
    H264_LEVEL_4_2 = 'H264_LEVEL_4_2'
    H264_LEVEL_5 = 'H264_LEVEL_5'
    H264_LEVEL_5_1 = 'H264_LEVEL_5_1'
    H264_LEVEL_5_2 = 'H264_LEVEL_5_2'
    H264_LEVEL_AUTO = 'H264_LEVEL_AUTO'


class H264LookAheadRateControl(str, Enum):
    """H264 Look Ahead Rate Control."""

    HIGH = 'HIGH'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'


class H264ParControl(str, Enum):
    """H264 Par Control."""

    INITIALIZE_FROM_SOURCE = 'INITIALIZE_FROM_SOURCE'
    SPECIFIED = 'SPECIFIED'


class H264Profile(str, Enum):
    """H264 Profile."""

    BASELINE = 'BASELINE'
    HIGH = 'HIGH'
    HIGH_10BIT = 'HIGH_10BIT'
    HIGH_422 = 'HIGH_422'
    HIGH_422_10BIT = 'HIGH_422_10BIT'
    MAIN = 'MAIN'


class H264QualityLevel(str, Enum):
    """H264 Quality Level."""

    ENHANCED_QUALITY = 'ENHANCED_QUALITY'
    STANDARD_QUALITY = 'STANDARD_QUALITY'


class H264RateControlMode(str, Enum):
    """H264 Rate Control Mode."""

    CBR = 'CBR'
    MULTIPLEX = 'MULTIPLEX'
    QVBR = 'QVBR'
    VBR = 'VBR'


class H264ScanType(str, Enum):
    """H264 Scan Type."""

    INTERLACED = 'INTERLACED'
    PROGRESSIVE = 'PROGRESSIVE'


class H264SceneChangeDetect(str, Enum):
    """H264 Scene Change Detect."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H264SpatialAq(str, Enum):
    """H264 Spatial Aq."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H264SubGopLength(str, Enum):
    """H264 Sub Gop Length."""

    DYNAMIC = 'DYNAMIC'
    FIXED = 'FIXED'


class H264Syntax(str, Enum):
    """H264 Syntax."""

    DEFAULT = 'DEFAULT'
    RP2027 = 'RP2027'


class H264TemporalAq(str, Enum):
    """H264 Temporal Aq."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H264TimecodeInsertionBehavior(str, Enum):
    """H264 Timecode Insertion Behavior."""

    DISABLED = 'DISABLED'
    PIC_TIMING_SEI = 'PIC_TIMING_SEI'


class H265AdaptiveQuantization(str, Enum):
    """H265 Adaptive Quantization."""

    AUTO = 'AUTO'
    HIGH = 'HIGH'
    HIGHER = 'HIGHER'
    LOW = 'LOW'
    MAX = 'MAX'
    MEDIUM = 'MEDIUM'
    OFF = 'OFF'


class H265AlternativeTransferFunction(str, Enum):
    """H265 Alternative Transfer Function."""

    INSERT = 'INSERT'
    OMIT = 'OMIT'


class H265ColorMetadata(str, Enum):
    """H265 Color Metadata."""

    IGNORE = 'IGNORE'
    INSERT = 'INSERT'


class H265FlickerAq(str, Enum):
    """H265 Flicker Aq."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H265GopSizeUnits(str, Enum):
    """H265 Gop Size Units."""

    FRAMES = 'FRAMES'
    SECONDS = 'SECONDS'


class H265Level(str, Enum):
    """H265 Level."""

    H265_LEVEL_1 = 'H265_LEVEL_1'
    H265_LEVEL_2 = 'H265_LEVEL_2'
    H265_LEVEL_2_1 = 'H265_LEVEL_2_1'
    H265_LEVEL_3 = 'H265_LEVEL_3'
    H265_LEVEL_3_1 = 'H265_LEVEL_3_1'
    H265_LEVEL_4 = 'H265_LEVEL_4'
    H265_LEVEL_4_1 = 'H265_LEVEL_4_1'
    H265_LEVEL_5 = 'H265_LEVEL_5'
    H265_LEVEL_5_1 = 'H265_LEVEL_5_1'
    H265_LEVEL_5_2 = 'H265_LEVEL_5_2'
    H265_LEVEL_6 = 'H265_LEVEL_6'
    H265_LEVEL_6_1 = 'H265_LEVEL_6_1'
    H265_LEVEL_6_2 = 'H265_LEVEL_6_2'
    H265_LEVEL_AUTO = 'H265_LEVEL_AUTO'


class H265LookAheadRateControl(str, Enum):
    """H265 Look Ahead Rate Control."""

    HIGH = 'HIGH'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'


class H265Profile(str, Enum):
    """H265 Profile."""

    MAIN = 'MAIN'
    MAIN_10BIT = 'MAIN_10BIT'


class H265RateControlMode(str, Enum):
    """H265 Rate Control Mode."""

    CBR = 'CBR'
    MULTIPLEX = 'MULTIPLEX'
    QVBR = 'QVBR'


class H265ScanType(str, Enum):
    """H265 Scan Type."""

    INTERLACED = 'INTERLACED'
    PROGRESSIVE = 'PROGRESSIVE'


class H265SceneChangeDetect(str, Enum):
    """H265 Scene Change Detect."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H265Tier(str, Enum):
    """H265 Tier."""

    HIGH = 'HIGH'
    MAIN = 'MAIN'


class H265TimecodeInsertionBehavior(str, Enum):
    """H265 Timecode Insertion Behavior."""

    DISABLED = 'DISABLED'
    PIC_TIMING_SEI = 'PIC_TIMING_SEI'


class HlsAdMarkers(str, Enum):
    """Hls Ad Markers."""

    ADOBE = 'ADOBE'
    ELEMENTAL = 'ELEMENTAL'
    ELEMENTAL_SCTE35 = 'ELEMENTAL_SCTE35'


class HlsAkamaiHttpTransferMode(str, Enum):
    """Hls Akamai Http Transfer Mode."""

    CHUNKED = 'CHUNKED'
    NON_CHUNKED = 'NON_CHUNKED'


class HlsCaptionLanguageSetting(str, Enum):
    """Hls Caption Language Setting."""

    INSERT = 'INSERT'
    NONE = 'NONE'
    OMIT = 'OMIT'


class HlsClientCache(str, Enum):
    """Hls Client Cache."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class HlsCodecSpecification(str, Enum):
    """Hls Codec Specification."""

    RFC_4281 = 'RFC_4281'
    RFC_6381 = 'RFC_6381'


class HlsDirectoryStructure(str, Enum):
    """Hls Directory Structure."""

    SINGLE_DIRECTORY = 'SINGLE_DIRECTORY'
    SUBDIRECTORY_PER_STREAM = 'SUBDIRECTORY_PER_STREAM'


class HlsDiscontinuityTags(str, Enum):
    """Hls Discontinuity Tags."""

    INSERT = 'INSERT'
    NEVER_INSERT = 'NEVER_INSERT'


class HlsEncryptionType(str, Enum):
    """Hls Encryption Type."""

    AES128 = 'AES128'
    SAMPLE_AES = 'SAMPLE_AES'


class HlsH265PackagingType(str, Enum):
    """Hls H265 Packaging Type."""

    HEV1 = 'HEV1'
    HVC1 = 'HVC1'


class HlsId3SegmentTaggingState(str, Enum):
    """State of HLS ID3 Segment Tagging."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class HlsIncompleteSegmentBehavior(str, Enum):
    """Hls Incomplete Segment Behavior."""

    AUTO = 'AUTO'
    SUPPRESS = 'SUPPRESS'


class HlsIvInManifest(str, Enum):
    """Hls Iv In Manifest."""

    EXCLUDE = 'EXCLUDE'
    INCLUDE = 'INCLUDE'


class HlsIvSource(str, Enum):
    """Hls Iv Source."""

    EXPLICIT = 'EXPLICIT'
    FOLLOWS_SEGMENT_NUMBER = 'FOLLOWS_SEGMENT_NUMBER'


class HlsManifestCompression(str, Enum):
    """Hls Manifest Compression."""

    GZIP = 'GZIP'
    NONE = 'NONE'


class HlsManifestDurationFormat(str, Enum):
    """Hls Manifest Duration Format."""

    FLOATING_POINT = 'FLOATING_POINT'
    INTEGER = 'INTEGER'


class HlsMediaStoreStorageClass(str, Enum):
    """Hls Media Store Storage Class."""

    TEMPORAL = 'TEMPORAL'


class HlsMode(str, Enum):
    """Hls Mode."""

    LIVE = 'LIVE'
    VOD = 'VOD'


class HlsOutputSelection(str, Enum):
    """Hls Output Selection."""

    MANIFESTS_AND_SEGMENTS = 'MANIFESTS_AND_SEGMENTS'
    SEGMENTS_ONLY = 'SEGMENTS_ONLY'
    VARIANT_MANIFESTS_AND_SEGMENTS = 'VARIANT_MANIFESTS_AND_SEGMENTS'


class HlsProgramDateTime(str, Enum):
    """Hls Program Date Time."""

    EXCLUDE = 'EXCLUDE'
    INCLUDE = 'INCLUDE'


class HlsProgramDateTimeClock(str, Enum):
    """Hls Program Date Time Clock."""

    INITIALIZE_FROM_OUTPUT_TIMECODE = 'INITIALIZE_FROM_OUTPUT_TIMECODE'
    SYSTEM_CLOCK = 'SYSTEM_CLOCK'


class HlsRedundantManifest(str, Enum):
    """Hls Redundant Manifest."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class HlsS3LogUploads(str, Enum):
    """Hls S3 Log Uploads."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class HlsScte35SourceType(str, Enum):
    """Hls Scte35 Source Type."""

    MANIFEST = 'MANIFEST'
    SEGMENTS = 'SEGMENTS'


class HlsSegmentationMode(str, Enum):
    """Hls Segmentation Mode."""

    USE_INPUT_SEGMENTATION = 'USE_INPUT_SEGMENTATION'
    USE_SEGMENT_DURATION = 'USE_SEGMENT_DURATION'


class HlsStreamInfResolution(str, Enum):
    """Hls Stream Inf Resolution."""

    EXCLUDE = 'EXCLUDE'
    INCLUDE = 'INCLUDE'


class HlsTimedMetadataId3Frame(str, Enum):
    """Hls Timed Metadata Id3 Frame."""

    NONE = 'NONE'
    PRIV = 'PRIV'
    TDRL = 'TDRL'


class HlsTsFileMode(str, Enum):
    """Hls Ts File Mode."""

    SEGMENTED_FILES = 'SEGMENTED_FILES'
    SINGLE_FILE = 'SINGLE_FILE'


class HlsWebdavHttpTransferMode(str, Enum):
    """Hls Webdav Http Transfer Mode."""

    CHUNKED = 'CHUNKED'
    NON_CHUNKED = 'NON_CHUNKED'


class IFrameOnlyPlaylistType(str, Enum):
    """When set to "standard", an I-Frame only playlist will be written out for each video output in the output group. This I-Frame only playlist will contain byte range offsets pointing to the I-frame(s) in each segment."""

    DISABLED = 'DISABLED'
    STANDARD = 'STANDARD'


class IncludeFillerNalUnits(str, Enum):
    """Include Filler Nal Units."""

    AUTO = 'AUTO'
    DROP = 'DROP'
    INCLUDE = 'INCLUDE'


class InputClass(str, Enum):
    """A standard input has two sources and a single pipeline input only has one."""

    STANDARD = 'STANDARD'
    SINGLE_PIPELINE = 'SINGLE_PIPELINE'


class InputCodec(str, Enum):
    """codec in increasing order of complexity."""

    MPEG2 = 'MPEG2'
    AVC = 'AVC'
    HEVC = 'HEVC'


class InputDeblockFilter(str, Enum):
    """Input Deblock Filter."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class InputDenoiseFilter(str, Enum):
    """Input Denoise Filter."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class InputDeviceActiveInput(str, Enum):
    """The source at the input device that is currently active."""

    HDMI = 'HDMI'
    SDI = 'SDI'


class InputDeviceCodec(str, Enum):
    """The codec to use on the video that the device produces."""

    HEVC = 'HEVC'
    AVC = 'AVC'


class InputDeviceConfiguredInput(str, Enum):
    """The source to activate (use) from the input device."""

    AUTO = 'AUTO'
    HDMI = 'HDMI'
    SDI = 'SDI'


class InputDeviceConnectionState(str, Enum):
    """The state of the connection between the input device and AWS."""

    DISCONNECTED = 'DISCONNECTED'
    CONNECTED = 'CONNECTED'


class InputDeviceIpScheme(str, Enum):
    """Specifies whether the input device has been configured (outside of MediaLive) to use a dynamic IP address assignment (DHCP) or a static IP address."""

    STATIC = 'STATIC'
    DHCP = 'DHCP'


class InputDeviceOutputType(str, Enum):
    """The output attachment type of the input device."""

    NONE = 'NONE'
    MEDIALIVE_INPUT = 'MEDIALIVE_INPUT'
    MEDIACONNECT_FLOW = 'MEDIACONNECT_FLOW'


class InputDeviceScanType(str, Enum):
    """The scan type of the video source."""

    INTERLACED = 'INTERLACED'
    PROGRESSIVE = 'PROGRESSIVE'


class InputDeviceState(str, Enum):
    """The state of the input device."""

    IDLE = 'IDLE'
    STREAMING = 'STREAMING'


class InputDeviceTransferType(str, Enum):
    """The type of device transfer. INCOMING for an input device that is being transferred to you, OUTGOING for an input device that you are transferring to another AWS account."""

    OUTGOING = 'OUTGOING'
    INCOMING = 'INCOMING'


class InputDeviceType(str, Enum):
    """The type of the input device. For an AWS Elemental Link device that outputs resolutions up to 1080, choose "HD"."""

    HD = 'HD'
    UHD = 'UHD'


class InputFilter(str, Enum):
    """Input Filter."""

    AUTO = 'AUTO'
    DISABLED = 'DISABLED'
    FORCED = 'FORCED'


class InputLossActionForHlsOut(str, Enum):
    """Input Loss Action For Hls Out."""

    EMIT_OUTPUT = 'EMIT_OUTPUT'
    PAUSE_OUTPUT = 'PAUSE_OUTPUT'


class InputLossActionForMsSmoothOut(str, Enum):
    """Input Loss Action For Ms Smooth Out."""

    EMIT_OUTPUT = 'EMIT_OUTPUT'
    PAUSE_OUTPUT = 'PAUSE_OUTPUT'


class InputLossActionForRtmpOut(str, Enum):
    """Input Loss Action For Rtmp Out."""

    EMIT_OUTPUT = 'EMIT_OUTPUT'
    PAUSE_OUTPUT = 'PAUSE_OUTPUT'


class InputLossActionForUdpOut(str, Enum):
    """Input Loss Action For Udp Out."""

    DROP_PROGRAM = 'DROP_PROGRAM'
    DROP_TS = 'DROP_TS'
    EMIT_PROGRAM = 'EMIT_PROGRAM'


class InputLossImageType(str, Enum):
    """Input Loss Image Type."""

    COLOR = 'COLOR'
    SLATE = 'SLATE'


class InputMaximumBitrate(str, Enum):
    """Maximum input bitrate in megabits per second. Bitrates up to 50 Mbps are supported currently."""

    MAX_10_MBPS = 'MAX_10_MBPS'
    MAX_20_MBPS = 'MAX_20_MBPS'
    MAX_50_MBPS = 'MAX_50_MBPS'


class InputPreference(str, Enum):
    r"""Input preference when deciding which input to make active when a previously failed input has recovered. If \"EQUAL_INPUT_PREFERENCE\", then the active input will stay active as long as it is healthy. If \"PRIMARY_INPUT_PREFERRED\", then always switch back to the primary input when it is healthy."""

    EQUAL_INPUT_PREFERENCE = 'EQUAL_INPUT_PREFERENCE'
    PRIMARY_INPUT_PREFERRED = 'PRIMARY_INPUT_PREFERRED'


class InputResolution(str, Enum):
    """Input resolution based on lines of vertical resolution in the input; SD is less than 720 lines, HD is 720 to 1080 lines, UHD is greater than 1080 lines."""

    SD = 'SD'
    HD = 'HD'
    UHD = 'UHD'


class InputSecurityGroupState(str, Enum):
    """Placeholder documentation for InputSecurityGroupState."""

    IDLE = 'IDLE'
    IN_USE = 'IN_USE'
    UPDATING = 'UPDATING'
    DELETED = 'DELETED'


class InputSourceEndBehavior(str, Enum):
    """Input Source End Behavior."""

    CONTINUE = 'CONTINUE'
    LOOP = 'LOOP'


class InputSourceType(str, Enum):
    """There are two types of input sources, static and dynamic. If an input source is dynamic you can change the source url of the input dynamically using an input switch action. Currently, two input types support a dynamic url at this time, MP4_FILE and TS_FILE. By default all input sources are static."""

    STATIC = 'STATIC'
    DYNAMIC = 'DYNAMIC'


class InputState(str, Enum):
    """Placeholder documentation for InputState."""

    CREATING = 'CREATING'
    DETACHED = 'DETACHED'
    ATTACHED = 'ATTACHED'
    DELETING = 'DELETING'
    DELETED = 'DELETED'


class InputTimecodeSource(str, Enum):
    """Documentation update needed."""

    ZEROBASED = 'ZEROBASED'
    EMBEDDED = 'EMBEDDED'


class InputType(str, Enum):
    """The different types of inputs that AWS Elemental MediaLive supports."""

    UDP_PUSH = 'UDP_PUSH'
    RTP_PUSH = 'RTP_PUSH'
    RTMP_PUSH = 'RTMP_PUSH'
    RTMP_PULL = 'RTMP_PULL'
    URL_PULL = 'URL_PULL'
    MP4_FILE = 'MP4_FILE'
    MEDIACONNECT = 'MEDIACONNECT'
    INPUT_DEVICE = 'INPUT_DEVICE'
    AWS_CDI = 'AWS_CDI'
    TS_FILE = 'TS_FILE'
    SRT_CALLER = 'SRT_CALLER'
    MULTICAST = 'MULTICAST'
    SMPTE_2110_RECEIVER_GROUP = 'SMPTE_2110_RECEIVER_GROUP'
    SDI = 'SDI'


class LastFrameClippingBehavior(str, Enum):
    """If you specify a StopTimecode in an input (in order to clip the file), you can specify if you want the clip to exclude (the default) or include the frame specified by the timecode."""

    EXCLUDE_LAST_FRAME = 'EXCLUDE_LAST_FRAME'
    INCLUDE_LAST_FRAME = 'INCLUDE_LAST_FRAME'


class LogLevel(str, Enum):
    """The log level the user wants for their channel."""

    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'
    DEBUG = 'DEBUG'
    DISABLED = 'DISABLED'


class M2tsAbsentInputAudioBehavior(str, Enum):
    """M2ts Absent Input Audio Behavior."""

    DROP = 'DROP'
    ENCODE_SILENCE = 'ENCODE_SILENCE'


class M2tsArib(str, Enum):
    """M2ts Arib."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class M2tsAribCaptionsPidControl(str, Enum):
    """M2ts Arib Captions Pid Control."""

    AUTO = 'AUTO'
    USE_CONFIGURED = 'USE_CONFIGURED'


class M2tsAudioBufferModel(str, Enum):
    """M2ts Audio Buffer Model."""

    ATSC = 'ATSC'
    DVB = 'DVB'


class M2tsAudioInterval(str, Enum):
    """M2ts Audio Interval."""

    VIDEO_AND_FIXED_INTERVALS = 'VIDEO_AND_FIXED_INTERVALS'
    VIDEO_INTERVAL = 'VIDEO_INTERVAL'


class M2tsAudioStreamType(str, Enum):
    """M2ts Audio Stream Type."""

    ATSC = 'ATSC'
    DVB = 'DVB'


class M2tsBufferModel(str, Enum):
    """M2ts Buffer Model."""

    MULTIPLEX = 'MULTIPLEX'
    NONE = 'NONE'


class M2tsCcDescriptor(str, Enum):
    """M2ts Cc Descriptor."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class M2tsEbifControl(str, Enum):
    """M2ts Ebif Control."""

    NONE = 'NONE'
    PASSTHROUGH = 'PASSTHROUGH'


class M2tsEbpPlacement(str, Enum):
    """M2ts Ebp Placement."""

    VIDEO_AND_AUDIO_PIDS = 'VIDEO_AND_AUDIO_PIDS'
    VIDEO_PID = 'VIDEO_PID'


class M2tsEsRateInPes(str, Enum):
    """M2ts Es Rate In Pes."""

    EXCLUDE = 'EXCLUDE'
    INCLUDE = 'INCLUDE'


class M2tsKlv(str, Enum):
    """M2ts Klv."""

    NONE = 'NONE'
    PASSTHROUGH = 'PASSTHROUGH'


class M2tsNielsenId3Behavior(str, Enum):
    """M2ts Nielsen Id3 Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class M2tsPcrControl(str, Enum):
    """M2ts Pcr Control."""

    CONFIGURED_PCR_PERIOD = 'CONFIGURED_PCR_PERIOD'
    PCR_EVERY_PES_PACKET = 'PCR_EVERY_PES_PACKET'


class M2tsRateMode(str, Enum):
    """M2ts Rate Mode."""

    CBR = 'CBR'
    VBR = 'VBR'


class M2tsScte35Control(str, Enum):
    """M2ts Scte35 Control."""

    NONE = 'NONE'
    PASSTHROUGH = 'PASSTHROUGH'


class M2tsSegmentationMarkers(str, Enum):
    """M2ts Segmentation Markers."""

    EBP = 'EBP'
    EBP_LEGACY = 'EBP_LEGACY'
    NONE = 'NONE'
    PSI_SEGSTART = 'PSI_SEGSTART'
    RAI_ADAPT = 'RAI_ADAPT'
    RAI_SEGSTART = 'RAI_SEGSTART'


class M2tsSegmentationStyle(str, Enum):
    """M2ts Segmentation Style."""

    MAINTAIN_CADENCE = 'MAINTAIN_CADENCE'
    RESET_CADENCE = 'RESET_CADENCE'


class M2tsTimedMetadataBehavior(str, Enum):
    """M2ts Timed Metadata Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class M3u8KlvBehavior(str, Enum):
    """M3u8 Klv Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class M3u8NielsenId3Behavior(str, Enum):
    """M3u8 Nielsen Id3 Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class M3u8PcrControl(str, Enum):
    """M3u8 Pcr Control."""

    CONFIGURED_PCR_PERIOD = 'CONFIGURED_PCR_PERIOD'
    PCR_EVERY_PES_PACKET = 'PCR_EVERY_PES_PACKET'


class M3u8Scte35Behavior(str, Enum):
    """M3u8 Scte35 Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class M3u8TimedMetadataBehavior(str, Enum):
    """M3u8 Timed Metadata Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class MaintenanceDay(str, Enum):
    """The currently selected maintenance day."""

    MONDAY = 'MONDAY'
    TUESDAY = 'TUESDAY'
    WEDNESDAY = 'WEDNESDAY'
    THURSDAY = 'THURSDAY'
    FRIDAY = 'FRIDAY'
    SATURDAY = 'SATURDAY'
    SUNDAY = 'SUNDAY'


class MotionGraphicsInsertion(str, Enum):
    """Motion Graphics Insertion."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class Mp2CodingMode(str, Enum):
    """Mp2 Coding Mode."""

    CODING_MODE_1_0 = 'CODING_MODE_1_0'
    CODING_MODE_2_0 = 'CODING_MODE_2_0'


class Mpeg2AdaptiveQuantization(str, Enum):
    """Mpeg2 Adaptive Quantization."""

    AUTO = 'AUTO'
    HIGH = 'HIGH'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    OFF = 'OFF'


class Mpeg2ColorMetadata(str, Enum):
    """Mpeg2 Color Metadata."""

    IGNORE = 'IGNORE'
    INSERT = 'INSERT'


class Mpeg2ColorSpace(str, Enum):
    """Mpeg2 Color Space."""

    AUTO = 'AUTO'
    PASSTHROUGH = 'PASSTHROUGH'


class Mpeg2DisplayRatio(str, Enum):
    """Mpeg2 Display Ratio."""

    DISPLAYRATIO16X9 = 'DISPLAYRATIO16X9'
    DISPLAYRATIO4X3 = 'DISPLAYRATIO4X3'


class Mpeg2GopSizeUnits(str, Enum):
    """Mpeg2 Gop Size Units."""

    FRAMES = 'FRAMES'
    SECONDS = 'SECONDS'


class Mpeg2ScanType(str, Enum):
    """Mpeg2 Scan Type."""

    INTERLACED = 'INTERLACED'
    PROGRESSIVE = 'PROGRESSIVE'


class Mpeg2SubGopLength(str, Enum):
    """Mpeg2 Sub Gop Length."""

    DYNAMIC = 'DYNAMIC'
    FIXED = 'FIXED'


class Mpeg2TimecodeInsertionBehavior(str, Enum):
    """Mpeg2 Timecode Insertion Behavior."""

    DISABLED = 'DISABLED'
    GOP_TIMECODE = 'GOP_TIMECODE'


class MsSmoothH265PackagingType(str, Enum):
    """Ms Smooth H265 Packaging Type."""

    HEV1 = 'HEV1'
    HVC1 = 'HVC1'


class MultiplexState(str, Enum):
    """The current state of the multiplex."""

    CREATING = 'CREATING'
    CREATE_FAILED = 'CREATE_FAILED'
    IDLE = 'IDLE'
    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    RECOVERING = 'RECOVERING'
    STOPPING = 'STOPPING'
    DELETING = 'DELETING'
    DELETED = 'DELETED'


class NetworkInputServerValidation(str, Enum):
    """Network Input Server Validation."""

    CHECK_CRYPTOGRAPHY_AND_VALIDATE_NAME = 'CHECK_CRYPTOGRAPHY_AND_VALIDATE_NAME'
    CHECK_CRYPTOGRAPHY_ONLY = 'CHECK_CRYPTOGRAPHY_ONLY'


class NielsenPcmToId3TaggingState(str, Enum):
    """State of Nielsen PCM to ID3 tagging."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class NielsenWatermarkTimezones(str, Enum):
    """Nielsen Watermark Timezones."""

    AMERICA_PUERTO_RICO = 'AMERICA_PUERTO_RICO'
    US_ALASKA = 'US_ALASKA'
    US_ARIZONA = 'US_ARIZONA'
    US_CENTRAL = 'US_CENTRAL'
    US_EASTERN = 'US_EASTERN'
    US_HAWAII = 'US_HAWAII'
    US_MOUNTAIN = 'US_MOUNTAIN'
    US_PACIFIC = 'US_PACIFIC'
    US_SAMOA = 'US_SAMOA'
    UTC = 'UTC'


class NielsenWatermarksCbetStepaside(str, Enum):
    """Nielsen Watermarks Cbet Stepaside."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class NielsenWatermarksDistributionTypes(str, Enum):
    """Nielsen Watermarks Distribution Types."""

    FINAL_DISTRIBUTOR = 'FINAL_DISTRIBUTOR'
    PROGRAM_CONTENT = 'PROGRAM_CONTENT'


class OfferingDurationUnits(str, Enum):
    """Units for duration, e.g. 'MONTHS'."""

    MONTHS = 'MONTHS'


class OfferingType(str, Enum):
    """Offering type, e.g. 'NO_UPFRONT'."""

    NO_UPFRONT = 'NO_UPFRONT'


class PipelineId(str, Enum):
    """Pipeline ID."""

    PIPELINE_0 = 'PIPELINE_0'
    PIPELINE_1 = 'PIPELINE_1'


class PreferredChannelPipeline(str, Enum):
    r"""Indicates which pipeline is preferred by the multiplex for program ingest. If set to \"PIPELINE_0\" or \"PIPELINE_1\" and an unhealthy ingest causes the multiplex to switch to the non-preferred pipeline, it will switch back once that ingest is healthy again. If set to \"CURRENTLY_ACTIVE\", it will not switch back to the other pipeline based on it recovering to a healthy state, it will only switch if the active pipeline becomes unhealthy."""

    CURRENTLY_ACTIVE = 'CURRENTLY_ACTIVE'
    PIPELINE_0 = 'PIPELINE_0'
    PIPELINE_1 = 'PIPELINE_1'


class RebootInputDeviceForce(str, Enum):
    """Whether or not to force reboot the input device."""

    NO = 'NO'
    YES = 'YES'


class ReservationAutomaticRenewal(str, Enum):
    """Automatic Renewal Status for Reservation."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'
    UNAVAILABLE = 'UNAVAILABLE'


class ReservationCodec(str, Enum):
    """Codec, 'MPEG2', 'AVC', 'HEVC', 'AUDIO', 'LINK', or 'AV1'."""

    MPEG2 = 'MPEG2'
    AVC = 'AVC'
    HEVC = 'HEVC'
    AUDIO = 'AUDIO'
    LINK = 'LINK'
    AV1 = 'AV1'


class ReservationMaximumBitrate(str, Enum):
    """Maximum bitrate in megabits per second."""

    MAX_10_MBPS = 'MAX_10_MBPS'
    MAX_20_MBPS = 'MAX_20_MBPS'
    MAX_50_MBPS = 'MAX_50_MBPS'


class ReservationMaximumFramerate(str, Enum):
    """Maximum framerate in frames per second (Outputs only)."""

    MAX_30_FPS = 'MAX_30_FPS'
    MAX_60_FPS = 'MAX_60_FPS'


class ReservationResolution(str, Enum):
    """Resolution based on lines of vertical resolution; SD is less than 720 lines, HD is 720 to 1080 lines, FHD is 1080 lines, UHD is greater than 1080 lines."""

    SD = 'SD'
    HD = 'HD'
    FHD = 'FHD'
    UHD = 'UHD'


class ReservationResourceType(str, Enum):
    """Resource type, 'INPUT', 'OUTPUT', 'MULTIPLEX', or 'CHANNEL'."""

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    MULTIPLEX = 'MULTIPLEX'
    CHANNEL = 'CHANNEL'


class ReservationSpecialFeature(str, Enum):
    """Special features, 'ADVANCED_AUDIO' 'AUDIO_NORMALIZATION' 'MGHD' or 'MGUHD'."""

    ADVANCED_AUDIO = 'ADVANCED_AUDIO'
    AUDIO_NORMALIZATION = 'AUDIO_NORMALIZATION'
    MGHD = 'MGHD'
    MGUHD = 'MGUHD'


class ReservationState(str, Enum):
    """Current reservation state."""

    ACTIVE = 'ACTIVE'
    EXPIRED = 'EXPIRED'
    CANCELED = 'CANCELED'
    DELETED = 'DELETED'


class ReservationVideoQuality(str, Enum):
    """Video quality, e.g. 'STANDARD' (Outputs only)."""

    STANDARD = 'STANDARD'
    ENHANCED = 'ENHANCED'
    PREMIUM = 'PREMIUM'


class RtmpAdMarkers(str, Enum):
    """Rtmp Ad Markers."""

    ON_CUE_POINT_SCTE35 = 'ON_CUE_POINT_SCTE35'


class RtmpCacheFullBehavior(str, Enum):
    """Rtmp Cache Full Behavior."""

    DISCONNECT_IMMEDIATELY = 'DISCONNECT_IMMEDIATELY'
    WAIT_FOR_SERVER = 'WAIT_FOR_SERVER'


class RtmpCaptionData(str, Enum):
    """Rtmp Caption Data."""

    ALL = 'ALL'
    FIELD1_608 = 'FIELD1_608'
    FIELD1_AND_FIELD2_608 = 'FIELD1_AND_FIELD2_608'


class RtmpOutputCertificateMode(str, Enum):
    """Rtmp Output Certificate Mode."""

    SELF_SIGNED = 'SELF_SIGNED'
    VERIFY_AUTHENTICITY = 'VERIFY_AUTHENTICITY'


class S3CannedAcl(str, Enum):
    """S3 Canned Acl."""

    AUTHENTICATED_READ = 'AUTHENTICATED_READ'
    BUCKET_OWNER_FULL_CONTROL = 'BUCKET_OWNER_FULL_CONTROL'
    BUCKET_OWNER_READ = 'BUCKET_OWNER_READ'
    PUBLIC_READ = 'PUBLIC_READ'


class Scte20Convert608To708(str, Enum):
    """Scte20 Convert608 To708."""

    DISABLED = 'DISABLED'
    UPCONVERT = 'UPCONVERT'


class Scte27OcrLanguage(str, Enum):
    """Scte27 Ocr Language."""

    DEU = 'DEU'
    ENG = 'ENG'
    FRA = 'FRA'
    NLD = 'NLD'
    POR = 'POR'
    SPA = 'SPA'


class Scte35AposNoRegionalBlackoutBehavior(str, Enum):
    """Scte35 Apos No Regional Blackout Behavior."""

    FOLLOW = 'FOLLOW'
    IGNORE = 'IGNORE'


class Scte35AposWebDeliveryAllowedBehavior(str, Enum):
    """Scte35 Apos Web Delivery Allowed Behavior."""

    FOLLOW = 'FOLLOW'
    IGNORE = 'IGNORE'


class Scte35ArchiveAllowedFlag(str, Enum):
    """Corresponds to the archive_allowed parameter. A value of ARCHIVE_NOT_ALLOWED corresponds to 0 (false) in the SCTE-35 specification. If you include one of the "restriction" flags then you must include all four of them."""

    ARCHIVE_NOT_ALLOWED = 'ARCHIVE_NOT_ALLOWED'
    ARCHIVE_ALLOWED = 'ARCHIVE_ALLOWED'


class Scte35DeviceRestrictions(str, Enum):
    """Corresponds to the device_restrictions parameter in a segmentation_descriptor. If you include one of the "restriction" flags then you must include all four of them."""

    NONE = 'NONE'
    RESTRICT_GROUP0 = 'RESTRICT_GROUP0'
    RESTRICT_GROUP1 = 'RESTRICT_GROUP1'
    RESTRICT_GROUP2 = 'RESTRICT_GROUP2'


class Scte35InputMode(str, Enum):
    """Whether the SCTE-35 input should be the active input or a fixed input."""

    FIXED = 'FIXED'
    FOLLOW_ACTIVE = 'FOLLOW_ACTIVE'


class Scte35NoRegionalBlackoutFlag(str, Enum):
    """Corresponds to the no_regional_blackout_flag parameter. A value of REGIONAL_BLACKOUT corresponds to 0 (false) in the SCTE-35 specification. If you include one of the "restriction" flags then you must include all four of them."""

    REGIONAL_BLACKOUT = 'REGIONAL_BLACKOUT'
    NO_REGIONAL_BLACKOUT = 'NO_REGIONAL_BLACKOUT'


class Scte35SegmentationCancelIndicator(str, Enum):
    """Corresponds to SCTE-35 segmentation_event_cancel_indicator. SEGMENTATION_EVENT_NOT_CANCELED corresponds to 0 in the SCTE-35 specification and indicates that this is an insertion request. SEGMENTATION_EVENT_CANCELED corresponds to 1 in the SCTE-35 specification and indicates that this is a cancelation request, in which case complete this field and the existing event ID to cancel."""

    SEGMENTATION_EVENT_NOT_CANCELED = 'SEGMENTATION_EVENT_NOT_CANCELED'
    SEGMENTATION_EVENT_CANCELED = 'SEGMENTATION_EVENT_CANCELED'


class Scte35SpliceInsertNoRegionalBlackoutBehavior(str, Enum):
    """Scte35 Splice Insert No Regional Blackout Behavior."""

    FOLLOW = 'FOLLOW'
    IGNORE = 'IGNORE'


class Scte35SpliceInsertWebDeliveryAllowedBehavior(str, Enum):
    """Scte35 Splice Insert Web Delivery Allowed Behavior."""

    FOLLOW = 'FOLLOW'
    IGNORE = 'IGNORE'


class Scte35WebDeliveryAllowedFlag(str, Enum):
    """Corresponds to the web_delivery_allowed_flag parameter. A value of WEB_DELIVERY_NOT_ALLOWED corresponds to 0 (false) in the SCTE-35 specification. If you include one of the "restriction" flags then you must include all four of them."""

    WEB_DELIVERY_NOT_ALLOWED = 'WEB_DELIVERY_NOT_ALLOWED'
    WEB_DELIVERY_ALLOWED = 'WEB_DELIVERY_ALLOWED'


class SmoothGroupAudioOnlyTimecodeControl(str, Enum):
    """Smooth Group Audio Only Timecode Control."""

    PASSTHROUGH = 'PASSTHROUGH'
    USE_CONFIGURED_CLOCK = 'USE_CONFIGURED_CLOCK'


class SmoothGroupCertificateMode(str, Enum):
    """Smooth Group Certificate Mode."""

    SELF_SIGNED = 'SELF_SIGNED'
    VERIFY_AUTHENTICITY = 'VERIFY_AUTHENTICITY'


class SmoothGroupEventIdMode(str, Enum):
    """Smooth Group Event Id Mode."""

    NO_EVENT_ID = 'NO_EVENT_ID'
    USE_CONFIGURED = 'USE_CONFIGURED'
    USE_TIMESTAMP = 'USE_TIMESTAMP'


class SmoothGroupEventStopBehavior(str, Enum):
    """Smooth Group Event Stop Behavior."""

    NONE = 'NONE'
    SEND_EOS = 'SEND_EOS'


class SmoothGroupSegmentationMode(str, Enum):
    """Smooth Group Segmentation Mode."""

    USE_INPUT_SEGMENTATION = 'USE_INPUT_SEGMENTATION'
    USE_SEGMENT_DURATION = 'USE_SEGMENT_DURATION'


class SmoothGroupSparseTrackType(str, Enum):
    """Smooth Group Sparse Track Type."""

    NONE = 'NONE'
    SCTE_35 = 'SCTE_35'
    SCTE_35_WITHOUT_SEGMENTATION = 'SCTE_35_WITHOUT_SEGMENTATION'


class SmoothGroupStreamManifestBehavior(str, Enum):
    """Smooth Group Stream Manifest Behavior."""

    DO_NOT_SEND = 'DO_NOT_SEND'
    SEND = 'SEND'


class SmoothGroupTimestampOffsetMode(str, Enum):
    """Smooth Group Timestamp Offset Mode."""

    USE_CONFIGURED_OFFSET = 'USE_CONFIGURED_OFFSET'
    USE_EVENT_START_DATE = 'USE_EVENT_START_DATE'


class Smpte2038DataPreference(str, Enum):
    """Smpte2038 Data Preference."""

    IGNORE = 'IGNORE'
    PREFER = 'PREFER'


class TemporalFilterPostFilterSharpening(str, Enum):
    """Temporal Filter Post Filter Sharpening."""

    AUTO = 'AUTO'
    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class TemporalFilterStrength(str, Enum):
    """Temporal Filter Strength."""

    AUTO = 'AUTO'
    STRENGTH_1 = 'STRENGTH_1'
    STRENGTH_2 = 'STRENGTH_2'
    STRENGTH_3 = 'STRENGTH_3'
    STRENGTH_4 = 'STRENGTH_4'
    STRENGTH_5 = 'STRENGTH_5'
    STRENGTH_6 = 'STRENGTH_6'
    STRENGTH_7 = 'STRENGTH_7'
    STRENGTH_8 = 'STRENGTH_8'
    STRENGTH_9 = 'STRENGTH_9'
    STRENGTH_10 = 'STRENGTH_10'
    STRENGTH_11 = 'STRENGTH_11'
    STRENGTH_12 = 'STRENGTH_12'
    STRENGTH_13 = 'STRENGTH_13'
    STRENGTH_14 = 'STRENGTH_14'
    STRENGTH_15 = 'STRENGTH_15'
    STRENGTH_16 = 'STRENGTH_16'


class ThumbnailState(str, Enum):
    """Thumbnail State."""

    AUTO = 'AUTO'
    DISABLED = 'DISABLED'


class ThumbnailType(str, Enum):
    """Thumbnail type."""

    UNSPECIFIED = 'UNSPECIFIED'
    CURRENT_ACTIVE = 'CURRENT_ACTIVE'


class TimecodeBurninFontSize(str, Enum):
    """Timecode Burnin Font Size."""

    EXTRA_SMALL_10 = 'EXTRA_SMALL_10'
    LARGE_48 = 'LARGE_48'
    MEDIUM_32 = 'MEDIUM_32'
    SMALL_16 = 'SMALL_16'


class TimecodeBurninPosition(str, Enum):
    """Timecode Burnin Position."""

    BOTTOM_CENTER = 'BOTTOM_CENTER'
    BOTTOM_LEFT = 'BOTTOM_LEFT'
    BOTTOM_RIGHT = 'BOTTOM_RIGHT'
    MIDDLE_CENTER = 'MIDDLE_CENTER'
    MIDDLE_LEFT = 'MIDDLE_LEFT'
    MIDDLE_RIGHT = 'MIDDLE_RIGHT'
    TOP_CENTER = 'TOP_CENTER'
    TOP_LEFT = 'TOP_LEFT'
    TOP_RIGHT = 'TOP_RIGHT'


class TimecodeConfigSource(str, Enum):
    """Timecode Config Source."""

    EMBEDDED = 'EMBEDDED'
    SYSTEMCLOCK = 'SYSTEMCLOCK'
    ZEROBASED = 'ZEROBASED'


class TtmlDestinationStyleControl(str, Enum):
    """Ttml Destination Style Control."""

    PASSTHROUGH = 'PASSTHROUGH'
    USE_CONFIGURED = 'USE_CONFIGURED'


class UdpTimedMetadataId3Frame(str, Enum):
    """Udp Timed Metadata Id3 Frame."""

    NONE = 'NONE'
    PRIV = 'PRIV'
    TDRL = 'TDRL'


class VideoDescriptionRespondToAfd(str, Enum):
    """Video Description Respond To Afd."""

    NONE = 'NONE'
    PASSTHROUGH = 'PASSTHROUGH'
    RESPOND = 'RESPOND'


class VideoDescriptionScalingBehavior(str, Enum):
    """Video Description Scaling Behavior."""

    DEFAULT = 'DEFAULT'
    STRETCH_TO_OUTPUT = 'STRETCH_TO_OUTPUT'


class VideoSelectorColorSpace(str, Enum):
    """Video Selector Color Space."""

    FOLLOW = 'FOLLOW'
    HDR10 = 'HDR10'
    HLG_2020 = 'HLG_2020'
    REC_601 = 'REC_601'
    REC_709 = 'REC_709'


class VideoSelectorColorSpaceUsage(str, Enum):
    """Video Selector Color Space Usage."""

    FALLBACK = 'FALLBACK'
    FORCE = 'FORCE'


class WavCodingMode(str, Enum):
    """Wav Coding Mode."""

    CODING_MODE_1_0 = 'CODING_MODE_1_0'
    CODING_MODE_2_0 = 'CODING_MODE_2_0'
    CODING_MODE_4_0 = 'CODING_MODE_4_0'
    CODING_MODE_8_0 = 'CODING_MODE_8_0'


class WebvttDestinationStyleControl(str, Enum):
    """Webvtt Destination Style Control."""

    NO_STYLE_DATA = 'NO_STYLE_DATA'
    PASSTHROUGH = 'PASSTHROUGH'


class AcceptHeader(str, Enum):
    """The HTTP Accept header. Indicates the requested type fothe thumbnail."""

    IMAGE_JPEG = 'image/jpeg'


class ContentType(str, Enum):
    """Specifies the media type of the thumbnail."""

    IMAGE_JPEG = 'image/jpeg'


class InputDeviceConfigurableAudioChannelPairProfile(str, Enum):
    """Property of InputDeviceConfigurableAudioChannelPairConfig, which configures one audio channel that the device produces."""

    DISABLED = 'DISABLED'
    VBR_AAC_HHE_16000 = 'VBR-AAC_HHE-16000'
    VBR_AAC_HE_64000 = 'VBR-AAC_HE-64000'
    VBR_AAC_LC_128000 = 'VBR-AAC_LC-128000'
    CBR_AAC_HQ_192000 = 'CBR-AAC_HQ-192000'
    CBR_AAC_HQ_256000 = 'CBR-AAC_HQ-256000'
    CBR_AAC_HQ_384000 = 'CBR-AAC_HQ-384000'
    CBR_AAC_HQ_512000 = 'CBR-AAC_HQ-512000'


class InputDeviceUhdAudioChannelPairProfile(str, Enum):
    """Property of InputDeviceUhdAudioChannelPairConfig, which describes one audio channel that the device is configured to produce."""

    DISABLED = 'DISABLED'
    VBR_AAC_HHE_16000 = 'VBR-AAC_HHE-16000'
    VBR_AAC_HE_64000 = 'VBR-AAC_HE-64000'
    VBR_AAC_LC_128000 = 'VBR-AAC_LC-128000'
    CBR_AAC_HQ_192000 = 'CBR-AAC_HQ-192000'
    CBR_AAC_HQ_256000 = 'CBR-AAC_HQ-256000'
    CBR_AAC_HQ_384000 = 'CBR-AAC_HQ-384000'
    CBR_AAC_HQ_512000 = 'CBR-AAC_HQ-512000'


class ChannelPipelineIdToRestart(str, Enum):
    """Property of RestartChannelPipelinesRequest."""

    PIPELINE_0 = 'PIPELINE_0'
    PIPELINE_1 = 'PIPELINE_1'


class H265MvOverPictureBoundaries(str, Enum):
    """H265 Mv Over Picture Boundaries."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H265MvTemporalPredictor(str, Enum):
    """H265 Mv Temporal Predictor."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H265TilePadding(str, Enum):
    """H265 Tile Padding."""

    NONE = 'NONE'
    PADDED = 'PADDED'


class H265TreeblockSize(str, Enum):
    """H265 Treeblock Size."""

    AUTO = 'AUTO'
    TREE_SIZE_32X32 = 'TREE_SIZE_32X32'


class CmafIngestSegmentLengthUnits(str, Enum):
    """Cmaf Ingest Segment Length Units."""

    MILLISECONDS = 'MILLISECONDS'
    SECONDS = 'SECONDS'


class CmafNielsenId3Behavior(str, Enum):
    """Cmaf Nielsen Id3 Behavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class DashRoleAudio(str, Enum):
    """Dash Role Audio."""

    ALTERNATE = 'ALTERNATE'
    COMMENTARY = 'COMMENTARY'
    DESCRIPTION = 'DESCRIPTION'
    DUB = 'DUB'
    EMERGENCY = 'EMERGENCY'
    ENHANCED_AUDIO_INTELLIGIBILITY = 'ENHANCED-AUDIO-INTELLIGIBILITY'
    KARAOKE = 'KARAOKE'
    MAIN = 'MAIN'
    SUPPLEMENTARY = 'SUPPLEMENTARY'


class DashRoleCaption(str, Enum):
    """Dash Role Caption."""

    ALTERNATE = 'ALTERNATE'
    CAPTION = 'CAPTION'
    COMMENTARY = 'COMMENTARY'
    DESCRIPTION = 'DESCRIPTION'
    DUB = 'DUB'
    EASYREADER = 'EASYREADER'
    EMERGENCY = 'EMERGENCY'
    FORCED_SUBTITLE = 'FORCED-SUBTITLE'
    KARAOKE = 'KARAOKE'
    MAIN = 'MAIN'
    METADATA = 'METADATA'
    SUBTITLE = 'SUBTITLE'
    SUPPLEMENTARY = 'SUPPLEMENTARY'


class DvbDashAccessibility(str, Enum):
    """Dvb Dash Accessibility."""

    DVBDASH_1_VISUALLY_IMPAIRED = 'DVBDASH_1_VISUALLY_IMPAIRED'
    DVBDASH_2_HARD_OF_HEARING = 'DVBDASH_2_HARD_OF_HEARING'
    DVBDASH_3_SUPPLEMENTAL_COMMENTARY = 'DVBDASH_3_SUPPLEMENTAL_COMMENTARY'
    DVBDASH_4_DIRECTORS_COMMENTARY = 'DVBDASH_4_DIRECTORS_COMMENTARY'
    DVBDASH_5_EDUCATIONAL_NOTES = 'DVBDASH_5_EDUCATIONAL_NOTES'
    DVBDASH_6_MAIN_PROGRAM = 'DVBDASH_6_MAIN_PROGRAM'
    DVBDASH_7_CLEAN_FEED = 'DVBDASH_7_CLEAN_FEED'


class Scte35Type(str, Enum):
    """Scte35 Type."""

    NONE = 'NONE'
    SCTE_35_WITHOUT_SEGMENTATION = 'SCTE_35_WITHOUT_SEGMENTATION'


class CloudWatchAlarmTemplateComparisonOperator(str, Enum):
    """The comparison operator used to compare the specified statistic and the threshold."""

    GREATERTHANOREQUALTOTHRESHOLD = 'GreaterThanOrEqualToThreshold'
    GREATERTHANTHRESHOLD = 'GreaterThanThreshold'
    LESSTHANTHRESHOLD = 'LessThanThreshold'
    LESSTHANOREQUALTOTHRESHOLD = 'LessThanOrEqualToThreshold'


class CloudWatchAlarmTemplateStatistic(str, Enum):
    """The statistic to apply to the alarm's metric data."""

    SAMPLECOUNT = 'SampleCount'
    AVERAGE = 'Average'
    SUM = 'Sum'
    MINIMUM = 'Minimum'
    MAXIMUM = 'Maximum'


class CloudWatchAlarmTemplateTargetResourceType(str, Enum):
    """The resource type this template should dynamically generate cloudwatch metric alarms for."""

    CLOUDFRONT_DISTRIBUTION = 'CLOUDFRONT_DISTRIBUTION'
    MEDIALIVE_MULTIPLEX = 'MEDIALIVE_MULTIPLEX'
    MEDIALIVE_CHANNEL = 'MEDIALIVE_CHANNEL'
    MEDIALIVE_INPUT_DEVICE = 'MEDIALIVE_INPUT_DEVICE'
    MEDIAPACKAGE_CHANNEL = 'MEDIAPACKAGE_CHANNEL'
    MEDIAPACKAGE_ORIGIN_ENDPOINT = 'MEDIAPACKAGE_ORIGIN_ENDPOINT'
    MEDIACONNECT_FLOW = 'MEDIACONNECT_FLOW'
    S3_BUCKET = 'S3_BUCKET'
    MEDIATAILOR_PLAYBACK_CONFIGURATION = 'MEDIATAILOR_PLAYBACK_CONFIGURATION'


class CloudWatchAlarmTemplateTreatMissingData(str, Enum):
    """Specifies how missing data points are treated when evaluating the alarm's condition."""

    NOTBREACHING = 'notBreaching'
    BREACHING = 'breaching'
    IGNORE = 'ignore'
    MISSING = 'missing'


class EventBridgeRuleTemplateEventType(str, Enum):
    """The type of event to match with the rule."""

    MEDIALIVE_MULTIPLEX_ALERT = 'MEDIALIVE_MULTIPLEX_ALERT'
    MEDIALIVE_MULTIPLEX_STATE_CHANGE = 'MEDIALIVE_MULTIPLEX_STATE_CHANGE'
    MEDIALIVE_CHANNEL_ALERT = 'MEDIALIVE_CHANNEL_ALERT'
    MEDIALIVE_CHANNEL_INPUT_CHANGE = 'MEDIALIVE_CHANNEL_INPUT_CHANGE'
    MEDIALIVE_CHANNEL_STATE_CHANGE = 'MEDIALIVE_CHANNEL_STATE_CHANGE'
    MEDIAPACKAGE_INPUT_NOTIFICATION = 'MEDIAPACKAGE_INPUT_NOTIFICATION'
    MEDIAPACKAGE_KEY_PROVIDER_NOTIFICATION = 'MEDIAPACKAGE_KEY_PROVIDER_NOTIFICATION'
    MEDIAPACKAGE_HARVEST_JOB_NOTIFICATION = 'MEDIAPACKAGE_HARVEST_JOB_NOTIFICATION'
    SIGNAL_MAP_ACTIVE_ALARM = 'SIGNAL_MAP_ACTIVE_ALARM'
    MEDIACONNECT_ALERT = 'MEDIACONNECT_ALERT'
    MEDIACONNECT_SOURCE_HEALTH = 'MEDIACONNECT_SOURCE_HEALTH'
    MEDIACONNECT_OUTPUT_HEALTH = 'MEDIACONNECT_OUTPUT_HEALTH'
    MEDIACONNECT_FLOW_STATUS_CHANGE = 'MEDIACONNECT_FLOW_STATUS_CHANGE'


class SignalMapMonitorDeploymentStatus(str, Enum):
    """A signal map's monitor deployment status."""

    NOT_DEPLOYED = 'NOT_DEPLOYED'
    DRY_RUN_DEPLOYMENT_COMPLETE = 'DRY_RUN_DEPLOYMENT_COMPLETE'
    DRY_RUN_DEPLOYMENT_FAILED = 'DRY_RUN_DEPLOYMENT_FAILED'
    DRY_RUN_DEPLOYMENT_IN_PROGRESS = 'DRY_RUN_DEPLOYMENT_IN_PROGRESS'
    DEPLOYMENT_COMPLETE = 'DEPLOYMENT_COMPLETE'
    DEPLOYMENT_FAILED = 'DEPLOYMENT_FAILED'
    DEPLOYMENT_IN_PROGRESS = 'DEPLOYMENT_IN_PROGRESS'
    DELETE_COMPLETE = 'DELETE_COMPLETE'
    DELETE_FAILED = 'DELETE_FAILED'
    DELETE_IN_PROGRESS = 'DELETE_IN_PROGRESS'


class SignalMapStatus(str, Enum):
    """A signal map's current status which is dependent on its lifecycle actions or associated jobs."""

    CREATE_IN_PROGRESS = 'CREATE_IN_PROGRESS'
    CREATE_COMPLETE = 'CREATE_COMPLETE'
    CREATE_FAILED = 'CREATE_FAILED'
    UPDATE_IN_PROGRESS = 'UPDATE_IN_PROGRESS'
    UPDATE_COMPLETE = 'UPDATE_COMPLETE'
    UPDATE_REVERTED = 'UPDATE_REVERTED'
    UPDATE_FAILED = 'UPDATE_FAILED'
    READY = 'READY'
    NOT_READY = 'NOT_READY'


class Scte35SegmentationScope(str, Enum):
    """Scte35 Segmentation Scope."""

    ALL_OUTPUT_GROUPS = 'ALL_OUTPUT_GROUPS'
    SCTE35_ENABLED_OUTPUT_GROUPS = 'SCTE35_ENABLED_OUTPUT_GROUPS'


class Algorithm(str, Enum):
    """Placeholder documentation for Algorithm."""

    AES128 = 'AES128'
    AES192 = 'AES192'
    AES256 = 'AES256'


class Av1GopSizeUnits(str, Enum):
    """Av1 Gop Size Units."""

    FRAMES = 'FRAMES'
    SECONDS = 'SECONDS'


class Av1Level(str, Enum):
    """Av1 Level."""

    AV1_LEVEL_2 = 'AV1_LEVEL_2'
    AV1_LEVEL_2_1 = 'AV1_LEVEL_2_1'
    AV1_LEVEL_3 = 'AV1_LEVEL_3'
    AV1_LEVEL_3_1 = 'AV1_LEVEL_3_1'
    AV1_LEVEL_4 = 'AV1_LEVEL_4'
    AV1_LEVEL_4_1 = 'AV1_LEVEL_4_1'
    AV1_LEVEL_5 = 'AV1_LEVEL_5'
    AV1_LEVEL_5_1 = 'AV1_LEVEL_5_1'
    AV1_LEVEL_5_2 = 'AV1_LEVEL_5_2'
    AV1_LEVEL_5_3 = 'AV1_LEVEL_5_3'
    AV1_LEVEL_6 = 'AV1_LEVEL_6'
    AV1_LEVEL_6_1 = 'AV1_LEVEL_6_1'
    AV1_LEVEL_6_2 = 'AV1_LEVEL_6_2'
    AV1_LEVEL_6_3 = 'AV1_LEVEL_6_3'
    AV1_LEVEL_AUTO = 'AV1_LEVEL_AUTO'


class Av1LookAheadRateControl(str, Enum):
    """Av1 Look Ahead Rate Control."""

    HIGH = 'HIGH'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'


class Av1SceneChangeDetect(str, Enum):
    """Av1 Scene Change Detect."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class ChannelPlacementGroupState(str, Enum):
    """Used in DescribeChannelPlacementGroupResult."""

    UNASSIGNED = 'UNASSIGNED'
    ASSIGNING = 'ASSIGNING'
    ASSIGNED = 'ASSIGNED'
    DELETING = 'DELETING'
    DELETE_FAILED = 'DELETE_FAILED'
    DELETED = 'DELETED'
    UNASSIGNING = 'UNASSIGNING'


class ClusterState(str, Enum):
    """Used in DescribeClusterSummary, DescribeClusterResult, UpdateClusterResult."""

    CREATING = 'CREATING'
    CREATE_FAILED = 'CREATE_FAILED'
    ACTIVE = 'ACTIVE'
    DELETING = 'DELETING'
    DELETE_FAILED = 'DELETE_FAILED'
    DELETED = 'DELETED'


class ClusterType(str, Enum):
    """Used in CreateClusterSummary, DescribeClusterSummary, DescribeClusterResult, UpdateClusterResult."""

    ON_PREMISES = 'ON_PREMISES'


class InputNetworkLocation(str, Enum):
    """With the introduction of MediaLive Anywhere, a MediaLive input can now exist in two different places: AWS or inside an on-premises datacenter. By default all inputs will continue to be AWS inputs."""

    AWS = 'AWS'
    ON_PREMISES = 'ON_PREMISES'


class NetworkInterfaceMode(str, Enum):
    """Used in NodeInterfaceMapping and NodeInterfaceMappingCreateRequest."""

    NAT = 'NAT'
    BRIDGE = 'BRIDGE'


class NetworkState(str, Enum):
    """Used in DescribeNetworkResult, DescribeNetworkSummary, UpdateNetworkResult."""

    CREATING = 'CREATING'
    CREATE_FAILED = 'CREATE_FAILED'
    ACTIVE = 'ACTIVE'
    DELETING = 'DELETING'
    IDLE = 'IDLE'
    IN_USE = 'IN_USE'
    UPDATING = 'UPDATING'
    DELETE_FAILED = 'DELETE_FAILED'
    DELETED = 'DELETED'


class NodeConnectionState(str, Enum):
    """Used in DescribeNodeSummary."""

    CONNECTED = 'CONNECTED'
    DISCONNECTED = 'DISCONNECTED'


class NodeRole(str, Enum):
    """Used in CreateNodeRequest, CreateNodeRegistrationScriptRequest, DescribeNodeResult, DescribeNodeSummary, UpdateNodeRequest."""

    BACKUP = 'BACKUP'
    ACTIVE = 'ACTIVE'


class NodeState(str, Enum):
    """Used in DescribeNodeSummary."""

    CREATED = 'CREATED'
    REGISTERING = 'REGISTERING'
    READY_TO_ACTIVATE = 'READY_TO_ACTIVATE'
    REGISTRATION_FAILED = 'REGISTRATION_FAILED'
    ACTIVATION_FAILED = 'ACTIVATION_FAILED'
    ACTIVE = 'ACTIVE'
    READY = 'READY'
    IN_USE = 'IN_USE'
    DEREGISTERING = 'DEREGISTERING'
    DRAINING = 'DRAINING'
    DEREGISTRATION_FAILED = 'DEREGISTRATION_FAILED'
    DEREGISTERED = 'DEREGISTERED'


class SrtEncryptionType(str, Enum):
    """Srt Encryption Type."""

    AES128 = 'AES128'
    AES192 = 'AES192'
    AES256 = 'AES256'


class UpdateNodeState(str, Enum):
    """Used in UpdateNodeStateRequest."""

    ACTIVE = 'ACTIVE'
    DRAINING = 'DRAINING'


class BandwidthReductionFilterStrength(str, Enum):
    """Bandwidth Reduction Filter Strength."""

    AUTO = 'AUTO'
    STRENGTH_1 = 'STRENGTH_1'
    STRENGTH_2 = 'STRENGTH_2'
    STRENGTH_3 = 'STRENGTH_3'
    STRENGTH_4 = 'STRENGTH_4'


class BandwidthReductionPostFilterSharpening(str, Enum):
    """Bandwidth Reduction Post Filter Sharpening."""

    DISABLED = 'DISABLED'
    SHARPENING_1 = 'SHARPENING_1'
    SHARPENING_2 = 'SHARPENING_2'
    SHARPENING_3 = 'SHARPENING_3'


class H265Deblocking(str, Enum):
    """H265 Deblocking."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class CmafKLVBehavior(str, Enum):
    """Cmaf KLVBehavior."""

    NO_PASSTHROUGH = 'NO_PASSTHROUGH'
    PASSTHROUGH = 'PASSTHROUGH'


class CmafId3Behavior(str, Enum):
    """Cmaf Id3 Behavior."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class SdiSourceMode(str, Enum):
    """Used in SdiSource, CreateSdiSourceRequest, UpdateSdiSourceRequest."""

    QUADRANT = 'QUADRANT'
    INTERLEAVE = 'INTERLEAVE'


class SdiSourceState(str, Enum):
    """Used in SdiSource, DescribeNodeRequest, DescribeNodeResult."""

    IDLE = 'IDLE'
    IN_USE = 'IN_USE'
    DELETED = 'DELETED'


class SdiSourceType(str, Enum):
    """Used in SdiSource, CreateSdiSourceRequest, UpdateSdiSourceRequest."""

    SINGLE = 'SINGLE'
    QUAD = 'QUAD'


class CmafTimedMetadataId3Frame(str, Enum):
    """Cmaf Timed Metadata Id3 Frame."""

    NONE = 'NONE'
    PRIV = 'PRIV'
    TDRL = 'TDRL'


class CmafTimedMetadataPassthrough(str, Enum):
    """Cmaf Timed Metadata Passthrough."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class Av1RateControlMode(str, Enum):
    """Av1 Rate Control Mode."""

    CBR = 'CBR'
    QVBR = 'QVBR'


class BurnInDestinationSubtitleRows(str, Enum):
    """Burn In Destination Subtitle Rows."""

    ROWS_16 = 'ROWS_16'
    ROWS_20 = 'ROWS_20'
    ROWS_24 = 'ROWS_24'


class DvbSubDestinationSubtitleRows(str, Enum):
    """Dvb Sub Destination Subtitle Rows."""

    ROWS_16 = 'ROWS_16'
    ROWS_20 = 'ROWS_20'
    ROWS_24 = 'ROWS_24'


class HlsAutoSelect(str, Enum):
    """Hls Auto Select."""

    NO = 'NO'
    OMIT = 'OMIT'
    YES = 'YES'


class HlsDefault(str, Enum):
    """Hls Default."""

    NO = 'NO'
    OMIT = 'OMIT'
    YES = 'YES'


class H265GopBReference(str, Enum):
    """H265 Gop BReference."""

    DISABLED = 'DISABLED'
    ENABLED = 'ENABLED'


class H265SubGopLength(str, Enum):
    """H265 Sub Gop Length."""

    DYNAMIC = 'DYNAMIC'
    FIXED = 'FIXED'
