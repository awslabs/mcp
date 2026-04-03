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

"""Client for Amazon Bedrock Custom Model Import operations."""

import secrets
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.aws import (
    get_aws_client,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.matching import approximate_match
from botocore.exceptions import ClientError
from loguru import logger
from typing import Any, Dict, Optional


class BedrockModelImportClient:
    """Client for Amazon Bedrock Custom Model Import operations."""

    def __init__(self, region_name: str, profile_name: str | None = None):
        """Initialize the client with the given region and profile.

        Args:
            region_name: AWS region name
            profile_name: AWS profile name
        """
        self.region_name = region_name
        self.profile_name = profile_name
        self.bedrock_client = self._create_bedrock_client()
        self.s3_client = self._create_s3_client()
        logger.debug('Bedrock client initialized')

    def _create_bedrock_client(self) -> Any:
        """Create a Bedrock client.

        Returns:
            Any: Bedrock client
        """
        return get_aws_client(
            'bedrock',
            region_name=self.region_name,
            profile_name=self.profile_name,
        )

    def _create_s3_client(self) -> Any:
        """Create an S3 client.

        Returns:
            Any: S3 client
        """
        return get_aws_client(
            's3',
            region_name=self.region_name,
            profile_name=self.profile_name,
        )

    def create_model_import_job(self, create_args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a model import job.

        Args:
            create_args: Arguments for creating the model import job

        Returns:
            Dict[str, Any]: Response from the Bedrock API

        Raises:
            ClientError: If there is an error from the AWS service
        """
        try:
            response = self.bedrock_client.create_model_import_job(**create_args)
            logger.info(f'Created model import job: {create_args["jobName"]}')
            return response
        except ClientError as e:
            logger.error(f'Error creating model import job: {str(e)}')
            raise

    def get_model_import_job(self, job_identifier: str) -> Dict[str, Any]:
        """Get model import job details.

        Args:
            job_identifier: Name or ARN of the job

        Returns:
            Dict[str, Any]: Job details

        Raises:
            ValueError: If job cannot be found even with approximate matching
            ClientError: If there is an error from the AWS service
        """
        try:
            response = self.bedrock_client.get_model_import_job(jobIdentifier=job_identifier)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException':
                matched_job_name = self._find_job_by_approximate_match(job_identifier)
                if matched_job_name:
                    logger.info(f'Using closest matched job name: {matched_job_name}')
                    try:
                        response = self.bedrock_client.get_model_import_job(
                            jobIdentifier=matched_job_name
                        )
                        return response
                    except ClientError as e:
                        # If the second call also fails, raise the original error
                        error_msg = (
                            f'Approximate matched job {matched_job_name} also failed: {str(e)}'
                        )
                        logger.error(error_msg)
                        raise ValueError(
                            f'Could not find a job matching the name or ARN: {job_identifier}'
                        )
                else:
                    error_msg = f'Could not find a job matching the name or ARN: {job_identifier}'
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                logger.error(f'Error fetching import model job: {str(e)}')
                raise

    def list_model_import_jobs(self, **kwargs) -> Dict[str, Any]:
        """List model import jobs.

        Args:
            **kwargs: Optional parameters for filtering and pagination

        Returns:
            Dict[str, Any]: List of model import job summaries

        Raises:
            ClientError: If there is an error from the AWS service
        """
        try:
            response = self.bedrock_client.list_model_import_jobs(**kwargs)
            return response
        except ClientError as e:
            logger.error(f'Error listing model import jobs: {str(e)}')
            raise

    def get_imported_model(self, model_identifier: str) -> Dict[str, Any]:
        """Get imported model details.

        Args:
            model_identifier: Name or ARN of the model

        Returns:
            Dict[str, Any]: Model details

        Raises:
            ValueError: If model cannot be found even with approximate matching
            ClientError: If there is an error from the AWS service
        """
        try:
            response = self.bedrock_client.get_imported_model(modelIdentifier=model_identifier)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException':
                matched_model_name = self._find_model_by_approximate_match(model_identifier)
                if matched_model_name:
                    logger.info(f'Using approximate matched model name: {matched_model_name}')
                    try:
                        response = self.bedrock_client.get_imported_model(
                            modelIdentifier=matched_model_name
                        )
                        return response
                    except ClientError as e:
                        # If the second call also fails, raise the original error
                        error_msg = (
                            f'Approximate matched model {matched_model_name} also failed: {str(e)}'
                        )
                        logger.error(error_msg)
                        raise ValueError(
                            f'Could not find the model {model_identifier}. It could have been deleted.'
                        )
                else:
                    error_msg = (
                        f'Could not find the model {model_identifier}. It could have been deleted.'
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                logger.error(f'Error fetching imported model: {str(e)}')
                raise

    def list_imported_models(self, **kwargs) -> Dict[str, Any]:
        """List imported models.

        Args:
            **kwargs: Optional parameters for filtering and pagination

        Returns:
            Dict[str, Any]: List of model summaries

        Raises:
            ClientError: If there is an error from the AWS service
        """
        try:
            response = self.bedrock_client.list_imported_models(**kwargs)
            return response
        except ClientError as e:
            logger.error(f'Error listing imported models: {str(e)}')
            raise

    def delete_imported_model(self, model_identifier: str) -> None:
        """Delete an imported model.

        Args:
            model_identifier: ID or ARN of the model to delete

        Raises:
            ClientError: If there is an error from the AWS service
        """
        try:
            self.bedrock_client.delete_imported_model(modelIdentifier=model_identifier)
            logger.info(f'Successfully deleted model: {model_identifier}')
        except ClientError as e:
            logger.error(f'Error deleting imported model: {str(e)}')
            raise

    def _paginate_results(self, paginator, **kwargs) -> list:
        """Helper method for pagination.

        Args:
            paginator: The paginator object
            **kwargs: Additional parameters to pass to the paginate method

        Returns:
            list: Aggregated results from all pages

        Raises:
            ClientError: If there is an error from the AWS service (except throttling errors)
        """
        all_results = []

        try:
            for page in paginator.paginate(**kwargs):
                for key in page:
                    if isinstance(page[key], list):
                        all_results.extend(page[key])
                        break
        except ClientError as e:
            if e.response['Error']['Code'] in [
                'ThrottlingException',
                'Throttling',
                'TooManyRequestsException',
                'RequestLimitExceeded',
            ]:
                logger.warning(
                    'Throttling occurred during pagination. Proceeding with partial results.'
                )
                return all_results
            raise

        return all_results

    def _find_model_in_s3(self, bucket_name: str, model_name: str) -> Optional[str]:
        """Search for a model in S3 bucket using approximate matching.

        Uses approximate string matching to find the best matching path for the model.
        If multiple matches have the same score, one is chosen randomly.
        Only considers paths that contain at least one .safetensors file.

        Args:
            s3_client: The S3 client
            bucket_name: Name of the S3 bucket
            model_name: Name of the model to find

        Returns:
            Optional[str]: S3 URI if found, None otherwise
        """
        try:
            # Get all objects in the bucket using the pagination helper
            paginator = self.s3_client.get_paginator('list_objects_v2')
            all_objects = self._paginate_results(paginator, Bucket=bucket_name)
            if not all_objects:
                logger.warning(
                    f'No objects found in bucket {bucket_name}. Please ensure the bucket exists and contains model files.'
                )
                return None

            # Find paths that contain .safetensors files
            valid_model_paths = {}  # {path_name: full_path}
            for obj in all_objects:
                key = obj['Key']
                if key.endswith('.safetensors'):  # Only process .safetensors files
                    parts = key.split('/')
                    if len(parts) >= 2:  # Must have at least a path and file
                        path_name = parts[-2]
                        if path_name not in valid_model_paths:
                            # Find the full path to this path
                            path_index = parts.index(path_name)
                            model_path = '/'.join(parts[: path_index + 1])
                            valid_model_paths[path_name] = model_path

            if not valid_model_paths:
                logger.warning(
                    f'No model paths with .safetensors files found in bucket {bucket_name}. '
                    'Please ensure model paths contain Hugging Face model weights in .safetensors format.'
                )
                return None

            # Get list of path names for approximate matching
            path_candidates = list(valid_model_paths.keys())

            # Use the approximate matching utility function
            best_matches = approximate_match(path_candidates, model_name)
            if not best_matches:
                logger.warning(f'No closest matching model found for {model_name}.')
                return None

            logger.debug(f'Found following models in the bucket: {best_matches}')

            # If multiple matches have the same score, choose one randomly
            chosen_path = secrets.choice(best_matches)

            logger.debug(
                f'Found model path "{chosen_path}" with approximate match '
                f'(searching for "{model_name}")'
            )

            # Return the full path for the chosen path
            return f's3://{bucket_name}/{valid_model_paths[chosen_path]}'

        except Exception as e:
            logger.warning(
                f'Error searching for model {model_name} in bucket {bucket_name}: {str(e)}. '
            )
            if isinstance(e, ClientError):
                error_code = e.response['Error']['Code']
                if error_code == 'AccessDenied':
                    logger.warning('Not enough permissions to query the bucket')
                    return None
            raise e

    def _find_job_by_approximate_match(self, job_name: str) -> Optional[str]:
        """Find a job by name.

        First tries using nameContains parameter, then falls back to approximate matching if no results.

        Args:
            bedrock_client: The Bedrock client
            job_name: Name of the job to find

        Returns:
            Optional[str]: Matched job name if found, None otherwise
        """
        try:
            try:
                response = self.bedrock_client.list_model_import_jobs(nameContains=job_name)
                jobs = [
                    (job['jobName'], job['status']) for job in response['modelImportJobSummaries']
                ]

                if jobs:
                    # If jobs found, prefer active jobs
                    active_jobs = [
                        (name, status) for name, status in jobs if status == 'InProgress'
                    ]
                    if active_jobs:
                        chosen_job = active_jobs[0][0]
                    else:
                        chosen_job = jobs[0][0]

                    logger.debug(f'Found job "{chosen_job}" using nameContains="{job_name}"')
                    return chosen_job

                # If no jobs found, fall back to approximate matching
                logger.debug(
                    f'No jobs found using nameContains="{job_name}", falling back to approximate matching'
                )
            except Exception as e:
                logger.warning(
                    f'Error using nameContains parameter: {str(e)}, falling back to approximate matching'
                )

            # Fall back to approximate matching
            # Create a map of job names to their status
            job_status_map = {}
            paginator = self.bedrock_client.get_paginator('list_model_import_jobs')
            job_summaries = self._paginate_results(paginator)
            for job in job_summaries:
                job_status_map[job['jobName']] = job['status']

            if not job_status_map:
                logger.warning('No model import jobs found')
                return None

            # Use the approximate matching utility function
            best_matches = approximate_match(list(job_status_map.keys()), job_name)
            if not best_matches:
                return None

            # If multiple matches have the same score, prefer active jobs
            active_matches = [
                name for name in best_matches if job_status_map[name] == 'InProgress'
            ]
            if active_matches:
                chosen_job = secrets.choice(active_matches)
            else:
                chosen_job = secrets.choice(best_matches)

            logger.debug(
                f'Found job "{chosen_job}" with approximate match (searching for "{job_name}")'
            )
            return chosen_job
        except Exception as e:
            logger.error(f'Error searching for job {job_name}: {str(e)}')
            raise e

    def _find_model_by_approximate_match(self, model_name: str) -> Optional[str]:
        """Find a model by name.

        First tries using nameContains parameter, then falls back to approximate matching if no results.

        Args:
            bedrock_client: The Bedrock client
            model_name: Name of the model to find

        Returns:
            Optional[str]: Matched model name if found, None otherwise
        """
        try:
            try:
                response = self.bedrock_client.list_imported_models(nameContains=model_name)
                model_names = [model['modelName'] for model in response['modelSummaries']]

                if model_names:
                    # If models found, use the first one
                    chosen_model = model_names[0]

                    logger.debug(f'Found model "{chosen_model}" from the list of imported models"')
                    return chosen_model

                # If no models found, fall back to approximate matching
                logger.debug(
                    f'No models found using {model_name}, falling back to approximate matching'
                )
            except Exception as e:
                logger.warning(
                    f'Error using listing imported models: {str(e)}, falling back to approximate matching'
                )

            # Fall back to approximate matching
            # Get a list of all model names
            paginator = self.bedrock_client.get_paginator('list_imported_models')
            model_summaries = self._paginate_results(paginator)
            model_names = [model['modelName'] for model in model_summaries]

            if not model_names:
                logger.warning('No imported models found')
                return None

            # Use the approximate matching utility function
            best_matches = approximate_match(model_names, model_name)

            if not best_matches:
                return None

            # Choose one of the best matches randomly
            chosen_model = secrets.choice(best_matches)

            logger.debug(
                f'Found model "{chosen_model}" with approximate match '
                f'(searching for "{model_name}")'
            )
            return chosen_model
        except Exception as e:
            logger.error(f'Error searching for model {model_name}: {str(e)}')
            raise e
