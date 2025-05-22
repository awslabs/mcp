# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use
# this file except in compliance with the License. A copy of the License is
# located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an
# 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing permissions and
# limitations under the License.

"""Data models for the AWS Support MCP Server."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from awslabs.aws_support_mcp_server.consts import DEFAULT_ISSUE_TYPE, DEFAULT_LANGUAGE


class IssueType(str, Enum):
    """Issue types for AWS Support cases."""
    TECHNICAL = "technical"
    ACCOUNT_AND_BILLING = "account-and-billing"
    SERVICE_LIMIT = "service-limit"

class CaseStatus(str, Enum):
    """Status values for AWS Support cases."""
    OPENED = "opened"
    PENDING_CUSTOMER_ACTION = "pending-customer-action"
    RESOLVED = "resolved"
    UNASSIGNED = "unassigned"
    WORK_IN_PROGRESS = "work-in-progress"
    CLOSED = "closed"

JsonValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

class AttachmentDetails(BaseModel):
    """Details of an attachment to a support case communication."""

    attachment_id: str = Field(
        ...,
        description="The ID of the attachment",
        alias="attachmentId"
    )
    file_name: str = Field(
        ...,
        description="The file name of the attachment",
        alias="fileName"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        return {
            "attachmentId": self.attachment_id,
            "fileName": self.file_name
        }


class Communication(BaseModel):
    """A communication in a support case."""

    body: str = Field(
        ...,
        description="The text of the communication",
        min_length=1,
        max_length=8000
    )
    case_id: Optional[str] = Field(
        None,
        description="The ID of the support case",
        alias="caseId"
    )
    submitted_by: Optional[str] = Field(
        None,
        description="The identity of the account that submitted the communication",
        alias="submittedBy"
    )
    time_created: Optional[str] = Field(
        None,
        description="The time the communication was created",
        alias="timeCreated"
    )
    attachment_set: Optional[List[AttachmentDetails]] = Field(
        None,
        description="Information about the attachments to the case communication",
        alias="attachmentSet"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        result = {
            "body": self.body
        }

        if self.case_id:
            result["caseId"] = self.case_id
        if self.submitted_by:
            result["submittedBy"] = self.submitted_by
        if self.time_created:
            result["timeCreated"] = self.time_created
        if self.attachment_set:
            result["attachmentSet"] = [a.model_dump() for a in self.attachment_set]

        return result


class RecentCommunications(BaseModel):
    """Recent communications for a support case."""

    communications: List[Communication] = Field(
        default_factory=list,
        description="The five most recent communications associated with the case"
    )
    next_token: Optional[str] = Field(
        None,
        description="A resumption point for pagination",
        alias="nextToken"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        result = {
            "communications": [c.model_dump() for c in self.communications]
        }

        if self.next_token:
            result["nextToken"] = self.next_token

        return result


class Category(BaseModel):
    """A category for an AWS service."""

    code: str = Field(
        ..., description="The category code for the support case"
    )
    name: str = Field(
        ..., description="The category name for the support case"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        return {
            "code": self.code,
            "name": self.name
        }


class Service(BaseModel):
    """An AWS service."""

    code: str = Field(
        ..., description="The code for the AWS service"
    )
    name: str = Field(
        ..., description="The name of the AWS service"
    )
    categories: List[Category] = Field(
        default_factory=list,
        description="The categories for the AWS service"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        return {
            "code": self.code,
            "name": self.name,
            "categories": [c.model_dump() for c in self.categories]
        }


class SeverityLevel(BaseModel):
    """A severity level for a support case."""

    code: str = Field(
        ..., description="The code for the severity level"
    )
    name: str = Field(
        ..., description="The name of the severity level"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        return {
            "code": self.code,
            "name": self.name
        }


class SupportCase(BaseModel):
    """An AWS Support case."""

    case_id: str = Field(
        ...,
        description="The ID of the support case",
        alias="caseId"
    )
    display_id: Optional[str] = Field(
        None,
        description="The display ID of the support case",
        alias="displayId"
    )
    subject: str = Field(
        ..., description="The subject of the support case"
    )
    status: CaseStatus = Field(
        ..., description="The status of the support case"
    )
    service_code: str = Field(
        ...,
        description="The code for the AWS service",
        alias="serviceCode"
    )
    category_code: str = Field(
        ...,
        description="The category code for the issue",
        alias="categoryCode"
    )
    severity_code: str = Field(
        ...,
        description="The severity code for the issue",
        alias="severityCode"
    )
    submitted_by: str = Field(
        ...,
        description="The email address of the submitter",
        alias="submittedBy"
    )
    time_created: str = Field(
        ...,
        description="The time the case was created",
        alias="timeCreated"
    )
    recent_communications: Optional[RecentCommunications] = Field(
        None,
        description="Recent communications on the case",
        alias="recentCommunications"
    )
    cc_email_addresses: Optional[List[str]] = Field(
        None,
        description="Email addresses that receive copies of case correspondence",
        alias="ccEmailAddresses"
    )
    language: Optional[str] = Field(
        None, description="The language of the case"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        result = {
            "caseId": self.case_id,
            "subject": self.subject,
            "status": self.status,
            "serviceCode": self.service_code,
            "categoryCode": self.category_code,
            "severityCode": self.severity_code,
            "submittedBy": self.submitted_by,
            "timeCreated": self.time_created
        }

        if self.display_id:
            result["displayId"] = self.display_id
        if self.recent_communications:
            result["recentCommunications"] = self.recent_communications.model_dump()
        if self.cc_email_addresses:
            result["ccEmailAddresses"] = self.cc_email_addresses
        if self.language:
            result["language"] = self.language

        return result


# Request Models

class CreateCaseRequest(BaseModel):
    """Request model for creating a support case."""

    subject: str = Field(
        ..., description="The subject of the support case"
    )
    service_code: str = Field(
        ...,
        description="The code for the AWS service",
        alias="serviceCode"
    )
    category_code: str = Field(
        ...,
        description="The category code for the issue",
        alias="categoryCode"
    )
    severity_code: str = Field(
        ...,
        description="The severity code for the issue",
        alias="severityCode"
    )
    communication_body: str = Field(
        ...,
        description="The initial communication for the case",
        min_length=1,
        max_length=8000,
        alias="communicationBody"
    )
    cc_email_addresses: Optional[List[str]] = Field(
        None,
        description="Email addresses to CC on the case",
        max_items=10,
        alias="ccEmailAddresses"
    )
    language: str = Field(
        DEFAULT_LANGUAGE,
        description="The language of the case (ISO 639-1 code)"
    )
    issue_type: str = Field(
        DEFAULT_ISSUE_TYPE,
        description="The type of issue: technical, account-and-billing, or service-limit",
        alias="issueType"
    )
    attachment_set_id: Optional[str] = Field(
        None,
        description="The ID of the attachment set",
        alias="attachmentSetId"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def to_api_params(self) -> Dict[str, JsonValue]:
        """Convert to AWS API parameters."""
        params = {
            "subject": self.subject,
            "service_code": self.service_code,
            "category_code": self.category_code,
            "severity_code": self.severity_code,
            "communication_body": self.communication_body,
            "language": self.language,
            "issue_type": self.issue_type
        }

        if self.cc_email_addresses:
            params["cc_email_addresses"] = self.cc_email_addresses
        if self.attachment_set_id:
            params["attachment_set_id"] = self.attachment_set_id

        return params


class DescribeCasesRequest(BaseModel):
    """Request model for describing support cases."""

    case_id_list: Optional[List[str]] = Field(
        None,
        description="List of case IDs to retrieve",
        max_items=100,
        alias="caseIdList"
    )
    display_id: Optional[str] = Field(
        None,
        description="The display ID of the case",
        alias="displayId"
    )
    after_time: Optional[str] = Field(
        None,
        description="The start date for a filtered date search",
        alias="afterTime"
    )
    before_time: Optional[str] = Field(
        None,
        description="The end date for a filtered date search",
        alias="beforeTime"
    )
    include_resolved_cases: bool = Field(
        False,
        description="Include resolved cases in the results",
        alias="includeResolvedCases"
    )
    include_communications: bool = Field(
        True,
        description="Include communications in the results",
        alias="includeCommunications"
    )
    language: str = Field(
        DEFAULT_LANGUAGE, description="The language of the case (ISO 639-1 code)"
    )
    max_results: Optional[int] = Field(
        None,
        description="The maximum number of results to return",
        ge=10,
        le=100,
        alias="maxResults"
    )
    next_token: Optional[str] = Field(
        None,
        description="A resumption point for pagination",
        alias="nextToken"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def to_api_params(self) -> Dict[str, JsonValue]:
        """Convert to AWS API parameters."""
        params = {
            "include_resolved_cases": self.include_resolved_cases,
            "include_communications": self.include_communications,
            "language": self.language
        }

        if self.case_id_list:
            params["case_id_list"] = self.case_id_list
        if self.display_id:
            params["display_id"] = self.display_id
        if self.after_time:
            params["after_time"] = self.after_time
        if self.before_time:
            params["before_time"] = self.before_time
        if self.max_results:
            params["max_results"] = self.max_results
        if self.next_token:
            params["next_token"] = self.next_token

        return params


class AddCommunicationRequest(BaseModel):
    """Request model for adding communication to a case."""

    case_id: str = Field(
        ...,
        description="The ID of the support case",
        alias="caseId"
    )
    communication_body: str = Field(
        ...,
        description="The text of the communication",
        min_length=1,
        max_length=8000,
        alias="communicationBody"
    )
    cc_email_addresses: Optional[List[str]] = Field(
        None,
        description="Email addresses to CC on the communication",
        max_items=10,
        alias="ccEmailAddresses"
    )
    attachment_set_id: Optional[str] = Field(
        None,
        description="The ID of the attachment set",
        alias="attachmentSetId"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def to_api_params(self) -> Dict[str, JsonValue]:
        """Convert to AWS API parameters."""
        params = {
            "case_id": self.case_id,
            "communication_body": self.communication_body
        }

        if self.cc_email_addresses:
            params["cc_email_addresses"] = self.cc_email_addresses
        if self.attachment_set_id:
            params["attachment_set_id"] = self.attachment_set_id

        return params


class ResolveCaseRequest(BaseModel):
    """Request model for resolving a support case."""

    case_id: str = Field(
        ...,
        description="The ID of the support case",
        alias="caseId"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def to_api_params(self) -> Dict[str, Any]:
        """Convert to AWS API parameters."""
        return {
            "case_id": self.case_id
        }


# Response Models

class CreateCaseResponse(BaseModel):
    """Response model for creating a support case."""

    case_id: str = Field(
        ...,
        description="The ID of the created support case",
        alias="caseId"
    )
    status: str = Field(
        "success", description="The status of the operation"
    )
    message: str = Field(
        ..., description="A message describing the result of the operation"
    )
    detected_language: Optional[str] = Field(
        None, description="The detected language of the case (if auto-detected)"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True


class DescribeCasesResponse(BaseModel):
    """Response model for describing support cases."""

    cases: List[SupportCase] = Field(
        ..., description="The list of support cases"
    )
    next_token: Optional[str] = Field(
        None,
        description="A resumption point for pagination",
        alias="nextToken"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True


class AddCommunicationResponse(BaseModel):
    """Response model for adding communication to a case."""

    result: bool = Field(
        ..., description="Whether the operation was successful"
    )
    status: str = Field(
        "success", description="The status of the operation"
    )
    message: str = Field(
        ..., description="A message describing the result of the operation"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True


class ResolveCaseResponse(BaseModel):
    """Response model for resolving a support case."""

    initial_case_status: str = Field(
        ...,
        description="The status of the case before resolving",
        alias="initial_case_status"
    )
    final_case_status: str = Field(
        ...,
        description="The status of the case after resolving",
        alias="final_case_status"
    )
    status: str = Field(
        "success", description="The status of the operation"
    )
    message: str = Field(
        ..., description="A message describing the result of the operation"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True


class DescribeCreateCaseOptionsRequest(BaseModel):
    """Request model for describing create case options."""

    service_code: str = Field(
        ...,
        description="The code for the AWS service",
        alias="serviceCode"
    )
    language: str = Field(
        DEFAULT_LANGUAGE,
        description="The language to use (ISO 639-1 code)"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def to_api_params(self) -> Dict[str, JsonValue]:
        """Convert to AWS API parameters."""
        return {
            "service_code": self.service_code,
            "language": self.language
        }


class CreateCaseCategory(BaseModel):
    """Model for a category in create case options."""

    code: str = Field(
        ...,
        description="The code for the category"
    )
    name: str = Field(
        ...,
        description="The name of the category"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        return {
            "code": self.code,
            "name": self.name
        }


class DescribeCreateCaseOptionsResponse(BaseModel):
    """Response model for describing create case options."""

    category_list: List[CreateCaseCategory] = Field(
        ...,
        description="The list of available categories for the specified service",
        alias="categoryList"
    )
    severity_levels: List[SeverityLevel] = Field(
        ...,
        description="The list of available severity levels for the specified service",
        alias="severityLevels"
    )
    status: str = Field(
        "success",
        description="The status of the operation"
    )
    message: str = Field(
        ...,
        description="A message describing the result of the operation"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        return {
            "categoryList": [cat.model_dump() for cat in self.category_list],
            "severityLevels": [sev.model_dump() for sev in self.severity_levels]
        }
class AttachmentData(BaseModel):
    """Model for attachment data."""

    data: str = Field(
        ...,
        description="The base64-encoded contents of the attachment"
    )
    file_name: str = Field(
        ...,
        description="The name of the attachment file",
        alias="fileName"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def model_dump(self) -> Dict[str, JsonValue]:
        """Convert model to dictionary."""
        return {
            "data": self.data,
            "fileName": self.file_name
        }


class AddAttachmentsToSetRequest(BaseModel):
    """Request model for adding attachments to a set."""

    attachments: List[AttachmentData] = Field(
        ...,
        description="The list of attachments to add. Each attachment must be base64-encoded and "
                    "less than 5MB in size.",
        min_items=1
    )
    attachment_set_id: Optional[str] = Field(
        None,
        description="The ID of an existing attachment set to add to. If not specified, "
                    "a new attachment set will be created.",
        alias="attachmentSetId"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def to_api_params(self) -> Dict[str, JsonValue]:
        """Convert to AWS API parameters."""
        params = {
            "attachments": [a.model_dump() for a in self.attachments]
        }

        if self.attachment_set_id:
            params["attachment_set_id"] = self.attachment_set_id

        return params


class AddAttachmentsToSetResponse(BaseModel):
    """Response model for adding attachments to a set."""

    attachment_set_id: str = Field(
        ...,
        description="The ID of the attachment set",
        alias="attachmentSetId"
    )
    expiry_time: str = Field(
        ...,
        description="The time when the attachment set expires (ISO 8601 format)",
        alias="expiryTime"
    )
    status: str = Field(
        "success", description="The status of the operation"
    )
    message: str = Field(
        ..., description="A message describing the result of the operation"
    )

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True


class DescribeSupportedLanguagesRequest(BaseModel):
    """Request model for describing supported languages.

    This operation takes no parameters but we include a request model
    for consistency with other operations.
    """

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True

    def to_api_params(self) -> Dict[str, JsonValue]:
        """Convert to AWS API parameters."""
        return {}  # No parameters needed for this operation


class SupportedLanguage(BaseModel):
    """Model for a supported language."""

    code: str = Field(
        ...,
        description="The ISO 639-1 language code (e.g., 'en' for English)"
    )
    name: str = Field(
        ...,
        description="The full name of the language in English"
    )
    native_name: Optional[str] = Field(
        None, description="The name of the language in its native script"
    )


class DescribeSupportedLanguagesResponse(BaseModel):
    """Response model for describing supported languages."""

    languages: List[str] = Field(
        ...,
        description="The list of supported language codes"
    )
    status: str = Field(
        "success",
        description="The status of the operation"
    )
    message: str = Field(
        ..., description="A message describing the result of the operation"
    )

    class Config:
        """Pydantic model configuration."""

