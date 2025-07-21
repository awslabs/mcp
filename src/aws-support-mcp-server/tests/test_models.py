"""Tests for the AWS Support MCP Server data models."""

import pytest
from awslabs.aws_support_mcp_server.consts import (
    CaseStatus,
    IssueType,
)
from awslabs.aws_support_mcp_server.models import (
    AddAttachmentsToSetRequest,
    AddAttachmentsToSetResponse,
    AddCommunicationRequest,
    AddCommunicationResponse,
    AttachmentData,
    AttachmentDetails,
    Category,
    Communication,
    CreateCaseRequest,
    CreateCaseResponse,
    DescribeCasesRequest,
    DescribeCasesResponse,
    DescribeSupportedLanguagesRequest,
    DescribeSupportedLanguagesResponse,
    RecentCommunications,
    ResolveCaseRequest,
    ResolveCaseResponse,
    Service,
    SeverityLevel,
    SupportCase,
    SupportedLanguage,
)
from pydantic import ValidationError


# Test Data
VALID_ATTACHMENT_DETAILS = {'attachmentId': 'test-attachment-id', 'fileName': 'test.txt'}

VALID_COMMUNICATION = {
    'body': 'Test communication body',
    'caseId': 'test-case-id',
    'submittedBy': 'test@example.com',
    'timeCreated': '2023-01-01T00:00:00Z',
    'attachmentSet': [VALID_ATTACHMENT_DETAILS],
}

VALID_RECENT_COMMUNICATIONS = {'communications': [VALID_COMMUNICATION], 'nextToken': 'test-token'}

VALID_CATEGORY = {'code': 'test-category', 'name': 'Test Category'}

VALID_SERVICE = {'code': 'test-service', 'name': 'Test Service', 'categories': [VALID_CATEGORY]}

VALID_SEVERITY_LEVEL = {'code': 'test-severity', 'name': 'Test Severity'}

VALID_SUPPORT_CASE = {
    'caseId': 'test-case-id',
    'displayId': 'test-display-id',
    'subject': 'Test subject',
    'status': 'opened',
    'serviceCode': 'test-service',
    'categoryCode': 'test-category',
    'severityCode': 'test-severity',
    'submittedBy': 'test@example.com',
    'timeCreated': '2023-01-01T00:00:00Z',
    'recentCommunications': VALID_RECENT_COMMUNICATIONS,
    'ccEmailAddresses': ['cc@example.com'],
    'language': 'en',
}


