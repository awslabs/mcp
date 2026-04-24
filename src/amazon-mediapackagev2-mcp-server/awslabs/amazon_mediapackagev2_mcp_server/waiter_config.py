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


"""Auto-generated waiter configuration from botocore waiter model.

DO NOT EDIT — regenerate with: python src/codegen/generate.py mediapackagev2
"""

WAITER_REGISTRY: dict[str, dict] = {
    'harvest_job_finished': {
        'boto3_waiter_name': 'harvest_job_finished',
        'description': 'Wait until GetHarvestJob returns COMPLETED, CANCELLED',
        'delay': 2,
        'max_attempts': 60,
    },
}
