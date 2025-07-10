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

import os
import pytest
from awslabs.healthlake_mcp_server.server import (
    create_datastore,
    create_fhir_bundle,
    create_fhir_resource,
    create_observation_template,
    create_patient_template,
    get_datastore_capabilities,
    get_fhir_resource_history,
    list_datastores,
    read_fhir_resource,
    search_fhir_resources_advanced,
    validate_fhir_resource,
)
from moto import mock_aws
from unittest.mock import MagicMock, patch


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'


class TestHealthLakeServer:
    """Test class for HealthLake MCP server functionality."""

    @mock_aws
    def test_create_datastore(self, aws_credentials):
        """Test creating a datastore."""
        with patch('boto3.client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.create_fhir_datastore.return_value = {
                'DatastoreId': 'test-datastore-id',
                'DatastoreArn': 'arn:aws:healthlake:us-west-2:123456789012:datastore/fhir/test-datastore-id',
            }

            result = create_datastore(datastore_type_version='R4', datastore_name='test-datastore')

            assert result['DatastoreId'] == 'test-datastore-id'
            mock_client_instance.create_fhir_datastore.assert_called_once()

    def test_read_fhir_resource(self, aws_credentials):
        """Test reading a FHIR resource."""
        with (
            patch('boto3.client') as mock_client,
            patch('awslabs.healthlake_mcp_server.server._make_fhir_request') as mock_fhir_request,
        ):
            # Mock the describe_fhir_datastore call
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.describe_fhir_datastore.return_value = {
                'DatastoreProperties': {
                    'DatastoreEndpoint': 'https://healthlake.us-west-2.amazonaws.com/datastore/test-id/r4/'
                }
            }

            # Mock the FHIR request
            mock_fhir_request.return_value = {'resourceType': 'Patient', 'id': 'test-id'}

            result = read_fhir_resource(
                datastore_id='test-datastore-id',
                resource_type='Patient',
                resource_id='test-patient-id',
            )

            assert result['resourceType'] == 'Patient'
            assert result['id'] == 'test-id'
            mock_fhir_request.assert_called_once()

    def test_validate_fhir_resource_valid_patient(self):
        """Test validating a valid patient FHIR resource."""
        patient_data = {
            'resourceType': 'Patient',
            'name': [{'family': 'Doe', 'given': ['John']}],
            'gender': 'male',
            'birthDate': '1990-01-01',
        }

        result = validate_fhir_resource(resource_data=patient_data)

        assert result['valid'] is True
        assert len(result['issues']) == 0

    def test_validate_fhir_resource_missing_resource_type(self):
        """Test validating FHIR resource with missing resource type."""
        invalid_data = {'name': [{'family': 'Doe', 'given': ['John']}]}

        result = validate_fhir_resource(resource_data=invalid_data)

        assert result['valid'] is False
        assert "Missing required 'resourceType' field" in result['issues']

    def test_validate_fhir_resource_type_mismatch(self):
        """Test validating FHIR resource with type mismatch."""
        patient_data = {'resourceType': 'Patient', 'name': [{'family': 'Doe', 'given': ['John']}]}

        result = validate_fhir_resource(resource_data=patient_data, resource_type='Observation')

        assert result['valid'] is False
        assert 'Resource type mismatch' in result['issues'][0]

    def test_create_patient_template(self):
        """Test creating a patient template."""
        result = create_patient_template(
            family_name='Doe',
            given_names=['John', 'William'],
            gender='male',
            birth_date='1990-01-01',
            identifier_system='http://hospital.smarthealthit.org',
            identifier_value='12345',
            phone='+1-555-123-4567',
            email='john.doe@example.com',
        )

        assert result['resourceType'] == 'Patient'
        assert result['name'][0]['family'] == 'Doe'
        assert result['name'][0]['given'] == ['John', 'William']
        assert result['gender'] == 'male'
        assert result['birthDate'] == '1990-01-01'
        assert len(result['identifier']) == 1
        assert len(result['telecom']) == 2

    def test_create_observation_template(self):
        """Test creating an observation template."""
        result = create_observation_template(
            patient_reference='Patient/test-patient-id',
            code_system='http://loinc.org',
            code_value='8867-4',
            code_display='Heart rate',
            status='final',
            value_quantity={
                'value': 72,
                'unit': 'beats/min',
                'system': 'http://unitsofmeasure.org',
            },
            effective_datetime='2023-01-01T10:00:00Z',
            category_code='vital-signs',
        )

        assert result['resourceType'] == 'Observation'
        assert result['subject']['reference'] == 'Patient/test-patient-id'
        assert result['code']['coding'][0]['system'] == 'http://loinc.org'
        assert result['code']['coding'][0]['code'] == '8867-4'
        assert result['valueQuantity']['value'] == 72
        assert result['category'][0]['coding'][0]['code'] == 'vital-signs'

    def test_search_fhir_resources_advanced(self, aws_credentials):
        """Test advanced FHIR resource search."""
        with (
            patch('boto3.client') as mock_client,
            patch('awslabs.healthlake_mcp_server.server._make_fhir_request') as mock_fhir_request,
        ):
            # Mock the describe_fhir_datastore call
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.describe_fhir_datastore.return_value = {
                'DatastoreProperties': {
                    'DatastoreEndpoint': 'https://healthlake.us-west-2.amazonaws.com/datastore/test-id/r4/'
                }
            }

            # Mock the FHIR request
            mock_fhir_request.return_value = {'resourceType': 'Bundle', 'entry': []}

            result = search_fhir_resources_advanced(
                datastore_id='test-datastore-id',
                resource_type='Patient',
                search_parameters={'name': 'Smith'},
                include_parameters=['Patient:general-practitioner'],
                sort_parameters=['family', 'given'],
                count=10,
            )

            assert result['resourceType'] == 'Bundle'
            mock_fhir_request.assert_called_once()

    @patch.dict(os.environ, {'HEALTHLAKE_MCP_READONLY': 'false'})
    def test_create_fhir_bundle(self, aws_credentials):
        """Test creating a FHIR bundle."""
        with (
            patch('boto3.client') as mock_client,
            patch('awslabs.healthlake_mcp_server.server._make_fhir_request') as mock_fhir_request,
        ):
            # Mock the describe_fhir_datastore call
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.describe_fhir_datastore.return_value = {
                'DatastoreProperties': {
                    'DatastoreEndpoint': 'https://healthlake.us-west-2.amazonaws.com/datastore/test-id/r4/'
                }
            }

            # Mock the FHIR request
            mock_fhir_request.return_value = {'resourceType': 'Bundle', 'id': 'test-bundle-id'}

            bundle_resources = [
                {
                    'resourceType': 'Patient',
                    'name': [{'family': 'Smith', 'given': ['Jane']}],
                    'gender': 'female',
                    'birthDate': '1985-03-15',
                }
            ]

            result = create_fhir_bundle(
                datastore_id='test-datastore-id',
                bundle_resources=bundle_resources,
                bundle_type='transaction',
            )

            assert result['resourceType'] == 'Bundle'
            assert result['id'] == 'test-bundle-id'
            mock_fhir_request.assert_called_once()

    def test_get_fhir_resource_history(self, aws_credentials):
        """Test getting FHIR resource history."""
        with (
            patch('boto3.client') as mock_client,
            patch('awslabs.healthlake_mcp_server.server._make_fhir_request') as mock_fhir_request,
        ):
            # Mock the describe_fhir_datastore call
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.describe_fhir_datastore.return_value = {
                'DatastoreProperties': {
                    'DatastoreEndpoint': 'https://healthlake.us-west-2.amazonaws.com/datastore/test-id/r4/'
                }
            }

            # Mock the FHIR request
            mock_fhir_request.return_value = {'resourceType': 'Bundle', 'entry': []}

            result = get_fhir_resource_history(
                datastore_id='test-datastore-id',
                resource_type='Patient',
                resource_id='test-patient-id',
            )

            assert result['resourceType'] == 'Bundle'
            mock_fhir_request.assert_called_once()

    def test_get_datastore_capabilities(self, aws_credentials):
        """Test getting datastore capabilities."""
        with (
            patch('boto3.client') as mock_client,
            patch('awslabs.healthlake_mcp_server.server._make_fhir_request') as mock_fhir_request,
        ):
            # Mock the describe_fhir_datastore call
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.describe_fhir_datastore.return_value = {
                'DatastoreProperties': {
                    'DatastoreEndpoint': 'https://healthlake.us-west-2.amazonaws.com/datastore/test-id/r4/'
                }
            }

            # Mock the FHIR request
            mock_fhir_request.return_value = {
                'resourceType': 'CapabilityStatement',
                'status': 'active',
            }

            result = get_datastore_capabilities(datastore_id='test-datastore-id')

            assert result['resourceType'] == 'CapabilityStatement'
            assert result['status'] == 'active'
            mock_fhir_request.assert_called_once()