class TestBaseModels:
    """Tests for base data models."""

    def test_attachment_details(self):
        """Test AttachmentDetails model."""
        # Test valid data
        attachment = AttachmentDetails(**VALID_ATTACHMENT_DETAILS)
        assert attachment.attachment_id == 'test-attachment-id'
        assert attachment.file_name == 'test.txt'

        # Test model_dump
        dumped = attachment.model_dump()
        assert dumped['attachmentId'] == 'test-attachment-id'
        assert dumped['fileName'] == 'test.txt'

        # Test missing required fields
        with pytest.raises(ValidationError):
            AttachmentDetails(attachmentId='test-id', fileName='')  # Empty fileName should fail

    def test_communication(self):
        """Test Communication model."""
        # Test valid data
        comm = Communication(**VALID_COMMUNICATION)
        assert comm.body == 'Test communication body'
        assert comm.case_id == 'test-case-id'
        assert comm.submitted_by == 'test@example.com'
        assert comm.time_created == '2023-01-01T00:00:00Z'
        assert comm.attachment_set is not None
        assert len(comm.attachment_set) == 1

        # Test model_dump
        dumped = comm.model_dump()
        assert dumped['body'] == 'Test communication body'
        assert dumped['caseId'] == 'test-case-id'
        assert dumped['submittedBy'] == 'test@example.com'
        assert dumped['timeCreated'] == '2023-01-01T00:00:00Z'
        assert isinstance(dumped['attachmentSet'], list)
        assert len(dumped['attachmentSet']) == 1

        # Test valid communication with minimal required fields
        valid_comm = Communication(
            body='Test body',
            caseId='test-case-id',
            submittedBy='test@example.com',
            timeCreated='2023-01-01T00:00:00Z',
            attachmentSet=[],
        )
        assert valid_comm.body == 'Test body'

        # Test body validation - empty body should fail
        with pytest.raises(ValidationError):
            Communication(
                body='',  # Empty body should fail validation
                caseId='test-case-id',
                submittedBy='test@example.com',
                timeCreated='2023-01-01T00:00:00Z',
                attachmentSet=[],
            )

        # Test body length validation - body too long should fail
        with pytest.raises(ValidationError):
            Communication(
                body='x' * 8001,  # Body too long
                caseId='test-case-id',
                submittedBy='test@example.com',
                timeCreated='2023-01-01T00:00:00Z',
                attachmentSet=[],
            )

    def test_recent_communications(self):
        """Test RecentCommunications model."""
        # Test valid data
        recent = RecentCommunications(**VALID_RECENT_COMMUNICATIONS)
        assert len(recent.communications) == 1
        assert recent.next_token == 'test-token'

        # Test model_dump
        dumped = recent.model_dump()
        assert isinstance(dumped['communications'], list)
        assert len(dumped['communications']) == 1
        assert dumped['nextToken'] == 'test-token'

        # Test empty communications
        empty = RecentCommunications(communications=[], nextToken=None)
        assert len(empty.communications) == 0
        assert empty.next_token is None

    def test_category(self):
        """Test Category model."""
        # Test valid data
        category = Category(**VALID_CATEGORY)
        assert category.code == 'test-category'
        assert category.name == 'Test Category'

        # Test model_dump
        dumped = category.model_dump()
        assert dumped['code'] == 'test-category'
        assert dumped['name'] == 'Test Category'

        # Test missing required fields
        with pytest.raises(ValidationError):
            Category(code='test-code', name='')  # Empty name should fail

    def test_service(self):
        """Test Service model."""
        # Test valid data
        service = Service(**VALID_SERVICE)
        assert service.code == 'test-service'
        assert service.name == 'Test Service'
        assert len(service.categories) == 1

        # Test model_dump
        dumped = service.model_dump()
        assert dumped['code'] == 'test-service'
        assert dumped['name'] == 'Test Service'
        assert isinstance(dumped['categories'], list)
        assert len(dumped['categories']) == 1

        # Test missing required fields
        with pytest.raises(ValidationError):
            Service(code='test-code', name='')  # Empty name should fail

        # Test empty categories
        service = Service(code='test', name='Test', categories=[])
        assert len(service.categories) == 0

    def test_severity_level(self):
        """Test SeverityLevel model."""
        # Test valid data
        severity = SeverityLevel(**VALID_SEVERITY_LEVEL)
        assert severity.code == 'test-severity'
        assert severity.name == 'Test Severity'

        # Test model_dump
        dumped = severity.model_dump()
        assert dumped['code'] == 'test-severity'
        assert dumped['name'] == 'Test Severity'

        # Test missing required fields
        with pytest.raises(ValidationError):
            SeverityLevel(code='test-code', name='')  # Empty name should fail

    def test_support_case(self):
        """Test SupportCase model."""
        # Test valid data
        case = SupportCase(**VALID_SUPPORT_CASE)
        assert case.case_id == 'test-case-id'
        assert case.display_id == 'test-display-id'
        assert case.subject == 'Test subject'
        assert case.status == CaseStatus.OPENED
        assert case.service_code == 'test-service'
        assert case.category_code == 'test-category'
        assert case.severity_code == 'test-severity'
        assert case.submitted_by == 'test@example.com'
        assert case.time_created == '2023-01-01T00:00:00Z'
        assert case.recent_communications is not None
        assert len(case.recent_communications.communications) == 1
        assert case.cc_email_addresses == ['cc@example.com']
        assert case.language == 'en'

        # Test model_dump
        dumped = case.model_dump()
        assert dumped['caseId'] == 'test-case-id'
        assert dumped['displayId'] == 'test-display-id'
        assert dumped['subject'] == 'Test subject'
        assert dumped['status'] == 'opened'
        assert dumped['serviceCode'] == 'test-service'
        assert dumped['categoryCode'] == 'test-category'
        assert dumped['severityCode'] == 'test-severity'
        assert dumped['submittedBy'] == 'test@example.com'
        assert dumped['timeCreated'] == '2023-01-01T00:00:00Z'
        assert isinstance(dumped['recentCommunications'], dict)
        assert 'communications' in dumped['recentCommunications']
        assert len(dumped['recentCommunications']['communications']) == 1
        assert dumped['ccEmailAddresses'] == ['cc@example.com']
        assert dumped['language'] == 'en'

        # Test invalid status
        with pytest.raises(ValidationError):
            SupportCase(**{**VALID_SUPPORT_CASE, 'status': 'invalid'})


