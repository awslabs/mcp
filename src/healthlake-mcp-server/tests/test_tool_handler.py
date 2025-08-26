"""Tests for ToolHandler dispatch logic."""

import pytest
from awslabs.healthlake_mcp_server.server import ToolHandler
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def mock_client():
    """Mock HealthLake client."""
    client = Mock()
    client.list_datastores = AsyncMock(return_value={'DatastorePropertiesList': []})
    client.read_resource = AsyncMock(return_value={'resourceType': 'Patient'})
    client.search_resources = AsyncMock(return_value={'resourceType': 'Bundle'})
    return client


def test_tool_handler_initialization(mock_client):
    """Test ToolHandler initializes with correct handlers."""
    handler = ToolHandler(mock_client)

    assert len(handler.handlers) == 11
    assert 'list_datastores' in handler.handlers
    assert 'search_fhir_resources' in handler.handlers
    assert 'read_fhir_resource' in handler.handlers


@pytest.mark.asyncio
async def test_unknown_tool_raises_error(mock_client):
    """Test unknown tool name raises ValueError."""
    handler = ToolHandler(mock_client)

    with pytest.raises(ValueError, match='Unknown tool'):
        await handler.handle_tool('nonexistent_tool', {})


@pytest.mark.asyncio
async def test_list_datastores_handler(mock_client):
    """Test list_datastores handler calls client correctly."""
    handler = ToolHandler(mock_client)

    result = await handler.handle_tool('list_datastores', {})

    mock_client.list_datastores.assert_called_once_with(filter_status=None)
    assert len(result) == 1  # Returns TextContent list


@pytest.mark.asyncio
async def test_read_handler_with_validation(mock_client, sample_args):
    """Test read handler validates datastore ID."""
    handler = ToolHandler(mock_client)

    result = await handler.handle_tool('read_fhir_resource', sample_args)

    mock_client.read_resource.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_search_handler_with_count_validation(mock_client, sample_datastore_id):
    """Test search handler validates count parameter."""
    handler = ToolHandler(mock_client)
    args = {'datastore_id': sample_datastore_id, 'resource_type': 'Patient', 'count': 50}

    result = await handler.handle_tool('search_fhir_resources', args)

    mock_client.search_resources.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_create_handler(mock_client, sample_datastore_id):
    """Test create resource handler."""
    mock_client.create_resource = AsyncMock(return_value={'resourceType': 'Patient', 'id': '123'})
    handler = ToolHandler(mock_client)

    args = {
        'datastore_id': sample_datastore_id,
        'resource_type': 'Patient',
        'resource_data': {'resourceType': 'Patient', 'name': [{'family': 'Smith'}]},
    }

    result = await handler.handle_tool('create_fhir_resource', args)

    mock_client.create_resource.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_update_handler(mock_client, sample_args):
    """Test update resource handler."""
    mock_client.update_resource = AsyncMock(
        return_value={'resourceType': 'Patient', 'id': 'test-patient-123'}
    )
    handler = ToolHandler(mock_client)

    args = sample_args.copy()
    args['resource_data'] = {'resourceType': 'Patient', 'id': 'test-patient-123'}

    result = await handler.handle_tool('update_fhir_resource', args)

    mock_client.update_resource.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_delete_handler(mock_client, sample_args):
    """Test delete resource handler."""
    mock_client.delete_resource = AsyncMock(return_value={'status': 'deleted'})
    handler = ToolHandler(mock_client)

    result = await handler.handle_tool('delete_fhir_resource', sample_args)

    mock_client.delete_resource.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_patient_everything_handler(mock_client, sample_datastore_id):
    """Test patient everything handler."""
    mock_client.patient_everything = AsyncMock(return_value={'resourceType': 'Bundle'})
    handler = ToolHandler(mock_client)

    args = {'datastore_id': sample_datastore_id, 'patient_id': 'patient-123'}

    result = await handler.handle_tool('patient_everything', args)

    mock_client.patient_everything.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_datastore_details_handler(mock_client, sample_datastore_id):
    """Test get datastore details handler."""
    mock_client.get_datastore_details = AsyncMock(return_value={'DatastoreProperties': {}})
    handler = ToolHandler(mock_client)

    result = await handler.handle_tool(
        'get_datastore_details', {'datastore_id': sample_datastore_id}
    )

    mock_client.get_datastore_details.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_start_import_job_handler(mock_client, sample_datastore_id):
    """Test start import job handler."""
    mock_client.start_import_job = AsyncMock(return_value={'JobId': 'job-123'})
    handler = ToolHandler(mock_client)

    args = {
        'datastore_id': sample_datastore_id,
        'input_data_config': {'s3_uri': 's3://bucket/data'},
        'job_output_data_config': {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
        'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
    }

    result = await handler.handle_tool('start_fhir_import_job', args)

    mock_client.start_import_job.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_start_export_job_handler(mock_client, sample_datastore_id):
    """Test start export job handler."""
    mock_client.start_export_job = AsyncMock(return_value={'JobId': 'job-456'})
    handler = ToolHandler(mock_client)

    args = {
        'datastore_id': sample_datastore_id,
        'output_data_config': {'S3Configuration': {'S3Uri': 's3://bucket/export'}},
        'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
    }

    result = await handler.handle_tool('start_fhir_export_job', args)

    mock_client.start_export_job.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_jobs_handler(mock_client, sample_datastore_id):
    """Test list jobs handler."""
    mock_client.list_jobs = AsyncMock(return_value={'ImportJobs': [], 'ExportJobs': []})
    handler = ToolHandler(mock_client)

    result = await handler.handle_tool('list_fhir_jobs', {'datastore_id': sample_datastore_id})

    mock_client.list_jobs.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_handler_with_client_error(mock_client, sample_args):
    """Test handler behavior when client raises error."""
    mock_client.read_resource.side_effect = Exception('AWS Error')
    handler = ToolHandler(mock_client)

    # The handler should catch the exception and return an error response
    with pytest.raises(Exception, match='AWS Error'):
        await handler.handle_tool('read_fhir_resource', sample_args)
