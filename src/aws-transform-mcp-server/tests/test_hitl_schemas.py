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
from awslabs.aws_transform_mcp_server.hitl_schemas import (
    _preprocess_auto_form,
    _preprocess_delete_qt_refresh,
    _preprocess_dotnet_deployment_automation,
    _preprocess_dotnet_discovered_repo_selector,
    _preprocess_dotnet_post_transformation_error,
    _preprocess_dotnet_repo_access_error,
    _preprocess_eba_candidate,
    _preprocess_file_upload_component,
    _preprocess_file_upload_v2,
    _preprocess_mainframe_smf_configure,
    _preprocess_mainframe_test_data_add,
    _preprocess_mainframe_test_scripts_provide,
    _preprocess_specify_assets_location,
    _preprocess_text_input,
    build_dynamic_output_schema,
    enrich_task,
    enrich_tasks,
    extract_dynamic_hitl_fields,
    extract_dynamic_hitl_fields_rich,
    format_and_validate,
    validate_fields_against_schema,
)


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

    def test_create_or_select_connectors(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'uxComponentId': 'CreateOrSelectConnectors', 'taskId': 't-conn'}
        result = enrich_task(task)

        assert result['_responseTemplate'] == {
            'connectorId': '<connector-id>',
            'connectorType': '<connector-type>',
        }
        assert (
            'connectorId' in result['_responseHint'].lower()
            or 'connector' in result['_responseHint'].lower()
        )
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

    def test_chat_hint_attached(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'uxComponentId': 'MainframeAssessmentSummaryComponent', 'taskId': 't-assess'}
        result = enrich_task(task)

        assert '_chatHint' in result
        assert 'send_message' in result['_chatHint']
        assert '_outputSchema' in result
        assert result['_outputSchema']['displayOnly'] is False

    def test_chat_hint_absent_when_not_set(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task

        task = {'uxComponentId': 'TextInput', 'taskId': 't-no-hint'}
        result = enrich_task(task)

        assert '_chatHint' not in result

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

    def test_create_or_select_connectors_string(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate('CreateOrSelectConnectors', '"conn-abc123"')
        assert result.ok is False
        assert 'connectorType' in result.error

    def test_create_or_select_connectors_object(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate('CreateOrSelectConnectors', '{"connectorId": "conn-abc123"}')
        assert result.ok is False
        assert 'connectorType' in result.error

    def test_create_or_select_connectors_with_type(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        result = format_and_validate(
            'CreateOrSelectConnectors',
            '{"connectorId": "conn-abc123", "connectorType": "vmware_migration|infra_provisioning|2"}',
        )
        assert result.ok is True
        parsed = json.loads(result.content)
        assert parsed == {
            'connectorId': 'conn-abc123',
            'connectorType': 'vmware_migration|infra_provisioning|2',
        }

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

    def test_mainframe_assessment_summary_passthrough(self):
        from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate

        content = json.dumps(
            {
                'rejectRetirementCandidates': {
                    'nodes': [{'node_name': 'PKG-A', 'node_type': 'COBOL'}]
                },
            }
        )
        result = format_and_validate('MainframeAssessmentSummaryComponent', content)
        assert result.ok is True
        parsed = json.loads(result.content)
        assert 'rejectRetirementCandidates' in parsed
        assert parsed['rejectRetirementCandidates']['nodes'][0]['node_name'] == 'PKG-A'

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


# ── New test classes covering uncovered lines ────────────────────────────


class TestPreprocessTextInput:
    def test_string_input_returns_data_wrapper(self):
        result = _preprocess_text_input('hello')
        assert result == {'data': 'hello'}

    def test_dict_passes_through(self):
        inp = {'data': 'hello'}
        result = _preprocess_text_input(inp)
        assert result is inp


class TestPreprocessAutoForm:
    def test_already_formed_with_data_and_metadata(self):
        inp = {'data': {'name': 'Alice'}, 'metadata': {'schemaVersion': '1.0'}}
        result = _preprocess_auto_form(inp)
        assert result is inp

    def test_data_dict_no_metadata_adds_metadata(self):
        result = _preprocess_auto_form({'data': {'field1': 'v1', 'field2': 'v2'}})
        assert result['data'] == {'field1': 'v1', 'field2': 'v2'}
        assert 'metadata' in result
        assert result['metadata']['fieldCount'] == 2
        assert result['metadata']['schemaVersion'] == '1.0'

    def test_data_is_string_passes_through(self):
        inp = {'data': 'some string'}
        result = _preprocess_auto_form(inp)
        assert result is inp

    def test_empty_dict_passes_through(self):
        inp = {}
        result = _preprocess_auto_form(inp)
        assert result is inp

    def test_plain_fields_wrapped(self):
        result = _preprocess_auto_form({'name': 'Bob', 'age': '30'})
        assert result['data'] == {'name': 'Bob', 'age': '30'}
        assert result['metadata']['fieldCount'] == 2

    def test_non_dict_passes_through(self):
        result = _preprocess_auto_form([1, 2, 3])
        assert result == [1, 2, 3]


class TestPreprocessFileUploadV2:
    def test_single_artifact_dict_wraps_to_array(self):
        inp = {'artifactId': 'a-1', 'name': 'file.txt'}
        result = _preprocess_file_upload_v2(inp)
        assert result == [inp]

    def test_array_passes_through(self):
        inp = [{'artifactId': 'a-1'}]
        result = _preprocess_file_upload_v2(inp)
        assert result is inp

    def test_dict_without_artifactId_passes_through(self):
        inp = {'name': 'file.txt'}
        result = _preprocess_file_upload_v2(inp)
        assert result is inp


class TestPreprocessFileUploadComponent:
    def test_bare_list_wraps_in_uploaded_file(self):
        inp = [{'content': 'abc', 'name': 'f.txt'}]
        result = _preprocess_file_upload_component(inp)
        assert result == {'uploadedFile': inp}

    def test_dict_passes_through(self):
        inp = {'uploadedFile': []}
        result = _preprocess_file_upload_component(inp)
        assert result is inp


class TestPreprocessDotnetRepoAccessError:
    def test_bool_wraps_to_resolved(self):
        assert _preprocess_dotnet_repo_access_error(True) == {'resolved': True}
        assert _preprocess_dotnet_repo_access_error(False) == {'resolved': False}

    def test_dict_passes_through(self):
        inp = {'resolved': True, 'error': 'AUTH'}
        result = _preprocess_dotnet_repo_access_error(inp)
        assert result is inp


class TestPreprocessDotnetPostTransformationError:
    def test_bool_wraps_to_resolved(self):
        assert _preprocess_dotnet_post_transformation_error(True) == {'resolved': True}
        assert _preprocess_dotnet_post_transformation_error(False) == {'resolved': False}

    def test_dict_passes_through(self):
        inp = {'resolved': True}
        result = _preprocess_dotnet_post_transformation_error(inp)
        assert result is inp


class TestPreprocessDotnetDeploymentAutomation:
    def test_string_wraps_to_config_type(self):
        assert _preprocess_dotnet_deployment_automation('PROVISION') == {'configType': 'PROVISION'}

    def test_dict_passes_through(self):
        inp = {'configType': 'COMMIT'}
        result = _preprocess_dotnet_deployment_automation(inp)
        assert result is inp


class TestPreprocessDotnetDiscoveredRepoSelector:
    def test_non_dict_returns_as_is(self):
        assert _preprocess_dotnet_discovered_repo_selector('text') == 'text'
        assert _preprocess_dotnet_discovered_repo_selector(42) == 42

    def test_custom_file_upload_empty_filename_removed(self):
        inp = {
            'selectedTableResources': [{'id': 'r1'}],
            'customFileUpload': {'fileName': ''},
        }
        result = _preprocess_dotnet_discovered_repo_selector(inp)
        assert result['customFileUpload'] is None

    def test_custom_file_upload_none_filename_removed(self):
        inp = {
            'selectedTableResources': [{'id': 'r1'}],
            'customFileUpload': {'fileName': None},
        }
        result = _preprocess_dotnet_discovered_repo_selector(inp)
        assert result['customFileUpload'] is None

    def test_custom_file_upload_valid_filename_kept(self):
        inp = {
            'selectedTableResources': [{'id': 'r1'}],
            'customFileUpload': {'fileName': 'my-repos.zip'},
        }
        result = _preprocess_dotnet_discovered_repo_selector(inp)
        assert result['customFileUpload']['fileName'] == 'my-repos.zip'


class TestPreprocessSpecifyAssetsLocation:
    def test_string_input(self):
        result = _preprocess_specify_assets_location('s3://bucket/path')
        assert result['assetLocation'] == 's3://bucket/path'
        assert result['optInChatBox'] is False
        assert result['enableFeatures'] == []

    def test_dict_with_value_remapped(self):
        result = _preprocess_specify_assets_location({'value': 's3://bucket/new'})
        assert result['assetLocation'] == 's3://bucket/new'
        assert 'value' not in result
        assert result['optInChatBox'] is False
        assert result['enableFeatures'] == []

    def test_dict_with_asset_location_passes_through(self):
        result = _preprocess_specify_assets_location({'assetLocation': 's3://bucket/direct'})
        assert result['assetLocation'] == 's3://bucket/direct'

    def test_non_dict_non_string_passes_through(self):
        assert _preprocess_specify_assets_location(42) == 42


class TestPreprocessMainframeComponents:
    def test_smf_configure_string(self):
        result = _preprocess_mainframe_smf_configure('s3://bucket/src/')
        assert result == {'sourceCodeS3Path': 's3://bucket/src/'}

    def test_smf_configure_dict_passes_through(self):
        inp = {'sourceCodeS3Path': 's3://bucket/src/'}
        result = _preprocess_mainframe_smf_configure(inp)
        assert result is inp

    def test_test_data_add_string(self):
        result = _preprocess_mainframe_test_data_add('s3://bucket/data/')
        assert result == {'s3Path': 's3://bucket/data/'}

    def test_test_data_add_dict_passes_through(self):
        inp = {'s3Path': 's3://bucket/data/'}
        result = _preprocess_mainframe_test_data_add(inp)
        assert result is inp

    def test_test_scripts_provide_string(self):
        result = _preprocess_mainframe_test_scripts_provide('s3://bucket/scripts/')
        assert result == {'s3Path': 's3://bucket/scripts/'}

    def test_test_scripts_provide_dict_passes_through(self):
        inp = {'s3Path': 's3://bucket/scripts/'}
        result = _preprocess_mainframe_test_scripts_provide(inp)
        assert result is inp


class TestPreprocessDeleteQtRefresh:
    def test_removes_qt_refresh(self):
        inp = {'field1': 'a', 'QT_REFRESH': True}
        result = _preprocess_delete_qt_refresh(inp)
        assert 'QT_REFRESH' not in result
        assert result['field1'] == 'a'

    def test_non_dict_passes_through(self):
        assert _preprocess_delete_qt_refresh('string') == 'string'
        assert _preprocess_delete_qt_refresh(123) == 123

    def test_dict_without_qt_refresh_unchanged(self):
        inp = {'field1': 'a'}
        result = _preprocess_delete_qt_refresh(inp)
        assert result == {'field1': 'a'}


class TestPreprocessEbaCandidate:
    def test_adds_metadata_when_missing(self):
        inp = {'selectedApplication': {'name': 'app1'}}
        result = _preprocess_eba_candidate(inp)
        assert 'metadata' in result
        assert result['metadata']['schemaVersion'] == '1.0'
        assert result['metadata']['totalApplications'] == 0
        assert 'timestamp' in result['metadata']
        assert result['selectedApplication'] == {'name': 'app1'}

    def test_passes_through_when_metadata_present(self):
        inp = {'selectedApplication': {'name': 'app1'}, 'metadata': {'custom': True}}
        result = _preprocess_eba_candidate(inp)
        assert result is inp

    def test_non_dict_passes_through(self):
        assert _preprocess_eba_candidate('text') == 'text'


class TestExtractDynamicHitlFieldsEdgeCases:
    def test_non_dict_node_returns_empty(self):
        assert extract_dynamic_hitl_fields_rich(None) == []
        assert extract_dynamic_hitl_fields_rich('string') == []
        assert extract_dynamic_hitl_fields_rich(42) == []

    def test_props_not_a_dict_treated_as_empty(self):
        node = {'type': 'Input', 'props': 'not-a-dict'}
        result = extract_dynamic_hitl_fields_rich(node)
        assert result == []

    def test_props_as_list_treated_as_empty(self):
        node = {'type': 'Input', 'props': ['fieldId', 'test']}
        result = extract_dynamic_hitl_fields_rich(node)
        assert result == []


class TestExtractDynamicHitlFields:
    def test_returns_field_ids(self):
        node = {
            'type': 'FormField',
            'props': {'label': 'Name'},
            'children': [
                {'type': 'Input', 'props': {'fieldId': 'nameField'}},
            ],
        }
        result = extract_dynamic_hitl_fields(node)
        assert result == ['nameField']


class TestBuildDynamicOutputSchemaEdgeCases:
    def test_dynamic_hitl_no_fields_returns_none(self):
        artifact = {'properties': {'domTreeJson': {}}}
        result = build_dynamic_output_schema('DynamicHITLRenderEngine', artifact)
        assert result is None

    def test_dynamic_hitl_file_upload_field(self):
        artifact = {
            'properties': {
                'domTreeJson': {
                    'type': 'FormField',
                    'props': {'label': 'Upload file'},
                    'children': [
                        {'type': 'FileUpload', 'props': {'fieldId': 'uploadField'}},
                    ],
                }
            }
        }
        schema = build_dynamic_output_schema('DynamicHITLRenderEngine', artifact)
        assert schema is not None
        assert 'uploadField' in schema['properties']
        assert schema['properties']['uploadField']['type'] == 'object'
        assert schema['properties']['uploadField']['description'] == 'Upload file'
        assert 'uploadedFiles' in schema['properties']['uploadField']['properties']


class TestValidateFieldsEdgeCases:
    def test_non_dict_content_returns_none(self):
        schema = {'properties': {'f': {}}, 'additionalProperties': False}
        assert validate_fields_against_schema(None, schema) is None
        assert validate_fields_against_schema('string', schema) is None
        assert validate_fields_against_schema([], schema) is None

    def test_additional_properties_not_false_returns_none(self):
        content = {'unknownField': 'val'}
        schema = {'properties': {'f': {}}, 'additionalProperties': True}
        assert validate_fields_against_schema(content, schema) is None

    def test_no_additional_properties_key_returns_none(self):
        content = {'unknownField': 'val'}
        schema = {'properties': {'f': {}}}
        assert validate_fields_against_schema(content, schema) is None

    def test_all_fields_valid_returns_none(self):
        content = {'field1': 'val1', 'field2': 'val2'}
        schema = {
            'properties': {'field1': {}, 'field2': {}},
            'additionalProperties': False,
        }
        assert validate_fields_against_schema(content, schema) is None


class TestEnrichTaskMetaOnly:
    def test_meta_display_only(self):
        result = enrich_task({'uxComponentId': 'CompleteMigration', 'taskId': 't-1'})
        assert 'display-only' in result['_responseHint'].lower()

    def test_meta_multiple_examples(self):
        # ConfirmInstanceLaunch has 3 examples, not display_only, not merge_with_artifact
        result = enrich_task({'uxComponentId': 'ConfirmInstanceLaunch', 'taskId': 't-2'})
        assert '_responseHint' in result
        assert 'multiple response shapes' in result['_responseHint']

    def test_meta_single_example(self):
        # DBModSimpleTextInput has 1 example, not display_only, not merge_with_artifact
        result = enrich_task({'uxComponentId': 'DBModSimpleTextInput', 'taskId': 't-3'})
        assert '_responseHint' in result
        assert 'Example:' in result['_responseHint']

    def test_meta_no_examples(self, monkeypatch):
        from awslabs.aws_transform_mcp_server import hitl_schemas
        from awslabs.aws_transform_mcp_server.hitl_output_schemas import OutputSchemaMeta

        fake_meta = OutputSchemaMeta(
            display_only=False,
            merge_with_artifact=False,
            examples=[],
            json_schema={},
        )
        monkeypatch.setitem(hitl_schemas.OUTPUT_SCHEMA_META, 'FakeNoExamples', fake_meta)

        result = enrich_task({'uxComponentId': 'FakeNoExamples', 'taskId': 't-4'})
        assert 'FakeNoExamples output schema' in result['_responseHint']

    def test_meta_merge_with_artifact(self, monkeypatch):
        from awslabs.aws_transform_mcp_server import hitl_schemas
        from awslabs.aws_transform_mcp_server.hitl_output_schemas import OutputSchemaMeta

        fake_meta = OutputSchemaMeta(
            display_only=False,
            merge_with_artifact=True,
            examples=[{'field': 'val'}],
            json_schema={},
        )
        monkeypatch.setitem(hitl_schemas.OUTPUT_SCHEMA_META, 'FakeMerge', fake_meta)

        result = enrich_task({'uxComponentId': 'FakeMerge', 'taskId': 't-5'})
        assert '_responseHint' in result
        assert 'merge' in result['_responseHint'].lower()


class TestEnrichTasksWrapper:
    def test_non_dict_data_returns_as_is(self):
        assert enrich_tasks(None) is None
        assert enrich_tasks('string') == 'string'
        assert enrich_tasks([]) == []

    def test_hitl_tasks_list_path(self):
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

    def test_data_without_task_or_hitl_tasks_returns_as_is(self):
        data = {'other': 'value'}
        result = enrich_tasks(data)
        assert result == data


class TestFormatAndValidateMetaMerge:
    def test_meta_merge_with_artifact_without_custom(self, monkeypatch):
        from awslabs.aws_transform_mcp_server import hitl_schemas
        from awslabs.aws_transform_mcp_server.hitl_output_schemas import OutputSchemaMeta

        fake_meta = OutputSchemaMeta(
            display_only=False,
            merge_with_artifact=True,
            examples=[],
            json_schema={},
        )
        monkeypatch.setitem(hitl_schemas.OUTPUT_SCHEMA_META, 'FakeMetaMerge', fake_meta)

        artifact = {'properties': {'existingField': 'old'}}
        result = format_and_validate(
            'FakeMetaMerge',
            '{"newField": "new"}',
            artifact,
        )
        assert result.ok is True
        parsed = json.loads(result.content)
        assert parsed['newField'] == 'new'
        assert parsed['existingField'] == 'old'
