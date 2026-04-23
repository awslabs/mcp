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

DO NOT EDIT — this file is auto-generated from the botocore service model.
"""

import boto3
from loguru import logger
from typing import Any, Dict, Optional


class MediaLiveClient:
    """Wrapper around boto3 MediaLive client."""

    def __init__(self, region_name: str = 'us-east-1', profile_name: Optional[str] = None):
        """Initialize the MediaLive client."""
        session = boto3.Session(region_name=region_name, profile_name=profile_name)
        self._client = session.client('medialive')
        logger.info(f'Initialized MediaLive client for region {region_name}')

    async def accept_input_device_transfer(self, **kwargs) -> Dict[str, Any]:
        """Accept an incoming input device transfer. The ownership of the device will transfer to your AWS account."""
        logger.info('Calling AcceptInputDeviceTransfer')
        response = self._client.accept_input_device_transfer(**kwargs)
        return response

    async def batch_delete(self, **kwargs) -> Dict[str, Any]:
        """Starts delete of resources."""
        logger.info('Calling BatchDelete')
        response = self._client.batch_delete(**kwargs)
        return response

    async def batch_start(self, **kwargs) -> Dict[str, Any]:
        """Starts existing resources."""
        logger.info('Calling BatchStart')
        response = self._client.batch_start(**kwargs)
        return response

    async def batch_stop(self, **kwargs) -> Dict[str, Any]:
        """Stops running resources."""
        logger.info('Calling BatchStop')
        response = self._client.batch_stop(**kwargs)
        return response

    async def batch_update_schedule(self, **kwargs) -> Dict[str, Any]:
        """Update a channel schedule."""
        logger.info('Calling BatchUpdateSchedule')
        response = self._client.batch_update_schedule(**kwargs)
        return response

    async def cancel_input_device_transfer(self, **kwargs) -> Dict[str, Any]:
        """Cancel an input device transfer that you have requested."""
        logger.info('Calling CancelInputDeviceTransfer')
        response = self._client.cancel_input_device_transfer(**kwargs)
        return response

    async def claim_device(self, **kwargs) -> Dict[str, Any]:
        """Send a request to claim an AWS Elemental device that you have purchased from a third-party vendor. After the request succeeds, you will own the device."""
        logger.info('Calling ClaimDevice')
        response = self._client.claim_device(**kwargs)
        return response

    async def create_channel(self, **kwargs) -> Dict[str, Any]:
        """Creates a new channel."""
        logger.info('Calling CreateChannel')
        response = self._client.create_channel(**kwargs)
        return response

    async def create_input(self, **kwargs) -> Dict[str, Any]:
        """Create an input."""
        logger.info('Calling CreateInput')
        response = self._client.create_input(**kwargs)
        return response

    async def create_input_security_group(self, **kwargs) -> Dict[str, Any]:
        """Creates a Input Security Group."""
        logger.info('Calling CreateInputSecurityGroup')
        response = self._client.create_input_security_group(**kwargs)
        return response

    async def create_multiplex(self, **kwargs) -> Dict[str, Any]:
        """Create a new multiplex."""
        logger.info('Calling CreateMultiplex')
        response = self._client.create_multiplex(**kwargs)
        return response

    async def create_multiplex_program(self, **kwargs) -> Dict[str, Any]:
        """Create a new program in the multiplex."""
        logger.info('Calling CreateMultiplexProgram')
        response = self._client.create_multiplex_program(**kwargs)
        return response

    async def create_partner_input(self, **kwargs) -> Dict[str, Any]:
        """Create a partner input."""
        logger.info('Calling CreatePartnerInput')
        response = self._client.create_partner_input(**kwargs)
        return response

    async def create_tags(self, **kwargs) -> Dict[str, Any]:
        """Create tags for a resource."""
        logger.info('Calling CreateTags')
        response = self._client.create_tags(**kwargs)
        return response

    async def delete_channel(self, **kwargs) -> Dict[str, Any]:
        """Starts deletion of channel. The associated outputs are also deleted."""
        logger.info('Calling DeleteChannel')
        response = self._client.delete_channel(**kwargs)
        return response

    async def delete_input(self, **kwargs) -> Dict[str, Any]:
        """Deletes the input end point."""
        logger.info('Calling DeleteInput')
        response = self._client.delete_input(**kwargs)
        return response

    async def delete_input_security_group(self, **kwargs) -> Dict[str, Any]:
        """Deletes an Input Security Group."""
        logger.info('Calling DeleteInputSecurityGroup')
        response = self._client.delete_input_security_group(**kwargs)
        return response

    async def delete_multiplex(self, **kwargs) -> Dict[str, Any]:
        """Delete a multiplex. The multiplex must be idle."""
        logger.info('Calling DeleteMultiplex')
        response = self._client.delete_multiplex(**kwargs)
        return response

    async def delete_multiplex_program(self, **kwargs) -> Dict[str, Any]:
        """Delete a program from a multiplex."""
        logger.info('Calling DeleteMultiplexProgram')
        response = self._client.delete_multiplex_program(**kwargs)
        return response

    async def delete_reservation(self, **kwargs) -> Dict[str, Any]:
        """Delete an expired reservation."""
        logger.info('Calling DeleteReservation')
        response = self._client.delete_reservation(**kwargs)
        return response

    async def delete_schedule(self, **kwargs) -> Dict[str, Any]:
        """Delete all schedule actions on a channel."""
        logger.info('Calling DeleteSchedule')
        response = self._client.delete_schedule(**kwargs)
        return response

    async def delete_tags(self, **kwargs) -> Dict[str, Any]:
        """Removes tags for a resource."""
        logger.info('Calling DeleteTags')
        response = self._client.delete_tags(**kwargs)
        return response

    async def describe_account_configuration(self, **kwargs) -> Dict[str, Any]:
        """Describe account configuration."""
        logger.info('Calling DescribeAccountConfiguration')
        response = self._client.describe_account_configuration(**kwargs)
        return response

    async def describe_channel(self, **kwargs) -> Dict[str, Any]:
        """Gets details about a channel."""
        logger.info('Calling DescribeChannel')
        response = self._client.describe_channel(**kwargs)
        return response

    async def describe_input(self, **kwargs) -> Dict[str, Any]:
        """Produces details about an input."""
        logger.info('Calling DescribeInput')
        response = self._client.describe_input(**kwargs)
        return response

    async def describe_input_device(self, **kwargs) -> Dict[str, Any]:
        """Gets the details for the input device."""
        logger.info('Calling DescribeInputDevice')
        response = self._client.describe_input_device(**kwargs)
        return response

    async def describe_input_device_thumbnail(self, **kwargs) -> Dict[str, Any]:
        """Get the latest thumbnail data for the input device."""
        logger.info('Calling DescribeInputDeviceThumbnail')
        response = self._client.describe_input_device_thumbnail(**kwargs)
        return response

    async def describe_input_security_group(self, **kwargs) -> Dict[str, Any]:
        """Produces a summary of an Input Security Group."""
        logger.info('Calling DescribeInputSecurityGroup')
        response = self._client.describe_input_security_group(**kwargs)
        return response

    async def describe_multiplex(self, **kwargs) -> Dict[str, Any]:
        """Gets details about a multiplex."""
        logger.info('Calling DescribeMultiplex')
        response = self._client.describe_multiplex(**kwargs)
        return response

    async def describe_multiplex_program(self, **kwargs) -> Dict[str, Any]:
        """Get the details for a program in a multiplex."""
        logger.info('Calling DescribeMultiplexProgram')
        response = self._client.describe_multiplex_program(**kwargs)
        return response

    async def describe_offering(self, **kwargs) -> Dict[str, Any]:
        """Get details for an offering."""
        logger.info('Calling DescribeOffering')
        response = self._client.describe_offering(**kwargs)
        return response

    async def describe_reservation(self, **kwargs) -> Dict[str, Any]:
        """Get details for a reservation."""
        logger.info('Calling DescribeReservation')
        response = self._client.describe_reservation(**kwargs)
        return response

    async def describe_schedule(self, **kwargs) -> Dict[str, Any]:
        """Get a channel schedule."""
        logger.info('Calling DescribeSchedule')
        response = self._client.describe_schedule(**kwargs)
        return response

    async def describe_thumbnails(self, **kwargs) -> Dict[str, Any]:
        """Describe the latest thumbnails data."""
        logger.info('Calling DescribeThumbnails')
        response = self._client.describe_thumbnails(**kwargs)
        return response

    async def list_channels(self, **kwargs) -> Dict[str, Any]:
        """Produces list of channels that have been created."""
        logger.info('Calling ListChannels')
        response = self._client.list_channels(**kwargs)
        return response

    async def list_input_device_transfers(self, **kwargs) -> Dict[str, Any]:
        """List input devices that are currently being transferred. List input devices that you are transferring from your AWS account or input devices that another AWS account is transferring to you."""
        logger.info('Calling ListInputDeviceTransfers')
        response = self._client.list_input_device_transfers(**kwargs)
        return response

    async def list_input_devices(self, **kwargs) -> Dict[str, Any]:
        """List input devices."""
        logger.info('Calling ListInputDevices')
        response = self._client.list_input_devices(**kwargs)
        return response

    async def list_input_security_groups(self, **kwargs) -> Dict[str, Any]:
        """Produces a list of Input Security Groups for an account."""
        logger.info('Calling ListInputSecurityGroups')
        response = self._client.list_input_security_groups(**kwargs)
        return response

    async def list_inputs(self, **kwargs) -> Dict[str, Any]:
        """Produces list of inputs that have been created."""
        logger.info('Calling ListInputs')
        response = self._client.list_inputs(**kwargs)
        return response

    async def list_multiplex_programs(self, **kwargs) -> Dict[str, Any]:
        """List the programs that currently exist for a specific multiplex."""
        logger.info('Calling ListMultiplexPrograms')
        response = self._client.list_multiplex_programs(**kwargs)
        return response

    async def list_multiplexes(self, **kwargs) -> Dict[str, Any]:
        """Retrieve a list of the existing multiplexes."""
        logger.info('Calling ListMultiplexes')
        response = self._client.list_multiplexes(**kwargs)
        return response

    async def list_offerings(self, **kwargs) -> Dict[str, Any]:
        """List offerings available for purchase."""
        logger.info('Calling ListOfferings')
        response = self._client.list_offerings(**kwargs)
        return response

    async def list_reservations(self, **kwargs) -> Dict[str, Any]:
        """List purchased reservations."""
        logger.info('Calling ListReservations')
        response = self._client.list_reservations(**kwargs)
        return response

    async def list_tags_for_resource(self, **kwargs) -> Dict[str, Any]:
        """Produces list of tags that have been created for a resource."""
        logger.info('Calling ListTagsForResource')
        response = self._client.list_tags_for_resource(**kwargs)
        return response

    async def purchase_offering(self, **kwargs) -> Dict[str, Any]:
        """Purchase an offering and create a reservation."""
        logger.info('Calling PurchaseOffering')
        response = self._client.purchase_offering(**kwargs)
        return response

    async def reboot_input_device(self, **kwargs) -> Dict[str, Any]:
        """Send a reboot command to the specified input device. The device will begin rebooting within a few seconds of sending the command. When the reboot is complete, the device’s connection status will chang."""
        logger.info('Calling RebootInputDevice')
        response = self._client.reboot_input_device(**kwargs)
        return response

    async def reject_input_device_transfer(self, **kwargs) -> Dict[str, Any]:
        """Reject the transfer of the specified input device to your AWS account."""
        logger.info('Calling RejectInputDeviceTransfer')
        response = self._client.reject_input_device_transfer(**kwargs)
        return response

    async def start_channel(self, **kwargs) -> Dict[str, Any]:
        """Starts an existing channel."""
        logger.info('Calling StartChannel')
        response = self._client.start_channel(**kwargs)
        return response

    async def start_input_device(self, **kwargs) -> Dict[str, Any]:
        """Start an input device that is attached to a MediaConnect flow. (There is no need to start a device that is attached to a MediaLive input; MediaLive starts the device when the channel starts.)."""
        logger.info('Calling StartInputDevice')
        response = self._client.start_input_device(**kwargs)
        return response

    async def start_input_device_maintenance_window(self, **kwargs) -> Dict[str, Any]:
        """Start a maintenance window for the specified input device. Starting a maintenance window will give the device up to two hours to install software. If the device was streaming prior to the maintenance,."""
        logger.info('Calling StartInputDeviceMaintenanceWindow')
        response = self._client.start_input_device_maintenance_window(**kwargs)
        return response

    async def start_multiplex(self, **kwargs) -> Dict[str, Any]:
        """Start (run) the multiplex. Starting the multiplex does not start the channels. You must explicitly start each channel."""
        logger.info('Calling StartMultiplex')
        response = self._client.start_multiplex(**kwargs)
        return response

    async def stop_channel(self, **kwargs) -> Dict[str, Any]:
        """Stops a running channel."""
        logger.info('Calling StopChannel')
        response = self._client.stop_channel(**kwargs)
        return response

    async def stop_input_device(self, **kwargs) -> Dict[str, Any]:
        """Stop an input device that is attached to a MediaConnect flow. (There is no need to stop a device that is attached to a MediaLive input; MediaLive automatically stops the device when the channel stops."""
        logger.info('Calling StopInputDevice')
        response = self._client.stop_input_device(**kwargs)
        return response

    async def stop_multiplex(self, **kwargs) -> Dict[str, Any]:
        """Stops a running multiplex. If the multiplex isn't running, this action has no effect."""
        logger.info('Calling StopMultiplex')
        response = self._client.stop_multiplex(**kwargs)
        return response

    async def transfer_input_device(self, **kwargs) -> Dict[str, Any]:
        """Start an input device transfer to another AWS account. After you make the request, the other account must accept or reject the transfer."""
        logger.info('Calling TransferInputDevice')
        response = self._client.transfer_input_device(**kwargs)
        return response

    async def update_account_configuration(self, **kwargs) -> Dict[str, Any]:
        """Update account configuration."""
        logger.info('Calling UpdateAccountConfiguration')
        response = self._client.update_account_configuration(**kwargs)
        return response

    async def update_channel(self, **kwargs) -> Dict[str, Any]:
        """Updates a channel."""
        logger.info('Calling UpdateChannel')
        response = self._client.update_channel(**kwargs)
        return response

    async def update_channel_class(self, **kwargs) -> Dict[str, Any]:
        """Changes the class of the channel."""
        logger.info('Calling UpdateChannelClass')
        response = self._client.update_channel_class(**kwargs)
        return response

    async def update_input(self, **kwargs) -> Dict[str, Any]:
        """Updates an input."""
        logger.info('Calling UpdateInput')
        response = self._client.update_input(**kwargs)
        return response

    async def update_input_device(self, **kwargs) -> Dict[str, Any]:
        """Updates the parameters for the input device."""
        logger.info('Calling UpdateInputDevice')
        response = self._client.update_input_device(**kwargs)
        return response

    async def update_input_security_group(self, **kwargs) -> Dict[str, Any]:
        """Update an Input Security Group's Whilelists."""
        logger.info('Calling UpdateInputSecurityGroup')
        response = self._client.update_input_security_group(**kwargs)
        return response

    async def update_multiplex(self, **kwargs) -> Dict[str, Any]:
        """Updates a multiplex."""
        logger.info('Calling UpdateMultiplex')
        response = self._client.update_multiplex(**kwargs)
        return response

    async def update_multiplex_program(self, **kwargs) -> Dict[str, Any]:
        """Update a program in a multiplex."""
        logger.info('Calling UpdateMultiplexProgram')
        response = self._client.update_multiplex_program(**kwargs)
        return response

    async def update_reservation(self, **kwargs) -> Dict[str, Any]:
        """Update reservation."""
        logger.info('Calling UpdateReservation')
        response = self._client.update_reservation(**kwargs)
        return response

    async def restart_channel_pipelines(self, **kwargs) -> Dict[str, Any]:
        """Restart pipelines in one channel that is currently running."""
        logger.info('Calling RestartChannelPipelines')
        response = self._client.restart_channel_pipelines(**kwargs)
        return response

    async def create_cloud_watch_alarm_template(self, **kwargs) -> Dict[str, Any]:
        """Creates a cloudwatch alarm template to dynamically generate cloudwatch metric alarms on targeted resource types."""
        logger.info('Calling CreateCloudWatchAlarmTemplate')
        response = self._client.create_cloud_watch_alarm_template(**kwargs)
        return response

    async def create_cloud_watch_alarm_template_group(self, **kwargs) -> Dict[str, Any]:
        """Creates a cloudwatch alarm template group to group your cloudwatch alarm templates and to attach to signal maps for dynamically creating alarms."""
        logger.info('Calling CreateCloudWatchAlarmTemplateGroup')
        response = self._client.create_cloud_watch_alarm_template_group(**kwargs)
        return response

    async def create_event_bridge_rule_template(self, **kwargs) -> Dict[str, Any]:
        """Creates an eventbridge rule template to monitor events and send notifications to your targeted resources."""
        logger.info('Calling CreateEventBridgeRuleTemplate')
        response = self._client.create_event_bridge_rule_template(**kwargs)
        return response

    async def create_event_bridge_rule_template_group(self, **kwargs) -> Dict[str, Any]:
        """Creates an eventbridge rule template group to group your eventbridge rule templates and to attach to signal maps for dynamically creating notification rules."""
        logger.info('Calling CreateEventBridgeRuleTemplateGroup')
        response = self._client.create_event_bridge_rule_template_group(**kwargs)
        return response

    async def create_signal_map(self, **kwargs) -> Dict[str, Any]:
        """Initiates the creation of a new signal map. Will discover a new mediaResourceMap based on the provided discoveryEntryPointArn."""
        logger.info('Calling CreateSignalMap')
        response = self._client.create_signal_map(**kwargs)
        return response

    async def delete_cloud_watch_alarm_template(self, **kwargs) -> Dict[str, Any]:
        """Deletes a cloudwatch alarm template."""
        logger.info('Calling DeleteCloudWatchAlarmTemplate')
        response = self._client.delete_cloud_watch_alarm_template(**kwargs)
        return response

    async def delete_cloud_watch_alarm_template_group(self, **kwargs) -> Dict[str, Any]:
        """Deletes a cloudwatch alarm template group. You must detach this group from all signal maps and ensure its existing templates are moved to another group or deleted."""
        logger.info('Calling DeleteCloudWatchAlarmTemplateGroup')
        response = self._client.delete_cloud_watch_alarm_template_group(**kwargs)
        return response

    async def delete_event_bridge_rule_template(self, **kwargs) -> Dict[str, Any]:
        """Deletes an eventbridge rule template."""
        logger.info('Calling DeleteEventBridgeRuleTemplate')
        response = self._client.delete_event_bridge_rule_template(**kwargs)
        return response

    async def delete_event_bridge_rule_template_group(self, **kwargs) -> Dict[str, Any]:
        """Deletes an eventbridge rule template group. You must detach this group from all signal maps and ensure its existing templates are moved to another group or deleted."""
        logger.info('Calling DeleteEventBridgeRuleTemplateGroup')
        response = self._client.delete_event_bridge_rule_template_group(**kwargs)
        return response

    async def delete_signal_map(self, **kwargs) -> Dict[str, Any]:
        """Deletes the specified signal map."""
        logger.info('Calling DeleteSignalMap')
        response = self._client.delete_signal_map(**kwargs)
        return response

    async def get_cloud_watch_alarm_template(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified cloudwatch alarm template."""
        logger.info('Calling GetCloudWatchAlarmTemplate')
        response = self._client.get_cloud_watch_alarm_template(**kwargs)
        return response

    async def get_cloud_watch_alarm_template_group(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified cloudwatch alarm template group."""
        logger.info('Calling GetCloudWatchAlarmTemplateGroup')
        response = self._client.get_cloud_watch_alarm_template_group(**kwargs)
        return response

    async def get_event_bridge_rule_template(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified eventbridge rule template."""
        logger.info('Calling GetEventBridgeRuleTemplate')
        response = self._client.get_event_bridge_rule_template(**kwargs)
        return response

    async def get_event_bridge_rule_template_group(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified eventbridge rule template group."""
        logger.info('Calling GetEventBridgeRuleTemplateGroup')
        response = self._client.get_event_bridge_rule_template_group(**kwargs)
        return response

    async def get_signal_map(self, **kwargs) -> Dict[str, Any]:
        """Retrieves the specified signal map."""
        logger.info('Calling GetSignalMap')
        response = self._client.get_signal_map(**kwargs)
        return response

    async def list_cloud_watch_alarm_template_groups(self, **kwargs) -> Dict[str, Any]:
        """Lists cloudwatch alarm template groups."""
        logger.info('Calling ListCloudWatchAlarmTemplateGroups')
        response = self._client.list_cloud_watch_alarm_template_groups(**kwargs)
        return response

    async def list_cloud_watch_alarm_templates(self, **kwargs) -> Dict[str, Any]:
        """Lists cloudwatch alarm templates."""
        logger.info('Calling ListCloudWatchAlarmTemplates')
        response = self._client.list_cloud_watch_alarm_templates(**kwargs)
        return response

    async def list_event_bridge_rule_template_groups(self, **kwargs) -> Dict[str, Any]:
        """Lists eventbridge rule template groups."""
        logger.info('Calling ListEventBridgeRuleTemplateGroups')
        response = self._client.list_event_bridge_rule_template_groups(**kwargs)
        return response

    async def list_event_bridge_rule_templates(self, **kwargs) -> Dict[str, Any]:
        """Lists eventbridge rule templates."""
        logger.info('Calling ListEventBridgeRuleTemplates')
        response = self._client.list_event_bridge_rule_templates(**kwargs)
        return response

    async def list_signal_maps(self, **kwargs) -> Dict[str, Any]:
        """Lists signal maps."""
        logger.info('Calling ListSignalMaps')
        response = self._client.list_signal_maps(**kwargs)
        return response

    async def start_delete_monitor_deployment(self, **kwargs) -> Dict[str, Any]:
        """Initiates a deployment to delete the monitor of the specified signal map."""
        logger.info('Calling StartDeleteMonitorDeployment')
        response = self._client.start_delete_monitor_deployment(**kwargs)
        return response

    async def start_monitor_deployment(self, **kwargs) -> Dict[str, Any]:
        """Initiates a deployment to deploy the latest monitor of the specified signal map."""
        logger.info('Calling StartMonitorDeployment')
        response = self._client.start_monitor_deployment(**kwargs)
        return response

    async def start_update_signal_map(self, **kwargs) -> Dict[str, Any]:
        """Initiates an update for the specified signal map. Will discover a new signal map if a changed discoveryEntryPointArn is provided."""
        logger.info('Calling StartUpdateSignalMap')
        response = self._client.start_update_signal_map(**kwargs)
        return response

    async def update_cloud_watch_alarm_template(self, **kwargs) -> Dict[str, Any]:
        """Updates the specified cloudwatch alarm template."""
        logger.info('Calling UpdateCloudWatchAlarmTemplate')
        response = self._client.update_cloud_watch_alarm_template(**kwargs)
        return response

    async def update_cloud_watch_alarm_template_group(self, **kwargs) -> Dict[str, Any]:
        """Updates the specified cloudwatch alarm template group."""
        logger.info('Calling UpdateCloudWatchAlarmTemplateGroup')
        response = self._client.update_cloud_watch_alarm_template_group(**kwargs)
        return response

    async def update_event_bridge_rule_template(self, **kwargs) -> Dict[str, Any]:
        """Updates the specified eventbridge rule template."""
        logger.info('Calling UpdateEventBridgeRuleTemplate')
        response = self._client.update_event_bridge_rule_template(**kwargs)
        return response

    async def update_event_bridge_rule_template_group(self, **kwargs) -> Dict[str, Any]:
        """Updates the specified eventbridge rule template group."""
        logger.info('Calling UpdateEventBridgeRuleTemplateGroup')
        response = self._client.update_event_bridge_rule_template_group(**kwargs)
        return response

    async def create_channel_placement_group(self, **kwargs) -> Dict[str, Any]:
        """Create a ChannelPlacementGroup in the specified Cluster. As part of the create operation, you specify the Nodes to attach the group to.After you create a ChannelPlacementGroup, you add Channels to the."""
        logger.info('Calling CreateChannelPlacementGroup')
        response = self._client.create_channel_placement_group(**kwargs)
        return response

    async def create_cluster(self, **kwargs) -> Dict[str, Any]:
        """Create a new Cluster."""
        logger.info('Calling CreateCluster')
        response = self._client.create_cluster(**kwargs)
        return response

    async def create_network(self, **kwargs) -> Dict[str, Any]:
        """Create as many Networks as you need. You will associate one or more Clusters with each Network.Each Network provides MediaLive Anywhere with required information about the network in your organization."""
        logger.info('Calling CreateNetwork')
        response = self._client.create_network(**kwargs)
        return response

    async def create_node(self, **kwargs) -> Dict[str, Any]:
        """Create a Node in the specified Cluster. You can also create Nodes using the CreateNodeRegistrationScript. Note that you can't move a Node to another Cluster."""
        logger.info('Calling CreateNode')
        response = self._client.create_node(**kwargs)
        return response

    async def create_node_registration_script(self, **kwargs) -> Dict[str, Any]:
        """Create the Register Node script for all the nodes intended for a specific Cluster. You will then run the script on each hardware unit that is intended for that Cluster. The script creates a Node in th."""
        logger.info('Calling CreateNodeRegistrationScript')
        response = self._client.create_node_registration_script(**kwargs)
        return response

    async def delete_channel_placement_group(self, **kwargs) -> Dict[str, Any]:
        """Delete the specified ChannelPlacementGroup that exists in the specified Cluster."""
        logger.info('Calling DeleteChannelPlacementGroup')
        response = self._client.delete_channel_placement_group(**kwargs)
        return response

    async def delete_cluster(self, **kwargs) -> Dict[str, Any]:
        """Delete a Cluster. The Cluster must be idle."""
        logger.info('Calling DeleteCluster')
        response = self._client.delete_cluster(**kwargs)
        return response

    async def delete_network(self, **kwargs) -> Dict[str, Any]:
        """Delete a Network. The Network must have no resources associated with it."""
        logger.info('Calling DeleteNetwork')
        response = self._client.delete_network(**kwargs)
        return response

    async def delete_node(self, **kwargs) -> Dict[str, Any]:
        """Delete a Node. The Node must be IDLE."""
        logger.info('Calling DeleteNode')
        response = self._client.delete_node(**kwargs)
        return response

    async def describe_channel_placement_group(self, **kwargs) -> Dict[str, Any]:
        """Get details about a ChannelPlacementGroup."""
        logger.info('Calling DescribeChannelPlacementGroup')
        response = self._client.describe_channel_placement_group(**kwargs)
        return response

    async def describe_cluster(self, **kwargs) -> Dict[str, Any]:
        """Get details about a Cluster."""
        logger.info('Calling DescribeCluster')
        response = self._client.describe_cluster(**kwargs)
        return response

    async def describe_network(self, **kwargs) -> Dict[str, Any]:
        """Get details about a Network."""
        logger.info('Calling DescribeNetwork')
        response = self._client.describe_network(**kwargs)
        return response

    async def describe_node(self, **kwargs) -> Dict[str, Any]:
        """Get details about a Node in the specified Cluster."""
        logger.info('Calling DescribeNode')
        response = self._client.describe_node(**kwargs)
        return response

    async def list_channel_placement_groups(self, **kwargs) -> Dict[str, Any]:
        """Retrieve the list of ChannelPlacementGroups in the specified Cluster."""
        logger.info('Calling ListChannelPlacementGroups')
        response = self._client.list_channel_placement_groups(**kwargs)
        return response

    async def list_clusters(self, **kwargs) -> Dict[str, Any]:
        """Retrieve the list of Clusters."""
        logger.info('Calling ListClusters')
        response = self._client.list_clusters(**kwargs)
        return response

    async def list_networks(self, **kwargs) -> Dict[str, Any]:
        """Retrieve the list of Networks."""
        logger.info('Calling ListNetworks')
        response = self._client.list_networks(**kwargs)
        return response

    async def list_nodes(self, **kwargs) -> Dict[str, Any]:
        """Retrieve the list of Nodes."""
        logger.info('Calling ListNodes')
        response = self._client.list_nodes(**kwargs)
        return response

    async def update_channel_placement_group(self, **kwargs) -> Dict[str, Any]:
        """Change the settings for a ChannelPlacementGroup."""
        logger.info('Calling UpdateChannelPlacementGroup')
        response = self._client.update_channel_placement_group(**kwargs)
        return response

    async def update_cluster(self, **kwargs) -> Dict[str, Any]:
        """Change the settings for a Cluster."""
        logger.info('Calling UpdateCluster')
        response = self._client.update_cluster(**kwargs)
        return response

    async def update_network(self, **kwargs) -> Dict[str, Any]:
        """Change the settings for a Network."""
        logger.info('Calling UpdateNetwork')
        response = self._client.update_network(**kwargs)
        return response

    async def update_node(self, **kwargs) -> Dict[str, Any]:
        """Change the settings for a Node."""
        logger.info('Calling UpdateNode')
        response = self._client.update_node(**kwargs)
        return response

    async def update_node_state(self, **kwargs) -> Dict[str, Any]:
        """Update the state of a node."""
        logger.info('Calling UpdateNodeState')
        response = self._client.update_node_state(**kwargs)
        return response

    async def list_versions(self, **kwargs) -> Dict[str, Any]:
        """Retrieves an array of all the encoder engine versions that are available in this AWS account."""
        logger.info('Calling ListVersions')
        response = self._client.list_versions(**kwargs)
        return response

    async def create_sdi_source(self, **kwargs) -> Dict[str, Any]:
        """Create an SdiSource for each video source that uses the SDI protocol. You will reference the SdiSource when you create an SDI input in MediaLive. You will also reference it in an SdiSourceMapping, in."""
        logger.info('Calling CreateSdiSource')
        response = self._client.create_sdi_source(**kwargs)
        return response

    async def delete_sdi_source(self, **kwargs) -> Dict[str, Any]:
        """Delete an SdiSource. The SdiSource must not be part of any SidSourceMapping and must not be attached to any input."""
        logger.info('Calling DeleteSdiSource')
        response = self._client.delete_sdi_source(**kwargs)
        return response

    async def describe_sdi_source(self, **kwargs) -> Dict[str, Any]:
        """Gets details about a SdiSource."""
        logger.info('Calling DescribeSdiSource')
        response = self._client.describe_sdi_source(**kwargs)
        return response

    async def list_sdi_sources(self, **kwargs) -> Dict[str, Any]:
        """List all the SdiSources in the AWS account."""
        logger.info('Calling ListSdiSources')
        response = self._client.list_sdi_sources(**kwargs)
        return response

    async def update_sdi_source(self, **kwargs) -> Dict[str, Any]:
        """Change some of the settings in an SdiSource."""
        logger.info('Calling UpdateSdiSource')
        response = self._client.update_sdi_source(**kwargs)
        return response
