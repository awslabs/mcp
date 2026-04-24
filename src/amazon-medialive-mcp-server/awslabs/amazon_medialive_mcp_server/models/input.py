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

"""Input-related Pydantic models — input CRUD, HLS/SRT/multicast sources, failover settings."""

from __future__ import annotations

from awslabs.amazon_medialive_mcp_server.enums import (
    Algorithm,
    DeviceSettingsSyncState,
    DeviceUpdateStatus,
    HlsAdMarkers,
    HlsAkamaiHttpTransferMode,
    HlsCaptionLanguageSetting,
    HlsClientCache,
    HlsCodecSpecification,
    HlsDirectoryStructure,
    HlsDiscontinuityTags,
    HlsEncryptionType,
    HlsH265PackagingType,
    HlsId3SegmentTaggingState,
    HlsIncompleteSegmentBehavior,
    HlsIvInManifest,
    HlsIvSource,
    HlsManifestCompression,
    HlsManifestDurationFormat,
    HlsMediaStoreStorageClass,
    HlsMode,
    HlsOutputSelection,
    HlsProgramDateTime,
    HlsProgramDateTimeClock,
    HlsRedundantManifest,
    HlsScte35SourceType,
    HlsSegmentationMode,
    HlsStreamInfResolution,
    HlsTimedMetadataId3Frame,
    HlsTsFileMode,
    HlsWebdavHttpTransferMode,
    IFrameOnlyPlaylistType,
    InputClass,
    InputCodec,
    InputDeblockFilter,
    InputDenoiseFilter,
    InputDeviceActiveInput,
    InputDeviceCodec,
    InputDeviceConfigurableAudioChannelPairProfile,
    InputDeviceConfiguredInput,
    InputDeviceConnectionState,
    InputDeviceIpScheme,
    InputDeviceOutputType,
    InputDeviceScanType,
    InputDeviceState,
    InputDeviceType,
    InputDeviceUhdAudioChannelPairProfile,
    InputFilter,
    InputLossActionForHlsOut,
    InputLossActionForUdpOut,
    InputLossImageType,
    InputMaximumBitrate,
    InputNetworkLocation,
    InputPreference,
    InputResolution,
    InputSecurityGroupState,
    InputSourceEndBehavior,
    InputSourceType,
    InputState,
    InputTimecodeSource,
    InputType,
    NetworkInputServerValidation,
    S3CannedAcl,
    Smpte2038DataPreference,
    SrtEncryptionType,
)
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Annotated, Optional


if TYPE_CHECKING:
    from awslabs.amazon_medialive_mcp_server.models.common import (
        AudioOnlyHlsSettings,
        AudioSelector,
        CaptionLanguageMapping,
        CaptionSelector,
        MediaConnectFlow,
        StandardHlsSettings,
        StartTimecode,
        StopTimecode,
        ValidationError,
    )
    from awslabs.amazon_medialive_mcp_server.models.encoding import (
        FrameCaptureHlsSettings,
        VideoSelector,
    )
    from awslabs.amazon_medialive_mcp_server.models.output import (
        Fmp4HlsSettings,
        KeyProviderSettings,
        OutputLocationRef,
        UdpContainerSettings,
    )


class AudioSilenceFailoverSettings(BaseModel):
    """Placeholder documentation for AudioSilenceFailoverSettings."""

    model_config = ConfigDict(populate_by_name=True)

    audio_selector_name: Annotated[
        str,
        Field(
            ...,
            alias='AudioSelectorName',
            description='The name of the audio selector in the input that MediaLive should monitor to detect silence. Select your most important rendition. If you didn\u0027t create an audio selector in this input, leave blank.',
        ),
    ]

    audio_silence_threshold_msec: Annotated[
        Optional[int],
        Field(
            None,
            alias='AudioSilenceThresholdMsec',
            description='The amount of time (in milliseconds) that the active input must be silent before automatic input failover occurs. Silence is defined as audio loss or audio quieter than -50 dBFS.',
        ),
    ]


class HlsAkamaiSettings(BaseModel):
    """Hls Akamai Settings."""

    model_config = ConfigDict(populate_by_name=True)

    connection_retry_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='ConnectionRetryInterval',
            description='Number of seconds to wait before retrying connection to the CDN if the connection is lost.',
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

    http_transfer_mode: Annotated[
        Optional[HlsAkamaiHttpTransferMode],
        Field(
            None,
            alias='HttpTransferMode',
            description='Specify whether or not to use chunked transfer encoding to Akamai. User should contact Akamai to enable this feature.',
        ),
    ]

    num_retries: Annotated[
        Optional[int],
        Field(
            None,
            alias='NumRetries',
            description='Number of retry attempts that will be made before the Live Event is put into an error state. Applies only if the CDN destination URI begins with "s3" or "mediastore". For other URIs, the value is always 3.',
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

    salt: Annotated[
        Optional[str],
        Field(
            None,
            alias='Salt',
            description='Salt for authenticated Akamai.',
        ),
    ]

    token: Annotated[
        Optional[str],
        Field(
            None,
            alias='Token',
            description='Token parameter for authenticated akamai. If not specified, _gda_ is used.',
        ),
    ]


class HlsBasicPutSettings(BaseModel):
    """Hls Basic Put Settings."""

    model_config = ConfigDict(populate_by_name=True)

    connection_retry_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='ConnectionRetryInterval',
            description='Number of seconds to wait before retrying connection to the CDN if the connection is lost.',
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

    num_retries: Annotated[
        Optional[int],
        Field(
            None,
            alias='NumRetries',
            description='Number of retry attempts that will be made before the Live Event is put into an error state. Applies only if the CDN destination URI begins with "s3" or "mediastore". For other URIs, the value is always 3.',
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


class HlsId3SegmentTaggingScheduleActionSettings(BaseModel):
    """Settings for the action to insert ID3 metadata in every segment, in HLS output groups."""

    model_config = ConfigDict(populate_by_name=True)

    tag: Annotated[
        Optional[str],
        Field(
            None,
            alias='Tag',
            description='Complete this parameter if you want to specify only the metadata, not the entire frame. MediaLive will insert the metadata in a TXXX frame. Enter the value as plain text. You can include standard MediaLive variable data such as the current segment number.',
        ),
    ]

    id3: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id3',
            description='Complete this parameter if you want to specify the entire ID3 metadata. Enter a base64 string that contains one or more fully formed ID3 tags, according to the ID3 specification: http://id3.org/id3v2.4.0-structure',
        ),
    ]


class HlsInputSettings(BaseModel):
    """Hls Input Settings."""

    model_config = ConfigDict(populate_by_name=True)

    bandwidth: Annotated[
        Optional[int],
        Field(
            None,
            alias='Bandwidth',
            description='When specified the HLS stream with the m3u8 BANDWIDTH that most closely matches this value will be chosen, otherwise the highest bandwidth stream in the m3u8 will be chosen. The bitrate is specified in bits per second, as in an HLS manifest.',
        ),
    ]

    buffer_segments: Annotated[
        Optional[int],
        Field(
            None,
            alias='BufferSegments',
            description='When specified, reading of the HLS input will begin this many buffer segments from the end (most recently written segment). When not specified, the HLS input will begin with the first segment specified in the m3u8.',
        ),
    ]

    retries: Annotated[
        Optional[int],
        Field(
            None,
            alias='Retries',
            description='The number of consecutive times that attempts to read a manifest or segment must fail before the input is considered unavailable.',
        ),
    ]

    retry_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='RetryInterval',
            description='The number of seconds between retries when an attempt to read a manifest or segment fails.',
        ),
    ]

    scte35_source: Annotated[
        Optional[HlsScte35SourceType],
        Field(
            None,
            alias='Scte35Source',
            description='Identifies the source for the SCTE-35 messages that MediaLive will ingest. Messages can be ingested from the content segments (in the stream) or from tags in the playlist (the HLS manifest). MediaLive ignores SCTE-35 information in the source that is not selected.',
        ),
    ]


