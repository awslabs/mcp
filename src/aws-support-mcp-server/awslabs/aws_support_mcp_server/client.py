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
"""AWS Support API client for the AWS Support MCP Server."""

import asyncio
import re
from typing import Any, Callable, Dict, List, Optional, Pattern, Union, cast

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from loguru import logger

from awslabs.aws_support_mcp_server.consts import (
    API_TIMEOUT,
    DEFAULT_REGION,
    ERROR_CASE_NOT_FOUND,
    ERROR_SUBSCRIPTION_REQUIRED,
    MAX_RESULTS_PER_PAGE,
    PERMITTED_LANGUAGE_CODES,
    IssueType,
)


class SupportClient:
    """Client for interacting with the AWS Support API.

    This client provides a convenient interface for interacting with the AWS Support API,
    handling authentication, error handling, and response formatting.

    Attributes:
        client: The boto3 Support client
        region_name: The AWS region name
    """

    _EMAIL_PATTERN: Pattern[str] = re.compile(
        r"^(?!.*\.\.)[a-zA-Z0-9](\.?[a-zA-Z0-9_\-+%])*@[a-zA-Z0-9-]+(\.[a-zA-Z]{2,})+$"
    )

    def __init__(self, region_name: str = DEFAULT_REGION, profile_name: Optional[str] = None):
        """Initialize the Support client.

        Args:
            region_name: AWS region name (default: us-east-1)
            profile_name: AWS profile name (optional)

        Raises:
            ClientError: If there is an error creating the boto3 client
        """
        try:
            logger.info(
                f"Initializing AWS Support client with region={region_name}, profile={profile_name}"
            )

            session_kwargs = {"region_name": region_name}
            if profile_name:
                session_kwargs["profile_name"] = profile_name

            logger.debug(f"Creating boto3 session with kwargs: {session_kwargs}")
            session = boto3.Session(**session_kwargs)

            # Log available AWS credentials
            try:
                credentials = session.get_credentials()
                if credentials:
                    logger.info(
                        f"AWS credentials found: access_key_id={credentials.access_key[:4]}***"
                    )
                else:
                    logger.warning("No AWS credentials found in session")
            except Exception as cred_err:
                logger.warning(f"Error checking credentials: {str(cred_err)}")

            # Create client with retry configuration
            retry_config = BotoConfig(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=API_TIMEOUT,
                read_timeout=10,
            )
            logger.debug("Creating support client with retry configuration")
            self.client = session.client("support", config=retry_config)
            self.region_name = region_name

            logger.info(f"Successfully initialized AWS Support client in region {region_name}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "SubscriptionRequiredException":
                logger.error(
                    f"{ERROR_SUBSCRIPTION_REQUIRED} - AWS Business Support or higher is required"
                )
                raise
            else:
                logger.error(
                    f"Failed to initialize AWS Support client: {error_code} - {error_message}"
                )
                raise
        except Exception as e:
            logger.error(
                f"Unexpected error initializing AWS Support client: {str(e)}", exc_info=True
            )
            raise

    async def _run_in_executor(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run a synchronous function in an executor.

        Args:
            func: The function to run
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function call

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def _validate_email_addresses(self, cc_email_addresses: List[str]) -> None:
        """Validate a list of email addresses.

        Args:
            cc_email_addresses: List of email addresses to validate

        Raises:
            ValueError: If any email address is invalid
        """
        if not cc_email_addresses:
            return

        invalid_emails = [
            email for email in cc_email_addresses if not self._EMAIL_PATTERN.match(email)
        ]
        if invalid_emails:
            raise ValueError(f"Invalid email address(es): {', '.join(invalid_emails)}")

    def _validate_issue_type(self, issue_type: str) -> None:
        """Validate the issue type.

        Args:
            issue_type: The issue type to validate

        Raises:
            ValueError: If the issue type is invalid
        """
        try:
            # This will raise ValueError if the issue_type is not a valid enum value
            cast(str, IssueType(issue_type))
        except ValueError as err:
            valid_types = [t.value for t in IssueType]
            raise ValueError(
                f"Invalid issue type: {issue_type}. Must be one of: {', '.join(valid_types)}"
            ) from err

    def _validate_language(self, language: str) -> None:
        """Validate the language code.

        Args:
            language: The language code to validate

        Raises:
            ValueError: If the language code is invalid
        """
        if language not in PERMITTED_LANGUAGE_CODES:
            raise ValueError(
                f"Invalid language code: {language}. Must be one of: {', '.join(PERMITTED_LANGUAGE_CODES)}"
            )

    async def create_case(
        self,
        subject: str,
        service_code: str,
        category_code: str,
        severity_code: str,
        communication_body: str,
        cc_email_addresses: Optional[List[str]] = None,
        language: str = "en",
        issue_type: str = "technical",
        attachment_set_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new support case.

        Args:
            subject: The subject of the support case
            service_code: The code for the AWS service
            category_code: The category code for the issue
            severity_code: The severity code for the issue
            communication_body: The initial communication for the case
            cc_email_addresses: Email addresses to CC on the case (optional)
            language: The language of the case (default: en)
            issue_type: The type of issue (default: technical)
            attachment_set_id: The ID of the attachment set (optional)

        Returns:
            A dictionary containing the case ID

        Raises:
            ClientError: If there is an error calling the AWS Support API
            ValueError: If any cc_email_addresses are invalid, or if issue_type or language is invalid
            Exception: If there is an unexpected error
        """
        try:
            # Validate inputs
            if cc_email_addresses:
                self._validate_email_addresses(cc_email_addresses)

            self._validate_issue_type(issue_type)
            self._validate_language(language)

            kwargs: Dict[str, Any] = {
                "subject": subject,
                "serviceCode": service_code,
                "categoryCode": category_code,
                "severityCode": severity_code,
                "communicationBody": communication_body,
                "language": language,
                "issueType": issue_type,
            }

            if cc_email_addresses:
                kwargs["ccEmailAddresses"] = cc_email_addresses

            if attachment_set_id:
                kwargs["attachmentSetId"] = attachment_set_id

            logger.debug(f"Creating support case: {subject}")
            response = await self._run_in_executor(self.client.create_case, **kwargs)

            logger.info(f"Created support case: {response['caseId']}")
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(f"Failed to create support case: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating support case: {str(e)}")
            raise

    async def describe_cases(
        self,
        case_id_list: Optional[List[str]] = None,
        display_id: Optional[str] = None,
        after_time: Optional[str] = None,
        before_time: Optional[str] = None,
        include_resolved_cases: bool = False,
        include_communications: bool = True,
        language: str = "en",
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve information about support cases.

        Args:
            case_id_list: List of case IDs to retrieve (optional)
            display_id: The display ID of the case (optional)
            after_time: The start date for a filtered date search (optional)
            before_time: The end date for a filtered date search (optional)
            include_resolved_cases: Include resolved cases in the results (default: False)
            include_communications: Include communications in the results (default: True)
            language: The language of the case (default: en)
            max_results: The maximum number of results to return (optional)
            next_token: A resumption point for pagination (optional)

        Returns:
            A dictionary containing the cases and a next token for pagination

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        try:
            # Convert snake_case parameter names to camelCase for the AWS API
            kwargs: Dict[str, Any] = {
                "includeResolvedCases": include_resolved_cases,
                "includeCommunications": include_communications,
                "language": language,
            }

            if case_id_list:
                kwargs["caseIdList"] = case_id_list
            if display_id:
                kwargs["displayId"] = display_id
            if after_time:
                kwargs["afterTime"] = after_time
            if before_time:
                kwargs["beforeTime"] = before_time
            if max_results:
                kwargs["maxResults"] = min(max_results, MAX_RESULTS_PER_PAGE)
            if next_token:
                kwargs["nextToken"] = next_token

            logger.debug(f"Describing support cases: {kwargs}")
            response = await self._run_in_executor(self.client.describe_cases, **kwargs)

            logger.info(f"Retrieved {len(response.get('cases', []))} support cases")
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "CaseIdNotFound":
                logger.error(ERROR_CASE_NOT_FOUND)
            else:
                logger.error(f"Failed to describe support cases: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error describing support cases: {str(e)}")
            raise

    async def resolve_case(self, case_id: str) -> Dict[str, Any]:
        """Resolve a support case.

        Args:
            case_id: The ID of the support case

        Returns:
            A dictionary containing the initial and final case status

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        try:
            logger.debug(f"Resolving support case: {case_id}")
            response = await self._run_in_executor(self.client.resolve_case, caseId=case_id)

            logger.info(f"Resolved support case: {case_id}")
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "CaseIdNotFound":
                logger.error(ERROR_CASE_NOT_FOUND)
            else:
                logger.error(f"Failed to resolve support case: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error resolving support case: {str(e)}")
            raise

    async def add_communication_to_case(
        self,
        case_id: str,
        communication_body: str = "",
        cc_email_addresses: Optional[List[str]] = None,
        attachment_set_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add communication to a support case.

        Args:
            case_id: The ID of the support case
            communication_body: The text of the communication
            cc_email_addresses: Email addresses to CC on the communication (optional)
            attachment_set_id: The ID of the attachment set (optional)

        Returns:
            A dictionary containing the result of the operation

        Raises:
            ValueError: If any cc_email_addresses are invalid
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        if cc_email_addresses:
            self._validate_email_addresses(cc_email_addresses)

        try:
            kwargs: Dict[str, Union[str, List[str]]] = {
                "caseId": case_id,
                "communicationBody": communication_body,
            }

            if cc_email_addresses:
                kwargs["ccEmailAddresses"] = cc_email_addresses

            if attachment_set_id:
                kwargs["attachmentSetId"] = attachment_set_id

            logger.debug(f"Adding communication to support case: {case_id}")
            response = await self._run_in_executor(self.client.add_communication_to_case, **kwargs)

            logger.info(f"Added communication to support case: {case_id}")
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "CaseIdNotFound":
                logger.error(ERROR_CASE_NOT_FOUND)
            else:
                logger.error(
                    f"Failed to add communication to support case: {error_code} - {error_message}"
                )
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding communication to support case: {str(e)}")
            raise

    async def describe_communications(
        self,
        case_id: str,
        after_time: Optional[str] = None,
        before_time: Optional[str] = None,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve communications for a support case.

        Args:
            case_id: The ID of the support case
            after_time: The start date for a filtered date search (optional)
            before_time: The end date for a filtered date search (optional)
            max_results: The maximum number of results to return (optional)
            next_token: A resumption point for pagination (optional)

        Returns:
            A dictionary containing the communications and a next token for pagination

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        try:
            kwargs: Dict[str, Union[str, int, List[str], None]] = {
                "caseId": case_id,
            }

            if after_time:
                kwargs["afterTime"] = after_time
            if before_time:
                kwargs["beforeTime"] = before_time
            if max_results:
                kwargs["maxResults"] = str(min(max_results, MAX_RESULTS_PER_PAGE))
            if next_token:
                kwargs["nextToken"] = next_token

            logger.debug(f"Describing communications for support case: {case_id}")
            response = await self._run_in_executor(self.client.describe_communications, **kwargs)

            logger.info(
                f"Retrieved {len(response.get('communications', []))} communications for support case: {case_id}"
            )
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "CaseIdNotFound":
                logger.error(ERROR_CASE_NOT_FOUND)
            else:
                logger.error(
                    f"Failed to describe communications for support case: {error_code} - {error_message}"
                )
            raise
        except Exception as e:
            logger.error(f"Unexpected error describing communications for support case: {str(e)}")
            raise

    async def describe_services(
        self, service_code_list: Optional[List[str]] = None, language: str = "en"
    ) -> Dict[str, Any]:
        """Retrieve available AWS services.

        Args:
            service_code_list: List of service codes to retrieve (optional)
            language: The language to use (default: en)

        Returns:
            A dictionary containing the services

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        try:
            kwargs: Dict[str, Any] = {
                "language": language,
            }

            if service_code_list:
                kwargs["serviceCodeList"] = service_code_list

            logger.debug("Describing AWS services")
            response = await self._run_in_executor(self.client.describe_services, **kwargs)

            logger.info(f"Retrieved {len(response.get('services', []))} AWS services")
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(f"Failed to describe AWS services: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error describing AWS services: {str(e)}")
            raise

    async def describe_severity_levels(self, language: str = "en") -> Dict[str, Any]:
        """Retrieve available severity levels.

        Args:
            language: The language to use (default: en)

        Returns:
            A dictionary containing the severity levels

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        try:
            logger.debug("Describing severity levels")
            response = await self._run_in_executor(
                self.client.describe_severity_levels, language=language
            )

            logger.info(f"Retrieved {len(response.get('severityLevels', []))} severity levels")
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(f"Failed to describe severity levels: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error describing severity levels: {str(e)}")
            raise

    async def describe_supported_languages(self) -> Dict[str, Any]:
        """Retrieve the list of supported languages for the AWS Support API.

        Returns:
            A dictionary containing the list of supported languages

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        try:
            logger.debug("Describing supported languages")
            response = await self._run_in_executor(self.client.describe_supported_languages)

            logger.info(f"Retrieved {len(response.get('languages', []))} supported languages")
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(f"Failed to describe supported languages: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error describing supported languages: {str(e)}")
            raise

    async def describe_create_case_options(
        self, service_code: str, language: str = "en"
    ) -> Dict[str, Any]:
        """Retrieve available options for creating a support case for a specific service.

        Args:
            service_code: The code for the AWS service
            language: The language to use (default: en)

        Returns:
            A dictionary containing the available categories and severity levels for the service

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error
        """
        try:
            kwargs: Dict[str, Any] = {
                "serviceCode": service_code,
                "language": language,
            }

            logger.debug(f"Describing create case options for service: {service_code}")
            response = await self._run_in_executor(
                self.client.describe_create_case_options, **kwargs
            )

            categories = len(response.get("categoryList", []))
            severity_levels = len(response.get("severityLevels", []))
            logger.info(
                f"Retrieved {categories} categories and {severity_levels} severity levels "
                f"for service: {service_code}"
            )
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(f"Failed to describe create case options: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error describing create case options: {str(e)}")
            raise

    async def add_attachments_to_set(
        self,
        attachments: List[Dict[str, str]],
        attachment_set_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add one or more attachments to an attachment set.

        If an attachment set ID is not specified, a new attachment set is created.
        The attachment set is available for 1 hour after it is created. The maximum
        size of an attachment file is 5 MB.

        Args:
            attachments: List of attachments to add. Each attachment should be a dict with:
                - data: The base64-encoded contents of the file
                - fileName: The name of the file
            attachment_set_id: The ID of the attachment set to add to (optional)

        Returns:
            A dictionary containing:
                - attachmentSetId: The ID of the attachment set
                - expiryTime: The time when the attachment set expires

        Raises:
            ClientError: If there is an error calling the AWS Support API
            Exception: If there is an unexpected error

        Example:
            >>> import base64
            >>> with open('file.txt', 'rb') as f:
            ...     data = base64.b64encode(f.read()).decode('utf-8')
            >>> attachments = [{'data': data, 'fileName': 'file.txt'}]
            >>> result = await client.add_attachments_to_set(attachments)
        """
        try:
            kwargs: Dict[str, Any] = {
                "attachments": [
                    {
                        "data": attachment["data"],
                        "fileName": attachment["fileName"],
                    }
                    for attachment in attachments
                ]
            }

            if attachment_set_id:
                kwargs["attachmentSetId"] = str(attachment_set_id) if attachment_set_id else None

            logger.debug(
                f"Adding {len(attachments)} attachments to "
                f"{'new set' if not attachment_set_id else f'set {attachment_set_id}'}"
            )
            response = await self._run_in_executor(self.client.add_attachments_to_set, **kwargs)

            logger.info(f"Added attachments to set: {response['attachmentSetId']}")
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"Failed to add attachments to set: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding attachments to set: {str(e)}")
            raise

    async def _retry_with_backoff(
        self, func: Callable[..., Any], *args: Any, max_retries: int = 3, **kwargs: Any
    ) -> Any:
        """Retry a function with exponential backoff.

        Args:
            func: The function to retry
            *args: Positional arguments to pass to the function
            max_retries: The maximum number of retries (default: 3)
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function call

        Raises:
            ClientError: If there is an error calling the AWS Support API after all retries
            Exception: If there is an unexpected error
        """
        retries = 0
        while True:
            try:
                func_kwargs = {k: v for k, v in kwargs.items() if k != "max_retries"}
                return await func(*args, **func_kwargs)
            except ClientError as e:
                error_code = e.response["Error"]["Code"]

                if (
                    error_code in ["ThrottlingException", "TooManyRequestsException"]
                    and retries < max_retries
                ):
                    wait_time = 2**retries
                    logger.warning(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    retries += 1
                else:
                    raise
            except Exception:
                raise
