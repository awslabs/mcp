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
import awscli.customizations.eks.update_kubeconfig
import awscli.paramfile
from .errors import sanitized_exceptions
from .file_system_controls import validate_file_path


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


# Patch KubeconfigWriter.write_kubeconfig to validate the output path before writing.
_original_write_kubeconfig = (
    awscli.customizations.eks.update_kubeconfig.KubeconfigWriter.write_kubeconfig
)


@sanitized_exceptions
def _validated_write_kubeconfig(self, config):
    """Validate the kubeconfig path, then delegate to the original writer."""
    validate_file_path(config.path)
    return _original_write_kubeconfig(self, config)


awscli.customizations.eks.update_kubeconfig.KubeconfigWriter.write_kubeconfig = (
    _validated_write_kubeconfig
)