class HlsMediaStoreSettings(BaseModel):
    """Hls Media Store Settings."""

    model_config = ConfigDict(populate_by_name=True)

    connection_retry_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='ConnectionRetryInterval',
            description='Number of seconds to wait before retrying connection to the CDN if the connection is lost.',
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

    media_store_storage_class: Annotated[
        Optional[HlsMediaStoreStorageClass],
        Field(
            None,
            alias='MediaStoreStorageClass',
            description='When set to temporal, output files are stored in non-persistent memory for faster reading and writing.',
        ),
    ]

    num_retries: Annotated[
        Optional[int],
        Field(
            None,
            alias='NumRetries',
            description='Number of retry attempts that will be made before the Live Event is put into an error state. Applies only if the CDN destination URI begins with "s3" or "mediastore". For other URIs, the value is always 3.',
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


class HlsS3Settings(BaseModel):
    """Hls S3 Settings."""

    model_config = ConfigDict(populate_by_name=True)

    canned_acl: Annotated[
        Optional[S3CannedAcl],
        Field(
            None,
            alias='CannedAcl',
            description='Specify the canned ACL to apply to each S3 request. Defaults to none.',
        ),
    ]


class HlsTimedMetadataScheduleActionSettings(BaseModel):
    """Settings for the action to insert ID3 metadata (as a one-time action) in HLS output groups."""

    model_config = ConfigDict(populate_by_name=True)

    id3: Annotated[
        str,
        Field(
            ...,
            alias='Id3',
            description='Enter a base64 string that contains one or more fully formed ID3 tags.See the ID3 specification: http://id3.org/id3v2.4.0-structure',
        ),
    ]


class HlsWebdavSettings(BaseModel):
    """Hls Webdav Settings."""

    model_config = ConfigDict(populate_by_name=True)

    connection_retry_interval: Annotated[
        Optional[int],
        Field(
            None,
            alias='ConnectionRetryInterval',
            description='Number of seconds to wait before retrying connection to the CDN if the connection is lost.',
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

    http_transfer_mode: Annotated[
        Optional[HlsWebdavHttpTransferMode],
        Field(
            None,
            alias='HttpTransferMode',
            description='Specify whether or not to use chunked transfer encoding to WebDAV.',
        ),
    ]

    num_retries: Annotated[
        Optional[int],
        Field(
            None,
            alias='NumRetries',
            description='Number of retry attempts that will be made before the Live Event is put into an error state. Applies only if the CDN destination URI begins with "s3" or "mediastore". For other URIs, the value is always 3.',
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


class HlsCdnSettings(BaseModel):
    """Hls Cdn Settings."""

    model_config = ConfigDict(populate_by_name=True)

    hls_akamai_settings: Annotated[
        Optional[HlsAkamaiSettings],
        Field(
            None,
            alias='HlsAkamaiSettings',
            description='',
        ),
    ]

    hls_basic_put_settings: Annotated[
        Optional[HlsBasicPutSettings],
        Field(
            None,
            alias='HlsBasicPutSettings',
            description='',
        ),
    ]

    hls_media_store_settings: Annotated[
        Optional[HlsMediaStoreSettings],
        Field(
            None,
            alias='HlsMediaStoreSettings',
            description='',
        ),
    ]

    hls_s3_settings: Annotated[
        Optional[HlsS3Settings],
        Field(
            None,
            alias='HlsS3Settings',
            description='',
        ),
    ]

    hls_webdav_settings: Annotated[
        Optional[HlsWebdavSettings],
        Field(
            None,
            alias='HlsWebdavSettings',
            description='',
        ),
    ]


class InputChannelLevel(BaseModel):
    """Input Channel Level."""

    model_config = ConfigDict(populate_by_name=True)

    gain: Annotated[
        int,
        Field(
            ...,
            alias='Gain',
            description='Remixing value. Units are in dB and acceptable values are within the range from -60 (mute) and 6 dB.',
        ),
    ]

    input_channel: Annotated[
        int,
        Field(
            ...,
            alias='InputChannel',
            description='The index of the input channel used as a source.',
        ),
    ]


class InputDestinationRoute(BaseModel):
    """A network route configuration."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='The CIDR of the route.',
        ),
    ]

    gateway: Annotated[
        Optional[str],
        Field(
            None,
            alias='Gateway',
            description='An optional gateway for the route.',
        ),
    ]


class InputDestinationVpc(BaseModel):
    """The properties for a VPC type input destination."""

    model_config = ConfigDict(populate_by_name=True)

    availability_zone: Annotated[
        Optional[str],
        Field(
            None,
            alias='AvailabilityZone',
            description='The availability zone of the Input destination.',
        ),
    ]

    network_interface_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='NetworkInterfaceId',
            description='The network interface ID of the Input destination in the VPC.',
        ),
    ]


class InputDestination(BaseModel):
    """The settings for a PUSH type input."""

    model_config = ConfigDict(populate_by_name=True)

    ip: Annotated[
        Optional[str],
        Field(
            None,
            alias='Ip',
            description='The system-generated static IP address of endpoint. It remains fixed for the lifetime of the input.',
        ),
    ]

    port: Annotated[
        Optional[str],
        Field(
            None,
            alias='Port',
            description='The port number for the input.',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='This represents the endpoint that the customer stream will be pushed to.',
        ),
    ]

    vpc: Annotated[
        Optional[InputDestinationVpc],
        Field(
            None,
            alias='Vpc',
            description='',
        ),
    ]

    network: Annotated[
        Optional[str],
        Field(
            None,
            alias='Network',
            description='The ID of the attached network.',
        ),
    ]

    network_routes: Annotated[
        Optional[list[InputDestinationRoute]],
        Field(
            None,
            alias='NetworkRoutes',
            description='If the push input has an input location of ON-PREM it\u0027s a requirement to specify what the route of the input is going to be on the customer local network.',
        ),
    ]


class InputDeviceConfigurableAudioChannelPairConfig(BaseModel):
    """One audio configuration that specifies the format for one audio pair that the device produces as output."""

    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[
        Optional[int],
        Field(
            None,
            alias='Id',
            description='The ID for one audio pair configuration, a value from 1 to 8.',
        ),
    ]

    profile: Annotated[
        Optional[InputDeviceConfigurableAudioChannelPairProfile],
        Field(
            None,
            alias='Profile',
            description='The profile to set for one audio pair configuration. Choose an enumeration value. Each value describes one audio configuration using the format (rate control algorithm)-(codec)_(quality)-(bitrate in bytes). For example, CBR-AAC_HQ-192000. Or choose DISABLED, in which case the device won\u0027t produce audio for this pair.',
        ),
    ]


class InputDeviceHdSettings(BaseModel):
    """Settings that describe the active source from the input device, and the video characteristics of that source."""

    model_config = ConfigDict(populate_by_name=True)

    active_input: Annotated[
        Optional[InputDeviceActiveInput],
        Field(
            None,
            alias='ActiveInput',
            description='If you specified Auto as the configured input, specifies which of the sources is currently active (SDI or HDMI).',
        ),
    ]

    configured_input: Annotated[
        Optional[InputDeviceConfiguredInput],
        Field(
            None,
            alias='ConfiguredInput',
            description='The source at the input device that is currently active. You can specify this source.',
        ),
    ]

    device_state: Annotated[
        Optional[InputDeviceState],
        Field(
            None,
            alias='DeviceState',
            description='The state of the input device.',
        ),
    ]

    framerate: Annotated[
        Optional[float],
        Field(
            None,
            alias='Framerate',
            description='The frame rate of the video source.',
        ),
    ]

    height: Annotated[
        Optional[int],
        Field(
            None,
            alias='Height',
            description='The height of the video source, in pixels.',
        ),
    ]

    max_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxBitrate',
            description='The current maximum bitrate for ingesting this source, in bits per second. You can specify this maximum.',
        ),
    ]

    scan_type: Annotated[
        Optional[InputDeviceScanType],
        Field(
            None,
            alias='ScanType',
            description='The scan type of the video source.',
        ),
    ]

    width: Annotated[
        Optional[int],
        Field(
            None,
            alias='Width',
            description='The width of the video source, in pixels.',
        ),
    ]

    latency_ms: Annotated[
        Optional[int],
        Field(
            None,
            alias='LatencyMs',
            description='The Link device\u0027s buffer size (latency) in milliseconds (ms). You can specify this value.',
        ),
    ]


class InputDeviceMediaConnectConfigurableSettings(BaseModel):
    """Parameters required to attach a MediaConnect flow to the device."""

    model_config = ConfigDict(populate_by_name=True)

    flow_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='FlowArn',
            description='The ARN of the MediaConnect flow to attach this device to.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The ARN for the role that MediaLive assumes to access the attached flow and secret. For more information about how to create this role, see the MediaLive user guide.',
        ),
    ]

    secret_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='SecretArn',
            description='The ARN for the secret that holds the encryption key to encrypt the content output by the device.',
        ),
    ]

    source_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='SourceName',
            description='The name of the MediaConnect Flow source to stream to.',
        ),
    ]


class InputDeviceConfigurableSettings(BaseModel):
    """Configurable settings for the input device."""

    model_config = ConfigDict(populate_by_name=True)

    configured_input: Annotated[
        Optional[InputDeviceConfiguredInput],
        Field(
            None,
            alias='ConfiguredInput',
            description='The input source that you want to use. If the device has a source connected to only one of its input ports, or if you don\u0027t care which source the device sends, specify Auto. If the device has sources connected to both its input ports, and you want to use a specific source, specify the source.',
        ),
    ]

    max_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxBitrate',
            description='The maximum bitrate in bits per second. Set a value here to throttle the bitrate of the source video.',
        ),
    ]

    latency_ms: Annotated[
        Optional[int],
        Field(
            None,
            alias='LatencyMs',
            description='The Link device\u0027s buffer size (latency) in milliseconds (ms).',
        ),
    ]

    codec: Annotated[
        Optional[InputDeviceCodec],
        Field(
            None,
            alias='Codec',
            description='Choose the codec for the video that the device produces. Only UHD devices can specify this parameter.',
        ),
    ]

    mediaconnect_settings: Annotated[
        Optional[InputDeviceMediaConnectConfigurableSettings],
        Field(
            None,
            alias='MediaconnectSettings',
            description='To attach this device to a MediaConnect flow, specify these parameters. To detach an existing flow, enter {} for the value of mediaconnectSettings. Only UHD devices can specify this parameter.',
        ),
    ]

    audio_channel_pairs: Annotated[
        Optional[list[InputDeviceConfigurableAudioChannelPairConfig]],
        Field(
            None,
            alias='AudioChannelPairs',
            description='An array of eight audio configurations, one for each audio pair in the source. Set up each audio configuration either to exclude the pair, or to format it and include it in the output from the device. This parameter applies only to UHD devices, and only when the device is configured as the source for a MediaConnect flow. For an HD device, you configure the audio by setting up audio selectors in the channel configuration.',
        ),
    ]

    input_resolution: Annotated[
        Optional[str],
        Field(
            None,
            alias='InputResolution',
            description='Choose the resolution of the Link device\u0027s source (HD or UHD). Make sure the resolution matches the current source from the device. This value determines MediaLive resource allocation and billing for this input. Only UHD devices can specify this parameter.',
        ),
    ]


class InputDeviceMediaConnectSettings(BaseModel):
    """Information about the MediaConnect flow attached to the device."""

    model_config = ConfigDict(populate_by_name=True)

    flow_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='FlowArn',
            description='The ARN of the MediaConnect flow.',
        ),
    ]

    role_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='RoleArn',
            description='The ARN for the role that MediaLive assumes to access the attached flow and secret.',
        ),
    ]

    secret_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='SecretArn',
            description='The ARN of the secret used to encrypt the stream.',
        ),
    ]

    source_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='SourceName',
            description='The name of the MediaConnect flow source.',
        ),
    ]


class InputDeviceNetworkSettings(BaseModel):
    """The network settings for the input device."""

    model_config = ConfigDict(populate_by_name=True)

    dns_addresses: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='DnsAddresses',
            description='The DNS addresses of the input device.',
        ),
    ]

    gateway: Annotated[
        Optional[str],
        Field(
            None,
            alias='Gateway',
            description='The network gateway IP address.',
        ),
    ]

    ip_address: Annotated[
        Optional[str],
        Field(
            None,
            alias='IpAddress',
            description='The IP address of the input device.',
        ),
    ]

    ip_scheme: Annotated[
        Optional[InputDeviceIpScheme],
        Field(
            None,
            alias='IpScheme',
            description='Specifies whether the input device has been configured (outside of MediaLive) to use a dynamic IP address assignment (DHCP) or a static IP address.',
        ),
    ]

    subnet_mask: Annotated[
        Optional[str],
        Field(
            None,
            alias='SubnetMask',
            description='The subnet mask of the input device.',
        ),
    ]


class InputDeviceRequest(BaseModel):
    """Settings for an input device."""

    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID for the device.',
        ),
    ]


class InputDeviceSettings(BaseModel):
    """Settings for an input device."""

    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[
        Optional[str],
        Field(
            None,
            alias='Id',
            description='The unique ID for the device.',
        ),
    ]


class InputDeviceUhdAudioChannelPairConfig(BaseModel):
    """One audio configuration that specifies the format for one audio pair that the device produces as output."""

    model_config = ConfigDict(populate_by_name=True)

    id: Annotated[
        Optional[int],
        Field(
            None,
            alias='Id',
            description='The ID for one audio pair configuration, a value from 1 to 8.',
        ),
    ]

    profile: Annotated[
        Optional[InputDeviceUhdAudioChannelPairProfile],
        Field(
            None,
            alias='Profile',
            description='The profile for one audio pair configuration. This property describes one audio configuration in the format (rate control algorithm)-(codec)_(quality)-(bitrate in bytes). For example, CBR-AAC_HQ-192000. Or DISABLED, in which case the device won\u0027t produce audio for this pair.',
        ),
    ]


class InputDeviceUhdSettings(BaseModel):
    """Settings that describe the active source from the input device, and the video characteristics of that source."""

    model_config = ConfigDict(populate_by_name=True)

    active_input: Annotated[
        Optional[InputDeviceActiveInput],
        Field(
            None,
            alias='ActiveInput',
            description='If you specified Auto as the configured input, specifies which of the sources is currently active (SDI or HDMI).',
        ),
    ]

    configured_input: Annotated[
        Optional[InputDeviceConfiguredInput],
        Field(
            None,
            alias='ConfiguredInput',
            description='The source at the input device that is currently active. You can specify this source.',
        ),
    ]

    device_state: Annotated[
        Optional[InputDeviceState],
        Field(
            None,
            alias='DeviceState',
            description='The state of the input device.',
        ),
    ]

    framerate: Annotated[
        Optional[float],
        Field(
            None,
            alias='Framerate',
            description='The frame rate of the video source.',
        ),
    ]

    height: Annotated[
        Optional[int],
        Field(
            None,
            alias='Height',
            description='The height of the video source, in pixels.',
        ),
    ]

    max_bitrate: Annotated[
        Optional[int],
        Field(
            None,
            alias='MaxBitrate',
            description='The current maximum bitrate for ingesting this source, in bits per second. You can specify this maximum.',
        ),
    ]

    scan_type: Annotated[
        Optional[InputDeviceScanType],
        Field(
            None,
            alias='ScanType',
            description='The scan type of the video source.',
        ),
    ]

    width: Annotated[
        Optional[int],
        Field(
            None,
            alias='Width',
            description='The width of the video source, in pixels.',
        ),
    ]

    latency_ms: Annotated[
        Optional[int],
        Field(
            None,
            alias='LatencyMs',
            description='The Link device\u0027s buffer size (latency) in milliseconds (ms). You can specify this value.',
        ),
    ]

    codec: Annotated[
        Optional[InputDeviceCodec],
        Field(
            None,
            alias='Codec',
            description='The codec for the video that the device produces.',
        ),
    ]

    mediaconnect_settings: Annotated[
        Optional[InputDeviceMediaConnectSettings],
        Field(
            None,
            alias='MediaconnectSettings',
            description='Information about the MediaConnect flow attached to the device. Returned only if the outputType is MEDIACONNECT_FLOW.',
        ),
    ]

    audio_channel_pairs: Annotated[
        Optional[list[InputDeviceUhdAudioChannelPairConfig]],
        Field(
            None,
            alias='AudioChannelPairs',
            description='An array of eight audio configurations, one for each audio pair in the source. Each audio configuration specifies either to exclude the pair, or to format it and include it in the output from the UHD device. Applies only when the device is configured as the source for a MediaConnect flow.',
        ),
    ]

    input_resolution: Annotated[
        Optional[str],
        Field(
            None,
            alias='InputResolution',
            description='The resolution of the Link device\u0027s source (HD or UHD). This value determines MediaLive resource allocation and billing for this input.',
        ),
    ]


class InputDevice(BaseModel):
    """An input device."""

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


class InputDeviceSummary(BaseModel):
    """Details of the input device."""

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
            description='Network settings for the input device.',
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


class InputLocation(BaseModel):
    """Input Location."""

    model_config = ConfigDict(populate_by_name=True)

    password_param: Annotated[
        Optional[str],
        Field(
            None,
            alias='PasswordParam',
            description='key used to extract the password from EC2 Parameter store',
        ),
    ]

    uri: Annotated[
        str,
        Field(
            ...,
            alias='Uri',
            description='Uniform Resource Identifier - This should be a path to a file accessible to the Live system (eg. a http:// URI) depending on the output type. For example, a RTMP destination should have a uri simliar to: "rtmp://fmsserver/live".',
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


class InputLossBehavior(BaseModel):
    """Input Loss Behavior."""

    model_config = ConfigDict(populate_by_name=True)

    black_frame_msec: Annotated[
        Optional[int],
        Field(
            None,
            alias='BlackFrameMsec',
            description='Documentation update needed',
        ),
    ]

    input_loss_image_color: Annotated[
        Optional[str],
        Field(
            None,
            alias='InputLossImageColor',
            description='When input loss image type is "color" this field specifies the color to use. Value: 6 hex characters representing the values of RGB.',
        ),
    ]

    input_loss_image_slate: Annotated[
        Optional[InputLocation],
        Field(
            None,
            alias='InputLossImageSlate',
            description='When input loss image type is "slate" these fields specify the parameters for accessing the slate.',
        ),
    ]

    input_loss_image_type: Annotated[
        Optional[InputLossImageType],
        Field(
            None,
            alias='InputLossImageType',
            description='Indicates whether to substitute a solid color or a slate into the output after input loss exceeds blackFrameMsec.',
        ),
    ]

    repeat_frame_msec: Annotated[
        Optional[int],
        Field(
            None,
            alias='RepeatFrameMsec',
            description='Documentation update needed',
        ),
    ]


class InputLossFailoverSettings(BaseModel):
    """MediaLive will perform a failover if content is not detected in this input for the specified period."""

    model_config = ConfigDict(populate_by_name=True)

    input_loss_threshold_msec: Annotated[
        Optional[int],
        Field(
            None,
            alias='InputLossThresholdMsec',
            description='The amount of time (in milliseconds) that no input is detected. After that time, an input failover will occur.',
        ),
    ]


class InputRequestDestinationRoute(BaseModel):
    """A network route configuration."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='The CIDR of the route.',
        ),
    ]

    gateway: Annotated[
        Optional[str],
        Field(
            None,
            alias='Gateway',
            description='An optional gateway for the route.',
        ),
    ]


class InputDestinationRequest(BaseModel):
    """Endpoint settings for a PUSH type input."""

    model_config = ConfigDict(populate_by_name=True)

    stream_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='StreamName',
            description='A unique name for the location the RTMP stream is being pushed to.',
        ),
    ]

    network: Annotated[
        Optional[str],
        Field(
            None,
            alias='Network',
            description='If the push input has an input location of ON-PREM, ID the ID of the attached network.',
        ),
    ]

    network_routes: Annotated[
        Optional[list[InputRequestDestinationRoute]],
        Field(
            None,
            alias='NetworkRoutes',
            description='If the push input has an input location of ON-PREM it\u0027s a requirement to specify what the route of the input is going to be on the customer local network.',
        ),
    ]

    static_ip_address: Annotated[
        Optional[str],
        Field(
            None,
            alias='StaticIpAddress',
            description='If the push input has an input location of ON-PREM it\u0027s optional to specify what the ip address of the input is going to be on the customer local network.',
        ),
    ]


class InputSdpLocation(BaseModel):
    """The location of the SDP file for one of the SMPTE 2110 streams in a receiver group."""

    model_config = ConfigDict(populate_by_name=True)

    media_index: Annotated[
        Optional[int],
        Field(
            None,
            alias='MediaIndex',
            description='The index of the media stream in the SDP file for one SMPTE 2110 stream.',
        ),
    ]

    sdp_url: Annotated[
        Optional[str],
        Field(
            None,
            alias='SdpUrl',
            description='The URL of the SDP file for one SMPTE 2110 stream.',
        ),
    ]


class InputSource(BaseModel):
    """The settings for a PULL type input."""

    model_config = ConfigDict(populate_by_name=True)

    password_param: Annotated[
        Optional[str],
        Field(
            None,
            alias='PasswordParam',
            description='The key used to extract the password from EC2 Parameter store.',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='This represents the customer\u0027s source URL where stream is pulled from.',
        ),
    ]

    username: Annotated[
        Optional[str],
        Field(
            None,
            alias='Username',
            description='The username for the input source.',
        ),
    ]


class InputSourceRequest(BaseModel):
    """Settings for for a PULL type input."""

    model_config = ConfigDict(populate_by_name=True)

    password_param: Annotated[
        Optional[str],
        Field(
            None,
            alias='PasswordParam',
            description='The key used to extract the password from EC2 Parameter store.',
        ),
    ]

    url: Annotated[
        Optional[str],
        Field(
            None,
            alias='Url',
            description='This represents the customer\u0027s source URL where stream is pulled from.',
        ),
    ]

    username: Annotated[
        Optional[str],
        Field(
            None,
            alias='Username',
            description='The username for the input source.',
        ),
    ]


class InputSpecification(BaseModel):
    """Placeholder documentation for InputSpecification."""

    model_config = ConfigDict(populate_by_name=True)

    codec: Annotated[
        Optional[InputCodec],
        Field(
            None,
            alias='Codec',
            description='Input codec',
        ),
    ]

    maximum_bitrate: Annotated[
        Optional[InputMaximumBitrate],
        Field(
            None,
            alias='MaximumBitrate',
            description='Maximum input bitrate, categorized coarsely',
        ),
    ]

    resolution: Annotated[
        Optional[InputResolution],
        Field(
            None,
            alias='Resolution',
            description='Input resolution, categorized coarsely',
        ),
    ]


class InputVpcRequest(BaseModel):
    """Settings for a private VPC Input. When this property is specified, the input destination addresses will be created in a VPC rather than with public Internet addresses. This property requires setting the roleArn property on Input creation. Not compatible with the inputSecurityGroups property."""

    model_config = ConfigDict(populate_by_name=True)

    security_group_ids: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='SecurityGroupIds',
            description='A list of up to 5 EC2 VPC security group IDs to attach to the Input VPC network interfaces. Requires subnetIds. If none are specified then the VPC default security group will be used.',
        ),
    ]

    subnet_ids: Annotated[
        list[str],
        Field(
            ...,
            alias='SubnetIds',
            description='A list of 2 VPC subnet IDs from the same VPC. Subnet IDs must be mapped to two unique availability zones (AZ).',
        ),
    ]


