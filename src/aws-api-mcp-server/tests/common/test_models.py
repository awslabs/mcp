import pytest
from awslabs.aws_api_mcp_server.core.common.models import (
    AwsCliAliasResponse,
    CallAWSResponse,
    InterpretationResponse,
    ProgramInterpretationResponse,
)


def test_call_aws_response_with_response():
    """Test CallAWSResponse with response field."""
    response = ProgramInterpretationResponse(
        response=InterpretationResponse(error=None, json='{"test": "data"}', status_code=200)
    )

    call_response = CallAWSResponse(cli_command='aws s3 ls', response=response)

    assert call_response.cli_command == 'aws s3 ls'
    assert call_response.response == response
    assert call_response.error is None


def test_call_aws_response_with_error():
    """Test CallAWSResponse with error field."""
    call_response = CallAWSResponse(cli_command='aws s3 ls', error='Command failed')

    assert call_response.cli_command == 'aws s3 ls'
    assert call_response.response is None
    assert call_response.error == 'Command failed'


def test_call_aws_response_with_both():
    """Test CallAWSResponse with both response and error."""
    response = AwsCliAliasResponse(response='output', error='warning')
    call_response = CallAWSResponse(
        cli_command='aws s3 ls', response=response, error='Command failed'
    )

    assert call_response.cli_command == 'aws s3 ls'
    assert call_response.response == response
    assert call_response.error == 'Command failed'


def test_call_aws_response_validation_error():
    """Test CallAWSResponse validation fails when neither response nor error provided."""
    with pytest.raises(ValueError, match="Either 'response' or 'error' must be provided"):
        CallAWSResponse(cli_command='aws s3 ls')


def test_call_aws_response_serialization_with_response():
    """Test CallAWSResponse serialization with response."""
    response = ProgramInterpretationResponse(
        response=InterpretationResponse(error=None, json='{"test": "data"}', status_code=200)
    )
    call_response = CallAWSResponse(cli_command='aws s3 ls', response=response)

    serialized = call_response.model_dump()

    assert serialized['cli_command'] == 'aws s3 ls'
    assert 'response' in serialized
    assert serialized['response']['status_code'] == 200


def test_call_aws_response_serialization_with_error():
    """Test CallAWSResponse serialization with error."""
    call_response = CallAWSResponse(cli_command='aws s3 ls', error='Command failed')

    serialized = call_response.model_dump()

    assert serialized['cli_command'] == 'aws s3 ls'
    assert serialized['error'] == 'Command failed'
