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

"""Environment variable manager for the MCP server."""

import json
import os
import subprocess
from typing import Any, Dict, Optional


# Default values based on README
DEFAULT_VALUES = {
    'AWS_REGION': '',  # Let AWS profile/config determine default region
    'AWS_PROFILE': '',
    'DEFAULT_TAGS': 'enabled',
}


def load_environment_variables() -> Dict[str, str]:
    """Load all environment variables with proper defaults.

    Returns:
        Dictionary of environment variables with defaults applied
    """
    env_vars = {}

    # Apply defaults for specific variables
    for key, default in DEFAULT_VALUES.items():
        env_vars[key] = os.environ.get(key, default)

    # No validation needed for removed environment variables

    return env_vars


def get_env_var(name: str, default: Optional[str] = None) -> str:
    """Get an environment variable with proper defaults.

    Args:
        name: The name of the environment variable
        default: Default value if the variable is not set and not in DEFAULT_VALUES

    Returns:
        The value of the environment variable or the default value
    """
    if name in DEFAULT_VALUES and name not in os.environ:
        return DEFAULT_VALUES[name]
    return os.environ.get(name, default or '')


def check_aws_credentials() -> Dict[str, Any]:
    """Check if AWS credentials are valid and available.

    Returns:
        Dictionary with credential status and information
    """
    # Get environment variables
    env_vars = load_environment_variables()
    profile = env_vars['AWS_PROFILE']
    region = env_vars['AWS_REGION']

    # If no region in env var, try to get from profile
    if not region and profile:
        try:
            cmd = ['aws', 'configure', 'get', 'region', '--profile', profile]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                region = process.stdout.strip()
        except Exception:
            pass

    # Final fallback to us-east-1
    if not region:
        region = 'us-east-1'

    result = {
        'valid': False,
        'profile': profile,
        'region': region,
        'environment_variables': env_vars,
    }

    # Try to get caller identity using AWS CLI
    try:
        cmd = ['aws', 'sts', 'get-caller-identity']

        # Add profile if specified
        if profile:
            cmd.extend(['--profile', profile])

        # Add region
        cmd.extend(['--region', region])

        # Run the command
        process = subprocess.run(cmd, capture_output=True, text=True)

        if process.returncode == 0:
            # Parse the JSON output
            identity = json.loads(process.stdout)

            result.update(
                {
                    'valid': True,
                    'account_id': identity.get('Account', 'Unknown'),
                    'arn': identity.get('Arn', 'Unknown'),
                    'user_id': identity.get('UserId', 'Unknown'),
                    'error': None,
                }
            )
        else:
            # Command failed - provide helpful error message for SSO
            error_msg = process.stderr.strip()
            if profile and ('sso' in error_msg.lower() or 'token' in error_msg.lower()):
                error_msg += f'\n\nTo fix SSO token issues, run: aws sso login --profile {profile}'
            result.update({'error': error_msg, 'error_code': process.returncode})
    except Exception as e:
        # Exception occurred
        result.update({'error': str(e), 'exception': True})

    return result


def list_aws_profiles() -> Dict[str, Any]:
    """List available AWS profiles from the AWS config and credentials files.

    Returns:
        Dictionary with profile information
    """
    profiles = {}
    config_file = os.path.expanduser('~/.aws/config')
    credentials_file = os.path.expanduser('~/.aws/credentials')

    # Check if config file exists and read profiles
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                lines = f.readlines()

            current_profile = None
            for line in lines:
                line = line.strip()
                if line.startswith('[profile ') and line.endswith(']'):
                    current_profile = line[9:-1]  # Extract profile name
                    profiles[current_profile] = {'source': 'config'}
                elif (
                    line.startswith('[')
                    and line.endswith(']')
                    and not line.startswith('[profile ')
                ):
                    current_profile = line[1:-1]  # Extract profile name
                    if current_profile != 'default':
                        profiles[current_profile] = {'source': 'config'}
                elif current_profile and '=' in line:
                    key, value = [x.strip() for x in line.split('=', 1)]
                    if current_profile in profiles:
                        profiles[current_profile][key] = value
        except Exception as e:
            return {'error': f'Error reading AWS config file: {str(e)}'}

    # Check if credentials file exists and read profiles
    if os.path.exists(credentials_file):
        try:
            with open(credentials_file, 'r') as f:
                lines = f.readlines()

            current_profile = None
            for line in lines:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_profile = line[1:-1]  # Extract profile name
                    if current_profile not in profiles:
                        profiles[current_profile] = {'source': 'credentials'}
                    else:
                        profiles[current_profile]['source'] = 'both'
                elif current_profile and '=' in line:
                    key, value = [x.strip() for x in line.split('=', 1)]
                    if current_profile in profiles:
                        # Don't store actual credentials, just mark that they exist
                        if key in ['aws_access_key_id', 'aws_secret_access_key']:
                            profiles[current_profile][key] = '[CREDENTIAL AVAILABLE]'
                        else:
                            profiles[current_profile][key] = value
        except Exception as e:
            return {'error': f'Error reading AWS credentials file: {str(e)}'}

    return {
        'profiles': profiles,
        'config_file': config_file,
        'credentials_file': credentials_file,
        'count': len(profiles),
    }


def update_environment_variable(name: str, value: str) -> Dict[str, Any]:
    """Update an environment variable for the current process.

    Args:
        name: The name of the environment variable
        value: The value to set

    Returns:
        Dictionary with update status information
    """
    try:
        # Update the environment variable for the current process
        os.environ[name] = value

        # Return success
        return {
            'success': True,
            'name': name,
            'value': value,
            'message': f'Environment variable {name} updated successfully.',
        }
    except Exception as e:
        # Return error
        return {
            'success': False,
            'name': name,
            'error': str(e),
            'message': f'Failed to update environment variable {name}: {str(e)}',
        }
