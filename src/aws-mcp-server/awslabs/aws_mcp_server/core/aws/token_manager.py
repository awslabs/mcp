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

import secrets
import time


class TokenManager:
    """Manages consent tokens for AWS CLI operations that require explicit user consent.

    Tokens are generated with a configurable expiration time and stored in memory.
    Each token is associated with the service and API it was generated for.
    """

    EXPIRY_TIME_IN_SECONDS = 300

    def __init__(self, token_expiry_seconds: int = EXPIRY_TIME_IN_SECONDS):
        """Initialize the TokenManager.

        Args:
            token_expiry_seconds: Time in seconds after which a token expires
        """
        # Store both expiry time and command for each token
        self._tokens: dict[str, tuple[float, str]] = {}
        self._token_expiry_seconds = token_expiry_seconds

    def _extract_command_signature(self, command: str) -> str:
        """Extract the service and API signature from a command.

        Args:
            command: The AWS CLI command

        Returns:
            A string containing the first three tokens of the command (aws + service + operation)
        """
        # Split the command and take the first three tokens (aws + service + operation)
        tokens = command.split()
        if len(tokens) >= 3:
            return ' '.join(tokens[:3])
        return command  # Return the full command if it has fewer than 3 tokens

    def generate_token(self, command: str) -> str:
        """Generate a new consent token for a specific command.

        Args:
            command: The AWS CLI command that requires consent

        Returns:
            A unique token string
        """
        # Generate a secure random token
        token = secrets.token_hex(16)

        # Extract the command signature (service and API)
        command_signature = self._extract_command_signature(command)

        # Store the token with its expiration time and the command signature
        expiry_time = time.time() + self._token_expiry_seconds
        self._tokens[token] = (expiry_time, command_signature)

        return token

    def validate_token(self, token: str, command: str) -> bool:
        """Validate if a token exists, has not expired, and matches the command signature.

        Args:
            token: The token to validate
            command: The command to validate against the stored command signature

        Returns:
            True if the token is valid for the given command signature, False otherwise
        """
        stored_token = self._tokens.get(token)
        if not stored_token:
            return False

        expiry_time, stored_command_signature = stored_token

        # Check if the token has expired
        if time.time() > expiry_time:
            # Remove expired token
            self._tokens.pop(token)
            return False

        # Extract the command signature from the current command
        command_signature = self._extract_command_signature(command)

        # Return if the command signature matches
        return command_signature == stored_command_signature

    def find_valid_token_for_command(self, command: str) -> str | None:
        """Find a valid token for a command based on its signature.

        Args:
            command: The AWS CLI command to find a token for

        Returns:
            A valid token if one exists for the command signature, None otherwise
        """
        command_signature = self._extract_command_signature(command)
        current_time = time.time()

        # Return the first valid token if any exist
        return next(
            (
                token
                for token, (expiry_time, stored_signature) in self._tokens.items()
                if current_time <= expiry_time and stored_signature == command_signature
            ),
            None,
        )

    def has_valid_token_for_command(self, command: str) -> bool:
        """Check if there is a valid token for a command based on its signature.

        Args:
            command: The AWS CLI command to check for valid tokens

        Returns:
            True if a valid token exists for the command signature, False otherwise
        """
        return self.find_valid_token_for_command(command) is not None

    def invalidate_token(self, token: str) -> None:
        """Invalidate a token after it has been used.

        Args:
            token: The token to invalidate
        """
        self._tokens.pop(token, None)

    def cleanup_expired_tokens(self) -> None:
        """Remove all expired tokens from the cache."""
        current_time = time.time()
        expired_tokens = [
            token for token, (expiry_time, _) in self._tokens.items() if current_time > expiry_time
        ]

        for token in expired_tokens:
            self._tokens.pop(token)