class TestRequestModels:
    """Tests for request models."""

    def test_create_case_request(self):
        """Test CreateCaseRequest model."""
        # Test valid data
        data = {
            'subject': 'Test subject',
            'serviceCode': 'test-service',
            'categoryCode': 'test-category',
            'severityCode': 'test-severity',
            'communicationBody': 'Test body',
            'ccEmailAddresses': ['test@example.com'],
            'language': 'en',
            'issueType': 'technical',
            'attachmentSetId': 'test-attachment-set',
        }
        request = CreateCaseRequest(**data)

        # Test to_api_params
        params = request.to_api_params()
        assert params['subject'] == 'Test subject'
        assert params['serviceCode'] == 'test-service'
        assert params['categoryCode'] == 'test-category'
        assert params['severityCode'] == 'test-severity'
        assert params['communicationBody'] == 'Test body'
        assert params['ccEmailAddresses'] == ['test@example.com']
        assert params['language'] == 'en'
        assert params['issueType'] == 'technical'
        assert params['attachmentSetId'] == 'test-attachment-set'

        # Test valid case first
        valid_request = CreateCaseRequest(
            subject='Test subject',
            serviceCode='test-service',
            categoryCode='test-category',
            severityCode='test-severity',
            communicationBody='Test body',
            ccEmailAddresses=['test@example.com'],
            language='en',
            issueType='technical',
            attachmentSetId='test-attachment-set',
        )
        assert valid_request.subject == 'Test subject'

        # Test communication body validation - empty body should fail
        with pytest.raises(ValidationError):
            CreateCaseRequest(**{**data, 'communicationBody': ''})

        # Test communication body length validation - body too long should fail
        with pytest.raises(ValidationError):
            CreateCaseRequest(**{**data, 'communicationBody': 'x' * 8001})

        # Test cc_email_addresses max items - too many emails should fail
        with pytest.raises(ValidationError):
            CreateCaseRequest(**{**data, 'ccEmailAddresses': ['test@example.com'] * 11})

    def test_describe_cases_request(self):
        """Test DescribeCasesRequest model."""
        # Test valid data
        data = {
            'caseIdList': ['case-1', 'case-2'],
            'displayId': 'display-1',
            'afterTime': '2023-01-01T00:00:00Z',
            'beforeTime': '2023-01-31T23:59:59Z',
            'includeResolvedCases': True,
            'includeCommunications': True,
            'language': 'en',
            'maxResults': 50,
            'nextToken': 'test-token',
        }
        request = DescribeCasesRequest(**data)

        # Test to_api_params
        params = request.to_api_params()
        assert params['caseIdList'] == ['case-1', 'case-2']
        assert params['displayId'] == 'display-1'
        assert params['afterTime'] == '2023-01-01T00:00:00Z'
        assert params['beforeTime'] == '2023-01-31T23:59:59Z'
        assert params['includeResolvedCases'] is True
        assert params['includeCommunications'] is True
        assert params['language'] == 'en'
        assert params['maxResults'] == 50
        assert params['nextToken'] == 'test-token'

        # Test defaults
        default_request = DescribeCasesRequest(
            caseIdList=None,
            displayId=None,
            afterTime=None,
            beforeTime=None,
            includeResolvedCases=False,
            includeCommunications=True,
            language='en',
            maxResults=100,
            nextToken=None,
        )
        assert default_request.include_resolved_cases is False
        assert default_request.include_communications is True
        assert default_request.language == 'en'

        # Test validation
        with pytest.raises(ValidationError):
            DescribeCasesRequest(
                caseIdList=None,
                displayId=None,
                afterTime=None,
                beforeTime=None,
                includeResolvedCases=False,
                includeCommunications=True,
                language='en',
                maxResults=5,  # Below minimum
                nextToken=None,
            )

        with pytest.raises(ValidationError):
            DescribeCasesRequest(
                caseIdList=None,
                displayId=None,
                afterTime=None,
                beforeTime=None,
                includeResolvedCases=False,
                includeCommunications=True,
                language='en',
                maxResults=101,  # Above maximum
                nextToken=None,
            )

        with pytest.raises(ValidationError):
            DescribeCasesRequest(
                caseIdList=['case'] * 101,  # Too many cases
                displayId=None,
                afterTime=None,
                beforeTime=None,
                includeResolvedCases=False,
                includeCommunications=True,
                language='en',
                maxResults=100,
                nextToken=None,
            )

    def test_add_communication_request(self):
        """Test AddCommunicationRequest model."""
        # Test valid data
        data = {
            'caseId': 'test-case',
            'communicationBody': 'Test communication',
            'ccEmailAddresses': ['test@example.com'],
            'attachmentSetId': 'test-attachment-set',
        }
        request = AddCommunicationRequest(**data)

        # Test to_api_params
        params = request.to_api_params()
        assert params['caseId'] == 'test-case'
        assert params['communicationBody'] == 'Test communication'
        assert params['ccEmailAddresses'] == ['test@example.com']
        assert params['attachmentSetId'] == 'test-attachment-set'

        # Test valid case first
        valid_request = AddCommunicationRequest(
            caseId='test-case',
            communicationBody='Test communication',
            ccEmailAddresses=['test@example.com'],
            attachmentSetId='test-attachment-set',
        )
        assert valid_request.case_id == 'test-case'

        # Test communication body validation - empty body should fail
        with pytest.raises(ValidationError):
            AddCommunicationRequest(**{**data, 'communicationBody': ''})

        # Test communication body length validation - body too long should fail
        with pytest.raises(ValidationError):
            AddCommunicationRequest(**{**data, 'communicationBody': 'x' * 8001})

        # Test cc_email_addresses max items - too many emails should fail
        with pytest.raises(ValidationError):
            AddCommunicationRequest(**{**data, 'ccEmailAddresses': ['test@example.com'] * 11})

    def test_resolve_case_request(self):
        """Test ResolveCaseRequest model."""
        # Test valid data
        data = {'caseId': 'test-case'}
        request = ResolveCaseRequest(**data)

        # Test to_api_params
        params = request.to_api_params()
        assert params['caseId'] == 'test-case'

        # Test with missing required fields
        valid_request = ResolveCaseRequest(caseId='test-case')  # This should pass
        assert valid_request.case_id == 'test-case'

        # Test missing required fields
        with pytest.raises(ValidationError):
            ResolveCaseRequest(caseId='')  # Empty caseId should fail


