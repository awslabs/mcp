"""Tests for the AWS Support MCP Server data models."""

import pytest
from pydantic import ValidationError

from awslabs.aws_support_mcp_server.models import (
    AddAttachmentsToSetRequest,
    AddAttachmentsToSetResponse,
    AddCommunicationRequest,
    AddCommunicationResponse,
    AttachmentData,
    AttachmentDetails,
    CaseStatus,
    Category,
    Communication,
    CreateCaseRequest,
    CreateCaseResponse,
    DescribeCasesRequest,
    DescribeCasesResponse,
    DescribeSupportedLanguagesRequest,
    DescribeSupportedLanguagesResponse,
    IssueType,
    RecentCommunications,
    ResolveCaseRequest,
    ResolveCaseResponse,
    Service,
    SeverityLevel,
    SupportCase,
    SupportedLanguage,
)

# Test Data
VALID_ATTACHMENT_DETAILS = {"attachmentId": "test-attachment-id", "fileName": "test.txt"}

VALID_COMMUNICATION = {
    "body": "Test communication body",
    "caseId": "test-case-id",
    "submittedBy": "test@example.com",
    "timeCreated": "2023-01-01T00:00:00Z",
    "attachmentSet": [VALID_ATTACHMENT_DETAILS],
}

VALID_RECENT_COMMUNICATIONS = {"communications": [VALID_COMMUNICATION], "nextToken": "test-token"}

VALID_CATEGORY = {"code": "test-category", "name": "Test Category"}

VALID_SERVICE = {"code": "test-service", "name": "Test Service", "categories": [VALID_CATEGORY]}

VALID_SEVERITY_LEVEL = {"code": "test-severity", "name": "Test Severity"}

VALID_SUPPORT_CASE = {
    "caseId": "test-case-id",
    "displayId": "test-display-id",
    "subject": "Test subject",
    "status": "opened",
    "serviceCode": "test-service",
    "categoryCode": "test-category",
    "severityCode": "test-severity",
    "submittedBy": "test@example.com",
    "timeCreated": "2023-01-01T00:00:00Z",
    "recentCommunications": VALID_RECENT_COMMUNICATIONS,
    "ccEmailAddresses": ["cc@example.com"],
    "language": "en",
}


