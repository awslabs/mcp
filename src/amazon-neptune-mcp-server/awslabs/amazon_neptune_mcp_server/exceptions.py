# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
from typing import Any, Dict, Union


class NeptuneException(Exception):
    """Exception class for Neptune-related errors.

    This exception is raised when operations on Neptune graphs fail,
    providing structured error information including a message and details.

    Args:
        exception (Union[str, Dict]): Either a string message or a dictionary
            containing 'message' and 'details' keys
    """

    def __init__(self, exception: Union[str, Dict]):
        """Initialize a new NeptuneException.

        Args:
            exception (Union[str, Dict]): Either a string message or a dictionary
                containing 'message' and 'details' keys
        """
        if isinstance(exception, dict):
            self.message = exception['message'] if 'message' in exception else 'unknown'
            self.details = exception['details'] if 'details' in exception else 'unknown'
        else:
            self.message = exception
            self.details = 'unknown'

    def get_message(self) -> str:
        """Get the exception message.

        Returns:
            str: The exception message
        """
        return self.message

    def get_details(self) -> Any:
        """Get the exception details.

        Returns:
            Any: Additional details about the exception
        """
        return self.details