class TestResponseModels:
    """Tests for response models."""

    def test_create_case_response(self):
        """Test CreateCaseResponse model."""
        # Test valid data
        data = {'caseId': 'test-case', 'status': 'success', 'message': 'Case created successfully'}
        response = CreateCaseResponse(**data)
        assert response.case_id == 'test-case'
        assert response.status == 'success'
        assert response.message == 'Case created successfully'

        # Test with missing required fields
        valid_response = CreateCaseResponse(
            caseId='test-case', status='success', message='Case created successfully'
        )  # This should pass
        assert valid_response.case_id == 'test-case'

        # Test missing required fields
        with pytest.raises(ValidationError):
            CreateCaseResponse(
                caseId='test-case', status='success', message=''
            )  # Empty message should fail

    def test_describe_cases_response(self):
        """Test DescribeCasesResponse model."""
        # Test valid data
        data = {'cases': [SupportCase(**VALID_SUPPORT_CASE)], 'nextToken': 'test-token'}
        response = DescribeCasesResponse(**data)
        assert len(response.cases) == 1
        assert response.next_token == 'test-token'

        # Test with missing required fields
        valid_response = DescribeCasesResponse(
            cases=[SupportCase(**VALID_SUPPORT_CASE)], nextToken='test-token'
        )  # This should pass
        assert len(valid_response.cases) == 1

        # Test missing required fields - empty nextToken should fail
        with pytest.raises(ValidationError):
            DescribeCasesResponse(
                cases=[], nextToken=''
            )  # Empty nextToken should fail if validation exists

    def test_add_communication_response(self):
        """Test AddCommunicationResponse model."""
        # Test valid data
        data = {'result': True, 'status': 'success', 'message': 'Communication added successfully'}
        response = AddCommunicationResponse(**data)
        assert response.result is True
        assert response.status == 'success'
        assert response.message == 'Communication added successfully'

        # Test with missing required fields
        valid_response = AddCommunicationResponse(
            result=True, status='success', message='Communication added successfully'
        )  # This should pass
        assert valid_response.result is True

        # Test missing required fields
        with pytest.raises(ValidationError):
            AddCommunicationResponse(
                result=True, status='success', message=''
            )  # Empty message should fail

    def test_resolve_case_response(self):
        """Test ResolveCaseResponse model."""
        # Test valid data
        data = {
            'initialCaseStatus': CaseStatus.OPENED.value,
            'finalCaseStatus': CaseStatus.RESOLVED.value,
            'status': 'success',
            'message': 'Case resolved successfully',
        }
        response = ResolveCaseResponse(**data)
        assert response.initial_case_status == 'opened'
        assert response.final_case_status == 'resolved'
        assert response.status == 'success'
        assert response.message == 'Case resolved successfully'

        # Test with missing required fields
        valid_response = ResolveCaseResponse(
            initialCaseStatus='opened',
            finalCaseStatus='resolved',
            status='success',
            message='Case resolved successfully',
        )  # This should pass
        assert valid_response.initial_case_status == 'opened'

        # Test missing required fields
        with pytest.raises(ValidationError):
            ResolveCaseResponse(
                initialCaseStatus='opened',
                finalCaseStatus='resolved',
                status='success',
                message='',  # Empty message should fail
            )