class TestBaseModels:
    """Tests for base data models."""

    def test_attachment_details(self):
        """Test AttachmentDetails model."""
        # Test valid data
        attachment = AttachmentDetails(**VALID_ATTACHMENT_DETAILS)
        assert attachment.attachment_id == "test-attachment-id"
        assert attachment.file_name == "test.txt"

        # Test model_dump
        dumped = attachment.model_dump()
        assert dumped["attachmentId"] == "test-attachment-id"
        assert dumped["fileName"] == "test.txt"

        # Test invalid data
        with pytest.raises(ValidationError):
            AttachmentDetails()  # Missing required fields

    def test_communication(self):
        """Test Communication model."""
        # Test valid data
        comm = Communication(**VALID_COMMUNICATION)
        assert comm.body == "Test communication body"
        assert comm.case_id == "test-case-id"
        assert comm.submitted_by == "test@example.com"
        assert comm.time_created == "2023-01-01T00:00:00Z"
        assert len(comm.attachment_set) == 1

        # Test model_dump
        dumped = comm.model_dump()
        assert dumped["body"] == "Test communication body"
        assert dumped["caseId"] == "test-case-id"
        assert dumped["submittedBy"] == "test@example.com"
        assert dumped["timeCreated"] == "2023-01-01T00:00:00Z"
        assert len(dumped["attachmentSet"]) == 1

        # Test invalid data
        with pytest.raises(ValidationError):
            Communication()  # Missing required fields

        # Test body length validation
        with pytest.raises(ValidationError):
            Communication(body="")  # Empty body

        with pytest.raises(ValidationError):
            Communication(body="x" * 8001)  # Body too long

    def test_recent_communications(self):
        """Test RecentCommunications model."""
        # Test valid data
        recent = RecentCommunications(**VALID_RECENT_COMMUNICATIONS)
        assert len(recent.communications) == 1
        assert recent.next_token == "test-token"

        # Test model_dump
        dumped = recent.model_dump()
        assert len(dumped["communications"]) == 1
        assert dumped["nextToken"] == "test-token"

        # Test empty communications
        empty = RecentCommunications(communications=[])
        assert len(empty.communications) == 0
        assert empty.next_token is None

    def test_category(self):
        """Test Category model."""
        # Test valid data
        category = Category(**VALID_CATEGORY)
        assert category.code == "test-category"
        assert category.name == "Test Category"

        # Test model_dump
        dumped = category.model_dump()
        assert dumped["code"] == "test-category"
        assert dumped["name"] == "Test Category"

        # Test invalid data
        with pytest.raises(ValidationError):
            Category()  # Missing required fields

    def test_service(self):
        """Test Service model."""
        # Test valid data
        service = Service(**VALID_SERVICE)
        assert service.code == "test-service"
        assert service.name == "Test Service"
        assert len(service.categories) == 1

        # Test model_dump
        dumped = service.model_dump()
        assert dumped["code"] == "test-service"
        assert dumped["name"] == "Test Service"
        assert len(dumped["categories"]) == 1

        # Test invalid data
        with pytest.raises(ValidationError):
            Service()  # Missing required fields

        # Test empty categories
        service = Service(code="test", name="Test", categories=[])
        assert len(service.categories) == 0

    def test_severity_level(self):
        """Test SeverityLevel model."""
        # Test valid data
        severity = SeverityLevel(**VALID_SEVERITY_LEVEL)
        assert severity.code == "test-severity"
        assert severity.name == "Test Severity"

        # Test model_dump
        dumped = severity.model_dump()
        assert dumped["code"] == "test-severity"
        assert dumped["name"] == "Test Severity"

        # Test invalid data
        with pytest.raises(ValidationError):
            SeverityLevel()  # Missing required fields

    def test_support_case(self):
        """Test SupportCase model."""
        # Test valid data
        case = SupportCase(**VALID_SUPPORT_CASE)
        assert case.case_id == "test-case-id"
        assert case.display_id == "test-display-id"
        assert case.subject == "Test subject"
        assert case.status == CaseStatus.OPENED
        assert case.service_code == "test-service"
        assert case.category_code == "test-category"
        assert case.severity_code == "test-severity"
        assert case.submitted_by == "test@example.com"
        assert case.time_created == "2023-01-01T00:00:00Z"
        assert len(case.recent_communications.communications) == 1
        assert case.cc_email_addresses == ["cc@example.com"]
        assert case.language == "en"

        # Test model_dump
        dumped = case.model_dump()
        assert dumped["caseId"] == "test-case-id"
        assert dumped["displayId"] == "test-display-id"
        assert dumped["subject"] == "Test subject"
        assert dumped["status"] == "opened"
        assert dumped["serviceCode"] == "test-service"
        assert dumped["categoryCode"] == "test-category"
        assert dumped["severityCode"] == "test-severity"
        assert dumped["submittedBy"] == "test@example.com"
        assert dumped["timeCreated"] == "2023-01-01T00:00:00Z"
        assert len(dumped["recentCommunications"]["communications"]) == 1
        assert dumped["ccEmailAddresses"] == ["cc@example.com"]
        assert dumped["language"] == "en"

        # Test invalid data
        with pytest.raises(ValidationError):
            SupportCase()  # Missing required fields

        # Test invalid status
        with pytest.raises(ValidationError):
            SupportCase(**{**VALID_SUPPORT_CASE, "status": "invalid"})


