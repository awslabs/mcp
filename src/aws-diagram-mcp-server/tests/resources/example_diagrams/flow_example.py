#
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
#

"""Example flow diagram for testing."""

from diagrams import Diagram
from diagrams.programming.flowchart import Action, Decision, Delay, InputOutput, StartEnd


with Diagram('Flow Example', show=False):
    start = StartEnd('Start')
    order = InputOutput('Order Received')
    check = Decision('In Stock?')
    process = Action('Process Order')
    wait = Delay('Backorder')
    ship = Action('Ship Order')
    end = StartEnd('End')

    start >> order >> check
    check >> process >> ship >> end
    check >> wait >> process