class TestEnums:
    """Tests for enum types."""

    def test_issue_type(self):
        """Test IssueType enum."""
        assert IssueType.TECHNICAL.value == 'technical'
        assert IssueType.ACCOUNT_AND_BILLING.value == 'account-and-billing'
        assert IssueType.SERVICE_LIMIT.value == 'service-limit'

        # Test invalid value
        with pytest.raises(ValueError):
            IssueType('invalid')

    def test_case_status(self):
        """Test CaseStatus enum."""
        assert CaseStatus.OPENED.value == 'opened'
        assert CaseStatus.PENDING_CUSTOMER_ACTION.value == 'pending-customer-action'
        assert CaseStatus.RESOLVED.value == 'resolved'
        assert CaseStatus.UNASSIGNED.value == 'unassigned'
        assert CaseStatus.WORK_IN_PROGRESS.value == 'work-in-progress'
        assert CaseStatus.CLOSED.value == 'closed'
        assert CaseStatus.REOPENED.value == 'reopened'

        # Test invalid value
        with pytest.raises(ValueError):
            CaseStatus('invalid')


class TestAttachmentModels:
    """Tests for attachment-related models."""

    def test_attachment_data(self):
        """Test AttachmentData model."""
        # Test valid data
        data = {'data': 'base64_encoded_content', 'fileName': 'test.txt'}
        attachment = AttachmentData(**data)
        assert attachment.data == 'base64_encoded_content'
        assert attachment.file_name == 'test.txt'

        # Test model_dump
        dumped = attachment.model_dump()
        assert dumped['data'] == 'base64_encoded_content'
        assert dumped['fileName'] == 'test.txt'

        # Test with missing required fields
        valid_attachment = AttachmentData(
            data='base64_encoded_content', fileName='test.txt'
        )  # This should pass
        assert valid_attachment.data == 'base64_encoded_content'

        # Test missing required fields
        with pytest.raises(ValidationError):
            AttachmentData(
                data='base64_encoded_content', fileName=''
            )  # Empty fileName should fail

    def test_add_attachments_to_set_request(self):
        """Test AddAttachmentsToSetRequest model."""
        # Test valid data
        data = {
            'attachments': [AttachmentData(data='base64_encoded_content', fileName='test.txt')],
            'attachmentSetId': 'test-set',
        }
        request = AddAttachmentsToSetRequest(**data)
        assert len(request.attachments) == 1
        assert request.attachment_set_id == 'test-set'

        # Test to_api_params
        params = request.to_api_params()
        assert isinstance(params['attachments'], list)
        assert len(params['attachments']) == 1
        assert params['attachmentSetId'] == 'test-set'

        # Test with missing required fields
        valid_request = AddAttachmentsToSetRequest(
            attachments=[AttachmentData(data='base64_encoded_content', fileName='test.txt')],
            attachmentSetId='test-set',
        )  # This should pass
        assert len(valid_request.attachments) == 1

        # Test empty attachments list should fail (min_length=1)
        with pytest.raises(ValidationError):
            AddAttachmentsToSetRequest(
                attachments=[],  # Empty attachments list should fail
                attachmentSetId='test-set',
            )

    def test_add_attachments_to_set_response(self):
        """Test AddAttachmentsToSetResponse model."""
        # Test valid data
        data = {
            'attachmentSetId': 'test-set',
            'expiryTime': '2023-01-01T00:00:00Z',
            'status': 'success',
            'message': 'Attachments added successfully',
        }
        response = AddAttachmentsToSetResponse(**data)
        assert response.attachment_set_id == 'test-set'
        assert response.expiry_time == '2023-01-01T00:00:00Z'
        assert response.status == 'success'
        assert response.message == 'Attachments added successfully'

        # Test with missing required fields
        valid_response = AddAttachmentsToSetResponse(
            attachmentSetId='test-set',
            expiryTime='2023-01-01T00:00:00Z',
            status='success',
            message='Attachments added successfully',
        )  # This should pass
        assert valid_response.attachment_set_id == 'test-set'

        # Test missing required fields
        with pytest.raises(ValidationError):
            AddAttachmentsToSetResponse(
                attachmentSetId='test-set',
                expiryTime='2023-01-01T00:00:00Z',
                status='success',
                message='',  # Empty message should fail
            )