class TestRequestModels:
    """Tests for request models."""

    def test_create_case_request(self):
        """Test CreateCaseRequest model."""
        # Test valid data
        data = {
            "subject": "Test subject",
            "serviceCode": "test-service",
            "categoryCode": "test-category",
            "severityCode": "test-severity",
            "communicationBody": "Test body",
            "ccEmailAddresses": ["test@example.com"],
            "language": "en",
            "issueType": "technical",
            "attachmentSetId": "test-attachment-set",
        }
        request = CreateCaseRequest(**data)

        # Test to_api_params
        params = request.to_api_params()
        assert params["subject"] == "Test subject"
        assert params["service_code"] == "test-service"
        assert params["category_code"] == "test-category"
        assert params["severity_code"] == "test-severity"
        assert params["communication_body"] == "Test body"
        assert params["cc_email_addresses"] == ["test@example.com"]
        assert params["language"] == "en"
        assert params["issue_type"] == "technical"
        assert params["attachment_set_id"] == "test-attachment-set"

        # Test invalid data
        with pytest.raises(ValidationError):
            CreateCaseRequest()  # Missing required fields

        # Test communication body length validation
        with pytest.raises(ValidationError):
            CreateCaseRequest(**{**data, "communicationBody": ""})

        with pytest.raises(ValidationError):
            CreateCaseRequest(**{**data, "communicationBody": "x" * 8001})

        # Test cc_email_addresses max items
        with pytest.raises(ValidationError):
            CreateCaseRequest(**{**data, "ccEmailAddresses": ["test@example.com"] * 11})

    def test_describe_cases_request(self):
        """Test DescribeCasesRequest model."""
        # Test valid data
        data = {
            "caseIdList": ["case-1", "case-2"],
            "displayId": "display-1",
            "afterTime": "2023-01-01T00:00:00Z",
            "beforeTime": "2023-01-31T23:59:59Z",
            "includeResolvedCases": True,
            "includeCommunications": True,
            "language": "en",
            "maxResults": 50,
            "nextToken": "test-token",
        }
        request = DescribeCasesRequest(**data)

        # Test to_api_params
        params = request.to_api_params()
        assert params["case_id_list"] == ["case-1", "case-2"]
        assert params["display_id"] == "display-1"
        assert params["after_time"] == "2023-01-01T00:00:00Z"
        assert params["before_time"] == "2023-01-31T23:59:59Z"
        assert params["include_resolved_cases"] is True
        assert params["include_communications"] is True
        assert params["language"] == "en"
        assert params["max_results"] == 50
        assert params["next_token"] == "test-token"

        # Test defaults
        default_request = DescribeCasesRequest()
        assert default_request.include_resolved_cases is False
        assert default_request.include_communications is True
        assert default_request.language == "en"

        # Test validation
        with pytest.raises(ValidationError):
            DescribeCasesRequest(maxResults=5)  # Below minimum

        with pytest.raises(ValidationError):
            DescribeCasesRequest(maxResults=101)  # Above maximum

        with pytest.raises(ValidationError):
            DescribeCasesRequest(caseIdList=["case"] * 101)  # Too many cases

    def test_add_communication_request(self):
        """Test AddCommunicationRequest model."""
        # Test valid data
        data = {
            "caseId": "test-case",
            "communicationBody": "Test communication",
            "ccEmailAddresses": ["test@example.com"],
            "attachmentSetId": "test-attachment-set",
        }
        request = AddCommunicationRequest(**data)

        # Test to_api_params
        params = request.to_api_params()
        assert params["case_id"] == "test-case"
        assert params["communication_body"] == "Test communication"
        assert params["cc_email_addresses"] == ["test@example.com"]
        assert params["attachment_set_id"] == "test-attachment-set"

        # Test invalid data
        with pytest.raises(ValidationError):
            AddCommunicationRequest()  # Missing required fields

        # Test communication body length validation
        with pytest.raises(ValidationError):
            AddCommunicationRequest(**{**data, "communicationBody": ""})

        with pytest.raises(ValidationError):
            AddCommunicationRequest(**{**data, "communicationBody": "x" * 8001})

        # Test cc_email_addresses max items
        with pytest.raises(ValidationError):
            AddCommunicationRequest(**{**data, "ccEmailAddresses": ["test@example.com"] * 11})

    def test_resolve_case_request(self):
        """Test ResolveCaseRequest model."""
        # Test valid data
        data = {"caseId": "test-case"}
        request = ResolveCaseRequest(**data)

        # Test to_api_params
        params = request.to_api_params()
        assert params["case_id"] == "test-case"

        # Test invalid data
        with pytest.raises(ValidationError):
            ResolveCaseRequest()  # Missing required fields


class TestResponseModels:
    """Tests for response models."""

    def test_create_case_response(self):
        """Test CreateCaseResponse model."""
        # Test valid data
        data = {
            "caseId": "test-case",
            "status": "success",
            "message": "Case created successfully",
            "detected_language": "en",
        }
        response = CreateCaseResponse(**data)
        assert response.case_id == "test-case"
        assert response.status == "success"
        assert response.message == "Case created successfully"
        assert response.detected_language == "en"

        # Test invalid data
        with pytest.raises(ValidationError):
            CreateCaseResponse()  # Missing required fields

    def test_describe_cases_response(self):
        """Test DescribeCasesResponse model."""
        # Test valid data
        data = {"cases": [VALID_SUPPORT_CASE], "nextToken": "test-token"}
        response = DescribeCasesResponse(**data)
        assert len(response.cases) == 1
        assert response.next_token == "test-token"

        # Test invalid data
        with pytest.raises(ValidationError):
            DescribeCasesResponse()  # Missing required fields

    def test_add_communication_response(self):
        """Test AddCommunicationResponse model."""
        # Test valid data
        data = {"result": True, "status": "success", "message": "Communication added successfully"}
        response = AddCommunicationResponse(**data)
        assert response.result is True
        assert response.status == "success"
        assert response.message == "Communication added successfully"

        # Test invalid data
        with pytest.raises(ValidationError):
            AddCommunicationResponse()  # Missing required fields

    def test_resolve_case_response(self):
        """Test ResolveCaseResponse model."""
        # Test valid data
        data = {
            "initial_case_status": CaseStatus.OPENED.value,
            "final_case_status": CaseStatus.RESOLVED.value,
            "status": "success",
            "message": "Case resolved successfully",
        }
        response = ResolveCaseResponse(**data)
        assert response.initial_case_status == "opened"
        assert response.final_case_status == "resolved"
        assert response.status == "success"
        assert response.message == "Case resolved successfully"

        # Test invalid data
        with pytest.raises(ValidationError):
            ResolveCaseResponse()  # Missing required fields


