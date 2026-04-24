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

"""FastMCP instructions for the MediaPackage V2 MCP server."""

INSTRUCTIONS: str = """AWS Elemental MediaPackage V2 is a just-in-time packaging and origination
service. It receives encoded video from MediaLive (or other sources) and
packages it into streaming formats (HLS, DASH, CMAF) with optional DRM,
ad markers, and access control.

=== Resource hierarchy ===

  ChannelGroup (logical container — IAM boundary)
  └── Channel (ingest point — receives encoded video)
      └── OriginEndpoint (packaging configuration — one per output format)

  HarvestJob (clips a time range from a live stream into a VOD asset)

=== Key concepts ===

- ChannelGroup: A top-level container for Channels. Provides IAM policy
  boundary. All Channels in a group share the same policy scope.
  In most setups, one ChannelGroup per environment (dev/staging/prod).

- Channel: The ingest point. Receives HLS input from MediaLive or other
  encoders via the Channel's IngestEndpoints (URLs). A Channel has two
  ingest endpoints for redundancy (matching MediaLive's two pipelines).
  Channels do NOT need to be started — they accept input as soon as created.

- OriginEndpoint: The output configuration. Each OriginEndpoint defines:
  - Container type: HLS, DASH, or CMAF (Low Latency)
  - Segment settings (duration, naming)
  - DRM / encryption (SPEKE key provider)
  - SCTE-35 ad marker handling (passthrough, date range, enhanced)
  - Startover/timeshift window
  - Access control policy
  One Channel can have multiple OriginEndpoints for different formats.

- HarvestJob: Creates a VOD clip from a live Channel within a time window.
  Exports to S3. Useful for highlight creation and catch-up TV.

=== Getting started: Receive from MediaLive and serve HLS ===

1. CreateChannelGroup — give it a name (e.g., "production").
2. CreateChannel in that group. Response includes IngestEndpoints with URLs.
3. CreateOriginEndpoint on that Channel:
   - ContainerType: TS (for HLS) or CMAF_SEGMENT
   - HlsManifests with ManifestName
   - Segment settings (SegmentDurationSeconds: 6 is typical)
4. Configure CloudFront with the OriginEndpoint URL as the origin.
5. In MediaLive, set your HLS OutputGroup Destination to the Channel's
   ingest endpoint URLs.
6. Start the MediaLive Channel. Video flows through.

=== Key differences from MediaPackage V1 ===

- V2 uses ChannelGroups (V1 did not have this concept)
- V2 supports channel/endpoint policies (IAM-style resource policies)
- V2 has native CMAF low-latency support
- V2 has HarvestJob for VOD clip creation
- V2 OriginEndpoints are created under Channels (V1 had them more independent)

=== Integration with CloudFront ===

MediaPackage V2 OriginEndpoints produce URLs that CloudFront uses as origins.
Authentication between CloudFront and MediaPackage uses either:
- Origin Access Control (OAC) — recommended, uses SigV4 signing
- CDN-Authorization header — legacy approach using a shared secret in
  Secrets Manager

=== Common gotchas ===

- 403 from OriginEndpoint: Check the endpoint policy (GetOriginEndpointPolicy).
  If using CloudFront OAC, verify the policy allows the CloudFront distribution.
- No video playing: Ensure MediaLive is pushing to the correct ingest endpoints
  (Channel has two — one per pipeline). Check that MediaLive's OutputGroup type
  is HLS and the destination matches the Channel ingest URL.
- Segment duration mismatch: MediaLive's OutputGroup SegmentLength should match
  MediaPackage's SegmentDurationSeconds for optimal performance.
- Timeshift window: Set StartoverWindowSeconds on the OriginEndpoint to enable
  DVR/rewind. Default is 0 (no timeshift).
- Channel vs ChannelGroup policies: Channel-level policies control ingest access.
  OriginEndpoint policies control playback access. They are separate.
"""