class TestLanguageModels:
    """Tests for language-related models."""

    def test_supported_language(self):
        """Test SupportedLanguage model."""
        # Test valid data
        data = {'code': 'en', 'name': 'English', 'native_name': 'English'}
        language = SupportedLanguage(**data)
        assert language.code == 'en'
        assert language.name == 'English'
        assert language.native_name == 'English'

        # Test without native name
        language = SupportedLanguage(code='en', name='English', native_name='English')
        assert language.native_name == 'English'

        # Test with missing required fields
        valid_language = SupportedLanguage(
            code='en', name='English', native_name='English'
        )  # This should pass
        assert valid_language.code == 'en'

        # Test missing required fields
        with pytest.raises(ValidationError):
            SupportedLanguage(
                code='en', name='English', native_name=''
            )  # Empty native_name should fail

    def test_describe_supported_languages_request(self):
        """Test DescribeSupportedLanguagesRequest model."""
        request = DescribeSupportedLanguagesRequest()
        assert request.to_api_params() == {}

    def test_describe_supported_languages_response(self):
        """Test DescribeSupportedLanguagesResponse model."""
        # Test valid data
        data = {
            'languages': ['en', 'es', 'fr'],
            'status': 'success',
            'message': 'Languages retrieved successfully',
        }
        response = DescribeSupportedLanguagesResponse(**data)
        assert response.languages == ['en', 'es', 'fr']
        assert response.status == 'success'
        assert response.message == 'Languages retrieved successfully'

        # Test with missing required fields
        valid_response = DescribeSupportedLanguagesResponse(
            languages=['en', 'es', 'fr'],
            status='success',
            message='Languages retrieved successfully',
        )  # This should pass
        assert valid_response.languages == ['en', 'es', 'fr']

        # Test missing required fields
        with pytest.raises(ValidationError):
            DescribeSupportedLanguagesResponse(
                languages=['en', 'es', 'fr'],
                status='success',
                message='',  # Empty message should fail
            )
