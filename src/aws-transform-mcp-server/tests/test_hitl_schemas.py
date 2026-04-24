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

"""Tests for HITL schema logic: enrich_task, format_and_validate, merge, extraction, dynamic schemas."""
# ruff: noqa: D101, D102, D103

import json


class TestEnrichTask:
    """Tests for enrich_task."""

    def test_text_input(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'uxComponentId': 'TextInput', 'taskId': 't-1'}
        result = enrich_task(task)

        assert result['_responseTemplate'] == {'data': '<your text here>'}
        assert '_responseHint' in result
        assert 'string' in result['_responseHint']

    def test_auto_form(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'uxComponentId': 'AutoForm', 'taskId': 't-2'}
        result = enrich_task(task)

        assert '_responseTemplate' in result
        assert '_responseHint' in result
        assert '_outputSchema' in result

    def test_display_only_via_customizations(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'uxComponentId': 'MarkdownRendererComponent', 'taskId': 't-3'}
        result = enrich_task(task)

        assert result['_responseTemplate'] == {}
        assert (
            'empty' in result['_responseHint'].lower()
            or 'no response' in result['_responseHint'].lower()
        )

    def test_display_only_via_meta(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'uxComponentId': 'CompleteMigration', 'taskId': 't-4'}
        result = enrich_task(task)

        assert '_responseHint' in result
        assert (
            'display-only' in result['_responseHint'].lower()
            or 'Display-only' in result['_responseHint']
        )

    def test_unknown_component(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'uxComponentId': 'NonExistentComponent', 'taskId': 't-5'}
        result = enrich_task(task)

        assert '_responseHint' in result
        assert 'Unknown component' in result['_responseHint']

    def test_no_component_id(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'taskId': 't-6'}
        result = enrich_task(task)

        # Should return task unchanged
        assert result == task

    def test_enrich_tasks_single(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_tasks

        data = {'task': {'uxComponentId': 'TextInput', 'taskId': 't-1'}}
        result = enrich_tasks(data)

        assert '_responseTemplate' in result['task']

    def test_enrich_tasks_list(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_tasks

        data = {
            'hitlTasks': [
                {'uxComponentId': 'TextInput', 'taskId': 't-1'},
                {'uxComponentId': 'AutoForm', 'taskId': 't-2'},
            ]
        }
        result = enrich_tasks(data)

        assert len(result['hitlTasks']) == 2
        assert '_responseTemplate' in result['hitlTasks'][0]
        assert '_responseTemplate' in result['hitlTasks'][1]


class TestFormatAndValidate:
    """Tests for format_and_validate."""

    def test_text_input_string(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate('TextInput', '"hello world"')
        assert result.ok is True
        parsed = json.loads(result.content)
        assert parsed == {'data': 'hello world'}

    def test_text_input_object(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate('TextInput', '{"data": "hello"}')
        assert result.ok is True
        parsed = json.loads(result.content)
        assert parsed == {'data': 'hello'}

    def test_auto_form_plain_fields(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate('AutoForm', '{"name": "Alice", "age": "30"}')
        assert result.ok is True
        parsed = json.loads(result.content)
        assert parsed['data'] == {'name': 'Alice', 'age': '30'}
        assert 'metadata' in parsed
        assert parsed['metadata']['fieldCount'] == 2

    def test_auto_form_already_wrapped(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        content = json.dumps(
            {
                'data': {'name': 'Alice'},
                'metadata': {
                    'schemaVersion': '1.0',
                    'fieldCount': 1,
                    'validationStatus': 'valid',
                    'timestamp': 'T',
                },
            }
        )
        result = format_and_validate('AutoForm', content)
        assert result.ok is True
        parsed = json.loads(result.content)
        assert parsed['data'] == {'name': 'Alice'}
        assert parsed['metadata']['schemaVersion'] == '1.0'

    def test_display_only_auto_submit(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        # MarkdownRendererComponent has a CUSTOMIZATIONS entry with preprocess
        result = format_and_validate('MarkdownRendererComponent', '{"ignored": true}')
        assert result.ok is True
        assert json.loads(result.content) == {}

    def test_display_only_via_meta(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        # CompleteMigration is display-only via OUTPUT_SCHEMA_META, no CUSTOMIZATIONS
        result = format_and_validate('CompleteMigration', '{"ignored": true}')
        assert result.ok is True
        assert json.loads(result.content) == {}

    def test_unknown_component_passthrough(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate('SomeUnknownComponent123', '{"foo": "bar"}')
        assert result.ok is True
        assert json.loads(result.content) == {'foo': 'bar'}

    def test_no_component_passthrough(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate(None, '{"anything": true}')
        assert result.ok is True

    def test_invalid_json(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate('TextInput', 'not json')
        assert result.ok is False
        assert 'not valid JSON' in result.error

    def test_merge_with_artifact(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        artifact = {'properties': {'existingField': 'old', 'anotherField': 'keep'}}
        result = format_and_validate(
            'DotnetCFNDownload',
            '{"skipDeployment": true}',
            artifact,
        )
        assert result.ok is True
        parsed = json.loads(result.content)
        assert parsed['skipDeployment'] is True
        assert parsed['existingField'] == 'old'
        assert parsed['anotherField'] == 'keep'

    def test_specify_assets_remap_value(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        artifact = {'properties': {'value': 's3://old'}}
        result = format_and_validate(
            'SpecifyAssetsLocation',
            '{"value": "s3://new"}',
            artifact,
        )
        assert result.ok is True
        parsed = json.loads(result.content)
        assert parsed['assetLocation'] == 's3://new'
        assert parsed['optInChatBox'] is False
        assert parsed['enableFeatures'] == []

    def test_dynamic_field_validation_rejects_unknown(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        artifact = {'properties': {'fields': [{'name': 'field1'}, {'name': 'field2'}]}}
        result = format_and_validate(
            'AutoForm',
            '{"field1": "ok", "unknownField": "bad"}',
            artifact,
        )
        assert result.ok is False
        assert 'Unknown field' in result.error

    def test_dotnet_discovered_repo_bulk_all(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        artifact = {
            'properties': {
                'discoveredResources': [
                    {'id': 'r1', 'name': 'repo1', 'sourceBranch': 'main'},
                    {'id': 'r2', 'name': 'repo2', 'sourceBranch': 'dev'},
                ],
                'selectedTableResources': [],
            }
        }
        result = format_and_validate(
            'DotnetDiscoveredRepoSelector',
            '{"bulkSelection": "ALL"}',
            artifact,
        )
        assert result.ok is True
        parsed = json.loads(result.content)
        assert len(parsed['selectedTableResources']) == 2


class TestMergeArtifactDiff:
    """Tests for merge_artifact_diff."""

    def test_basic_merge(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import merge_artifact_diff

        result = merge_artifact_diff(
            {'newKey': 'new'},
            {'oldKey': 'old', 'shared': 'artifact'},
        )
        assert result == {'oldKey': 'old', 'shared': 'artifact', 'newKey': 'new'}

    def test_llm_wins_on_conflict(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import merge_artifact_diff

        result = merge_artifact_diff(
            {'key': 'llm'},
            {'key': 'artifact'},
        )
        assert result['key'] == 'llm'


class TestUnwrapArtifactProperties:
    """Tests for unwrap_artifact_properties."""

    def test_unwrap_dict_properties(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import unwrap_artifact_properties

        result = unwrap_artifact_properties({'properties': {'a': 1, 'b': 2}})
        assert result == {'a': 1, 'b': 2}

    def test_no_properties(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import unwrap_artifact_properties

        result = unwrap_artifact_properties({'a': 1})
        assert result == {'a': 1}


class TestExtractAutoFormFields:
    """Tests for extract_auto_form_fields."""

    def test_pattern1_properties_fields(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import extract_auto_form_fields

        artifact = {
            'properties': {
                'fields': [
                    {'name': 'field1', 'type': 'string'},
                    {'name': 'field2', 'type': 'number'},
                ]
            }
        }
        assert extract_auto_form_fields(artifact) == ['field1', 'field2']

    def test_pattern1_properties_keys_fallback(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import extract_auto_form_fields

        artifact = {'properties': {'fieldA': {'type': 'string'}, 'fieldB': {'type': 'number'}}}
        result = extract_auto_form_fields(artifact)
        assert 'fieldA' in result
        assert 'fieldB' in result

    def test_pattern2_schema_properties(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import extract_auto_form_fields

        artifact = {'schema': {'properties': {'x': {}, 'y': {}}}}
        result = extract_auto_form_fields(artifact)
        assert set(result) == {'x', 'y'}

    def test_pattern3_top_level_fields(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import extract_auto_form_fields

        artifact = {'fields': [{'name': 'a'}, {'name': 'b'}]}
        assert extract_auto_form_fields(artifact) == ['a', 'b']

    def test_pattern4_form_data(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import extract_auto_form_fields

        artifact = {'formData': {'q1': 'answer1', 'q2': 'answer2'}}
        assert extract_auto_form_fields(artifact) == ['q1', 'q2']

    def test_empty_artifact(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import extract_auto_form_fields

        assert extract_auto_form_fields({}) == []


class TestBuildDynamicOutputSchema:
    """Tests for build_dynamic_output_schema."""

    def test_auto_form(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import build_dynamic_output_schema

        artifact = {'properties': {'fields': [{'name': 'name'}, {'name': 'email'}]}}
        schema = build_dynamic_output_schema('AutoForm', artifact)

        assert schema is not None
        assert schema['type'] == 'object'
        assert 'name' in schema['properties']
        assert 'email' in schema['properties']
        assert schema['additionalProperties'] is False

    def test_dynamic_hitl_render_engine(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import build_dynamic_output_schema

        artifact = {
            'properties': {
                'domTreeJson': {
                    'type': 'FormField',
                    'props': {'label': 'Name'},
                    'children': [
                        {'type': 'Input', 'props': {'fieldId': 'nameField'}},
                    ],
                }
            }
        }
        schema = build_dynamic_output_schema('DynamicHITLRenderEngine', artifact)

        assert schema is not None
        assert 'nameField' in schema['properties']
        assert schema['properties']['nameField']['type'] == 'string'
        assert schema['properties']['nameField']['description'] == 'Name'

    def test_dynamic_hitl_radio_group(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import build_dynamic_output_schema

        artifact = {
            'properties': {
                'domTreeJson': {
                    'type': 'RadioGroup',
                    'props': {
                        'fieldId': 'choice',
                        'items': [{'value': 'A'}, {'value': 'B'}],
                    },
                }
            }
        }
        schema = build_dynamic_output_schema('DynamicHITLRenderEngine', artifact)

        assert schema is not None
        assert schema['properties']['choice']['enum'] == ['A', 'B']

    def test_unknown_component(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import build_dynamic_output_schema

        assert build_dynamic_output_schema('TextInput', {}) is None

    def test_auto_form_no_fields(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import build_dynamic_output_schema

        assert build_dynamic_output_schema('AutoForm', {}) is None
