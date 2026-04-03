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


class BaseTool:
    """Base class for MCP tools."""

    def __init__(self, allow_write=None, allow_sensitive_data_access=None):
        """Initialize instance variables. None value means that the flag does not apply for the given tool."""
        self.allow_write = allow_write
        self.sensitive_data_access = allow_sensitive_data_access

    def checkToolAccess(self):
        """Checks if access to the tool is allowed based on allow-write and allow-sensitive-access flags."""
        if self.allow_write is False:
            raise Exception(
                'Write operations are not allowed. Set --allow-write flag to true to enable write operations.'
            )
        if self.sensitive_data_access is False:
            raise Exception(
                'Sensitive data access is not allowed. Set --allow-sensitive-data-access flag to true to access logs.'
            )

    @staticmethod
    def require_user_confirmation(
        operation_description: str, resources_affected: list | None = None
    ) -> dict:
        """Generate user confirmation requirement for mutating operations.

        Args:
            operation_description: Description of the operation requiring confirmation
            resources_affected: List of AWS resources that will be affected

        Returns:
            Dict containing confirmation requirements and safety warnings
        """
        return {
            'USER_CONFIRMATION_REQUIRED': True,
            'operation': operation_description,
            'resources_affected': resources_affected if resources_affected is not None else [],
            'confirmation_prompt': f'Do you want to proceed with: {operation_description}?',
            'safety_warning': 'This operation will make changes to your AWS infrastructure',
            'required_response': 'User must explicitly respond "yes" or "confirm" to proceed',
            'deployment_note': 'Use sam_deploy tool ONLY after user confirmation',
            'cancellation_note': 'If user declines, do not proceed with deployment',
        }

    @staticmethod
    def scrub_response_data(response: dict) -> dict:
        """Scrub sensitive data from tool responses before returning to LLM.

        Args:
            response: The response dictionary to scrub

        Returns:
            Scrubbed response with sensitive data redacted
        """
        from awslabs.aws_serverless_mcp_server.utils.data_scrubber import DataScrubber

        return DataScrubber.scrub_dict(response)
