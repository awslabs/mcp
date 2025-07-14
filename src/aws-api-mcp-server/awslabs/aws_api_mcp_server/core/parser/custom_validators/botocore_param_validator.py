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

import re
from botocore.validate import ParamValidator, ValidationErrors, range_check, type_check
from loguru import logger


def max_range_check(name, value, shape, error_type, errors):
    """Check if the value exceeds the maximum allowed by the shape."""
    if 'max' in shape.metadata:
        max_allowed = shape.metadata['max']
        if value > max_allowed:
            errors.report(name, error_type, param=value, max_allowed=max_allowed)


def pattern_check(name, value, shape, error_type, errors):
    """Check if the value matches the pattern in the shape."""
    if 'pattern' in shape.metadata:
        try:
            if not re.fullmatch(shape.metadata['pattern'], value):
                errors.report(name, error_type, param=value, pattern=shape.metadata['pattern'])
        except Exception as e:
            logger.warning(f'Unable to match pattern {shape.metadata["pattern"]} : {e}')


class BotoCoreValidationErrors(ValidationErrors):
    """Custom validation errors for botocore parameter validation."""

    def _format_error(self, error):
        """Format a validation error for display."""
        error_type, name, additional = error
        if error_type == 'invalid length' and 'max_allowed' in additional:
            param = additional['param']
            max_allowed = additional['max_allowed']
            return (
                f'Invalid length for parameter {name}, value: {param}, '
                f'valid max length: {max_allowed}'
            )
        if error_type == 'invalid pattern':
            param = additional['param']
            pattern = additional['pattern']
            return (
                f'Invalid pattern for parameter {name}, value: {param}, valid pattern: {pattern}'
            )
        return super()._format_error(error)


class BotoCoreParamValidator(ParamValidator):
    """Custom parameter validator for botocore."""

    def validate(self, params, shape):
        """Validate the parameters against the given shape."""
        errors = BotoCoreValidationErrors()
        self._validate(params, shape, errors, name='')
        return errors

    @type_check(valid_types=(str,))
    def _validate_string(self, param, shape, errors, name):
        range_check(name, len(param), shape, 'invalid length', errors)
        max_range_check(name, len(param), shape, 'invalid length', errors)
        pattern_check(name, param, shape, 'invalid pattern', errors)
