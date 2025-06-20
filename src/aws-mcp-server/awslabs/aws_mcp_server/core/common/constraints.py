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

import abc
from .models import ActionType, ApiType, IRTranslation


class Constraint(abc.ABC):
    """Abstract base class for constraints on IRTranslation objects."""

    @property
    def name(self):
        """Return the name of the constraint class."""
        return self.__class__.__name__

    @abc.abstractmethod
    def verify(self, ir: IRTranslation) -> bool:
        """Verify if the given IR matches the constraint represented by this class."""

    def __str__(self):
        """Return the string representation of the constraint."""
        return f'{self.name}'


class ReadOnlyConstraint(Constraint):
    """Constraint to verify that the given IR is read-only."""

    @property
    def name(self):
        """Return the name of the constraint class."""
        return 'Command is not Read Only'

    def verify(self, ir: IRTranslation) -> bool:
        """Return True if all action types in the IR are read-only."""
        if not ir.classification:
            return False
        return all(
            action_type == ActionType.READ_ONLY for action_type in ir.classification.action_types
        )


class ControlPlaneConstraint(Constraint):
    """Constraint to verify that the given IR is for control plane API."""

    @property
    def name(self):
        """Return the name of the constraint class."""
        return 'Command is not Control Plane'

    def verify(self, ir: IRTranslation) -> bool:
        """Return True if the IR's API type is management (control plane)."""
        if not ir.classification:
            return False
        api_type = ir.classification.api_type
        return api_type == ApiType.MANAGEMENT


# Streaming output support isn't implemented
class UnsupportedStreamingOutputContraint(Constraint):
    """Constraint to verify that the given IR has no streaming output body."""

    @property
    def name(self):
        """Return the name of the constraint class."""
        return 'Command has streaming output'

    def verify(self, ir: IRTranslation) -> bool:
        """Return True if the IR does not have streaming output."""
        if not ir.command_metadata:
            return False
        return not ir.command_metadata.has_streaming_output


class AllowEverything(Constraint):
    """Constraint that verifies everything."""

    @property
    def name(self):
        """Return the name of the constraint class."""
        return 'You will never see this error'

    def verify(self, ir: IRTranslation) -> bool:
        """Always return True, allowing everything."""
        return True


def verify_constraints_on_ir(ir: IRTranslation, constraints: list[Constraint]) -> list[str]:
    """Verify the given constraints against the given intermediate representation.

    Returns a list of strings representing the constraints that failed.
    """
    return [constraint.name for constraint in constraints if not constraint.verify(ir)]


ValidationsConfiguration = [
    AllowEverything(),
]
