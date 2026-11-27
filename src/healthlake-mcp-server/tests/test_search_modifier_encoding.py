"""Search parameter names with FHIR modifiers must reach HealthLake encoded once."""

import httpx
import pytest
from awslabs.healthlake_mcp_server.fhir_operations import HealthLakeClient
from unittest.mock import patch
from urllib.parse import parse_qs


DATASTORE_ID = '12345678901234567890123456789012'


async def _sent_form(**search_kwargs):
    """Run search_resources against a mock transport and return the decoded form body."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured['body'] = request.content.decode()
        return httpx.Response(
            200, json={'resourceType': 'Bundle', 'type': 'searchset', 'entry': []}
        )

    real_async_client = httpx.AsyncClient
    client = HealthLakeClient.__new__(HealthLakeClient)
    client.region = 'us-east-1'
    with (
        patch.object(HealthLakeClient, '_get_aws_auth', return_value=None),
        patch(
            'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient',
            side_effect=lambda **kwargs: real_async_client(
                transport=httpx.MockTransport(handler), **kwargs
            ),
        ),
    ):
        await client.search_resources(DATASTORE_ID, **search_kwargs)
    return parse_qs(captured['body'])


@pytest.mark.asyncio
async def test_modifier_in_search_params_is_sent_as_written():
    """A server decoding the form once must see ``name:contains``."""
    form = await _sent_form(resource_type='Patient', search_params={'name:contains': 'Smi'})

    assert form['name:contains'] == ['Smi']
    assert 'name%3Acontains' not in form


@pytest.mark.asyncio
async def test_type_modifier_in_chained_params_is_sent_as_written():
    """Chained parameters with a ``:Type`` modifier use the same encoding."""
    form = await _sent_form(
        resource_type='Observation', chained_params={'subject:Patient.name': 'Smith'}
    )

    assert form['subject:Patient.name'] == ['Smith']
    assert 'subject%3APatient.name' not in form
