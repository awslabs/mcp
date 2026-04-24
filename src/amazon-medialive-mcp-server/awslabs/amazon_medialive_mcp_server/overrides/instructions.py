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

# Hand-written FastMCP instructions string for the MediaLive MCP server.
# Passed to the FastMCP constructor so the AI assistant understands
# the server's capabilities and recommended usage patterns.

INSTRUCTIONS: str = """AWS Elemental MediaLive is a broadcast-grade live video processing service.
It encodes live video streams in real time, producing adaptive bitrate (ABR)
outputs for delivery to viewers via MediaPackage, S3, or directly to CDNs.

=== Resource hierarchy ===

The core resources and how they relate:

  InputSecurityGroup → Input → Channel → OutputGroup → Destination
                                  ↑
                              Schedule (actions timed to channel timeline)

- InputSecurityGroup: IP allowlist controlling who can push to an Input.
  Create this first. Accepts CIDR ranges.

- Input: The video source. Types include RTMP_PUSH, RTP_PUSH, HLS_PULL,
  MEDIACONNECT, MP4_FILE, UDP_PUSH, and others. Each Input has one or two
  endpoints (single-pipeline or standard) that your encoder pushes to.
  An Input references an InputSecurityGroup.

- Channel: The encoder. References one or more Inputs via InputAttachments.
  Contains EncoderSettings (audio descriptions, video descriptions, output
  groups) and Destinations. A Channel has a ChannelClass:
  - STANDARD: Two independent pipelines for redundancy. Use for production.
  - SINGLE_PIPELINE: One pipeline. Use for development/testing or cost savings.
  A Channel must be explicitly started (StartChannel) to begin encoding.
  A running channel incurs charges. A stopped channel does not.

- EncoderSettings: The encoding configuration inside a Channel. Contains:
  - AudioDescriptions: At least one required. Defines audio encoding (codec,
    bitrate, sample rate). Can reference an AudioSelector from the Input.
  - VideoDescriptions: At least one required. Defines video encoding (codec,
    resolution, bitrate, frame rate).
  - OutputGroups: At least one required. Each OutputGroup defines a destination
    type (HLS, DASH, CMAF, Archive to S3, Frame Capture, MediaPackage, etc.)
    and contains Outputs that reference AudioDescriptions and VideoDescriptions.

- Schedule: Timed actions on a running channel (input switches, SCTE-35
  insertion, image overlays, motion graphics activation). Managed via
  BatchUpdateSchedule.

- Multiplex: Bundles multiple channels into a single MPTS transport stream.
  Contains MultiplexPrograms, each mapping to a Channel.

=== MediaLive Anywhere resources ===

For on-premises/hybrid deployments:

- Network: Represents a physical network. Has Routes.
- Cluster: A group of Nodes in a Network.
- Node: A physical hardware unit registered to a Cluster.
- ChannelPlacementGroup: Associates Channels to Nodes within a Cluster.
- SdiSource: Represents an SDI video source connected to a Node.

=== Workflow Monitor resources ===

- CloudWatchAlarmTemplate / CloudWatchAlarmTemplateGroup
- EventBridgeRuleTemplate / EventBridgeRuleTemplateGroup
- SignalMap: Discovers and monitors the media resource topology.

=== Getting started: Minimal live stream ===

To create a basic RTMP-to-HLS live stream:

1. CreateInputSecurityGroup — allowlist your encoder's IP (e.g., "10.0.0.0/8")
2. CreateInput — type RTMP_PUSH, reference the security group.
   Response includes two push endpoints (pipeline 0 and 1).
3. Create your destination (e.g., a MediaPackage V2 Channel, or an S3 bucket)
4. CreateChannel with:
   - InputAttachments referencing your Input
   - EncoderSettings containing:
     - At least one AudioDescription (Name is required, acts as an identifier)
     - At least one VideoDescription (Name is required)
     - At least one OutputGroup with Outputs referencing those names
   - Destinations with the target URLs
   - ChannelClass: STANDARD for production, SINGLE_PIPELINE for dev/test
5. StartChannel — encoding begins. Your encoder pushes to the Input endpoints.
6. StopChannel when done — stopped channels do not incur charges.

=== Encoding guidance ===

Video (H264 — most common):
- RateControlMode: QVBR (Quality-Defined Variable Bitrate) gives best
  quality-per-bit. Set MaxBitrate as the ceiling.
- Typical bitrates: 1080p: 4-6 Mbps, 720p: 2-3 Mbps, 480p: 1-1.5 Mbps
- GopSize: Set to 2x your segment duration. For 6-second HLS segments
  at 30fps, use GopSize=60 (frames) or GopSize=2 (seconds).
- Profile: HIGH for 1080p, MAIN for 720p/480p, BASELINE for 360p and below.

Video (H265 / AV1):
- H265: ~40% bitrate savings over H264 at same quality. Use for 4K/HDR.
- AV1: Best compression but highest compute cost. Use for cost-sensitive
  high-volume delivery.

Audio (AAC — most common):
- Bitrate: 128000 for stereo, 64000 for mono
- SampleRate: 48000 (standard for video)
- CodingMode: CODING_MODE_2_0 for stereo

ABR ladder (multiple outputs in one OutputGroup):
- 1080p @ 5 Mbps, 720p @ 2.5 Mbps, 480p @ 1.2 Mbps, 360p @ 600 Kbps
- Each is a separate Output referencing a different VideoDescription.
- All Outputs in an HLS OutputGroup share segment settings.

=== Common gotchas ===

- Channel won't start: Verify Input is in ATTACHED state, not DETACHED.
  Check that all referenced AudioDescription/VideoDescription names match
  between OutputGroup Outputs and the top-level descriptions.
- Black video: Default InputLossAction is EMIT_OUTPUT (black frames +
  silent audio). This is correct behavior during input loss.
- "Too many requests": Batch operations (BatchDelete, BatchStart, BatchStop)
  exist specifically to avoid rate limits when managing many resources.
- MediaPackage output: Use OutputGroupSettings type MEDIA_PACKAGE_GROUP_SETTINGS
  and set the Destination to the MediaPackage channel's ingest endpoint URL.
- Schedule operations use BatchUpdateSchedule (PUT), not individual create calls.
- Bitrate units: Bitrate fields (bitrate, max_bitrate) are in bits per second,
  not kilobits. For example, 5 Mbps = 5_000_000 bps.
- buf_size units: The HRD buffer size is in bits, not bytes. Typical value
  is 2x the target bitrate.
- VideoDescriptionName cross-references: Each output's video_description_name
  must exactly match a Name in encoder_settings.video_descriptions. Same
  applies to audio_description_names.
"""
