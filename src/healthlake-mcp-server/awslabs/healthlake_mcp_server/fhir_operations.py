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

"""AWS HealthLake client for FHIR operations."""

# Standard library imports
# Third-party imports
import boto3
import httpx

# Local imports
from . import __version__
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin


# HealthLake API limits
MAX_SEARCH_COUNT = 100  # Maximum number of resources per search request
DATASTORE_ID_LENGTH = 32  # AWS HealthLake datastore ID length


def validate_datastore_id(datastore_id: str) -> str:
    """Validate AWS HealthLake datastore ID format."""
    if not datastore_id or len(datastore_id) != DATASTORE_ID_LENGTH:
        raise ValueError(f'Datastore ID must be {DATASTORE_ID_LENGTH} characters')
    return datastore_id


class FHIRSearchError(Exception):
    """Exception raised for FHIR search parameter errors."""

    def __init__(self, message: str, invalid_params: Optional[List[str]] = None):
        """Initialize FHIR search error with message and optional invalid parameters."""
        self.invalid_params = invalid_params or []
        super().__init__(message)


class AWSAuth(httpx.Auth):
    """Custom AWS SigV4 authentication for httpx."""

    def __init__(self, credentials, region: str, service: str = 'healthlake'):
        """Initialize AWS SigV4 authentication with credentials and region."""
        self.credentials = credentials
        self.region = region
        self.service = service

    def auth_flow(self, request):
        """Apply AWS SigV4 authentication to the request."""
        # Preserve the original Content-Length if it exists
        original_content_length = request.headers.get('content-length')

        # Use minimal headers for signing - include Content-Length if present
        headers = {
            'Accept': 'application/fhir+json',
            'Content-Type': 'application/fhir+json',
            'Host': request.url.host,
        }

        # Add Content-Length to headers for signing if present
        if original_content_length:
            headers['Content-Length'] = original_content_length

        # For GET requests, no body
        body = None if request.method.upper() == 'GET' else request.content

        # Create AWS request for signing
        aws_request = AWSRequest(
            method=request.method, url=str(request.url), data=body, headers=headers
        )

        # Sign the request
        signer = SigV4Auth(self.credentials, self.service, self.region)
        signer.add_auth(aws_request)

        # Clear existing headers and set only the signed ones
        request.headers.clear()
        for key, value in aws_request.headers.items():
            request.headers[key] = value

        yield request