class InputWhitelistRule(BaseModel):
    """Whitelist rule."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='The IPv4 CIDR that\u0027s whitelisted.',
        ),
    ]


class InputSecurityGroup(BaseModel):
    """An Input Security Group."""

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


class InputWhitelistRuleCidr(BaseModel):
    """An IPv4 CIDR to whitelist."""

    model_config = ConfigDict(populate_by_name=True)

    cidr: Annotated[
        Optional[str],
        Field(
            None,
            alias='Cidr',
            description='The IPv4 CIDR to whitelist.',
        ),
    ]


class InputSecurityGroupWhitelistRequest(BaseModel):
    """Request of IPv4 CIDR addresses to whitelist in a security group."""

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


class MulticastInputSettings(BaseModel):
    """Multicast-specific input settings."""

    model_config = ConfigDict(populate_by_name=True)

    source_ip_address: Annotated[
        Optional[str],
        Field(
            None,
            alias='SourceIpAddress',
            description='Optionally, a source ip address to filter by for Source-specific Multicast (SSM)',
        ),
    ]


class MulticastSource(BaseModel):
    """Pair of multicast url and source ip address (optional) that make up a multicast source."""

    model_config = ConfigDict(populate_by_name=True)

    source_ip: Annotated[
        Optional[str],
        Field(
            None,
            alias='SourceIp',
            description='This represents the ip address of the device sending the multicast stream.',
        ),
    ]

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='This represents the customer\u0027s source URL where multicast stream is pulled from.',
        ),
    ]


class MulticastSettings(BaseModel):
    """Settings for a Multicast input. Contains a list of multicast Urls and optional source ip addresses."""

    model_config = ConfigDict(populate_by_name=True)

    sources: Annotated[
        Optional[list[MulticastSource]],
        Field(
            None,
            alias='Sources',
            description='',
        ),
    ]


class MulticastSourceCreateRequest(BaseModel):
    """Pair of multicast url and source ip address (optional) that make up a multicast source."""

    model_config = ConfigDict(populate_by_name=True)

    source_ip: Annotated[
        Optional[str],
        Field(
            None,
            alias='SourceIp',
            description='This represents the ip address of the device sending the multicast stream.',
        ),
    ]

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='This represents the customer\u0027s source URL where multicast stream is pulled from.',
        ),
    ]


class MulticastSettingsCreateRequest(BaseModel):
    """Settings for a Multicast input. Contains a list of multicast Urls and optional source ip addresses."""

    model_config = ConfigDict(populate_by_name=True)

    sources: Annotated[
        Optional[list[MulticastSourceCreateRequest]],
        Field(
            None,
            alias='Sources',
            description='',
        ),
    ]


class MulticastSourceUpdateRequest(BaseModel):
    """Pair of multicast url and source ip address (optional) that make up a multicast source."""

    model_config = ConfigDict(populate_by_name=True)

    source_ip: Annotated[
        Optional[str],
        Field(
            None,
            alias='SourceIp',
            description='This represents the ip address of the device sending the multicast stream.',
        ),
    ]

    url: Annotated[
        str,
        Field(
            ...,
            alias='Url',
            description='This represents the customer\u0027s source URL where multicast stream is pulled from.',
        ),
    ]


class MulticastSettingsUpdateRequest(BaseModel):
    """Settings for a Multicast input. Contains a list of multicast Urls and optional source ip addresses."""

    model_config = ConfigDict(populate_by_name=True)

    sources: Annotated[
        Optional[list[MulticastSourceUpdateRequest]],
        Field(
            None,
            alias='Sources',
            description='',
        ),
    ]


class NetworkInputSettings(BaseModel):
    """Network source to transcode. Must be accessible to the Elemental Live node that is running the live event through a network connection."""

    model_config = ConfigDict(populate_by_name=True)

    hls_input_settings: Annotated[
        Optional[HlsInputSettings],
        Field(
            None,
            alias='HlsInputSettings',
            description='Specifies HLS input settings when the uri is for a HLS manifest.',
        ),
    ]

    server_validation: Annotated[
        Optional[NetworkInputServerValidation],
        Field(
            None,
            alias='ServerValidation',
            description='Check HTTPS server certificates. When set to checkCryptographyOnly, cryptography in the certificate will be checked, but not the server\u0027s name. Certain subdomains (notably S3 buckets that use dots in the bucket name) do not strictly match the corresponding certificate\u0027s wildcard pattern and would otherwise cause the event to error. This setting is ignored for protocols that do not use https.',
        ),
    ]

    multicast_input_settings: Annotated[
        Optional[MulticastInputSettings],
        Field(
            None,
            alias='MulticastInputSettings',
            description='Specifies multicast input settings when the uri is for a multicast event.',
        ),
    ]


class Smpte2110ReceiverGroupSdpSettings(BaseModel):
    """Information about the SDP files that describe the SMPTE 2110 streams that go into one SMPTE 2110 receiver group."""

    model_config = ConfigDict(populate_by_name=True)

    ancillary_sdps: Annotated[
        Optional[list[InputSdpLocation]],
        Field(
            None,
            alias='AncillarySdps',
            description='A list of InputSdpLocations. Each item in the list specifies the SDP file and index for one ancillary SMPTE 2110 stream. Each stream encapsulates one captions stream (out of any number you can include) or the single SCTE 35 stream that you can include.',
        ),
    ]

    audio_sdps: Annotated[
        Optional[list[InputSdpLocation]],
        Field(
            None,
            alias='AudioSdps',
            description='A list of InputSdpLocations. Each item in the list specifies the SDP file and index for one audio SMPTE 2110 stream.',
        ),
    ]

    video_sdp: Annotated[
        Optional[InputSdpLocation],
        Field(
            None,
            alias='VideoSdp',
            description='The InputSdpLocation that specifies the SDP file and index for the single video SMPTE 2110 stream for this 2110 input.',
        ),
    ]


class Smpte2110ReceiverGroup(BaseModel):
    """A receiver group is a collection of video, audio, and ancillary streams that you want to group together and attach to one input."""

    model_config = ConfigDict(populate_by_name=True)

    sdp_settings: Annotated[
        Optional[Smpte2110ReceiverGroupSdpSettings],
        Field(
            None,
            alias='SdpSettings',
            description='The single Smpte2110ReceiverGroupSdpSettings that identify the video, audio, and ancillary streams for this receiver group.',
        ),
    ]


class Smpte2110ReceiverGroupSettings(BaseModel):
    """Configures the sources for the SMPTE 2110 Receiver Group input."""

    model_config = ConfigDict(populate_by_name=True)

    smpte2110_receiver_groups: Annotated[
        Optional[list[Smpte2110ReceiverGroup]],
        Field(
            None,
            alias='Smpte2110ReceiverGroups',
            description='',
        ),
    ]


class SrtCallerDecryption(BaseModel):
    """The decryption settings for the SRT caller source. Present only if the source has decryption enabled."""

    model_config = ConfigDict(populate_by_name=True)

    algorithm: Annotated[
        Optional[Algorithm],
        Field(
            None,
            alias='Algorithm',
            description='The algorithm used to encrypt content.',
        ),
    ]

    passphrase_secret_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='PassphraseSecretArn',
            description='The ARN for the secret in Secrets Manager. Someone in your organization must create a secret and provide you with its ARN. The secret holds the passphrase that MediaLive uses to decrypt the source content.',
        ),
    ]


class SrtCallerDecryptionRequest(BaseModel):
    """Complete these parameters only if the content is encrypted."""

    model_config = ConfigDict(populate_by_name=True)

    algorithm: Annotated[
        Optional[Algorithm],
        Field(
            None,
            alias='Algorithm',
            description='The algorithm used to encrypt content.',
        ),
    ]

    passphrase_secret_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='PassphraseSecretArn',
            description='The ARN for the secret in Secrets Manager. Someone in your organization must create a secret and provide you with its ARN. This secret holds the passphrase that MediaLive will use to decrypt the source content.',
        ),
    ]


class SrtCallerSource(BaseModel):
    """The configuration for a source that uses SRT as the connection protocol. In terms of establishing the connection, MediaLive is always caller and the upstream system is always the listener. In terms of transmission of the source content, MediaLive is always the receiver and the upstream system is alw."""

    model_config = ConfigDict(populate_by_name=True)

    decryption: Annotated[
        Optional[SrtCallerDecryption],
        Field(
            None,
            alias='Decryption',
            description='',
        ),
    ]

    minimum_latency: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinimumLatency',
            description='The preferred latency (in milliseconds) for implementing packet loss and recovery. Packet recovery is a key feature of SRT.',
        ),
    ]

    srt_listener_address: Annotated[
        Optional[str],
        Field(
            None,
            alias='SrtListenerAddress',
            description='The IP address at the upstream system (the listener) that MediaLive (the caller) connects to.',
        ),
    ]

    srt_listener_port: Annotated[
        Optional[str],
        Field(
            None,
            alias='SrtListenerPort',
            description='The port at the upstream system (the listener) that MediaLive (the caller) connects to.',
        ),
    ]

    stream_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='StreamId',
            description='The stream ID, if the upstream system uses this identifier.',
        ),
    ]


class SrtCallerSourceRequest(BaseModel):
    """Configures the connection for a source that uses SRT as the connection protocol. In terms of establishing the connection, MediaLive is always the caller and the upstream system is always the listener. In terms of transmission of the source content, MediaLive is always the receiver and the upstream s."""

    model_config = ConfigDict(populate_by_name=True)

    decryption: Annotated[
        Optional[SrtCallerDecryptionRequest],
        Field(
            None,
            alias='Decryption',
            description='',
        ),
    ]

    minimum_latency: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinimumLatency',
            description='The preferred latency (in milliseconds) for implementing packet loss and recovery. Packet recovery is a key feature of SRT. Obtain this value from the operator at the upstream system.',
        ),
    ]

    srt_listener_address: Annotated[
        Optional[str],
        Field(
            None,
            alias='SrtListenerAddress',
            description='The IP address at the upstream system (the listener) that MediaLive (the caller) will connect to.',
        ),
    ]

    srt_listener_port: Annotated[
        Optional[str],
        Field(
            None,
            alias='SrtListenerPort',
            description='The port at the upstream system (the listener) that MediaLive (the caller) will connect to.',
        ),
    ]

    stream_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='StreamId',
            description='This value is required if the upstream system uses this identifier because without it, the SRT handshake between MediaLive (the caller) and the upstream system (the listener) might fail.',
        ),
    ]


class SrtGroupSettings(BaseModel):
    """Srt Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    input_loss_action: Annotated[
        Optional[InputLossActionForUdpOut],
        Field(
            None,
            alias='InputLossAction',
            description='Specifies behavior of last resort when input video is lost, and no more backup inputs are available. When dropTs is selected the entire transport stream will stop being emitted. When dropProgram is selected the program can be dropped from the transport stream (and replaced with null packets to meet the TS bitrate requirement). Or, when emitProgram is chosen the transport stream will continue to be produced normally with repeat frames, black frames, or slate frames substituted for the absent input video.',
        ),
    ]


