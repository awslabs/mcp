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

"""Config loading helpers for cross-account CloudWatch targets."""

from os import getenv
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import yaml


DEFAULT_CONFIG_FILENAME = 'cw_config.yaml'
EXAMPLE_CONFIG_FILENAME = 'cw_config.example.yaml'
CONFIG_PATH_ENV_VAR = 'CW_CONFIG_PATH'


class ConfiguredLogGroup(BaseModel):
    """A configured CloudWatch log group entry."""

    name: str = Field(description='CloudWatch log group name.')
    description: Optional[str] = Field(
        default=None, description='Optional description for the log group.'
    )


class ConfiguredAccount(BaseModel):
    """A configured AWS account target for CloudWatch access."""

    accountId: str = Field(description='12-digit AWS account ID.', pattern=r'^\d{12}$')
    region: str = Field(description='AWS region for the account.')
    roleName: str = Field(description='IAM role name to assume in the target account.')
    logGroups: List[ConfiguredLogGroup] = Field(
        default_factory=list,
        description='Known log groups in this account with optional descriptions.',
    )


class CloudWatchConfig(BaseModel):
    """Top-level config document for known CloudWatch targets."""

    accounts: List[ConfiguredAccount] = Field(
        default_factory=list, description='Configured AWS accounts and significant log groups.'
    )


class ConfigNotProvidedError(FileNotFoundError):
    """Raised when the required CloudWatch config file is not available."""


def resolve_config_path() -> Path:
    """Resolve the config file path from the environment or local default."""
    configured_path = getenv(CONFIG_PATH_ENV_VAR)
    if configured_path:
        return Path(configured_path).expanduser()
    return Path.cwd() / DEFAULT_CONFIG_FILENAME


def load_cloudwatch_config() -> tuple[CloudWatchConfig, Path]:
    """Load the required CloudWatch target config from disk."""
    config_path = resolve_config_path()
    if not config_path.exists():
        example_path = config_path.parent / EXAMPLE_CONFIG_FILENAME
        raise ConfigNotProvidedError(
            f'CloudWatch config file not found at {config_path}. '
            f'Create {DEFAULT_CONFIG_FILENAME} from {EXAMPLE_CONFIG_FILENAME} or set '
            f'{CONFIG_PATH_ENV_VAR} to a valid config path.'
            + (f' Example template: {example_path}' if not getenv(CONFIG_PATH_ENV_VAR) else '')
        )

    with config_path.open('r', encoding='utf-8') as config_file:
        raw_config = yaml.safe_load(config_file) or {}

    return CloudWatchConfig.model_validate(raw_config), config_path
