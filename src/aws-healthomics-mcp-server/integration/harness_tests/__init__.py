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


"""Offline property tests for the integration harness pure-logic utilities.

This package is deliberately separate from ``integration/tests/`` (which is
opt-in-gated and skipped without the activation signal) and from the top-level
``tests/`` suite (which must not import the harness). The property tests here
are pure and offline: they never touch AWS or the network and are not gated by
the Opt_In_Signal.
"""
