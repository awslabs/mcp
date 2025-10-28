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

"""AWS IoT SiteWise Data Ingestion and Retrieval Tools."""

import json
from ..validation import (
    ValidationError,
    check_storage_configuration_requirements,
    validate_asset_id,
    validate_max_results,
    validate_property_alias,
    validate_region,
)
from awslabs.aws_iot_sitewise_mcp_server.client import create_iam_client, create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.server.fastmcp.tools import Tool
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, List, Optional


@tool_metadata(readonly=False)
def create_bulk_import_job(
    job_name: str = Field(
        ..., description='The unique name that identifies the job request (1-256 characters)'
    ),
    job_role_arn: Optional[str] = Field(
        None,
        description='The ARN of the IAM role that allows IoT SiteWise to read Amazon S3 data. If not provided, ask the user if you can use create_bulk_import_iam_role helper function to create one.',
    ),
    files: List[Dict[str, Any]] = Field(
        ...,
        description='List of files in Amazon S3 that contain your data. Each file should have "bucket", "key", and optionally "versionId" fields',
    ),
    error_report_location: Dict[str, str] = Field(
        ..., description='Amazon S3 destination for errors. Must have "bucket" and "prefix" fields'
    ),
    job_configuration: Dict[str, Any] = Field(
        ...,
        description='Job configuration including file format. For CSV: {"fileFormat": {"csv": {"columnNames": ["ALIAS", "ASSET_ID", ...]}}}',
    ),
    adaptive_ingestion: bool = Field(
        False,
        description='Set to true for buffered ingestion (triggers computations and notifications for data within 7 days). Set to false for historical data ingestion only',
    ),
    delete_files_after_import: bool = Field(
        False, description='Set to true to delete data files from S3 after successful ingestion'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Create a bulk import job to ingest data from Amazon S3 to AWS IoT SiteWise.

    This function creates a bulk import job with automatic validation of storage configuration
    requirements based on the adaptive_ingestion setting.

    When adaptive_ingestion is True, the job ingests new data and calculates metrics, transforms,
    and supports notifications for data with timestamps within seven days. No additional storage
    configuration is required.

    When adaptive_ingestion is False, the job performs historical data ingestion only and requires
    multilayer storage or warm tier to be enabled. The function automatically validates that the
    current storage configuration supports historical data ingestion.

    If job_role_arn is not provided, use the create_bulk_import_iam_role helper function to create
    an IAM role with the necessary S3 permissions for the data and error buckets.

    Args:
        job_name: Unique name for the job (1-256 characters, no control characters)
        job_role_arn: IAM role ARN that allows IoT SiteWise to read S3 data (optional - ask the user if you can use create_bulk_import_iam_role helper function to create one.)
        files: List of S3 file objects with bucket, key, and optional versionId. Ask the user to provide this if not included.
        error_report_location: S3 location for error reports (bucket and prefix). Ask the user to provide this if not included.
        job_configuration: Configuration including file format (CSV or Parquet). Ask the user to provide the column headers if it is a CSV file.
        adaptive_ingestion: Enable buffered ingestion mode. When False, requires multilayer storage or warm tier to be configured. Ask the user to provide this if not included.
        delete_files_after_import: Delete S3 files after ingestion (default: False)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing job creation response with jobId, jobName, and jobStatus

    Example:
        files = [{"bucket": "my-data-bucket", "key": "data/timeseries.csv"}]
        error_location = {"bucket": "my-error-bucket", "prefix": "errors/"}
        job_config = {
            "fileFormat": {
                "csv": {
                    "columnNames": ["ALIAS", "TIMESTAMP_SECONDS", "VALUE", "QUALITY"]
                }
            }
        }

        result = create_bulk_import_job(
            job_name="my-buffered-ingestion-job",
            job_role_arn="arn:aws:iam::123456789012:role/IoTSiteWiseRole",
            files=files,
            error_report_location=error_location,
            job_configuration=job_config,
            adaptive_ingestion=True
        )
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)

        # Validate job name
        if not job_name or len(job_name) < 1 or len(job_name) > 256:
            raise ValidationError('Job name must be between 1 and 256 characters')

        # Basic validation for control characters in job name
        if any(ord(c) < 32 or ord(c) == 127 for c in job_name):
            raise ValidationError('Job name cannot contain control characters')

        # Validate job role ARN format
        if not job_role_arn:
            raise ValidationError(
                'Job role ARN is required. I can help you create one - please ask me to create an IAM role with the necessary S3 permissions for your data and error buckets.'
            )

        if len(job_role_arn) < 1 or len(job_role_arn) > 1600:
            raise ValidationError('Job role ARN must be between 1 and 1600 characters')

        if not job_role_arn.startswith('arn:aws'):
            raise ValidationError('Job role ARN must be a valid AWS ARN')

        # Validate files list
        if not files or not isinstance(files, list):
            raise ValidationError('Files must be a non-empty list')

        for file_obj in files:
            if not isinstance(file_obj, dict):
                raise ValidationError('Each file must be a dictionary')
            if 'bucket' not in file_obj or 'key' not in file_obj:
                raise ValidationError('Each file must have "bucket" and "key" fields')
            if len(file_obj['bucket']) < 3 or len(file_obj['bucket']) > 63:
                raise ValidationError('S3 bucket name must be between 3 and 63 characters')

        # Validate error report location
        if not isinstance(error_report_location, dict):
            raise ValidationError('Error report location must be a dictionary')
        if 'bucket' not in error_report_location or 'prefix' not in error_report_location:
            raise ValidationError('Error report location must have "bucket" and "prefix" fields')
        if len(error_report_location['bucket']) < 3 or len(error_report_location['bucket']) > 63:
            raise ValidationError('Error report bucket name must be between 3 and 63 characters')
        if not error_report_location['prefix'].endswith('/'):
            raise ValidationError('Error report prefix must end with a forward slash (/)')

        # Validate job configuration
        if not isinstance(job_configuration, dict):
            raise ValidationError('Job configuration must be a dictionary')
        if 'fileFormat' not in job_configuration:
            raise ValidationError('Job configuration must have "fileFormat" field')

        file_format = job_configuration['fileFormat']
        if not isinstance(file_format, dict):
            raise ValidationError('File format must be a dictionary')

        # Validate CSV or Parquet format
        if 'csv' in file_format:
            csv_config = file_format['csv']
            if not isinstance(csv_config, dict) or 'columnNames' not in csv_config:
                raise ValidationError('CSV configuration must have "columnNames" field')
            if not isinstance(csv_config['columnNames'], list) or not csv_config['columnNames']:
                raise ValidationError('CSV columnNames must be a non-empty list')

            # Validate column names are from allowed set
            valid_columns = {
                'ASSET_ID',
                'ALIAS',
                'PROPERTY_ID',
                'DATA_TYPE',
                'TIMESTAMP_SECONDS',
                'TIMESTAMP_NANO_OFFSET',
                'QUALITY',
                'VALUE',
            }
            for col in csv_config['columnNames']:
                if col not in valid_columns:
                    raise ValidationError(
                        f'Invalid column name: {col}. Must be one of: {", ".join(valid_columns)}'
                    )

            # Validate required columns are present
            required_columns = {'TIMESTAMP_SECONDS', 'VALUE', 'DATA_TYPE'}
            has_asset_id = 'ASSET_ID' in csv_config['columnNames']
            has_property_id = 'PROPERTY_ID' in csv_config['columnNames']
            has_alias = 'ALIAS' in csv_config['columnNames']

            # Must have either (ASSET_ID + PROPERTY_ID) OR ALIAS, but not all three
            if has_asset_id and has_property_id and has_alias:
                raise ValidationError(
                    'CSV cannot include ASSET_ID, PROPERTY_ID, and ALIAS together'
                )
            elif has_asset_id and not has_property_id:
                raise ValidationError('CSV with ASSET_ID must also include PROPERTY_ID')
            elif has_property_id and not has_asset_id:
                raise ValidationError('CSV with PROPERTY_ID must also include ASSET_ID')
            elif not (has_alias or (has_asset_id and has_property_id)):
                raise ValidationError(
                    'CSV must include either ALIAS or both ASSET_ID and PROPERTY_ID'
                )

            missing_required = required_columns - set(csv_config['columnNames'])
            if missing_required:
                raise ValidationError(
                    f'CSV missing required columns: {", ".join(missing_required)}'
                )
        elif 'parquet' not in file_format:
            raise ValidationError('File format must specify either "csv" or "parquet"')

        client = create_sitewise_client(region)

        # Validate adaptive_ingestion is provided
        if not isinstance(adaptive_ingestion, bool):
            raise ValidationError('Please provide a boolean value for adaptive_ingestion')

        # Validate storage configuration requirements based on adaptive_ingestion setting
        check_storage_configuration_requirements(client, adaptive_ingestion)

        # Build the API parameters
        params = {
            'jobName': job_name,
            'jobRoleArn': job_role_arn,
            'files': files,
            'errorReportLocation': error_report_location,
            'jobConfiguration': job_configuration,
            'adaptiveIngestion': adaptive_ingestion,
            'deleteFilesAfterImport': delete_files_after_import,
        }

        response = client.create_bulk_import_job(**params)

        return {
            'success': True,
            'job_id': response['jobId'],
            'job_name': response['jobName'],
            'job_status': response['jobStatus'],
        }

    except ValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def create_buffered_ingestion_job(
    job_name: str = Field(
        ..., description='The unique name that identifies the job request (1-256 characters)'
    ),
    job_role_arn: str = Field(
        ..., description='The ARN of the IAM role that allows IoT SiteWise to read Amazon S3 data'
    ),
    files: List[Dict[str, Any]] = Field(
        ...,
        description='List of files in Amazon S3 that contain your data. Each file should have "bucket", "key", and optionally "versionId" fields',
    ),
    error_report_location: Dict[str, str] = Field(
        ..., description='Amazon S3 destination for errors. Must have "bucket" and "prefix" fields'
    ),
    job_configuration: Dict[str, Any] = Field(
        ...,
        description='Job configuration including file format. For CSV: {"fileFormat": {"csv": {"columnNames": ["ALIAS", "ASSET_ID", ...]}}}',
    ),
    delete_files_after_import: bool = Field(
        False, description='Set to true to delete data files from S3 after successful ingestion'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Create a buffered ingestion job to ingest data from Amazon S3 to AWS IoT SiteWise.

    This is a convenience function that calls create_bulk_import_job with adaptive_ingestion=True
    to enable buffered ingestion mode for real-time processing of recent data (within 30 days).

    Args:
        job_name: Unique name for the job (1-256 characters, no control characters)
        job_role_arn: IAM role ARN that allows IoT SiteWise to read S3 data (optional - ask the user if you can use create_bulk_import_iam_role helper function to create one.)
        files: List of S3 file objects with bucket, key, and optional versionId
        error_report_location: S3 location for error reports (bucket and prefix)
        job_configuration: Configuration including file format (CSV or Parquet)
        delete_files_after_import: Delete S3 files after ingestion (default: False)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing job creation response with jobId, jobName, and jobStatus

    Example:
        files = [{"bucket": "my-data-bucket", "key": "data/timeseries.csv"}]
        error_location = {"bucket": "my-error-bucket", "prefix": "errors/"}
        job_config = {
            "fileFormat": {
                "csv": {
                    "columnNames": ["ALIAS", "TIMESTAMP_SECONDS", "VALUE", "QUALITY"]
                }
            }
        }

        result = create_buffered_ingestion_job(
            job_name="my-buffered-ingestion-job",
            job_role_arn="arn:aws:iam::123456789012:role/IoTSiteWiseRole",
            files=files,
            error_report_location=error_location,
            job_configuration=job_config
        )
    """
    # Call the general create_bulk_import_job function with adaptive_ingestion=True
    return create_bulk_import_job(
        job_name=job_name,
        job_role_arn=job_role_arn,
        files=files,
        error_report_location=error_report_location,
        job_configuration=job_configuration,
        adaptive_ingestion=True,  # Always set to True for buffered ingestion
        delete_files_after_import=delete_files_after_import,
        region=region,
    )


@tool_metadata(readonly=False)
def batch_put_asset_property_value(
    entries: List[Dict[str, Any]] = Field(
        ..., description='List of asset property value entries to send to AWS IoT SiteWise'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Send a list of asset property values to AWS IoT SiteWise.

    Args:
            entries: The list of asset property value entries to send to AWS IoT SiteWise
            region: AWS region (default: us-east-1)

    Returns:
            Dictionary containing batch put response
    """
    try:
        client = create_sitewise_client(region)

        response = client.batch_put_asset_property_value(entries=entries)

        return {'success': True, 'error_entries': response.get('errorEntries', [])}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def get_asset_property_value(
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    property_alias: Optional[str] = Field(
        None, description='The alias that identifies the property'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get the current value for the given asset property.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the asset property
        property_alias: The alias that identifies the property
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing current property value
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if property_alias and not isinstance(property_alias, FieldInfo):
            validate_property_alias(property_alias)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {}
        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if property_alias:
            params['propertyAlias'] = property_alias

        response = client.get_asset_property_value(**params)

        property_value = response['propertyValue']
        return {
            'success': True,
            'value': property_value['value'],
            'timestamp': property_value['timestamp'],
            'quality': property_value.get('quality', 'GOOD'),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def get_asset_property_value_history(
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    property_alias: Optional[str] = Field(
        None, description='The alias that identifies the property'
    ),
    start_date: Optional[str] = Field(
        None, description='The exclusive start of the range (ISO 8601 format)'
    ),
    end_date: Optional[str] = Field(
        None, description='The inclusive end of the range (ISO 8601 format)'
    ),
    qualities: Optional[List[str]] = Field(
        None, description='The quality by which to filter asset data (GOOD, BAD, UNCERTAIN)'
    ),
    time_ordering: str = Field(
        'ASCENDING', description='The chronological sorting order (ASCENDING, DESCENDING)'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-4000)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get the history of an asset property's values.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the asset property
        property_alias: The alias that identifies the property
        start_date: The exclusive start of the range (ISO 8601 format)
        end_date: The inclusive end of the range (ISO 8601 format)
        qualities: The quality by which to filter asset data (GOOD, BAD, UNCERTAIN)
        time_ordering: The chronological sorting order of the requested information \
            (ASCENDING, DESCENDING)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing property value history
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(max_results, FieldInfo):
            validate_max_results(max_results, min_val=1, max_val=4000)
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if property_alias and not isinstance(property_alias, FieldInfo):
            validate_property_alias(property_alias)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'timeOrdering': time_ordering,
            'maxResults': max_results,
        }

        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if property_alias:
            params['propertyAlias'] = property_alias
        if start_date:
            params['startDate'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            params['endDate'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if qualities:
            params['qualities'] = qualities
        if next_token:
            params['nextToken'] = next_token

        response = client.get_asset_property_value_history(**params)

        return {
            'success': True,
            'asset_property_value_history': response['assetPropertyValueHistory'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def get_asset_property_aggregates(
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    property_alias: Optional[str] = Field(
        None, description='The alias that identifies the property'
    ),
    aggregate_types: Optional[List[str]] = Field(
        None,
        description='The data aggregating function (AVERAGE, COUNT, MAXIMUM, MINIMUM, SUM, STANDARD_DEVIATION)',
    ),
    resolution: str = Field('1h', description='The time interval over which to aggregate data'),
    start_date: Optional[str] = Field(
        None, description='The exclusive start of the range (ISO 8601 format)'
    ),
    end_date: Optional[str] = Field(
        None, description='The inclusive end of the range (ISO 8601 format)'
    ),
    qualities: Optional[List[str]] = Field(
        None, description='The quality by which to filter asset data (GOOD, BAD, UNCERTAIN)'
    ),
    time_ordering: str = Field(
        'ASCENDING', description='The chronological sorting order (ASCENDING, DESCENDING)'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-4000)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get aggregated values for an asset property.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the asset property
        property_alias: The alias that identifies the property
        aggregate_types: The data aggregating function (AVERAGE, COUNT, MAXIMUM, \
            MINIMUM, SUM, STANDARD_DEVIATION)
        resolution: The time interval over which to aggregate data
        start_date: The exclusive start of the range (ISO 8601 format)
        end_date: The inclusive end of the range (ISO 8601 format)
        qualities: The quality by which to filter asset data (GOOD, BAD, UNCERTAIN)
        time_ordering: The chronological sorting order of the requested information \
            (ASCENDING, DESCENDING)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing property aggregates
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(max_results, FieldInfo):
            validate_max_results(max_results, min_val=1, max_val=4000)
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if property_alias and not isinstance(property_alias, FieldInfo):
            validate_property_alias(property_alias)

        client = create_sitewise_client(region)

        if not aggregate_types:
            aggregate_types = ['AVERAGE']

        params: Dict[str, Any] = {
            'aggregateTypes': aggregate_types,
            'resolution': resolution,
            'timeOrdering': time_ordering,
            'maxResults': max_results,
        }

        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if property_alias:
            params['propertyAlias'] = property_alias
        if start_date:
            params['startDate'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            params['endDate'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if qualities:
            params['qualities'] = qualities
        if next_token:
            params['nextToken'] = next_token

        response = client.get_asset_property_aggregates(**params)

        return {
            'success': True,
            'aggregated_values': response['aggregatedValues'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def get_interpolated_asset_property_values(
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    property_alias: Optional[str] = Field(
        None, description='The alias that identifies the property'
    ),
    start_time_in_seconds: Optional[int] = Field(
        None, description='The exclusive start of the range (Unix epoch time in seconds)'
    ),
    end_time_in_seconds: Optional[int] = Field(
        None, description='The inclusive end of the range (Unix epoch time in seconds)'
    ),
    quality: str = Field(
        'GOOD', description='The quality of the asset property value (GOOD, BAD, UNCERTAIN)'
    ),
    interval_in_seconds: int = Field(
        3600, description='The time interval in seconds over which to interpolate data'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-250)'),
    interpolation_type: str = Field(
        'LINEAR_INTERPOLATION',
        description='The interpolation type (LINEAR_INTERPOLATION, LOCF_INTERPOLATION)',
    ),
    interval_window_in_seconds: Optional[int] = Field(
        None, description='The query interval for interpolated values'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get interpolated values for an asset property for a specified time interval.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the asset property
        property_alias: The alias that identifies the property
        start_time_in_seconds: The exclusive start of the range (Unix epoch \
            time in seconds)
        end_time_in_seconds: The inclusive end of the range (Unix epoch time \
            in seconds)
        quality: The quality of the asset property value (GOOD, BAD, UNCERTAIN)
        interval_in_seconds: The time interval in seconds over which to \
            interpolate data
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        interpolation_type: The interpolation type (LINEAR_INTERPOLATION, \
            LOCF_INTERPOLATION)
        interval_window_in_seconds: The query interval for the window
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing interpolated property values
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(max_results, FieldInfo):
            validate_max_results(max_results, min_val=1, max_val=250)
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if property_alias and not isinstance(property_alias, FieldInfo):
            validate_property_alias(property_alias)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'startTimeInSeconds': start_time_in_seconds,
            'endTimeInSeconds': end_time_in_seconds,
            'quality': quality,
            'intervalInSeconds': interval_in_seconds,
            'maxResults': max_results,
            'type': interpolation_type,
        }

        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if property_alias:
            params['propertyAlias'] = property_alias
        if next_token:
            params['nextToken'] = next_token
        if interval_window_in_seconds:
            params['intervalWindowInSeconds'] = interval_window_in_seconds

        response = client.get_interpolated_asset_property_values(**params)

        return {
            'success': True,
            'interpolated_asset_property_values': response['interpolatedAssetPropertyValues'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def batch_get_asset_property_value(
    entries: List[Dict[str, Any]] = Field(
        ..., description='The list of asset property identifiers for the batch get request'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get the current values for multiple asset properties.

    Args:
        entries: The list of asset property identifiers for the batch get request
        next_token: The token to be used for the next set of paginated results
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing batch get response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'entries': entries}
        if next_token:
            params['nextToken'] = next_token

        response = client.batch_get_asset_property_value(**params)

        return {
            'success': True,
            'success_entries': response.get('successEntries', []),
            'skipped_entries': response.get('skippedEntries', []),
            'error_entries': response.get('errorEntries', []),
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def batch_get_asset_property_value_history(
    entries: List[Dict[str, Any]] = Field(
        ...,
        description='The list of asset property historical value entries for the batch get request',
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-4000)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get the historical values for multiple asset properties.

    Args:
        entries: The list of asset property historical value entries for the \
            batch get request
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing batch get history response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'entries': entries, 'maxResults': max_results}
        if next_token:
            params['nextToken'] = next_token

        response = client.batch_get_asset_property_value_history(**params)

        return {
            'success': True,
            'success_entries': response.get('successEntries', []),
            'skipped_entries': response.get('skippedEntries', []),
            'error_entries': response.get('errorEntries', []),
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def batch_get_asset_property_aggregates(
    entries: List[Dict[str, Any]] = Field(
        ..., description='The list of asset property aggregate entries for the batch get request'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-4000)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get aggregated values for multiple asset properties.

    Args:
        entries: The list of asset property aggregate entries for the batch get request
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing batch get aggregates response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'entries': entries, 'maxResults': max_results}
        if next_token:
            params['nextToken'] = next_token

        response = client.batch_get_asset_property_aggregates(**params)

        return {
            'success': True,
            'success_entries': response.get('successEntries', []),
            'skipped_entries': response.get('skippedEntries', []),
            'error_entries': response.get('errorEntries', []),
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def list_bulk_import_jobs(
    filter: Optional[str] = Field(
        None,
        description='Filter to apply to the list of bulk import jobs. Valid values: ALL, PENDING, RUNNING, CANCELLED, FAILED, COMPLETED_WITH_FAILURES, COMPLETED',
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(50, description='The maximum number of results to return (1-250)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """List bulk import jobs in AWS IoT SiteWise.

    This function retrieves a paginated list of bulk import job summaries with optional filtering
    by job status. Each job summary includes basic information like job ID, name, status, and timestamps.

    Args:
        filter: Optional filter to apply to the list. Valid values:
            - ALL: List all jobs (default)
            - PENDING: Jobs waiting to start
            - RUNNING: Jobs currently executing
            - CANCELLED: Jobs that were cancelled
            - FAILED: Jobs that failed
            - COMPLETED_WITH_FAILURES: Jobs completed but with some failures
            - COMPLETED: Jobs that completed successfully
        next_token: Token for paginated results
        max_results: Maximum number of results to return (1-250, default: 25)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing:
        - success: Boolean indicating operation success
        - job_summaries: List of job summary objects
        - next_token: Token for next page (if applicable)

    Example:
        # List all bulk import jobs
        result = list_bulk_import_jobs()

        # List only running jobs
        result = list_bulk_import_jobs(filter="RUNNING")

        # List with pagination
        result = list_bulk_import_jobs(max_results=10, next_token="...")
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(max_results, FieldInfo):
            validate_max_results(max_results, min_val=1, max_val=250)

        # Validate filter parameter
        valid_filters = {
            'ALL',
            'PENDING',
            'RUNNING',
            'CANCELLED',
            'FAILED',
            'COMPLETED_WITH_FAILURES',
            'COMPLETED',
        }
        if not isinstance(filter, FieldInfo) and filter and filter not in valid_filters:
            raise ValidationError(
                f'Invalid filter: {filter}. Must be one of: {", ".join(valid_filters)}'
            )

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'maxResults': max_results,
        }

        if filter:
            params['filter'] = filter
        if next_token:
            params['nextToken'] = next_token

        response = client.list_bulk_import_jobs(**params)

        return {
            'success': True,
            'job_summaries': response.get('jobSummaries', []),
            'next_token': response.get('nextToken', ''),
        }

    except ValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def describe_bulk_import_job(
    job_id: str = Field(
        ..., description='The ID of the bulk import job to describe (UUID format)'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get detailed information about a specific bulk import job in AWS IoT SiteWise.

    This function retrieves comprehensive details about a bulk import job including its configuration,
    status, progress, error information, and execution statistics.

    Args:
        job_id: The unique identifier of the bulk import job (UUID format)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing:
        - success: Boolean indicating operation success
        - job_id: The job identifier
        - job_name: The job name
        - job_status: Current status of the job
        - job_role_arn: IAM role ARN used by the job
        - files: List of input files
        - error_report_location: S3 location for error reports
        - job_configuration: Job configuration details
        - job_creation_date: When the job was created
        - job_last_update_date: When the job was last updated
        - adaptive_ingestion: Whether adaptive ingestion is enabled
        - delete_files_after_import: Whether files are deleted after import
        - Additional fields based on job status and execution

    Example:
        # Get details for a specific job
        result = describe_bulk_import_job(
            job_id="12345678-1234-1234-1234-123456789012"
        )

        if result['success']:
            print(f"Job Status: {result['job_status']}")
            print(f"Job Name: {result['job_name']}")
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)

        # Validate job_id format (should be UUID)
        if not job_id or not isinstance(job_id, str):
            raise ValidationError('Job ID must be a non-empty string')

        # Basic UUID format validation (36 characters with hyphens)
        if len(job_id) != 36 or job_id.count('-') != 4:
            raise ValidationError(
                'Job ID must be in UUID format (e.g., 12345678-1234-1234-1234-123456789012)'
            )

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'jobId': job_id,
        }

        response = client.describe_bulk_import_job(**params)

        return {
            'success': True,
            'job_id': response.get('jobId'),
            'job_name': response.get('jobName'),
            'job_status': response.get('jobStatus'),
            'job_role_arn': response.get('jobRoleArn'),
            'files': response.get('files', []),
            'error_report_location': response.get('errorReportLocation', {}),
            'job_configuration': response.get('jobConfiguration', {}),
            'job_creation_date': response.get('jobCreationDate'),
            'job_last_update_date': response.get('jobLastUpdateDate'),
            'adaptive_ingestion': response.get('adaptiveIngestion'),
            'delete_files_after_import': response.get('deleteFilesAfterImport'),
        }

    except ValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def execute_query(
    query_statement: str = Field(
        ..., description='SQL query statement to execute against AWS IoT SiteWise data'
    ),
    region: str = Field('us-east-1', description='AWS region'),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-10000)'),
) -> Dict[str, Any]:
    """Execute comprehensive SQL queries against AWS IoT SiteWise data using the executeQuery API.

    The AWS IoT SiteWise query language supports SQL capabilities including:
    - Views: asset, asset_property, raw_time_series, \
        latest_value_time_series, precomputed_aggregates
    - SQL clauses: SELECT, FROM, WHERE, GROUP BY, ORDER BY, HAVING, LIMIT
    - Functions: Aggregation, date/time, string, mathematical, conditional
    - Operators: Comparison, logical, arithmetic, pattern matching (LIKE)
    - JOIN operations: JOIN, LEFT JOIN,
        UNION (prefer implicit joins for performance)

    Available Views and Schema (From Official AWS Documentation):

    ASSET VIEW: Contains information about the asset and model derivation
    - asset_id (string), asset_name (string), asset_description (string)
    - asset_model_id (string), parent_asset_id (string),
        asset_external_id (string)
    - asset_external_model_id (string), hierarchy_id (string)

    ASSET_PROPERTY VIEW: Contains information about the asset property's structure
    - asset_id (string), property_id (string), property_name (string),
        property_alias (string)
    - property_external_id (string), asset_composite_model_id (string),
        property_type (string)
    - property_data_type (string), int_attribute_value (integer),
        double_attribute_value (double)
    - boolean_attribute_value (boolean), string_attribute_value (string)

    RAW_TIME_SERIES VIEW: Contains the historical data of the time series
    - asset_id (string), property_id (string), property_alias (string),
        event_timestamp (timestamp)
    - quality (string), boolean_value (boolean), int_value (integer),
        double_value (double), string_value (string)

    LATEST_VALUE_TIME_SERIES VIEW: Contains the latest value of the time series
    - asset_id (string), property_id (string), property_alias (string),
        event_timestamp (timestamp)
    - quality (string), boolean_value (boolean), int_value (integer),
        double_value (double), string_value (string)

    PRECOMPUTED_AGGREGATES VIEW: Contains automatically computed \
        aggregated asset property values
    - asset_id (string), property_id (string), property_alias (string),
        event_timestamp (timestamp)
    - quality (string), resolution (string), sum_value (double),
        count_value (integer)
    - average_value (double), maximum_value (double),
        minimum_value (double), stdev_value (double)

    Complete SQL Function Reference (From AWS IoT SiteWise User Guide):

    DATE/TIME FUNCTIONS:
    - DATE_ADD(
        unit,
        value,
        date): Add time to date (e.g.,
        DATE_ADD(DAY, 7, event_timestamp))    - DATE_SUB(
        unit,
        value,
        date): Subtract time from date (e.g.,
        DATE_SUB(
            YEAR,
            2,
            event_timestamp))    - TIMESTAMP_ADD(
                unit,
                value,
                timestamp): Add time to timestamp
    - TIMESTAMP_SUB(unit, value, timestamp): Subtract time from timestamp
    - NOW(
        ): Current timestamp (supported,
        but use TIMESTAMP_ADD/SUB for math operations)    - \
            TIMESTAMP literals: Use TIMESTAMP '2023-01-01 00:00:00' for specific dates
    - CAST(expression AS TIMESTAMP): Convert string to timestamp

    Note: NOW() IS supported. When doing math on NOW() or \
        any timestamp, use TIMESTAMP_ADD/TIMESTAMP_SUB functions rather than \
            +/- operators.

    TYPE CONVERSION FUNCTIONS:
    - TO_DATE(integer): Convert epoch milliseconds to date
    - TO_DATE(expression, format): Convert string to date with format
    - TO_TIMESTAMP(double): Convert epoch seconds to timestamp
    - TO_TIMESTAMP(string, format): Convert string to timestamp with format
    - TO_TIME(int): Convert epoch milliseconds to time
    - TO_TIME(string, format): Convert string to time with format
    - CAST(expression AS data_type): Convert between BOOLEAN, INTEGER,
        TIMESTAMP, DATE, STRING, etc.

    AGGREGATE FUNCTIONS:
    - AVG(expression): Average value
    - COUNT(expression): Count rows (COUNT(*) is supported)
    - MAX(expression): Maximum value
    - MIN(expression): Minimum value
    - SUM(expression): Sum values
    - STDDEV(expression): Standard deviation
    - GROUP BY expression: Group results
    - HAVING boolean-expression: Filter grouped results

    IMPORTANT LIMITATIONS:
    - Window functions, CTEs (WITH clauses), DISTINCT, SELECT *, and \
        ILIKE are NOT supported

    SUPPORTED FEATURES:
    - CASE statements (CASE WHEN...THEN...ELSE...END pattern) ARE supported
    - COUNT(*) IS supported (only SELECT * is blocked)
    - Use implicit JOINs for better performance when possible

    Args:
        query_statement: The SQL query statement to execute (max 64KB)
        region: AWS region (default: us-east-1)
        next_token: Token for paginated results
        max_results: Maximum results to return (1-4000, default: 100)

    Returns:
        Dictionary containing:
        - success: Boolean indicating query success
        - columns: List of column definitions
        - rows: List of result rows
        - next_token: Token for next page (if applicable)
        - query_statistics: Execution statistics
        - query_status: Query execution status

    Example Queries (Using Correct View and Column Names):

    Basic Asset Discovery:
        "SELECT asset_id, asset_name, asset_model_id FROM asset"

    Metadata Filtering:
        "SELECT a.asset_name, p.property_name FROM asset a, asset_property p \
            WHERE a.asset_id = p.asset_id AND a.asset_name LIKE 'Windmill%'"

    Value Filtering with Time Range:
        "SELECT a.asset_name, r.int_value FROM asset a, raw_time_series r
         WHERE a.asset_id = r.asset_id
         AND r.int_value > 30
         AND r.event_timestamp > TIMESTAMP '2022-01-05 12:15:00'
         AND r.event_timestamp < TIMESTAMP '2022-01-05 12:20:00'"

    Aggregation with Grouping:
        "SELECT MAX(d.int_value) AS max_int_value, d.asset_id
         FROM raw_time_series AS d
         GROUP BY d.asset_id
         HAVING MAX(d.int_value) > 5"

    Date/Time Manipulation:
        "SELECT r.asset_id, r.int_value,
         DATE_ADD(DAY, 7, r.event_timestamp) AS date_in_future,
         DATE_SUB(YEAR, 2, r.event_timestamp) AS date_in_past,
         TIMESTAMP_ADD(DAY, 2, r.event_timestamp) AS timestamp_in_future,
         TIMESTAMP_SUB(DAY, 2, r.event_timestamp) AS timestamp_in_past
         FROM raw_time_series AS r"

    Type Conversion Examples:
        "SELECT r.asset_id, TO_DATE(r.event_timestamp) AS date_value,
         TO_TIME(r.event_timestamp) AS time_value
         FROM raw_time_series AS r"

    Attribute Property Filtering (For Attribute Properties Only - \
        Note: Only one attribute value type can be non-null per property):
        "SELECT p.property_name,
         CASE
             WHEN p.string_attribute_value IS NOT NULL THEN p.string_attribute_value
             WHEN p.double_attribute_value IS NOT NULL THEN \
                 CAST(p.double_attribute_value AS STRING)
             ELSE 'NULL'
         END as attribute_value
         FROM asset_property p
         WHERE p.property_type = 'attribute'
         AND (p.string_attribute_value LIKE 'my-property-%' OR \
             p.double_attribute_value > 100.0)"

    Precomputed Aggregates (Include quality and resolution filters):
        "SELECT asset_id, property_id, average_value, event_timestamp
         FROM precomputed_aggregates
         WHERE quality = 'GOOD'
         AND resolution = '1h'
         AND event_timestamp BETWEEN TIMESTAMP '2023-01-01 00:00:00' AND \
             TIMESTAMP '2023-01-02 00:00:00'"

    Implicit JOIN for Better Performance:
        "SELECT a.asset_name, p.property_name, r.double_value
         FROM asset a, asset_property p, raw_time_series r
         WHERE a.asset_id = p.asset_id
         AND p.property_id = r.property_id
         AND r.quality = 'GOOD'"

    Data Quality Analysis:
        "SELECT asset_id, property_alias,
         SUM(CASE WHEN quality = 'GOOD' THEN 1 ELSE 0 END) as good_readings,
         SUM(CASE WHEN quality = 'BAD' THEN 1 ELSE 0 END) as bad_readings,
         ROUND(
             SUM(CASE WHEN quality = 'GOOD' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),

             2) as quality_percent         FROM raw_time_series WHERE \
                 event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
         GROUP BY asset_id, property_alias HAVING COUNT(*) > 10"

    CASE Statement and COUNT(*) Examples:
        "SELECT asset_id, COUNT(*) as total_records,
         CASE WHEN COUNT(*) = 0 THEN 'No Data' ELSE 'Has Data' END as data_status
         FROM raw_time_series GROUP BY asset_id"

    Query Optimization Guidelines (From AWS Documentation):

    1. METADATA FILTERS - \
        Use WHERE clause with these operators for metadata fields:
       - Equals (=), Not equals (!=), LIKE, IN, AND, OR
       - Use literals on right side of operators for better performance

    2. RAW DATA FILTERS - Always filter on event_timestamp using:
       - Equals (
           =), Greater than (>), Less than (<), Greater/Less than or \
               equals (>=,
           <=)       - BETWEEN, AND operators
       - Avoid != and OR operators as they don't limit data scan effectively

    3. PRECOMPUTED AGGREGATES - Always specify:
       - Quality filter (quality = 'GOOD') to reduce data scanned
       - Resolution filter (1m, 15m, 1h, 1d) to avoid full table scan

    4. JOIN OPTIMIZATION:
       - Use implicit JOINs instead of explicit JOIN keyword when possible
       - Push metadata filters into subqueries for better performance
       - Apply filters on individual JOINed tables to minimize data scanned

    5. PERFORMANCE TIPS:
       - Use LIMIT clause to reduce data scanned for some queries
       - Set page size to maximum 20000 for large queries
       - Use attribute value columns (
           double_attribute_value,
           etc.) for better performance than latest_value_time_series       - \
               Filter on asset_id, property_id for indexed access
       - Always include quality = 'GOOD' filters for reliable data

    """
    try:
        # Validate parameters
        if not query_statement or not query_statement.strip():
            raise ValidationError('Query statement cannot be empty')

        if len(query_statement) > 65536:  # 64KB limit
            raise ValidationError('Query statement cannot exceed 64KB')

        validate_region(region)
        validate_max_results(max_results, min_val=1, max_val=4000)

        if next_token and len(next_token) > 4096:
            raise ValidationError('Next token too long')

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'queryStatement': query_statement.strip(),
            'maxResults': max_results,
        }

        if next_token:
            params['nextToken'] = next_token

        response = client.execute_query(**params)

        return {
            'success': True,
            'columns': response.get('columns', []),
            'rows': response.get('rows', []),
            'next_token': response.get('nextToken', ''),
            'query_statistics': response.get('queryStatistics', {}),
            'query_status': response.get('queryStatus', 'COMPLETED'),
        }

    except ValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=False)
def create_bulk_import_iam_role(
    role_name: str = Field(
        'IoTSiteWiseBulkImportAssumableRole',
        description='Name of bulk import permissions IAM role',
    ),
    data_bucket_names: List[str] = Field(..., description='S3 bucket names containing data files'),
    error_bucket_name: str = Field(..., description='S3 bucket name for error reports'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Create an IAM role for AWS IoT SiteWise bulk import jobs."""
    try:
        # Create IAM client
        iam_client = create_iam_client(region)

        # Trust policy allowing IoT SiteWise to assume the role
        trust_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'Service': 'iotsitewise.amazonaws.com'},
                    'Action': 'sts:AssumeRole',
                }
            ],
        }

        # Create the IAM role
        create_role_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='IAM role for IoT SiteWise bulk import jobs',
        )

        # Create policy for S3 permissions following AWS documentation
        data_bucket_resources = []
        for bucket in data_bucket_names:
            data_bucket_resources.extend([f'arn:aws:s3:::{bucket}', f'arn:aws:s3:::{bucket}/*'])

        policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['s3:GetObject', 's3:GetBucketLocation'],
                    'Resource': data_bucket_resources,
                },
                {
                    'Effect': 'Allow',
                    'Action': ['s3:PutObject', 's3:GetObject', 's3:GetBucketLocation'],
                    'Resource': [
                        f'arn:aws:s3:::{error_bucket_name}',
                        f'arn:aws:s3:::{error_bucket_name}/*',
                    ],
                },
            ],
        }

        # Attach inline policy to the role
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=f'{role_name}Policy',
            PolicyDocument=json.dumps(policy_document),
        )

        return {
            'success': True,
            'role_arn': create_role_response['Role']['Arn'],
            'role_name': role_name,
        }

    except (ValidationError, ClientError) as e:
        return {
            'success': False,
            'error': str(e),
        }


create_bulk_import_job_tool = Tool.from_function(
    fn=create_bulk_import_job,
    name='create_bulk_import_job',
    description=(
        'Create a bulk import job to ingest data from Amazon S3 to AWS IoT SiteWise. '
        'Supports both historical data ingestion (adaptive_ingestion=False) and buffered '
        'ingestion (adaptive_ingestion=True) for real-time processing of recent data. '
        'Supports CSV and Parquet file formats with comprehensive validation and error handling.'
    ),
)

create_buffered_ingestion_job_tool = Tool.from_function(
    fn=create_buffered_ingestion_job,
    name='create_buffered_ingestion_job',
    description=(
        'Create a buffered ingestion job to ingest data from Amazon S3 to AWS IoT SiteWise '
        'with adaptive ingestion enabled for real-time processing of recent data (within 30 days). '
        'This is a convenience function that automatically sets adaptive_ingestion=True. '
        'Supports CSV and Parquet file formats with comprehensive validation and error handling.'
    ),
)

batch_put_asset_property_value_tool = Tool.from_function(
    fn=batch_put_asset_property_value,
    name='batch_put_asset_property_value',
    description=('Send a list of asset property values to AWS IoT SiteWise for data ingestion.'),
)

get_asset_property_value_tool = Tool.from_function(
    fn=get_asset_property_value,
    name='get_asset_property_value',
    description=('Get the current value for a given asset property in AWS IoT SiteWise.'),
)

get_asset_property_value_history_tool = Tool.from_function(
    fn=get_asset_property_value_history,
    name='get_asset_property_value_history',
    description=('Get the historical values for an asset property in AWS IoT SiteWise.'),
)

get_asset_property_aggregates_tool = Tool.from_function(
    fn=get_asset_property_aggregates,
    name='get_asset_property_aggregates',
    description='Get aggregated values (average, count, maximum, minimum, '
    'sum, standard deviation) for an asset property in AWS IoT SiteWise.',
)

get_interpolated_asset_property_values_tool = Tool.from_function(
    fn=get_interpolated_asset_property_values,
    name='get_interpl_asset_property_values',
    description=(
        'Get interpolated values for an asset property for a '
        'specified time interval in AWS IoT SiteWise.'
    ),
)

batch_get_asset_property_value_tool = Tool.from_function(
    fn=batch_get_asset_property_value,
    name='batch_get_asset_property_value',
    description=('Get the current values for multiple asset properties in AWS IoT SiteWise.'),
)

batch_get_asset_property_value_history_tool = Tool.from_function(
    fn=batch_get_asset_property_value_history,
    name='batch_get_asset_property_value_hist',
    description=('Get the historical values for multiple asset properties in AWS IoT SiteWise.'),
)

batch_get_asset_property_aggregates_tool = Tool.from_function(
    fn=batch_get_asset_property_aggregates,
    name='batch_get_asset_property_aggregates',
    description=('Get aggregated values for multiple asset properties in AWS IoT SiteWise.'),
)

list_bulk_import_jobs_tool = Tool.from_function(
    fn=list_bulk_import_jobs,
    name='list_bulk_import_jobs',
    description=(
        'List bulk import jobs in AWS IoT SiteWise with optional filtering by status '
        '(ALL, PENDING, RUNNING, CANCELLED, FAILED, COMPLETED_WITH_FAILURES, COMPLETED). '
        'Returns paginated job summaries with basic information like job ID, name, status, and timestamps.'
    ),
)

describe_bulk_import_job_tool = Tool.from_function(
    fn=describe_bulk_import_job,
    name='describe_bulk_import_job',
    description=(
        'Get detailed information about a specific bulk import job in AWS IoT SiteWise '
        'including configuration, status, progress, error information, and execution statistics. '
        'Requires the job ID in UUID format.'
    ),
)

create_bulk_import_iam_role_tool = Tool.from_function(
    fn=create_bulk_import_iam_role,
    name='create_bulk_import_iam_role',
    description=(
        'Create an IAM role for AWS IoT SiteWise bulk import jobs with the necessary '
        'S3 permissions and trust policy. Automatically configures read access to data '
        'buckets and write access to error bucket for IoT SiteWise service.'
    ),
)

execute_query_tool = Tool.from_function(
    fn=execute_query,
    name='execute_query',
    description=(
        'Execute comprehensive SQL queries against AWS IoT SiteWise data '
        'with SQL capabilities including views (asset, asset_property, '
        'raw_time_series, latest_value_time_series, precomputed_aggregates), '
        'functions (aggregation, date/time, string, mathematical), '
        'operators, joins, and analytics for industrial IoT data exploration.'
    ),
)
