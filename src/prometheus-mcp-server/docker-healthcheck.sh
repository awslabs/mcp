#!/bin/sh
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

if [ "$(lsof +c 0 -p 1 | grep -e "^awslabs\..*\s1\s.*\sunix\s.*socket$" | wc -l)" -ne "0" ]; then
  echo -n "$(lsof +c 0 -p 1 | grep -e "^awslabs\..*\s1\s.*\sunix\s.*socket$" | wc -l) awslabs.* streams found";
  exit 0;
else
  echo -n "Zero awslabs.* streams found";
  exit 1;
fi;

echo -n "Never should reach here";
exit 99;