class HealthLakeClient:
    """Client for AWS HealthLake FHIR operations."""

    def __init__(self, region_name: Optional[str] = None):
        """Initialize the HealthLake client."""
        try:
            self.session = boto3.Session()
            self.healthlake_client = self.session.client(
                'healthlake',
                region_name=region_name,
                config=Config(user_agent_extra=f'awslabs/mcp/healthlake-mcp-server/{__version__}'),
            )
            self.region = region_name or self.session.region_name or 'us-east-1'

        except NoCredentialsError:
            logger.error('AWS credentials not found. Please configure your credentials.')
            raise

    async def list_datastores(self, filter_status: Optional[str] = None) -> Dict[str, Any]:
        """List HealthLake datastores."""
        try:
            kwargs = {}
            if filter_status:
                kwargs['Filter'] = {'DatastoreStatus': filter_status}

            response = self.healthlake_client.list_fhir_datastores(**kwargs)
            return response
        except ClientError as e:
            logger.error(f'Error listing datastores: {e}')
            raise

    async def get_datastore_details(self, datastore_id: str) -> Dict[str, Any]:
        """Get details of a specific datastore."""
        try:
            response = self.healthlake_client.describe_fhir_datastore(DatastoreId=datastore_id)
            return response
        except ClientError as e:
            logger.error(f'Error getting datastore details: {e}')
            raise

    def _get_fhir_endpoint(self, datastore_id: str) -> str:
        """Get the FHIR endpoint URL for a datastore."""
        return f'https://healthlake.{self.region}.amazonaws.com/datastore/{datastore_id}/r4/'

    def _build_search_request(
        self,
        base_url: str,
        resource_type: str,
        search_params: Optional[Dict[str, Any]] = None,
        include_params: Optional[List[str]] = None,
        revinclude_params: Optional[List[str]] = None,
        chained_params: Optional[Dict[str, str]] = None,
        count: int = 100,
        next_token: Optional[str] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """Build search request with minimal processing."""
        # Handle pagination first
        if next_token:
            return next_token, {}

        # Build the search URL
        url = f'{base_url.rstrip("/")}/{resource_type}/_search'

        # Build form data with minimal processing
        form_data = {'_count': str(count)}

        # Add basic search parameters with proper encoding for FHIR modifiers
        if search_params:
            for key, value in search_params.items():
                # URL-encode colons in parameter names for FHIR modifiers
                encoded_key = key.replace(':', '%3A')
                if isinstance(value, list):
                    form_data[encoded_key] = ','.join(str(v) for v in value)
                else:
                    form_data[encoded_key] = str(value)

        # Add chained parameters with proper encoding for FHIR modifiers
        if chained_params:
            for key, value in chained_params.items():
                # URL-encode colons in parameter names for FHIR modifiers
                encoded_key = key.replace(':', '%3A')
                form_data[encoded_key] = str(value)

        # Add include parameters
        if include_params:
            form_data['_include'] = ','.join(include_params)

        # Add revinclude parameters
        if revinclude_params:
            form_data['_revinclude'] = ','.join(revinclude_params)

        return url, form_data

    def _validate_search_request(
        self,
        resource_type: str,
        search_params: Optional[Dict[str, Any]] = None,
        include_params: Optional[List[str]] = None,
        revinclude_params: Optional[List[str]] = None,
        chained_params: Optional[Dict[str, str]] = None,
        count: int = 100,
    ) -> List[str]:
        """Minimal validation - only catch obvious errors."""
        errors = []

        # Basic sanity checks only
        if not resource_type or not resource_type.strip():
            errors.append('Resource type is required')

        if count < 1 or count > 100:
            errors.append('Count must be between 1 and 100')

        # Basic format checks for include parameters
        if include_params:
            for param in include_params:
                if ':' not in param:
                    errors.append(
                        f"Invalid include format: '{param}'. Expected 'ResourceType:parameter'"
                    )

        if revinclude_params:
            for param in revinclude_params:
                if ':' not in param:
                    errors.append(
                        f"Invalid revinclude format: '{param}'. Expected 'ResourceType:parameter'"
                    )

        return errors

    def _process_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Process FHIR Bundle response and extract pagination information."""
        from urllib.parse import parse_qs, quote, urlparse

        result = {
            'resourceType': bundle.get('resourceType', 'Bundle'),
            'id': bundle.get('id'),
            'type': bundle.get('type', 'searchset'),
            'total': bundle.get('total'),
            'entry': bundle.get('entry', []),
            'link': bundle.get('link', []),
        }

        # Add total field if not present (some HealthLake responses may not include it)
        if 'total' not in result or result['total'] is None:
            result['total'] = len(result.get('entry', []))

        # Extract next URL from Bundle links and handle encoding issues
        next_url = None
        for link in bundle.get('link', []):
            if link.get('relation') == 'next':
                next_url = link.get('url', '')
                break

        # Process the next URL to handle HealthLake pagination encoding issues
        next_token = None
        if next_url:
            try:
                # Parse the URL to handle encoding issues
                link_parse = urlparse(next_url)
                link_qs = parse_qs(link_parse.query)

                if 'page' in link_qs:
                    # Encode the page parameter to prevent auth errors
                    encoded_page = quote(link_qs['page'][0])

                    # Reconstruct the URL with properly encoded page parameter
                    next_link_values = {
                        'scheme': link_parse.scheme,
                        'hostname': link_parse.hostname,
                        'path': link_parse.path,
                        'count': '?_count=' + link_qs['_count'][0] if '_count' in link_qs else '',
                        'page': '&page=' + encoded_page,
                    }
                    next_token = '{scheme}://{hostname}{path}{count}{page}'.format(
                        **next_link_values
                    )
                else:
                    # Fallback to original URL if no page parameter found
                    next_token = next_url

            except Exception as e:
                logger.warning(f'Error processing next URL: {e}, using original URL')
                next_token = next_url

        result['pagination'] = {'has_next': bool(next_token), 'next_token': next_token}
        return result

    def _process_bundle_with_includes(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Process bundle and organize included resources."""
        # Separate main results from included resources
        main_entries = []
        included_entries = []

        for entry in bundle.get('entry', []):
            search_mode = entry.get('search', {}).get('mode', 'match')
            if search_mode == 'match':
                main_entries.append(entry)
            elif search_mode == 'include':
                included_entries.append(entry)

        # Organize included resources by type and ID for easier access
        included_by_type: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for entry in included_entries:
            resource = entry.get('resource', {})
            resource_type = resource.get('resourceType')
            resource_id = resource.get('id')

            if resource_type and resource_id:
                if resource_type not in included_by_type:
                    included_by_type[resource_type] = {}
                included_by_type[resource_type][resource_id] = resource

        # Build response
        result = {
            'resourceType': bundle.get('resourceType', 'Bundle'),
            'id': bundle.get('id'),
            'type': bundle.get('type', 'searchset'),
            'total': bundle.get('total', len(main_entries)),  # Use main_entries count as fallback
            'entry': main_entries,
            'link': bundle.get('link', []),
        }

        # Add organized included resources
        if included_by_type:
            result['included'] = included_by_type

        # Add pagination metadata
        next_url = None
        for link in bundle.get('link', []):
            if link.get('relation') == 'next':
                next_url = link.get('url', '')
                break

        result['pagination'] = {'has_next': bool(next_url), 'next_token': next_url}

        return result

    def _create_helpful_error_message(self, error: Exception) -> str:
        """Create helpful error messages without over-engineering."""
        error_str = str(error)

        # Simple, actionable guidance
        if '400' in error_str:
            return (
                f'HealthLake rejected the search request: {error_str}\n\n'
                '💡 Common solutions:\n'
                '• Check parameter names and values\n'
                '• Try simpler search parameters\n'
                '• Verify resource type is correct\n'
                '• Some advanced FHIR features may not be supported'
            )
        elif 'validation' in error_str.lower():
            return (
                f'Search validation failed: {error_str}\n\n'
                '💡 Check your search parameters format and try again.'
            )
        else:
            return f'Search error: {error_str}'

    async def patient_everything(
        self,
        datastore_id: str,
        patient_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        count: int = 100,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve all resources related to a specific patient using $patient-everything operation."""
        try:
            endpoint = self._get_fhir_endpoint(datastore_id)
            auth = self._get_aws_auth()

            # Ensure count is within valid range
            count = max(1, min(count, MAX_SEARCH_COUNT))

            async with httpx.AsyncClient() as client:
                if next_token:
                    # For pagination, use the next_token URL directly
                    response = await client.get(next_token, auth=auth)
                else:
                    # Build $patient-everything URL
                    url = urljoin(endpoint, f'Patient/{patient_id}/$everything')

                    # Build query parameters
                    params = {'_count': str(count)}
                    if start:
                        params['start'] = start
                    if end:
                        params['end'] = end

                    logger.debug(f'Query params: {params}')

                    response = await client.get(url, params=params, auth=auth)

                response.raise_for_status()
                fhir_bundle = response.json()

                # Process the response
                result = self._process_bundle(fhir_bundle)
                return result

        except Exception as e:
            logger.error(f'Error in patient everything operation: {e}')
            raise

    async def search_resources(
        self,
        datastore_id: str,
        resource_type: str,
        search_params: Optional[Dict[str, str]] = None,
        include_params: Optional[List[str]] = None,
        revinclude_params: Optional[List[str]] = None,
        chained_params: Optional[Dict[str, str]] = None,
        count: int = 100,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for FHIR resources."""
        try:
            endpoint = self._get_fhir_endpoint(datastore_id)
            auth = self._get_aws_auth()

            # Ensure count is within valid range
            count = max(1, min(count, MAX_SEARCH_COUNT))

            # Minimal validation
            validation_errors = self._validate_search_request(
                resource_type=resource_type,
                search_params=search_params,
                include_params=include_params,
                revinclude_params=revinclude_params,
                chained_params=chained_params,
                count=count,
            )

            if validation_errors:
                raise FHIRSearchError(f'Search validation failed: {"; ".join(validation_errors)}')

            # Build request
            url, form_data = self._build_search_request(
                base_url=endpoint,
                resource_type=resource_type,
                search_params=search_params,
                include_params=include_params,
                revinclude_params=revinclude_params,
                chained_params=chained_params,
                count=count,
                next_token=next_token,
            )

            async with httpx.AsyncClient() as client:
                if next_token:
                    # For pagination, use GET with the next_token URL
                    response = await client.get(next_token, auth=auth)
                else:
                    # Use POST for search
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

                    logger.debug(f'Search URL: {url}')
                    logger.debug(f'Form data: {form_data}')

                    response = await client.post(url, data=form_data, headers=headers, auth=auth)

                response.raise_for_status()
                fhir_bundle = response.json()

                # Process response with appropriate handling
                has_includes = bool(include_params or revinclude_params)
                if has_includes:
                    result = self._process_bundle_with_includes(fhir_bundle)
                else:
                    result = self._process_bundle(fhir_bundle)

                return result

        except FHIRSearchError:
            # Re-raise FHIR search errors as-is
            raise
        except Exception as e:
            logger.error(f'Error searching resources: {e}')
            # Provide helpful error message
            raise Exception(self._create_helpful_error_message(e))

    async def read_resource(
        self, datastore_id: str, resource_type: str, resource_id: str
    ) -> Dict[str, Any]:
        """Get a specific FHIR resource by ID."""
        try:
            endpoint = self._get_fhir_endpoint(datastore_id)
            url = urljoin(endpoint, f'{resource_type}/{resource_id}')

            auth = self._get_aws_auth()

            async with httpx.AsyncClient() as client:
                response = await client.get(url, auth=auth)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f'Error getting resource: {e}')
            raise

    async def create_resource(
        self, datastore_id: str, resource_type: str, resource_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new FHIR resource."""
        try:
            endpoint = self._get_fhir_endpoint(datastore_id)
            url = urljoin(endpoint, resource_type)

            # Ensure resource has correct resourceType
            resource_data['resourceType'] = resource_type

            auth = self._get_aws_auth()

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=resource_data, auth=auth)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f'Error creating resource: {e}')
            raise

    async def update_resource(
        self,
        datastore_id: str,
        resource_type: str,
        resource_id: str,
        resource_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing FHIR resource."""
        try:
            endpoint = self._get_fhir_endpoint(datastore_id)
            url = urljoin(endpoint, f'{resource_type}/{resource_id}')

            # Ensure resource has correct resourceType and id
            resource_data['resourceType'] = resource_type
            resource_data['id'] = resource_id

            auth = self._get_aws_auth()

            async with httpx.AsyncClient() as client:
                response = await client.put(url, json=resource_data, auth=auth)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f'Error updating resource: {e}')
            raise

    async def delete_resource(
        self, datastore_id: str, resource_type: str, resource_id: str
    ) -> Dict[str, Any]:
        """Delete a FHIR resource."""
        try:
            endpoint = self._get_fhir_endpoint(datastore_id)
            url = urljoin(endpoint, f'{resource_type}/{resource_id}')

            auth = self._get_aws_auth()

            async with httpx.AsyncClient() as client:
                response = await client.delete(url, auth=auth)
                response.raise_for_status()
                return {'status': 'deleted', 'resourceType': resource_type, 'id': resource_id}

        except Exception as e:
            logger.error(f'Error deleting resource: {e}')
            raise

    async def start_import_job(
        self,
        datastore_id: str,
        input_data_config: Dict[str, Any],
        job_output_data_config: Dict[str, Any],
        data_access_role_arn: str,
        job_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a FHIR import job."""
        try:
            # Validate required parameters
            if not input_data_config.get('s3_uri'):
                raise ValueError("input_data_config must contain 's3_uri'")

            if not job_output_data_config.get('s3_configuration', {}).get('s3_uri'):
                raise ValueError(
                    'job_output_data_config must contain s3_configuration with s3_uri'
                )

            # Transform input_data_config to match AWS API format
            input_config = {'S3Uri': input_data_config['s3_uri']}

            # Transform job_output_data_config to match AWS API format
            s3_config = job_output_data_config['s3_configuration']
            output_config = {'S3Configuration': {'S3Uri': s3_config['s3_uri']}}

            # Add KMS key if provided
            if s3_config.get('kms_key_id'):
                output_config['S3Configuration']['KmsKeyId'] = s3_config['kms_key_id']

            kwargs = {
                'DatastoreId': datastore_id,
                'InputDataConfig': input_config,
                'JobOutputDataConfig': output_config,
                'DataAccessRoleArn': data_access_role_arn,
            }

            if job_name:
                kwargs['JobName'] = job_name

            response = self.healthlake_client.start_fhir_import_job(**kwargs)
            return response

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            # Provide more specific error messages
            if error_code == 'ValidationException':
                logger.error(f'Validation error starting import job: {error_message}')
                raise ValueError(f'Invalid parameters: {error_message}')
            elif error_code == 'AccessDeniedException':
                logger.error(f'Access denied starting import job: {error_message}')
                raise PermissionError(f'Access denied: {error_message}')
            elif error_code == 'ResourceNotFoundException':
                logger.error(f'Resource not found starting import job: {error_message}')
                raise ValueError(f'Datastore not found: {error_message}')
            else:
                logger.error(f'Error starting import job: {error_message}')
                raise

    async def start_export_job(
        self,
        datastore_id: str,
        output_data_config: Dict[str, Any],
        data_access_role_arn: str,
        job_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a FHIR export job."""
        try:
            kwargs = {
                'DatastoreId': datastore_id,
                'OutputDataConfig': output_data_config,
                'DataAccessRoleArn': data_access_role_arn,
            }
            if job_name:
                kwargs['JobName'] = job_name

            response = self.healthlake_client.start_fhir_export_job(**kwargs)
            return response
        except ClientError as e:
            logger.error(f'Error starting export job: {e}')
            raise

    async def list_jobs(
        self, datastore_id: str, job_status: Optional[str] = None, job_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """List FHIR import/export jobs."""
        try:
            if job_type == 'IMPORT':
                kwargs: Dict[str, Any] = {'DatastoreId': datastore_id}
                if job_status:
                    kwargs['JobStatus'] = job_status
                response = self.healthlake_client.list_fhir_import_jobs(**kwargs)
            elif job_type == 'EXPORT':
                kwargs: Dict[str, Any] = {'DatastoreId': datastore_id}
                if job_status:
                    kwargs['JobStatus'] = job_status
                response = self.healthlake_client.list_fhir_export_jobs(**kwargs)
            else:
                # List both import and export jobs
                import_jobs = self.healthlake_client.list_fhir_import_jobs(
                    DatastoreId=datastore_id
                )
                export_jobs = self.healthlake_client.list_fhir_export_jobs(
                    DatastoreId=datastore_id
                )
                response = {
                    'ImportJobs': import_jobs.get('ImportJobPropertiesList', []),
                    'ExportJobs': export_jobs.get('ExportJobPropertiesList', []),
                }
            return response
        except ClientError as e:
            logger.error(f'Error listing jobs: {e}')
            # Return error information instead of crashing
            return {'error': True, 'message': str(e), 'ImportJobs': [], 'ExportJobs': []}

    def _get_aws_auth(self):
        """Get AWS authentication for HTTP requests."""
        try:
            # Get AWS credentials from the session
            credentials = self.session.get_credentials()
            if not credentials:
                raise NoCredentialsError()

            # Create custom AWS authentication instance
            auth = AWSAuth(credentials=credentials, region=self.region, service='healthlake')

            return auth

        except Exception as e:
            logger.error(f'Failed to get AWS authentication: {e}')
            raise
