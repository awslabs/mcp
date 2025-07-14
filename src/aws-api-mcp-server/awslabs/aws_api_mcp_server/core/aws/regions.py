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

# These global services don't have regionalized endpoints
NON_REGIONALIZED_SERVICES = ('iam', 'route53')

# These global services have fixed regionalized endpoints
GLOBAL_SERVICE_REGIONS = {
    'devicefarm': 'us-west-2',
    'ecr-public': 'us-east-1',
    'globalaccelerator': 'us-west-2',
    'marketplace-catalog': 'us-east-1',
    'route53-recovery-control-config': 'us-west-2',
    'route53-recovery-readiness': 'us-west-2',
    'route53domains': 'us-east-1',
    'sagemaker-geospatial': 'us-west-2',
}
