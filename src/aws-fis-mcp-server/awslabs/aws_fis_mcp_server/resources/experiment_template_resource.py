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


def experiment_template_resource():
    """Sample FIS experiment template configuration.

    Returns a dictionary containing a sample experiment template configuration
    for stopping and restarting EC2 instances with specific filters.

    {
        "tags": {
            "Name": "StopEC2InstancesWithFilters"
        },
        "description": "Stop and restart all instances in us-east-1b with the tag env=prod in the specified VPC",
        "targets": {
            "myInstances": {
                "resourceType": "aws:ec2:instance",
                "resourceTags": {
                    "env": "prod"
                },
                "filters": [
                    {
                        "path": "Placement.AvailabilityZone",
                        "values": ["us-east-1b"]
                    },
                    {
                        "path": "State.Name",
                        "values": ["running"]
                    },
                    {
                        "path": "VpcId",
                        "values": [ "vpc-aabbcc11223344556"]
                    }
                ],
                "selectionMode": "ALL"
            }
        },
        "actions": {
            "StopInstances": {
                "actionId": "aws:ec2:stop-instances",
                "description": "stop the instances",
                "parameters": {
                    "startInstancesAfterDuration": "PT2M"
                },
                "targets": {
                    "Instances": "myInstances"
                }
            }
        },
        "stopConditions": [
            {
                "source": "aws:cloudwatch:alarm",
                "value": "arn:aws:cloudwatch:us-east-1:111122223333:alarm:alarm-name"
            }
        ],
        "roleArn": "arn:aws:iam::111122223333:role/role-name"
    }
    """
