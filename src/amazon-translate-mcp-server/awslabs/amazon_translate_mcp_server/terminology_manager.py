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

"""Terminology Manager for Amazon Translate MCP Server.

This module provides comprehensive terminology management capabilities including
listing, creating, importing, and retrieving custom terminologies for Amazon Translate.
Supports CSV and TMX formats with validation and conflict resolution.
"""

import csv
import defusedxml.ElementTree as ET
import io
import logging
import re
from .aws_client import AWSClientManager
from .models import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
    TerminologyData,
    TerminologyDetails,
    TerminologyError,
    TerminologySummary,
    ValidationError,
)
from botocore.exceptions import BotoCoreError, ClientError
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


logger = logging.getLogger(__name__)


class TerminologyManager:
    """Manages custom terminology operations for Amazon Translate.

    This class provides methods for listing, creating, importing, and retrieving
    custom terminologies. It supports CSV and TMX file formats with comprehensive
    validation and conflict resolution capabilities.
    """

    # Supported file formats
    SUPPORTED_FORMATS = {'CSV', 'TMX'}

    # Maximum terminology size (10MB)
    MAX_TERMINOLOGY_SIZE = 10 * 1024 * 1024

    # Maximum number of terminologies per account
    MAX_TERMINOLOGIES = 100

    # Maximum term pairs per terminology
    MAX_TERM_PAIRS = 10000

    # Supported language codes pattern
    LANGUAGE_CODE_PATTERN = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')

    def __init__(self, aws_client_manager: AWSClientManager):
        """Initialize the Terminology Manager.

        Args:
            aws_client_manager: AWS client manager instance for service access

        """
        self._aws_client_manager = aws_client_manager
        self._translate_client = None

    def _get_translate_client(self):
        """Get or create Amazon Translate client."""
        if self._translate_client is None:
            self._translate_client = self._aws_client_manager.get_translate_client()
        return self._translate_client

    def list_terminologies(
        self, max_results: int = 50, next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all available terminologies.

        Args:
            max_results: Maximum number of terminologies to return (1-500)
            next_token: Token for pagination

        Returns:
            Dictionary containing list of terminology summaries and next token

        Raises:
            ValidationError: If parameters are invalid
            AuthenticationError: If AWS credentials are invalid
            ServiceUnavailableError: If Translate service is unavailable
            TerminologyError: If terminology listing fails

        """
        # Validate parameters
        if not isinstance(max_results, int) or max_results < 1 or max_results > 500:
            raise ValidationError(
                'max_results must be an integer between 1 and 500', field='max_results'
            )

        if next_token is not None and not isinstance(next_token, str):
            raise ValidationError('next_token must be a string', field='next_token')

        try:
            client = self._get_translate_client()

            # Prepare request parameters
            params: Dict[str, Any] = {'MaxResults': max_results}
            if next_token:
                params['NextToken'] = next_token

            logger.debug('Listing terminologies with params: %s', params)

            # Call AWS Translate API
            response = client.list_terminologies(**params)

            # Parse response
            terminologies = []
            for term_props in response.get('TerminologyPropertiesList', []):
                terminology = TerminologySummary(
                    name=term_props['Name'],
                    description=term_props.get('Description', ''),
                    source_language=term_props['SourceLanguageCode'],
                    target_languages=term_props['TargetLanguageCodes'],
                    term_count=term_props['TermCount'],
                    created_at=term_props.get('CreatedAt'),
                )
                terminologies.append(terminology)

            result = {'terminologies': terminologies, 'next_token': response.get('NextToken')}

            logger.info('Listed %d terminologies', len(terminologies))
            return result

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'AccessDeniedException':
                raise AuthenticationError(
                    f'Access denied for terminology listing: {error_message}',
                    details={'error_code': error_code},
                )
            elif error_code == 'ThrottlingException':
                raise RateLimitError(
                    f'Rate limit exceeded for terminology listing: {error_message}',
                    retry_after=60,
                    details={'error_code': error_code},
                )
            else:
                raise TerminologyError(
                    f'Failed to list terminologies: {error_message}',
                    details={'error_code': error_code},
                )

        except BotoCoreError as e:
            raise ServiceUnavailableError(
                f'BotoCore error listing terminologies: {str(e)}',
                service='translate',
                details={'error_type': type(e).__name__},
            )

        except Exception as e:
            raise TerminologyError(
                f'Unexpected error listing terminologies: {str(e)}',
                details={'error_type': type(e).__name__},
            )

    def create_terminology(
        self,
        name: str,
        description: str,
        terminology_data: TerminologyData,
        encryption_key: Optional[str] = None,
    ) -> str:
        """Create a new custom terminology.

        Args:
            name: Terminology name (must be unique)
            description: Terminology description
            terminology_data: Terminology data with format and content
            encryption_key: Optional KMS key for encryption

        Returns:
            Terminology ARN

        Raises:
            ValidationError: If parameters are invalid
            AuthenticationError: If AWS credentials are invalid
            ServiceUnavailableError: If Translate service is unavailable
            TerminologyError: If terminology creation fails
            QuotaExceededError: If terminology limits are exceeded

        """
        # Validate parameters
        self._validate_terminology_name(name)
        self._validate_terminology_description(description)
        self._validate_terminology_data(terminology_data)

        if encryption_key is not None and not isinstance(encryption_key, str):
            raise ValidationError('encryption_key must be a string', field='encryption_key')

        try:
            client = self._get_translate_client()

            # Prepare request parameters
            params = {
                'Name': name,
                'Description': description,
                'TerminologyData': {
                    'File': terminology_data.terminology_data,
                    'Format': terminology_data.format,
                    'Directionality': terminology_data.directionality,
                },
            }

            if encryption_key:
                params['EncryptionKey'] = {'Type': 'KMS', 'Id': encryption_key}

            logger.debug("Creating terminology '%s' with format %s", name, terminology_data.format)

            # Call AWS Translate API
            response = client.import_terminology(**params)

            terminology_arn = response['TerminologyProperties']['Arn']

            logger.info("Created terminology '%s' with ARN: %s", name, terminology_arn)
            return terminology_arn

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'AccessDeniedException':
                raise AuthenticationError(
                    f'Access denied for terminology creation: {error_message}',
                    details={'error_code': error_code, 'terminology_name': name},
                )
            elif error_code == 'ConflictException':
                raise TerminologyError(
                    f"Terminology '{name}' already exists: {error_message}",
                    terminology_name=name,
                    details={'error_code': error_code},
                )
            elif error_code == 'LimitExceededException':
                raise QuotaExceededError(
                    f'Terminology limit exceeded: {error_message}',
                    quota_type='terminologies',
                    details={'error_code': error_code},
                )
            elif error_code == 'InvalidParameterValueException':
                raise ValidationError(
                    f'Invalid terminology data: {error_message}',
                    details={'error_code': error_code, 'terminology_name': name},
                )
            elif error_code == 'ThrottlingException':
                raise RateLimitError(
                    f'Rate limit exceeded for terminology creation: {error_message}',
                    retry_after=60,
                    details={'error_code': error_code},
                )
            else:
                raise TerminologyError(
                    f"Failed to create terminology '{name}': {error_message}",
                    terminology_name=name,
                    details={'error_code': error_code},
                )

        except BotoCoreError as e:
            raise ServiceUnavailableError(
                f'BotoCore error creating terminology: {str(e)}',
                service='translate',
                details={'error_type': type(e).__name__, 'terminology_name': name},
            )

        except Exception as e:
            raise TerminologyError(
                f"Unexpected error creating terminology '{name}': {str(e)}",
                terminology_name=name,
                details={'error_type': type(e).__name__},
            )

    def import_terminology(
        self,
        name: str,
        file_path: str,
        description: str = '',
        source_language: Optional[str] = None,
        target_languages: Optional[List[str]] = None,
        format_type: Optional[str] = None,
        directionality: str = 'UNI',
        encryption_key: Optional[str] = None,
    ) -> str:
        """Import terminology from a file.

        Args:
            name: Terminology name (must be unique)
            file_path: Path to terminology file (CSV or TMX)
            description: Terminology description
            source_language: Source language code (auto-detected if not provided)
            target_languages: Target language codes (auto-detected if not provided)
            format_type: File format ('CSV' or 'TMX', auto-detected if not provided)
            directionality: Terminology directionality ('UNI' or 'MULTI')
            encryption_key: Optional KMS key for encryption

        Returns:
            Terminology ARN

        Raises:
            ValidationError: If parameters or file format are invalid
            FileNotFoundError: If file doesn't exist
            TerminologyError: If terminology import fails

        """
        # Validate parameters
        self._validate_terminology_name(name)

        if not isinstance(file_path, str) or not file_path.strip():
            raise ValidationError('file_path cannot be empty', field='file_path')

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f'Terminology file not found: {file_path}')

        if not file_path_obj.is_file():
            raise ValidationError(f'Path is not a file: {file_path}', field='file_path')

        # Read and validate file
        try:
            with open(file_path_obj, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            raise TerminologyError(
                f'Failed to read terminology file: {str(e)}',
                terminology_name=name,
                details={'file_path': file_path},
            )

        # Auto-detect format if not provided
        if format_type is None:
            format_type = self._detect_file_format(file_path_obj, file_content)

        # Validate file content and extract metadata
        validation_result = self._validate_terminology_file(
            file_content, format_type, source_language, target_languages
        )

        # Use detected languages if not provided
        if source_language is None:
            source_lang = validation_result.get('source_language')
            source_language = source_lang if isinstance(source_lang, str) else None
        if target_languages is None:
            target_langs = validation_result.get('target_languages')
            target_languages = target_langs if isinstance(target_langs, list) else None

        # Create terminology data
        terminology_data = TerminologyData(
            terminology_data=file_content, format=format_type, directionality=directionality
        )

        # Use file name as description if not provided
        if not description:
            description = f'Imported from {file_path_obj.name}'

        logger.info(
            "Importing terminology '%s' from file '%s' (format: %s, terms: %d)",
            name,
            file_path,
            format_type,
            validation_result['term_count'],
        )

        # Create the terminology
        return self.create_terminology(name, description, terminology_data, encryption_key)

    def get_terminology(
        self, name: str, terminology_data_format: str = 'CSV'
    ) -> TerminologyDetails:
        """Get detailed information about a terminology.

        Args:
            name: Terminology name
            terminology_data_format: Format for returned terminology data ('CSV' or 'TMX')

        Returns:
            Detailed terminology information

        Raises:
            ValidationError: If parameters are invalid
            AuthenticationError: If AWS credentials are invalid
            ServiceUnavailableError: If Translate service is unavailable
            TerminologyError: If terminology retrieval fails

        """
        # Validate parameters
        self._validate_terminology_name(name)

        if terminology_data_format not in self.SUPPORTED_FORMATS:
            raise ValidationError(
                f'terminology_data_format must be one of {self.SUPPORTED_FORMATS}',
                field='terminology_data_format',
            )

        try:
            client = self._get_translate_client()

            logger.debug("Getting terminology '%s' in format %s", name, terminology_data_format)

            # Call AWS Translate API
            response = client.get_terminology(
                Name=name, TerminologyDataFormat=terminology_data_format
            )

            # Parse response
            props = response['TerminologyProperties']
            terminology_details = TerminologyDetails(
                name=props['Name'],
                description=props.get('Description', ''),
                source_language=props['SourceLanguageCode'],
                target_languages=props['TargetLanguageCodes'],
                term_count=props['TermCount'],
                created_at=props.get('CreatedAt'),
                last_updated=props.get('LastUpdatedAt'),
                size_bytes=props.get('SizeBytes'),
                format=props.get('Format'),
            )

            logger.info(
                "Retrieved terminology '%s' with %d terms", name, terminology_details.term_count
            )
            return terminology_details

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'ResourceNotFoundException':
                raise TerminologyError(
                    f"Terminology '{name}' not found: {error_message}",
                    terminology_name=name,
                    details={'error_code': error_code},
                )
            elif error_code == 'AccessDeniedException':
                raise AuthenticationError(
                    f'Access denied for terminology retrieval: {error_message}',
                    details={'error_code': error_code, 'terminology_name': name},
                )
            elif error_code == 'ThrottlingException':
                raise RateLimitError(
                    f'Rate limit exceeded for terminology retrieval: {error_message}',
                    retry_after=60,
                    details={'error_code': error_code},
                )
            else:
                raise TerminologyError(
                    f"Failed to get terminology '{name}': {error_message}",
                    terminology_name=name,
                    details={'error_code': error_code},
                )

        except BotoCoreError as e:
            raise ServiceUnavailableError(
                f'BotoCore error getting terminology: {str(e)}',
                service='translate',
                details={'error_type': type(e).__name__, 'terminology_name': name},
            )

        except Exception as e:
            raise TerminologyError(
                f"Unexpected error getting terminology '{name}': {str(e)}",
                terminology_name=name,
                details={'error_type': type(e).__name__},
            )

    def delete_terminology(self, name: str) -> bool:
        """Delete a terminology.

        Args:
            name: Terminology name

        Returns:
            True if deletion was successful

        Raises:
            ValidationError: If parameters are invalid
            AuthenticationError: If AWS credentials are invalid
            ServiceUnavailableError: If Translate service is unavailable
            TerminologyError: If terminology deletion fails

        """
        # Validate parameters
        self._validate_terminology_name(name)

        try:
            client = self._get_translate_client()

            logger.debug("Deleting terminology '%s'", name)

            # Call AWS Translate API
            client.delete_terminology(Name=name)

            logger.info("Deleted terminology '%s'", name)
            return True

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'ResourceNotFoundException':
                raise TerminologyError(
                    f"Terminology '{name}' not found: {error_message}",
                    terminology_name=name,
                    details={'error_code': error_code},
                )
            elif error_code == 'AccessDeniedException':
                raise AuthenticationError(
                    f'Access denied for terminology deletion: {error_message}',
                    details={'error_code': error_code, 'terminology_name': name},
                )
            elif error_code == 'ThrottlingException':
                raise RateLimitError(
                    f'Rate limit exceeded for terminology deletion: {error_message}',
                    retry_after=60,
                    details={'error_code': error_code},
                )
            else:
                raise TerminologyError(
                    f"Failed to delete terminology '{name}': {error_message}",
                    terminology_name=name,
                    details={'error_code': error_code},
                )

        except BotoCoreError as e:
            raise ServiceUnavailableError(
                f'BotoCore error deleting terminology: {str(e)}',
                service='translate',
                details={'error_type': type(e).__name__, 'terminology_name': name},
            )

        except Exception as e:
            raise TerminologyError(
                f"Unexpected error deleting terminology '{name}': {str(e)}",
                terminology_name=name,
                details={'error_type': type(e).__name__},
            )

    def validate_terminology_conflicts(
        self, terminology_names: List[str], source_language: str, target_language: str
    ) -> Dict[str, List[str]]:
        """Validate terminology conflicts for a language pair.

        Args:
            terminology_names: List of terminology names to check
            source_language: Source language code
            target_language: Target language code

        Returns:
            Dictionary with conflict information

        Raises:
            ValidationError: If parameters are invalid
            TerminologyError: If validation fails

        """
        # Validate parameters
        if not isinstance(terminology_names, list) or not terminology_names:
            raise ValidationError(
                'terminology_names must be a non-empty list', field='terminology_names'
            )

        self._validate_language_code(source_language, 'source_language')
        self._validate_language_code(target_language, 'target_language')

        conflicts = {'compatible': [], 'incompatible': [], 'not_found': []}

        for name in terminology_names:
            try:
                terminology = self.get_terminology(name)

                # Check language compatibility
                if (
                    terminology.source_language == source_language
                    and target_language in terminology.target_languages
                ):
                    conflicts['compatible'].append(name)
                else:
                    conflicts['incompatible'].append(name)

            except TerminologyError as e:
                if 'not found' in str(e).lower():
                    conflicts['not_found'].append(name)
                else:
                    raise

        logger.debug(
            'Terminology conflict validation for %s->%s: %s',
            source_language,
            target_language,
            conflicts,
        )

        return conflicts

    def _validate_terminology_name(self, name: str) -> None:
        """Validate terminology name."""
        if not isinstance(name, str) or not name.strip():
            raise ValidationError('Terminology name cannot be empty', field='name')

        if len(name) > 256:
            raise ValidationError('Terminology name cannot exceed 256 characters', field='name')

        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValidationError(
                'Terminology name can only contain alphanumeric characters, hyphens, and underscores',
                field='name',
            )

    def _validate_terminology_description(self, description: str) -> None:
        """Validate terminology description."""
        if not isinstance(description, str):
            raise ValidationError('Description must be a string', field='description')

        if len(description) > 256:
            raise ValidationError('Description cannot exceed 256 characters', field='description')

    def _validate_terminology_data(self, terminology_data: TerminologyData) -> None:
        """Validate terminology data."""
        if not isinstance(terminology_data, TerminologyData):
            raise ValidationError('terminology_data must be a TerminologyData instance')

        if len(terminology_data.terminology_data) > self.MAX_TERMINOLOGY_SIZE:
            raise ValidationError(
                f'Terminology data cannot exceed {self.MAX_TERMINOLOGY_SIZE} bytes',
                field='terminology_data',
            )

    def _validate_language_code(self, language_code: str, field_name: str) -> None:
        """Validate language code format."""
        if not isinstance(language_code, str) or not language_code.strip():
            raise ValidationError(f'{field_name} cannot be empty', field=field_name)

        if not self.LANGUAGE_CODE_PATTERN.match(language_code):
            raise ValidationError(
                f'Invalid language code format: {language_code}', field=field_name
            )

    def _detect_file_format(self, file_path: Path, file_content: bytes) -> str:
        """Detect file format based on extension and content."""
        # Check file extension first
        extension = file_path.suffix.lower()
        if extension == '.csv':
            return 'CSV'
        elif extension in ['.tmx', '.xml']:
            return 'TMX'

        # Try to detect from content
        try:
            # Try to decode as text
            text_content = file_content.decode('utf-8')

            # Check for TMX XML structure
            if '<?xml' in text_content and '<tmx' in text_content:
                return 'TMX'

            # Check for CSV structure (comma-separated values)
            if ',' in text_content and '\n' in text_content:
                return 'CSV'

        except UnicodeDecodeError:
            pass

        # Default to CSV if unable to detect
        logger.warning('Unable to detect file format for %s, defaulting to CSV', file_path)
        return 'CSV'

    def _validate_terminology_file(
        self,
        file_content: bytes,
        format_type: str,
        source_language: Optional[str] = None,
        target_languages: Optional[List[str]] = None,
    ) -> Dict[str, Union[str, List[str], int]]:
        """Validate terminology file content and extract metadata.

        Returns:
            Dictionary with validation results and metadata

        """
        if format_type == 'CSV':
            return self._validate_csv_file(file_content, source_language, target_languages)
        elif format_type == 'TMX':
            return self._validate_tmx_file(file_content, source_language, target_languages)
        else:
            raise ValidationError(f'Unsupported format: {format_type}')

    def _validate_csv_file(
        self,
        file_content: bytes,
        source_language: Optional[str] = None,
        target_languages: Optional[List[str]] = None,
    ) -> Dict[str, Union[str, List[str], int]]:
        """Validate CSV terminology file."""
        try:
            # Decode content
            text_content = file_content.decode('utf-8')

            # Parse CSV
            csv_reader = csv.reader(io.StringIO(text_content))
            rows = list(csv_reader)

            if not rows:
                raise ValidationError('CSV file is empty')

            # Check header row
            header = rows[0]
            if len(header) < 2:
                raise ValidationError(
                    'CSV file must have at least 2 columns (source and target terms)'
                )

            # Extract language codes from header if available
            detected_source = source_language
            detected_targets = target_languages or []

            # If languages not provided, try to detect from header
            if not detected_source or not detected_targets:
                # Simple heuristic: if header contains language codes, use them
                for col in header:
                    if self.LANGUAGE_CODE_PATTERN.match(col):
                        if not detected_source:
                            detected_source = col
                        elif col not in detected_targets:
                            detected_targets.append(col)

            # Default to common language codes if still not detected
            if not detected_source:
                detected_source = 'en'  # Default to English
            if not detected_targets:
                detected_targets = ['es']  # Default to Spanish

            # Count term pairs
            term_count = max(0, len(rows) - 1)  # Exclude header

            if term_count > self.MAX_TERM_PAIRS:
                raise ValidationError(
                    f'CSV file contains too many term pairs (max: {self.MAX_TERM_PAIRS})'
                )

            # Validate some sample rows
            for i, row in enumerate(rows[1:6]):  # Check first 5 data rows
                if len(row) < 2:
                    raise ValidationError(f'Row {i + 2} has insufficient columns')
                if not row[0].strip() or not row[1].strip():
                    raise ValidationError(f'Row {i + 2} contains empty terms')

            return {
                'source_language': detected_source,
                'target_languages': detected_targets,
                'term_count': term_count,
            }

        except UnicodeDecodeError as e:
            raise ValidationError(f'CSV file encoding error: {str(e)}')
        except csv.Error as e:
            raise ValidationError(f'CSV parsing error: {str(e)}')
        except Exception as e:
            raise ValidationError(f'CSV validation error: {str(e)}')

    def _validate_tmx_file(
        self,
        file_content: bytes,
        source_language: Optional[str] = None,
        target_languages: Optional[List[str]] = None,
    ) -> Dict[str, Union[str, List[str], int]]:
        """Validate TMX terminology file."""
        try:
            # Parse XML using defusedxml (safe from XML attacks)
            root = ET.fromstring(file_content)  # nosec B314

            # Check TMX structure
            if root.tag != 'tmx':
                raise ValidationError('File is not a valid TMX file (missing tmx root element)')

            # Find body element
            body = root.find('body')
            if body is None:
                raise ValidationError('TMX file missing body element')

            # Extract language codes and count translation units
            languages_found = set()
            term_count = 0

            for tu in body.findall('tu'):
                term_count += 1

                # Extract languages from translation variants
                for tuv in tu.findall('tuv'):
                    lang = tuv.get('xml:lang') or tuv.get('lang')
                    if lang:
                        languages_found.add(lang)

            if term_count > self.MAX_TERM_PAIRS:
                raise ValidationError(
                    f'TMX file contains too many term pairs (max: {self.MAX_TERM_PAIRS})'
                )

            # Determine source and target languages
            languages_list = list(languages_found)
            detected_source = source_language or (languages_list[0] if languages_list else 'en')
            detected_targets = target_languages or [
                lang for lang in languages_list if lang != detected_source
            ]

            if not detected_targets:
                detected_targets = ['es']  # Default fallback

            return {
                'source_language': detected_source,
                'target_languages': detected_targets,
                'term_count': term_count,
            }

        except ET.ParseError as e:
            raise ValidationError(f'TMX XML parsing error: {str(e)}')
        except Exception as e:
            raise ValidationError(f'TMX validation error: {str(e)}')
