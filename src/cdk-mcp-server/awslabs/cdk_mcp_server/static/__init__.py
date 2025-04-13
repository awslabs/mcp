# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
from importlib import resources  # nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2


with (
    resources.files('awslabs.cdk_mcp_server.static')
    .joinpath('CDK_GENERAL_GUIDANCE.md')
    .open('r', encoding='utf-8') as f
):
    CDK_GENERAL_GUIDANCE = f.read()
