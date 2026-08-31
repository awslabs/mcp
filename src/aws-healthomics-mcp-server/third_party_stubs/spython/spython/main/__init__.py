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

"""Stub for spython.main — see ../../README.md. Not the real spython package."""


class Client:
    """Stub for spython.main.Client. Real Singularity build/run is out of scope for this MCP server."""

    @staticmethod
    def build(*args, **kwargs):
        raise NotImplementedError(
            'spython is stubbed out in this project (see third_party_stubs/spython/README.md); '
            'Singularity container builds are not supported.'
        )