class SrtOutputDestinationSettings(BaseModel):
    """Placeholder documentation for SrtOutputDestinationSettings."""

    model_config = ConfigDict(populate_by_name=True)

    encryption_passphrase_secret_arn: Annotated[
        Optional[str],
        Field(
            None,
            alias='EncryptionPassphraseSecretArn',
            description='Arn used to extract the password from Secrets Manager',
        ),
    ]

    stream_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='StreamId',
            description='Stream id for SRT destinations (URLs of type srt://)',
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


class SrtSettings(BaseModel):
    """The configured sources for this SRT input."""

    model_config = ConfigDict(populate_by_name=True)

    srt_caller_sources: Annotated[
        Optional[list[SrtCallerSource]],
        Field(
            None,
            alias='SrtCallerSources',
            description='',
        ),
    ]


class Input(BaseModel):
    """Placeholder documentation for Input."""

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


class SrtSettingsRequest(BaseModel):
    """Configures the sources for this SRT input. For a single-pipeline input, include one srtCallerSource in the array. For a standard-pipeline input, include two srtCallerSource."""

    model_config = ConfigDict(populate_by_name=True)

    srt_caller_sources: Annotated[
        Optional[list[SrtCallerSourceRequest]],
        Field(
            None,
            alias='SrtCallerSources',
            description='',
        ),
    ]


