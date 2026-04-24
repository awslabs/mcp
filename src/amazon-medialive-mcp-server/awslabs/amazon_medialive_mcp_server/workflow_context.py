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

"""Self-contained cross-service workflow context tool for the MediaLive MCP server.

Each AWS Elemental Media Services mcp server in the awslabs/mcp repo
carries an identical copy of this module intentionally. The text below
describes how AWS Elemental Media Services connect in end-to-end video
workflows. It is exposed as a single tool so the LLM only pays the token
cost when it actually needs cross-service context.
"""

WORKFLOW_CONTEXT: str = """
AWS Elemental Media Services is a suite of services for live and on-demand
video processing and delivery. The services are independent but designed
to work together.

=== The live streaming chain ===

  Source -> MediaConnect (transport) -> MediaLive (encode) -> MediaPackage V2 (package) -> CloudFront (deliver)
                                                                    |
                                                                    v
                                                              MediaTailor (ad insertion)
                                                                    |
                                                                    v
                                                              CloudFront -> Viewers

You don't always need every service:

  Simple live stream:     MediaLive -> MediaPackage V2 -> CloudFront
  With transport:         MediaConnect -> MediaLive -> MediaPackage V2 -> CloudFront
  With ads:               MediaLive -> MediaPackage V2 -> MediaTailor -> CloudFront
  Transport only:         MediaConnect (no encoding needed)
  VOD processing:         S3 (source) -> MediaConvert (transcode) -> S3 (output) -> CloudFront
  Legacy live stream:     MediaLive -> MediaPackage V1 -> CloudFront
  Channel assembly:       S3 (clips) -> MediaTailor (channel assembly) -> CloudFront
  Live-to-VOD:            MediaLive -> MediaPackage V2 (HarvestJob) -> S3 -> MediaConvert -> CloudFront

=== How services connect ===

MediaConnect -> MediaLive:
  Create a MediaConnect Flow, then create a MediaLive Input of type
  MEDIACONNECT referencing the Flow ARN. MediaLive pulls from the Flow.

MediaLive -> MediaPackage V2:
  Create a MediaPackage V2 Channel (provides ingest endpoint URLs).
  In MediaLive, create an HLS OutputGroup with Destination set to the
  MediaPackage ingest URLs. MediaLive pushes HLS to MediaPackage.

MediaLive -> MediaPackage V1:
  Create a MediaPackage V1 Channel (provides ingest URLs + username/password).
  In MediaLive, create an HLS OutputGroup with Destination set to the
  MediaPackage ingest URLs. MediaLive pushes HLS to MediaPackage.

MediaPackage V2 -> S3 (VOD clips):
  Use CreateHarvestJob on a MediaPackage Channel to clip a time range
  from a live stream and export it to S3. Then use MediaConvert to
  transcode the clip into delivery formats.

MediaPackage V2 -> CloudFront:
  Create an OriginEndpoint on the MediaPackage Channel. Use the
  OriginEndpoint URL as the CloudFront distribution origin.

MediaPackage V2 -> MediaTailor:
  Create a MediaTailor PlaybackConfiguration with VideoContentSourceUrl
  set to the MediaPackage OriginEndpoint URL. Players use the MediaTailor
  playback URL instead of the MediaPackage URL directly.

S3 -> MediaConvert -> S3:
  Upload source files to S3. CreateJob with the S3 input path, an IAM role,
  and OutputGroup destinations pointing to an output S3 bucket. MediaConvert
  reads, transcodes, and writes output files asynchronously.

=== Naming disambiguation ===

Several services use the same resource names for different things:

- "Channel" in MediaLive = an encoder (processes video)
- "Channel" in MediaPackage V2 = an ingest point (receives video)
- "Channel" in MediaPackage V1 = an ingest point (receives video, uses username/password auth)
- "Channel" in MediaTailor = a virtual linear playout channel (assembles clips)
- "Job" in MediaConvert = a single file transcode operation
- "Input" in MediaLive = a video source endpoint
- "Source" in MediaConnect = a video source endpoint
- "Output" in MediaLive = an encoding output within an OutputGroup
- "Output" in MediaConnect = a transport delivery point

These are NOT interchangeable. Always use the service-specific tool.

MediaLive = live encoding. MediaConvert = file-based transcoding. Don't
use MediaLive for VOD processing or MediaConvert for live streams.
MediaPackage V1 = legacy packaging (username/password ingest).
MediaPackage V2 = current packaging (SigV4 ingest, ChannelGroups, policies).
""".strip()


TOOL_DESCRIPTION: str = (
    'Get context about how AWS Elemental Media Services connect to each other '
    'in end-to-end video workflows. Call this when the user asks about connecting '
    'services together, end-to-end live streaming or VOD workflows, where this '
    "service fits in the video chain, or when you're unsure which service handles "
    'a specific function.'
)


def get_media_workflow_context() -> str:
    """Return the cross-service workflow context as a single string.

    This is the handler body wired up as an MCP tool in server.py. Keep it
    synchronous and side-effect free so it costs nothing to call repeatedly.
    """
    return WORKFLOW_CONTEXT