@mock_aws
def test_list_datastores(aws_credentials):
    """Test listing datastores."""
    with patch('boto3.client') as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.list_fhir_datastores.return_value = {'DatastorePropertiesList': []}
        mock_client.return_value = mock_client_instance

        result = list_datastores()

        mock_client.assert_called_once()
        mock_client_instance.list_fhir_datastores.assert_called_once_with()
        assert result == {'DatastorePropertiesList': []}


def test_read_fhir_resource(aws_credentials):
    """Test reading a FHIR resource."""
    with (
        patch('boto3.client') as mock_client,
        patch('awslabs.healthlake_mcp_server.server._make_fhir_request') as mock_fhir_request,
    ):
        mock_client_instance = MagicMock()
        mock_client_instance.describe_fhir_datastore.return_value = {
            'DatastoreProperties': {
                'DatastoreEndpoint': 'https://healthlake.us-west-2.amazonaws.com/datastore/123/r4/'
            }
        }
        mock_client.return_value = mock_client_instance

        # Mock the FHIR request
        mock_fhir_request.return_value = {'resourceType': 'Patient', 'id': 'test-id'}

        result = read_fhir_resource(datastore_id='123', resource_type='Patient', resource_id='456')

        mock_client.assert_called_once()
        mock_client_instance.describe_fhir_datastore.assert_called_once_with(DatastoreId='123')
        assert result == {'resourceType': 'Patient', 'id': 'test-id'}


def test_create_fhir_resource(aws_credentials):
    """Test creating a FHIR resource."""
    with (
        patch('boto3.client') as mock_client,
        patch('awslabs.healthlake_mcp_server.server._make_fhir_request') as mock_fhir_request,
    ):
        mock_client_instance = MagicMock()
        mock_client_instance.describe_fhir_datastore.return_value = {
            'DatastoreProperties': {
                'DatastoreEndpoint': 'https://healthlake.us-west-2.amazonaws.com/datastore/123/r4/'
            }
        }
        mock_client.return_value = mock_client_instance

        # Mock the FHIR request
        mock_fhir_request.return_value = {'resourceType': 'Patient', 'id': 'created-id'}

        resource_data = {'resourceType': 'Patient', 'name': [{'family': 'Doe', 'given': ['John']}]}

        result = create_fhir_resource(
            datastore_id='123', resource_type='Patient', resource_data=resource_data
        )

        mock_client.assert_called_once()
        mock_client_instance.describe_fhir_datastore.assert_called_once_with(DatastoreId='123')
        assert result == {'resourceType': 'Patient', 'id': 'created-id'}
