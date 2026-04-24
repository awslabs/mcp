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

# Hand-written description overrides for MediaLive MCP tools and fields.
# These replace auto-generated botocore descriptions with enriched guidance
# that adds units, gotcha warnings, and usage context.

# Keyed by "{ModelName}.{field_name}" — replaces auto-generated field descriptions.
FIELD_DESCRIPTION_OVERRIDES: dict[str, str] = {
    'H264Settings.bitrate': (
        'Average bitrate in bits/second (bps). Required when rate_control_mode is VBR or CBR; '
        'ignored for QVBR. Common values: 5_000_000 (5 Mbps) for 1080p, 2_500_000 (2.5 Mbps) '
        'for 720p. In an MS Smooth output group each output must have a unique value when '
        'rounded down to the nearest multiple of 1000.'
    ),
    'H264Settings.max_bitrate': (
        'Maximum bitrate in bits/second (bps). For QVBR, caps the bitrate ceiling. '
        'For VBR, accommodates expected complexity spikes. Typical values: '
        '4_000_000 for primary screens, 1_500_000–3_000_000 for tablets, '
        '1_000_000–1_500_000 for smartphones.'
    ),
    'H264Settings.buf_size': (
        'HRD buffer size in bits (not bytes). A typical value is 2x the target bitrate. '
        'For example, for a 5 Mbps stream use 10_000_000.'
    ),
    'H264Settings.gop_size': (
        'GOP size (keyframe interval). Units depend on gop_size_units: if FRAMES, this must '
        'be an integer >= 1 (e.g., 60 for a 2-second GOP at 30 fps). If SECONDS, this can be '
        'a float > 0 (e.g., 2.0). Shorter GOPs improve seek accuracy but reduce compression.'
    ),
    'H264Settings.qvbr_quality_level': (
        'Target quality level for QVBR mode (1–10). Only applies when rate_control_mode is QVBR. '
        'Recommended: 8–10 for primary screens, 7 for tablets, 6 for smartphones. '
        'Leave empty to let MediaLive auto-select.'
    ),
    'H265Settings.bitrate': (
        'Average bitrate in bits/second (bps). Required when rate_control_mode is VBR or CBR; '
        'ignored for QVBR. H.265 is ~30–50%% more efficient than H.264 at the same quality, '
        'so target bitrates can be lower.'
    ),
    'H265Settings.max_bitrate': (
        'Maximum bitrate in bits/second (bps). For QVBR, caps the bitrate ceiling. '
        'H.265 typically needs lower max_bitrate than H.264 for equivalent quality.'
    ),
    'H265Settings.buf_size': (
        'HRD buffer size in bits (not bytes). A typical value is 2x the target bitrate.'
    ),
    'H265Settings.framerate_numerator': (
        'Framerate numerator (required). Framerate = numerator / denominator. '
        'Common values: 30000/1001 = 29.97 fps, 24000/1001 = 23.976 fps, 60000/1001 = 59.94 fps.'
    ),
    'H265Settings.framerate_denominator': (
        'Framerate denominator (required). Framerate = numerator / denominator. '
        'Use 1001 for NTSC-compatible rates (29.97, 23.976, 59.94 fps) or 1 for integer rates.'
    ),
    'CreateChannelRequest.encoder_settings': (
        'The encoding configuration for the channel. This is the core of the channel definition — '
        'it contains video_descriptions, audio_descriptions, output_groups, and timecode_config. '
        'At minimum you need one video description, one audio description, one output group, '
        'and a timecode config.'
    ),
    'CreateChannelRequest.destinations': (
        'Output destinations for the channel. Each destination maps to an output group in '
        'encoder_settings. The number of destinations must match the number of output groups. '
        'Each destination needs an id that is referenced by the corresponding output group.'
    ),
    'CreateChannelRequest.input_attachments': (
        'List of inputs attached to this channel. At least one input attachment is required. '
        'Each attachment references an input by input_id and can include input_settings '
        'for source selection and network configuration.'
    ),
    'CreateChannelRequest.role_arn': (
        'IAM role ARN that MediaLive assumes when operating this channel. The role must grant '
        'MediaLive access to the input, output destinations (S3, MediaPackage, etc.), and '
        'CloudWatch Logs. Format: arn:aws:iam::<account>:role/<role-name>.'
    ),
    'EncoderSettings.video_descriptions': (
        'List of video descriptions (required). Each video description defines a video encode '
        'and must have a unique name. These names are referenced by output video_description_name '
        'fields — a mismatch causes a validation error.'
    ),
    'EncoderSettings.audio_descriptions': (
        'List of audio descriptions (required). Each audio description defines an audio encode '
        'and must have a unique name. These names are referenced by output audio_description_names '
        'fields — a mismatch causes a validation error.'
    ),
    'EncoderSettings.output_groups': (
        'List of output groups (required). Each output group defines a destination type '
        '(HLS, RTMP, UDP, MediaPackage, etc.) and contains one or more outputs. '
        "Each output group must reference a destination defined in the channel's destinations list."
    ),
    'InputAttachment.input_id': (
        'The ID of the input to attach. This must be an existing MediaLive input. '
        'Use the describe_input or list_inputs tools to find available input IDs.'
    ),
    'VideoDescription.name': (
        'A unique name for this video description. This name is referenced by outputs via '
        'video_description_name. Names are case-sensitive and must be unique within the channel. '
        "A mismatch between this name and an output's video_description_name causes a "
        'validation error.'
    ),
}

# Keyed by tool name (snake_case) — replaces auto-generated tool descriptions.
TOOL_DESCRIPTION_OVERRIDES: dict[str, str] = {
    'create_channel': (
        'Create a new MediaLive channel. A channel ingests and transcodes source content, '
        'then packages it into outputs. Requires at minimum: a name, input_attachments '
        '(at least one input), encoder_settings (with video/audio descriptions, output groups, '
        'and timecode config), destinations, and a role_arn with appropriate permissions.'
    ),
    'describe_channel': (
        'Get full details of a MediaLive channel including its current state, encoder settings, '
        "input attachments, destinations, and pipeline details. Use this to inspect a channel's "
        'configuration or check its state (IDLE, CREATING, RUNNING, etc.).'
    ),
    'start_channel': (
        'Start a MediaLive channel. The channel must be in IDLE state. Starting a channel '
        'begins ingesting from the attached inputs and producing outputs. The channel '
        'transitions through STARTING to RUNNING. Billing begins when the channel is RUNNING.'
    ),
    'stop_channel': (
        'Stop a running MediaLive channel. The channel transitions through STOPPING to IDLE. '
        'Billing stops when the channel reaches IDLE state. Outputs cease immediately.'
    ),
    'delete_channel': (
        'Delete a MediaLive channel. The channel must be in IDLE state — you cannot delete '
        'a running channel. This action is irreversible. Associated inputs are NOT deleted.'
    ),
    'list_channels': (
        'List all MediaLive channels in the account/region. Returns summary information '
        'including channel ID, name, state, and channel class. Use describe_channel for '
        'full configuration details.'
    ),
    'create_input': (
        'Create a MediaLive input. An input represents a source of content (RTMP push, '
        'HLS pull, MediaConnect, MP4 file, etc.). After creation, attach the input to a '
        'channel via input_attachments.'
    ),
    'describe_input': (
        'Get full details of a MediaLive input including its type, state, sources, '
        'destinations, and attached channels.'
    ),
    'list_inputs': (
        'List all MediaLive inputs in the account/region. Returns summary information. '
        'Use describe_input for full details of a specific input.'
    ),
}