class TestEnums:
    """Tests for enum types."""

    def test_issue_type(self):
        """Test IssueType enum."""
        assert IssueType.TECHNICAL.value == "technical"
        assert IssueType.ACCOUNT_AND_BILLING.value == "account-and-billing"
        assert IssueType.SERVICE_LIMIT.value == "service-limit"

        # Test invalid value
        with pytest.raises(ValueError):
            IssueType("invalid")

    def test_case_status(self):
        """Test CaseStatus enum."""
        assert CaseStatus.OPENED.value == "opened"
        assert CaseStatus.PENDING_CUSTOMER_ACTION.value == "pending-customer-action"
        assert CaseStatus.RESOLVED.value == "resolved"
        assert CaseStatus.UNASSIGNED.value == "unassigned"
        assert CaseStatus.WORK_IN_PROGRESS.value == "work-in-progress"
        assert CaseStatus.CLOSED.value == "closed"

        # Test invalid value
        with pytest.raises(ValueError):
            CaseStatus("invalid")


class TestAttachmentModels:
    """Tests for attachment-related models."""

    def test_attachment_data(self):
        """Test AttachmentData model."""
        # Test valid data
        data = {"data": "base64_encoded_content", "fileName": "test.txt"}
        attachment = AttachmentData(**data)
        assert attachment.data == "base64_encoded_content"
        assert attachment.file_name == "test.txt"

        # Test model_dump
        dumped = attachment.model_dump()
        assert dumped["data"] == "base64_encoded_content"
        assert dumped["fileName"] == "test.txt"

        # Test invalid data
        with pytest.raises(ValidationError):
            AttachmentData()  # Missing required fields

    def test_add_attachments_to_set_request(self):
        """Test AddAttachmentsToSetRequest model."""
        # Test valid data
        data = {
            "attachments": [{"data": "base64_encoded_content", "fileName": "test.txt"}],
            "attachmentSetId": "test-set",
        }
        request = AddAttachmentsToSetRequest(**data)
        assert len(request.attachments) == 1
        assert request.attachment_set_id == "test-set"

        # Test to_api_params
        params = request.to_api_params()
        assert len(params["attachments"]) == 1
        assert params["attachment_set_id"] == "test-set"

        # Test invalid data
        with pytest.raises(ValidationError):
            AddAttachmentsToSetRequest()  # Missing required fields

        with pytest.raises(ValidationError):
            AddAttachmentsToSetRequest(attachments=[])  # Empty attachments list

    def test_add_attachments_to_set_response(self):
        """Test AddAttachmentsToSetResponse model."""
        # Test valid data
        data = {
            "attachmentSetId": "test-set",
            "expiryTime": "2023-01-01T00:00:00Z",
            "status": "success",
            "message": "Attachments added successfully",
        }
        response = AddAttachmentsToSetResponse(**data)
        assert response.attachment_set_id == "test-set"
        assert response.expiry_time == "2023-01-01T00:00:00Z"
        assert response.status == "success"
        assert response.message == "Attachments added successfully"

        # Test invalid data
        with pytest.raises(ValidationError):
            AddAttachmentsToSetResponse()  # Missing required fields


class TestLanguageModels:
    """Tests for language-related models."""

    def test_supported_language(self):
        """Test SupportedLanguage model."""
        # Test valid data
        data = {"code": "en", "name": "English", "native_name": "English"}
        language = SupportedLanguage(**data)
        assert language.code == "en"
        assert language.name == "English"
        assert language.native_name == "English"

        # Test without native name
        language = SupportedLanguage(code="en", name="English")
        assert language.native_name is None

        # Test invalid data
        with pytest.raises(ValidationError):
            SupportedLanguage()  # Missing required fields

    def test_describe_supported_languages_request(self):
        """Test DescribeSupportedLanguagesRequest model."""
        request = DescribeSupportedLanguagesRequest()
        assert request.to_api_params() == {}

    def test_describe_supported_languages_response(self):
        """Test DescribeSupportedLanguagesResponse model."""
        # Test valid data
        data = {
            "languages": ["en", "es", "fr"],
            "status": "success",
            "message": "Languages retrieved successfully",
        }
        response = DescribeSupportedLanguagesResponse(**data)
        assert response.languages == ["en", "es", "fr"]
        assert response.status == "success"
        assert response.message == "Languages retrieved successfully"

        # Test invalid data
        with pytest.raises(ValidationError):
            DescribeSupportedLanguagesResponse()  # Missing required fields
