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


"""Auto-generated boto3 client wrapper.

DO NOT EDIT — regenerate with: python src/codegen/generate.py mediapackagev2
"""

import boto3
from loguru import logger
from typing import Any, Dict, Optional


class mediapackagev2Client:
    """Wrapper around boto3 mediapackagev2 client."""

    def __init__(self, region_name: str = 'us-east-1', profile_name: Optional[str] = None):
        """Initialize the client."""
        session = boto3.Session(region_name=region_name, profile_name=profile_name)
        self._client = session.client('mediapackagev2')
        logger.info(f'Initialized mediapackagev2 client for region {region_name}')

    async def cancel_harvest_job(self, **kwargs) -> Dict[str, Any]:
        """Cancels an in-progress harvest job."""
        logger.info('Calling CancelHarvestJob')
        response = self._client.cancel_harvest_job(**kwargs)
        return response

    async def create_channel(self, **kwargs) -> Dict[str, Any]:
        """Create a channel to start receiving content streams. The channel represents the input to MediaPackage for incoming live content from an encoder such as AWS Elemental MediaLive. The channel receives content, and after packaging it, outputs it through an origin endpoint to downstream devices (such as video players or CDNs) that request the content. You can create only one channel with each request. We recommend that you spread out channels between channel groups, such as putting redundant channels in the same AWS Region in different channel groups."""
        logger.info('Calling CreateChannel')
        response = self._client.create_channel(**kwargs)
        return response

    async def create_channel_group(self, **kwargs) -> Dict[str, Any]:
        """Create a channel group to group your channels and origin endpoints. A channel group is the top-level resource that consists of channels and origin endpoints that are associated with it and that provides predictable URLs for stream delivery. All channels and origin endpoints within the channel group are guaranteed to share the DNS. You can create only one channel group with each request."""
        logger.info('Calling CreateChannelGroup')
        response = self._client.create_channel_group(**kwargs)
        return response

    async def create_harvest_job(self, **kwargs) -> Dict[str, Any]:
        """Creates a new harvest job to export content from a MediaPackage v2 channel to an S3 bucket."""
        logger.info('Calling CreateHarvestJob')
        response = self._client.create_harvest_job(**kwargs)
        return response

    async def create_origin_endpoint(self, **kwargs) -> Dict[str, Any]:
        """The endpoint is attached to a channel, and represents the output of the live content. You can associate multiple endpoints to a single channel. Each endpoint gives players and downstream CDNs (such as Amazon CloudFront) access to the content for playback. Content can't be served from a channel until it has an endpoint. You can create only one endpoint with each request."""
        logger.info('Calling CreateOriginEndpoint')
        response = self._client.create_origin_endpoint(**kwargs)
        return response

    async def delete_channel(self, **kwargs) -> Dict[str, Any]:
        """Delete a channel to stop AWS Elemental MediaPackage from receiving further content. You must delete the channel's origin endpoints before you can delete the channel."""
        logger.info('Calling DeleteChannel')
        response = self._client.delete_channel(**kwargs)
        return response

    async def delete_channel_group(self, **kwargs) -> Dict[str, Any]:
        """Delete a channel group. You must delete the channel group's channels and origin endpoints before you can delete the channel group. If you delete a channel group, you'll lose access to the egress domain and will have to create a new channel group to replace it."""
        logger.info('Calling DeleteChannelGroup')
        response = self._client.delete_channel_group(**kwargs)
        return response

    async def delete_channel_policy(self, **kwargs) -> Dict[str, Any]:
        """Delete a channel policy."""
        logger.info('Calling DeleteChannelPolicy')
        response = self._client.delete_channel_policy(**kwargs)
        return response

    async def delete_origin_endpoint(self, **kwargs) -> Dict[str, Any]:
        """Origin endpoints can serve content until they're deleted. Delete the endpoint if it should no longer respond to playback requests. You must delete all endpoints from a channel before you can delete the channel."""
        logger.info('Calling DeleteOriginEndpoint')
        response = self._client.delete_origin_endpoint(**kwargs)
        return response

    async def delete_origin_endpoint_policy(self, **kwargs) -> Dict[str, Any]:
        """Delete an origin endpoint policy."""
        logger.info('Calling DeleteOriginEndpointPolicy')
        response = self._client.delete_origin_endpoint_policy(**kwargs)
        return response

    async def get_channel(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified channel that's configured in AWS Elemental MediaPackage."""
        logger.info('Calling GetChannel')
        response = self._client.get_channel(**kwargs)
        return response

    async def get_channel_group(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified channel group that's configured in AWS Elemental MediaPackage."""
        logger.info('Calling GetChannelGroup')
        response = self._client.get_channel_group(**kwargs)
        return response

    async def get_channel_policy(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified channel policy that's configured in AWS Elemental MediaPackage. With policies, you can specify who has access to AWS resources and what actions they can perform on those resources."""
        logger.info('Calling GetChannelPolicy')
        response = self._client.get_channel_policy(**kwargs)
        return response

    async def get_harvest_job(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the details of a specific harvest job."""
        logger.info('Calling GetHarvestJob')
        response = self._client.get_harvest_job(**kwargs)
        return response

    async def get_origin_endpoint(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified origin endpoint that's configured in AWS Elemental MediaPackage to obtain its playback URL and to view the packaging settings that it's currently using."""
        logger.info('Calling GetOriginEndpoint')
        response = self._client.get_origin_endpoint(**kwargs)
        return response

    async def get_origin_endpoint_policy(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified origin endpoint policy that's configured in AWS Elemental MediaPackage."""
        logger.info('Calling GetOriginEndpointPolicy')
        response = self._client.get_origin_endpoint_policy(**kwargs)
        return response

    async def list_channel_groups(self, **kwargs) -> Dict[str, Any]:
        """Retrieves all channel groups that are configured in Elemental MediaPackage."""
        logger.info('Calling ListChannelGroups')
        response = self._client.list_channel_groups(**kwargs)
        return response

    async def list_channels(self, **kwargs) -> Dict[str, Any]:
        """Retrieves all channels in a specific channel group that are configured in AWS Elemental MediaPackage."""
        logger.info('Calling ListChannels')
        response = self._client.list_channels(**kwargs)
        return response

    async def list_harvest_jobs(self, **kwargs) -> Dict[str, Any]:
        """Retrieves a list of harvest jobs that match the specified criteria."""
        logger.info('Calling ListHarvestJobs')
        response = self._client.list_harvest_jobs(**kwargs)
        return response

    async def list_origin_endpoints(self, **kwargs) -> Dict[str, Any]:
        """Retrieves all origin endpoints in a specific channel that are configured in AWS Elemental MediaPackage."""
        logger.info('Calling ListOriginEndpoints')
        response = self._client.list_origin_endpoints(**kwargs)
        return response

    async def list_tags_for_resource(self, **kwargs) -> Dict[str, Any]:
        """Lists the tags assigned to a resource."""
        logger.info('Calling ListTagsForResource')
        response = self._client.list_tags_for_resource(**kwargs)
        return response

    async def put_channel_policy(self, **kwargs) -> Dict[str, Any]:
        """Attaches an IAM policy to the specified channel. With policies, you can specify who has access to AWS resources and what actions they can perform on those resources. You can attach only one policy with each request."""
        logger.info('Calling PutChannelPolicy')
        response = self._client.put_channel_policy(**kwargs)
        return response

    async def put_origin_endpoint_policy(self, **kwargs) -> Dict[str, Any]:
        """Attaches an IAM policy to the specified origin endpoint. You can attach only one policy with each request."""
        logger.info('Calling PutOriginEndpointPolicy')
        response = self._client.put_origin_endpoint_policy(**kwargs)
        return response

    async def reset_channel_state(self, **kwargs) -> Dict[str, Any]:
        """Resetting the channel can help to clear errors from misconfigurations in the encoder. A reset refreshes the ingest stream and removes previous content.   Be sure to stop the encoder before you reset the channel, and wait at least 30 seconds before you restart the encoder."""
        logger.info('Calling ResetChannelState')
        response = self._client.reset_channel_state(**kwargs)
        return response

    async def reset_origin_endpoint_state(self, **kwargs) -> Dict[str, Any]:
        """Resetting the origin endpoint can help to resolve unexpected behavior and other content packaging issues. It also helps to preserve special events when you don't want the previous content to be available for viewing. A reset clears out all previous content from the origin endpoint. MediaPackage might return old content from this endpoint in the first 30 seconds after the endpoint reset. For best results, when possible, wait 30 seconds from endpoint reset to send playback requests to this endpoint."""
        logger.info('Calling ResetOriginEndpointState')
        response = self._client.reset_origin_endpoint_state(**kwargs)
        return response

    async def tag_resource(self, **kwargs) -> Dict[str, Any]:
        """Assigns one of more tags (key-value pairs) to the specified MediaPackage resource. Tags can help you organize and categorize your resources. You can also use them to scope user permissions, by granting a user permission to access or change only resources with certain tag values. You can use the TagResource operation with a resource that already has tags. If you specify a new tag key for the resource, this tag is appended to the list of tags associated with the resource. If you specify a tag key that is already associated with the resource, the new tag value that you specify replaces the previous value for that tag."""
        logger.info('Calling TagResource')
        response = self._client.tag_resource(**kwargs)
        return response

    async def untag_resource(self, **kwargs) -> Dict[str, Any]:
        """Removes one or more tags from the specified resource."""
        logger.info('Calling UntagResource')
        response = self._client.untag_resource(**kwargs)
        return response

    async def update_channel(self, **kwargs) -> Dict[str, Any]:
        """Update the specified channel. You can edit if MediaPackage sends ingest or egress access logs to the CloudWatch log group, if content will be encrypted, the description on a channel, and your channel's policy settings. You can't edit the name of the channel or CloudFront distribution details. Any edits you make that impact the video output may not be reflected for a few minutes."""
        logger.info('Calling UpdateChannel')
        response = self._client.update_channel(**kwargs)
        return response

    async def update_channel_group(self, **kwargs) -> Dict[str, Any]:
        """Update the specified channel group. You can edit the description on a channel group for easier identification later from the AWS Elemental MediaPackage console. You can't edit the name of the channel group. Any edits you make that impact the video output may not be reflected for a few minutes."""
        logger.info('Calling UpdateChannelGroup')
        response = self._client.update_channel_group(**kwargs)
        return response

    async def update_origin_endpoint(self, **kwargs) -> Dict[str, Any]:
        """Update the specified origin endpoint. Edit the packaging preferences on an endpoint to optimize the viewing experience. You can't edit the name of the endpoint. Any edits you make that impact the video output may not be reflected for a few minutes."""
        logger.info('Calling UpdateOriginEndpoint')
        response = self._client.update_origin_endpoint(**kwargs)
        return response
