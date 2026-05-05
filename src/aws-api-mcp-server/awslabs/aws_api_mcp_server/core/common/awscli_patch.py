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

"""AWS CLI patching module for sanitizing file access exceptions."""

import awscli.argprocess
import awscli.customizations.arguments
import awscli.customizations.ecs.deploy
import awscli.paramfile
from .errors import sanitized_exceptions


# Patch AWS CLI functions that call os.path.expandvars under the hood when
# processing file path arguments.
awscli.argprocess.unpack_scalar_cli_arg = sanitized_exceptions(
    awscli.argprocess.unpack_scalar_cli_arg
)
awscli.customizations.arguments.resolve_given_outfile_path = sanitized_exceptions(
    awscli.customizations.arguments.resolve_given_outfile_path
)
awscli.paramfile.get_file = sanitized_exceptions(awscli.paramfile.get_file)
awscli.customizations.ecs.deploy.ECSDeploy._get_file_contents = sanitized_exceptions(
    awscli.customizations.ecs.deploy.ECSDeploy._get_file_contents
)