class HlsSettings(BaseModel):
    """Hls Settings."""

    model_config = ConfigDict(populate_by_name=True)

    audio_only_hls_settings: Annotated[
        Optional[AudioOnlyHlsSettings],
        Field(
            None,
            alias='AudioOnlyHlsSettings',
            description='',
        ),
    ]

    fmp4_hls_settings: Annotated[
        Optional[Fmp4HlsSettings],
        Field(
            None,
            alias='Fmp4HlsSettings',
            description='',
        ),
    ]

    frame_capture_hls_settings: Annotated[
        Optional[FrameCaptureHlsSettings],
        Field(
            None,
            alias='FrameCaptureHlsSettings',
            description='',
        ),
    ]

    standard_hls_settings: Annotated[
        Optional[StandardHlsSettings],
        Field(
            None,
            alias='StandardHlsSettings',
            description='',
        ),
    ]


class HlsOutputSettings(BaseModel):
    """Hls Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    h265_packaging_type: Annotated[
        Optional[HlsH265PackagingType],
        Field(
            None,
            alias='H265PackagingType',
            description='Only applicable when this output is referencing an H.265 video description. Specifies whether MP4 segments should be packaged as HEV1 or HVC1.',
        ),
    ]

    hls_settings: Annotated[
        HlsSettings,
        Field(
            ...,
            alias='HlsSettings',
            description='Settings regarding the underlying stream. These settings are different for audio-only outputs.',
        ),
    ]

    name_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='NameModifier',
            description='String concatenated to the end of the destination filename. Accepts \\"Format Identifiers\\":#formatIdentifierParameters.',
        ),
    ]

    segment_modifier: Annotated[
        Optional[str],
        Field(
            None,
            alias='SegmentModifier',
            description='String concatenated to end of segment filenames.',
        ),
    ]


class HlsGroupSettings(BaseModel):
    """Hls Group Settings."""

    model_config = ConfigDict(populate_by_name=True)

    ad_markers: Annotated[
        Optional[list[HlsAdMarkers]],
        Field(
            None,
            alias='AdMarkers',
            description='Choose one or more ad marker types to pass SCTE35 signals through to this group of Apple HLS outputs.',
        ),
    ]

    base_url_content: Annotated[
        Optional[str],
        Field(
            None,
            alias='BaseUrlContent',
            description='A partial URI prefix that will be prepended to each output in the media .m3u8 file. Can be used if base manifest is delivered from a different URL than the main .m3u8 file.',
        ),
    ]

    base_url_content1: Annotated[
        Optional[str],
        Field(
            None,
            alias='BaseUrlContent1',
            description='Optional. One value per output group. This field is required only if you are completing Base URL content A, and the downstream system has notified you that the media files for pipeline 1 of all outputs are in a location different from the media files for pipeline 0.',
        ),
    ]

    base_url_manifest: Annotated[
        Optional[str],
        Field(
            None,
            alias='BaseUrlManifest',
            description='A partial URI prefix that will be prepended to each output in the media .m3u8 file. Can be used if base manifest is delivered from a different URL than the main .m3u8 file.',
        ),
    ]

    base_url_manifest1: Annotated[
        Optional[str],
        Field(
            None,
            alias='BaseUrlManifest1',
            description='Optional. One value per output group. Complete this field only if you are completing Base URL manifest A, and the downstream system has notified you that the child manifest files for pipeline 1 of all outputs are in a location different from the child manifest files for pipeline 0.',
        ),
    ]

    caption_language_mappings: Annotated[
        Optional[list[CaptionLanguageMapping]],
        Field(
            None,
            alias='CaptionLanguageMappings',
            description='Mapping of up to 4 caption channels to caption languages. Is only meaningful if captionLanguageSetting is set to "insert".',
        ),
    ]

    caption_language_setting: Annotated[
        Optional[HlsCaptionLanguageSetting],
        Field(
            None,
            alias='CaptionLanguageSetting',
            description='Applies only to 608 Embedded output captions. insert: Include CLOSED-CAPTIONS lines in the manifest. Specify at least one language in the CC1 Language Code field. One CLOSED-CAPTION line is added for each Language Code you specify. Make sure to specify the languages in the order in which they appear in the original source (if the source is embedded format) or the order of the caption selectors (if the source is other than embedded). Otherwise, languages in the manifest will not match up properly with the output captions. none: Include CLOSED-CAPTIONS=NONE line in the manifest. omit: Omit any CLOSED-CAPTIONS line from the manifest.',
        ),
    ]

    client_cache: Annotated[
        Optional[HlsClientCache],
        Field(
            None,
            alias='ClientCache',
            description='When set to "disabled", sets the #EXT-X-ALLOW-CACHE:no tag in the manifest, which prevents clients from saving media segments for later replay.',
        ),
    ]

    codec_specification: Annotated[
        Optional[HlsCodecSpecification],
        Field(
            None,
            alias='CodecSpecification',
            description='Specification to use (RFC-6381 or the default RFC-4281) during m3u8 playlist generation.',
        ),
    ]

    constant_iv: Annotated[
        Optional[str],
        Field(
            None,
            alias='ConstantIv',
            description='For use with encryptionType. This is a 128-bit, 16-byte hex value represented by a 32-character text string. If ivSource is set to "explicit" then this parameter is required and is used as the IV for encryption.',
        ),
    ]

    destination: Annotated[
        OutputLocationRef,
        Field(
            ...,
            alias='Destination',
            description='A directory or HTTP destination for the HLS segments, manifest files, and encryption keys (if enabled).',
        ),
    ]

    directory_structure: Annotated[
        Optional[HlsDirectoryStructure],
        Field(
            None,
            alias='DirectoryStructure',
            description='Place segments in subdirectories.',
        ),
    ]

    discontinuity_tags: Annotated[
        Optional[HlsDiscontinuityTags],
        Field(
            None,
            alias='DiscontinuityTags',
            description='Specifies whether to insert EXT-X-DISCONTINUITY tags in the HLS child manifests for this output group. Typically, choose Insert because these tags are required in the manifest (according to the HLS specification) and serve an important purpose. Choose Never Insert only if the downstream system is doing real-time failover (without using the MediaLive automatic failover feature) and only if that downstream system has advised you to exclude the tags.',
        ),
    ]

    encryption_type: Annotated[
        Optional[HlsEncryptionType],
        Field(
            None,
            alias='EncryptionType',
            description='Encrypts the segments with the given encryption scheme. Exclude this parameter if no encryption is desired.',
        ),
    ]

    hls_cdn_settings: Annotated[
        Optional[HlsCdnSettings],
        Field(
            None,
            alias='HlsCdnSettings',
            description='Parameters that control interactions with the CDN.',
        ),
    ]

    hls_id3_segment_tagging: Annotated[
        Optional[HlsId3SegmentTaggingState],
        Field(
            None,
            alias='HlsId3SegmentTagging',
            description='State of HLS ID3 Segment Tagging',
        ),
    ]

    i_frame_only_playlists: Annotated[
        Optional[IFrameOnlyPlaylistType],
        Field(
            None,
            alias='IFrameOnlyPlaylists',
            description='DISABLED: Do not create an I-frame-only manifest, but do create the master and media manifests (according to the Output Selection field). STANDARD: Create an I-frame-only manifest for each output that contains video, as well as the other manifests (according to the Output Selection field). The I-frame manifest contains a #EXT-X-I-FRAMES-ONLY tag to indicate it is I-frame only, and one or more #EXT-X-BYTERANGE entries identifying the I-frame position. For example, #EXT-X-BYTERANGE:160364@1461888"',
        ),
    ]

    incomplete_segment_behavior: Annotated[
        Optional[HlsIncompleteSegmentBehavior],
        Field(
            None,
            alias='IncompleteSegmentBehavior',
            description='Specifies whether to include the final (incomplete) segment in the media output when the pipeline stops producing output because of a channel stop, a channel pause or a loss of input to the pipeline. Auto means that MediaLive decides whether to include the final segment, depending on the channel class and the types of output groups. Suppress means to never include the incomplete segment. We recommend you choose Auto and let MediaLive control the behavior.',
        ),
    ]

    index_n_segments: Annotated[
        Optional[int],
        Field(
            None,
            alias='IndexNSegments',
            description='Applies only if Mode field is LIVE. Specifies the maximum number of segments in the media manifest file. After this maximum, older segments are removed from the media manifest. This number must be smaller than the number in the Keep Segments field.',
        ),
    ]

    input_loss_action: Annotated[
        Optional[InputLossActionForHlsOut],
        Field(
            None,
            alias='InputLossAction',
            description='Parameter that control output group behavior on input loss.',
        ),
    ]

    iv_in_manifest: Annotated[
        Optional[HlsIvInManifest],
        Field(
            None,
            alias='IvInManifest',
            description='For use with encryptionType. The IV (Initialization Vector) is a 128-bit number used in conjunction with the key for encrypting blocks. If set to "include", IV is listed in the manifest, otherwise the IV is not in the manifest.',
        ),
    ]

    iv_source: Annotated[
        Optional[HlsIvSource],
        Field(
            None,
            alias='IvSource',
            description='For use with encryptionType. The IV (Initialization Vector) is a 128-bit number used in conjunction with the key for encrypting blocks. If this setting is "followsSegmentNumber", it will cause the IV to change every segment (to match the segment number). If this is set to "explicit", you must enter a constantIv value.',
        ),
    ]

    keep_segments: Annotated[
        Optional[int],
        Field(
            None,
            alias='KeepSegments',
            description='Applies only if Mode field is LIVE. Specifies the number of media segments to retain in the destination directory. This number should be bigger than indexNSegments (Num segments). We recommend (value = (2 x indexNsegments) + 1). If this "keep segments" number is too low, the following might happen: the player is still reading a media manifest file that lists this segment, but that segment has been removed from the destination directory (as directed by indexNSegments). This situation would result in a 404 HTTP error on the player.',
        ),
    ]

    key_format: Annotated[
        Optional[str],
        Field(
            None,
            alias='KeyFormat',
            description='The value specifies how the key is represented in the resource identified by the URI. If parameter is absent, an implicit value of "identity" is used. A reverse DNS string can also be given.',
        ),
    ]

    key_format_versions: Annotated[
        Optional[str],
        Field(
            None,
            alias='KeyFormatVersions',
            description='Either a single positive integer version value or a slash delimited list of version values (1/2/3).',
        ),
    ]

    key_provider_settings: Annotated[
        Optional[KeyProviderSettings],
        Field(
            None,
            alias='KeyProviderSettings',
            description='The key provider settings.',
        ),
    ]

    manifest_compression: Annotated[
        Optional[HlsManifestCompression],
        Field(
            None,
            alias='ManifestCompression',
            description='When set to gzip, compresses HLS playlist.',
        ),
    ]

    manifest_duration_format: Annotated[
        Optional[HlsManifestDurationFormat],
        Field(
            None,
            alias='ManifestDurationFormat',
            description='Indicates whether the output manifest should use floating point or integer values for segment duration.',
        ),
    ]

    min_segment_length: Annotated[
        Optional[int],
        Field(
            None,
            alias='MinSegmentLength',
            description='Minimum length of MPEG-2 Transport Stream segments in seconds. When set, minimum segment length is enforced by looking ahead and back within the specified range for a nearby avail and extending the segment size if needed.',
        ),
    ]

    mode: Annotated[
        Optional[HlsMode],
        Field(
            None,
            alias='Mode',
            description='If "vod", all segments are indexed and kept permanently in the destination and manifest. If "live", only the number segments specified in keepSegments and indexNSegments are kept; newer segments replace older segments, which may prevent players from rewinding all the way to the beginning of the event. VOD mode uses HLS EXT-X-PLAYLIST-TYPE of EVENT while the channel is running, converting it to a "VOD" type manifest on completion of the stream.',
        ),
    ]

    output_selection: Annotated[
        Optional[HlsOutputSelection],
        Field(
            None,
            alias='OutputSelection',
            description='MANIFESTS_AND_SEGMENTS: Generates manifests (master manifest, if applicable, and media manifests) for this output group. VARIANT_MANIFESTS_AND_SEGMENTS: Generates media manifests for this output group, but not a master manifest. SEGMENTS_ONLY: Does not generate any manifests for this output group.',
        ),
    ]

    program_date_time: Annotated[
        Optional[HlsProgramDateTime],
        Field(
            None,
            alias='ProgramDateTime',
            description='Includes or excludes EXT-X-PROGRAM-DATE-TIME tag in .m3u8 manifest files. The value is calculated using the program date time clock.',
        ),
    ]

    program_date_time_clock: Annotated[
        Optional[HlsProgramDateTimeClock],
        Field(
            None,
            alias='ProgramDateTimeClock',
            description='Specifies the algorithm used to drive the HLS EXT-X-PROGRAM-DATE-TIME clock. Options include: INITIALIZE_FROM_OUTPUT_TIMECODE: The PDT clock is initialized as a function of the first output timecode, then incremented by the EXTINF duration of each encoded segment. SYSTEM_CLOCK: The PDT clock is initialized as a function of the UTC wall clock, then incremented by the EXTINF duration of each encoded segment. If the PDT clock diverges from the wall clock by more than 500ms, it is resynchronized to the wall clock.',
        ),
    ]

    program_date_time_period: Annotated[
        Optional[int],
        Field(
            None,
            alias='ProgramDateTimePeriod',
            description='Period of insertion of EXT-X-PROGRAM-DATE-TIME entry, in seconds.',
        ),
    ]

    redundant_manifest: Annotated[
        Optional[HlsRedundantManifest],
        Field(
            None,
            alias='RedundantManifest',
            description='ENABLED: The master manifest (.m3u8 file) for each pipeline includes information about both pipelines: first its own media files, then the media files of the other pipeline. This feature allows playout device that support stale manifest detection to switch from one manifest to the other, when the current manifest seems to be stale. There are still two destinations and two master manifests, but both master manifests reference the media files from both pipelines. DISABLED: The master manifest (.m3u8 file) for each pipeline includes information about its own pipeline only. For an HLS output group with MediaPackage as the destination, the DISABLED behavior is always followed. MediaPackage regenerates the manifests it serves to players so a redundant manifest from MediaLive is irrelevant.',
        ),
    ]

    segment_length: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentLength',
            description='Length of MPEG-2 Transport Stream segments to create in seconds. Note that segments will end on the next keyframe after this duration, so actual segment length may be longer.',
        ),
    ]

    segmentation_mode: Annotated[
        Optional[HlsSegmentationMode],
        Field(
            None,
            alias='SegmentationMode',
            description='useInputSegmentation has been deprecated. The configured segment size is always used.',
        ),
    ]

    segments_per_subdirectory: Annotated[
        Optional[int],
        Field(
            None,
            alias='SegmentsPerSubdirectory',
            description='Number of segments to write to a subdirectory before starting a new one. directoryStructure must be subdirectoryPerStream for this setting to have an effect.',
        ),
    ]

    stream_inf_resolution: Annotated[
        Optional[HlsStreamInfResolution],
        Field(
            None,
            alias='StreamInfResolution',
            description='Include or exclude RESOLUTION attribute for video in EXT-X-STREAM-INF tag of variant manifest.',
        ),
    ]

    timed_metadata_id3_frame: Annotated[
        Optional[HlsTimedMetadataId3Frame],
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

    timestamp_delta_milliseconds: Annotated[
        Optional[int],
        Field(
            None,
            alias='TimestampDeltaMilliseconds',
            description='Provides an extra millisecond delta offset to fine tune the timestamps.',
        ),
    ]

    ts_file_mode: Annotated[
        Optional[HlsTsFileMode],
        Field(
            None,
            alias='TsFileMode',
            description='SEGMENTED_FILES: Emit the program as segments - multiple .ts media files. SINGLE_FILE: Applies only if Mode field is VOD. Emit the program as a single .ts media file. The media manifest includes #EXT-X-BYTERANGE tags to index segments for playback. A typical use for this value is when sending the output to AWS Elemental MediaConvert, which can accept only a single media file. Playback while the channel is running is not guaranteed due to HTTP server caching.',
        ),
    ]


class InputClippingSettings(BaseModel):
    """Settings to let you create a clip of the file input, in order to set up the input to ingest only a portion of the file."""

    model_config = ConfigDict(populate_by_name=True)

    input_timecode_source: Annotated[
        InputTimecodeSource,
        Field(
            ...,
            alias='InputTimecodeSource',
            description='The source of the timecodes in the source being clipped.',
        ),
    ]

    start_timecode: Annotated[
        Optional[StartTimecode],
        Field(
            None,
            alias='StartTimecode',
            description='Settings to identify the start of the clip.',
        ),
    ]

    stop_timecode: Annotated[
        Optional[StopTimecode],
        Field(
            None,
            alias='StopTimecode',
            description='Settings to identify the end of the clip.',
        ),
    ]


class InputPrepareScheduleActionSettings(BaseModel):
    """Action to prepare an input for a future immediate input switch."""

    model_config = ConfigDict(populate_by_name=True)

    input_attachment_name_reference: Annotated[
        Optional[str],
        Field(
            None,
            alias='InputAttachmentNameReference',
            description='The name of the input attachment that should be prepared by this action. If no name is provided, the action will stop the most recent prepare (if any) when activated.',
        ),
    ]

    input_clipping_settings: Annotated[
        Optional[InputClippingSettings],
        Field(
            None,
            alias='InputClippingSettings',
            description='Settings to let you create a clip of the file input, in order to set up the input to ingest only a portion of the file.',
        ),
    ]

    url_path: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='UrlPath',
            description='The value for the variable portion of the URL for the dynamic input, for this instance of the input. Each time you use the same dynamic input in an input switch action, you can provide a different value, in order to connect the input to a different content source.',
        ),
    ]


class InputSwitchScheduleActionSettings(BaseModel):
    """Settings for the "switch input" action: to switch from ingesting one input to ingesting another input."""

    model_config = ConfigDict(populate_by_name=True)

    input_attachment_name_reference: Annotated[
        str,
        Field(
            ...,
            alias='InputAttachmentNameReference',
            description='The name of the input attachment (not the name of the input!) to switch to. The name is specified in the channel configuration.',
        ),
    ]

    input_clipping_settings: Annotated[
        Optional[InputClippingSettings],
        Field(
            None,
            alias='InputClippingSettings',
            description='Settings to let you create a clip of the file input, in order to set up the input to ingest only a portion of the file.',
        ),
    ]

    url_path: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='UrlPath',
            description='The value for the variable portion of the URL for the dynamic input, for this instance of the input. Each time you use the same dynamic input in an input switch action, you can provide a different value, in order to connect the input to a different content source.',
        ),
    ]


class SrtOutputSettings(BaseModel):
    """Srt Output Settings."""

    model_config = ConfigDict(populate_by_name=True)

    buffer_msec: Annotated[
        Optional[int],
        Field(
            None,
            alias='BufferMsec',
            description='SRT output buffering in milliseconds. A higher value increases latency through the encoder. But the benefits are that it helps to maintain a constant, low-jitter SRT output, and it accommodates clock recovery, input switching, input disruptions, picture reordering, and so on. Range: 0-10000 milliseconds.',
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
            description='',
        ),
    ]

    encryption_type: Annotated[
        Optional[SrtEncryptionType],
        Field(
            None,
            alias='EncryptionType',
            description='The encryption level for the content. Valid values are AES128, AES192, AES256. You and the downstream system should plan how to set this field because the values must not conflict with each other.',
        ),
    ]

    latency: Annotated[
        Optional[int],
        Field(
            None,
            alias='Latency',
            description='The latency value, in milliseconds, that is proposed during the SRT connection handshake. SRT will choose the maximum of the values proposed by the sender and receiver. On the sender side, latency is the amount of time a packet is held to give it a chance to be delivered successfully. On the receiver side, latency is the amount of time the packet is held before delivering to the application, aiding in packet recovery and matching as closely as possible the packet timing of the sender. Range: 40-16000 milliseconds.',
        ),
    ]


class InputDeviceConfigurationValidationError(BaseModel):
    """Placeholder documentation for InputDeviceConfigurationValidationError."""

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


class VideoBlackFailoverSettings(BaseModel):
    """Placeholder documentation for VideoBlackFailoverSettings."""

    model_config = ConfigDict(populate_by_name=True)

    black_detect_threshold: Annotated[
        Optional[float],
        Field(
            None,
            alias='BlackDetectThreshold',
            description='A value used in calculating the threshold below which MediaLive considers a pixel to be \u0027black\u0027. For the input to be considered black, every pixel in a frame must be below this threshold. The threshold is calculated as a percentage (expressed as a decimal) of white. Therefore .1 means 10% white (or 90% black). Note how the formula works for any color depth. For example, if you set this field to 0.1 in 10-bit color depth: (1023*0.1=102.3), which means a pixel value of 102 or less is \u0027black\u0027. If you set this field to .1 in an 8-bit color depth: (255*0.1=25.5), which means a pixel value of 25 or less is \u0027black\u0027. The range is 0.0 to 1.0, with any number of decimal places.',
        ),
    ]

    video_black_threshold_msec: Annotated[
        Optional[int],
        Field(
            None,
            alias='VideoBlackThresholdMsec',
            description='The amount of time (in milliseconds) that the active input must be black before automatic input failover occurs.',
        ),
    ]


class FailoverConditionSettings(BaseModel):
    """Settings for one failover condition."""

    model_config = ConfigDict(populate_by_name=True)

    audio_silence_settings: Annotated[
        Optional[AudioSilenceFailoverSettings],
        Field(
            None,
            alias='AudioSilenceSettings',
            description='MediaLive will perform a failover if the specified audio selector is silent for the specified period.',
        ),
    ]

    input_loss_settings: Annotated[
        Optional[InputLossFailoverSettings],
        Field(
            None,
            alias='InputLossSettings',
            description='MediaLive will perform a failover if content is not detected in this input for the specified period.',
        ),
    ]

    video_black_settings: Annotated[
        Optional[VideoBlackFailoverSettings],
        Field(
            None,
            alias='VideoBlackSettings',
            description='MediaLive will perform a failover if content is considered black for the specified period.',
        ),
    ]


class FailoverCondition(BaseModel):
    """Failover Condition settings. There can be multiple failover conditions inside AutomaticInputFailoverSettings."""

    model_config = ConfigDict(populate_by_name=True)

    failover_condition_settings: Annotated[
        Optional[FailoverConditionSettings],
        Field(
            None,
            alias='FailoverConditionSettings',
            description='Failover condition type-specific settings.',
        ),
    ]


class AutomaticInputFailoverSettings(BaseModel):
    """The settings for Automatic Input Failover."""

    model_config = ConfigDict(populate_by_name=True)

    error_clear_time_msec: Annotated[
        Optional[int],
        Field(
            None,
            alias='ErrorClearTimeMsec',
            description='This clear time defines the requirement a recovered input must meet to be considered healthy. The input must have no failover conditions for this length of time. Enter a time in milliseconds. This value is particularly important if the input_preference for the failover pair is set to PRIMARY_INPUT_PREFERRED, because after this time, MediaLive will switch back to the primary input.',
        ),
    ]

    failover_conditions: Annotated[
        Optional[list[FailoverCondition]],
        Field(
            None,
            alias='FailoverConditions',
            description='A list of failover conditions. If any of these conditions occur, MediaLive will perform a failover to the other input.',
        ),
    ]

    input_preference: Annotated[
        Optional[InputPreference],
        Field(
            None,
            alias='InputPreference',
            description='Input preference when deciding which input to make active when a previously failed input has recovered.',
        ),
    ]

    secondary_input_id: Annotated[
        str,
        Field(
            ...,
            alias='SecondaryInputId',
            description='The input ID of the secondary input in the automatic input failover pair.',
        ),
    ]


class InputSettings(BaseModel):
    """Live Event input parameters. There can be multiple inputs in a single Live Event."""

    model_config = ConfigDict(populate_by_name=True)

    audio_selectors: Annotated[
        Optional[list[AudioSelector]],
        Field(
            None,
            alias='AudioSelectors',
            description='Used to select the audio stream to decode for inputs that have multiple available.',
        ),
    ]

    caption_selectors: Annotated[
        Optional[list[CaptionSelector]],
        Field(
            None,
            alias='CaptionSelectors',
            description='Used to select the caption input to use for inputs that have multiple available.',
        ),
    ]

    deblock_filter: Annotated[
        Optional[InputDeblockFilter],
        Field(
            None,
            alias='DeblockFilter',
            description='Enable or disable the deblock filter when filtering.',
        ),
    ]

    denoise_filter: Annotated[
        Optional[InputDenoiseFilter],
        Field(
            None,
            alias='DenoiseFilter',
            description='Enable or disable the denoise filter when filtering.',
        ),
    ]

    filter_strength: Annotated[
        Optional[int],
        Field(
            None,
            alias='FilterStrength',
            description='Adjusts the magnitude of filtering from 1 (minimal) to 5 (strongest).',
        ),
    ]

    input_filter: Annotated[
        Optional[InputFilter],
        Field(
            None,
            alias='InputFilter',
            description='Turns on the filter for this input. MPEG-2 inputs have the deblocking filter enabled by default. 1) auto - filtering will be applied depending on input type/quality 2) disabled - no filtering will be applied to the input 3) forced - filtering will be applied regardless of input type',
        ),
    ]

    network_input_settings: Annotated[
        Optional[NetworkInputSettings],
        Field(
            None,
            alias='NetworkInputSettings',
            description='Input settings.',
        ),
    ]

    scte35_pid: Annotated[
        Optional[int],
        Field(
            None,
            alias='Scte35Pid',
            description='PID from which to read SCTE-35 messages. If left undefined, EML will select the first SCTE-35 PID found in the input.',
        ),
    ]

    smpte2038_data_preference: Annotated[
        Optional[Smpte2038DataPreference],
        Field(
            None,
            alias='Smpte2038DataPreference',
            description='Specifies whether to extract applicable ancillary data from a SMPTE-2038 source in this input. Applicable data types are captions, timecode, AFD, and SCTE-104 messages. - PREFER: Extract from SMPTE-2038 if present in this input, otherwise extract from another source (if any). - IGNORE: Never extract any ancillary data from SMPTE-2038.',
        ),
    ]

    source_end_behavior: Annotated[
        Optional[InputSourceEndBehavior],
        Field(
            None,
            alias='SourceEndBehavior',
            description='Loop input if it is a file. This allows a file input to be streamed indefinitely.',
        ),
    ]

    video_selector: Annotated[
        Optional[VideoSelector],
        Field(
            None,
            alias='VideoSelector',
            description='Informs which video elementary stream to decode for input types that have multiple available.',
        ),
    ]


class InputAttachment(BaseModel):
    """Placeholder documentation for InputAttachment."""

    model_config = ConfigDict(populate_by_name=True)

    automatic_input_failover_settings: Annotated[
        Optional[AutomaticInputFailoverSettings],
        Field(
            None,
            alias='AutomaticInputFailoverSettings',
            description='User-specified settings for defining what the conditions are for declaring the input unhealthy and failing over to a different input.',
        ),
    ]

    input_attachment_name: Annotated[
        Optional[str],
        Field(
            None,
            alias='InputAttachmentName',
            description='User-specified name for the attachment. This is required if the user wants to use this input in an input switch action.',
        ),
    ]

    input_id: Annotated[
        Optional[str],
        Field(
            None,
            alias='InputId',
            description='The ID of the input',
        ),
    ]

    input_settings: Annotated[
        Optional[InputSettings],
        Field(
            None,
            alias='InputSettings',
            description='Settings of an input (caption selector, etc.)',
        ),
    ]

    logical_interface_names: Annotated[
        Optional[list[str]],
        Field(
            None,
            alias='LogicalInterfaceNames',
            description='Optional assignment of an input to a logical interface on the Node. Only applies to on premises channels.',
        ),
    ]
