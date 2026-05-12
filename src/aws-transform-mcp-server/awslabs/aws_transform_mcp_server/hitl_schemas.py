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

"""HITL response formatting, preprocessing, and validation.

Ported from hitl-schemas.ts. Provides:
  - CUSTOMIZATIONS: per-component preprocessing, templates, and hints
  - enrich_task / enrich_tasks: decorate tasks with _responseTemplate/_responseHint
  - format_and_validate: preprocess + validate + serialize LLM responses
  - Dynamic schema builders for AutoForm and DynamicHITLRenderEngine
"""
# ruff: noqa: E501

import json
from awslabs.aws_transform_mcp_server.hitl_output_schemas import OUTPUT_SCHEMA_META
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


# ── Result type ───────────────────────────────────────────────────────────


class FormatResult:
    """Result of format_and_validate: either ok with content, or error."""

    __slots__ = ('ok', 'content', 'error')

    def __init__(self, *, ok: bool, content: str = '', error: str = '') -> None:
        """Initialize FormatResult."""
        self.ok = ok
        self.content = content
        self.error = error


# ── AutoForm metadata helper ─────────────────────────────────────────────


def auto_form_metadata(field_count: int) -> Dict[str, Any]:
    """Build metadata block for AutoForm responses."""
    now = datetime.now(timezone.utc)
    # Match JS Date.toISOString(): YYYY-MM-DDTHH:MM:SS.sssZ (ms precision, Z suffix)
    timestamp = now.strftime('%Y-%m-%dT%H:%M:%S.') + f'{now.microsecond // 1000:03d}Z'
    return {
        'schemaVersion': '1.0',
        'fieldCount': field_count,
        'validationStatus': 'valid',
        'timestamp': timestamp,
    }


# ── Artifact-diff merge helpers ──────────────────────────────────────────


def unwrap_artifact_properties(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Unwrap SDK serialize() wrapper: {properties: {...}} -> inner object."""
    props = artifact.get('properties')
    if isinstance(props, dict) and not isinstance(props, list):
        return props
    return artifact


def merge_artifact_diff(
    llm_input: Dict[str, Any],
    artifact_props: Dict[str, Any],
) -> Dict[str, Any]:
    """Shallow-merge: artifact provides defaults, LLM input wins on conflicts."""
    return {**artifact_props, **llm_input}


# ── Per-component customization type ─────────────────────────────────────


class ComponentCustomization:
    """Configuration for a single UX component's preprocessing."""

    __slots__ = (
        'template',
        'hint',
        'preprocess',
        'merge_with_artifact',
        'skip_validation_after_preprocess',
    )

    def __init__(
        self,
        *,
        template: Any,
        hint: str,
        preprocess: Optional[Callable[..., Any]] = None,
        merge_with_artifact: bool = False,
        skip_validation_after_preprocess: bool = False,
    ) -> None:
        """Initialize ComponentCustomization."""
        self.template = template
        self.hint = hint
        self.preprocess = preprocess
        self.merge_with_artifact = merge_with_artifact
        self.skip_validation_after_preprocess = skip_validation_after_preprocess


# ── Preprocess functions ──────────────────────────────────────────────────


def _preprocess_text_input(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize TextInput content to {data: string} format."""
    if isinstance(inp, str):
        return {'data': inp}
    return inp


def _preprocess_auto_form(inp: Any, agent_artifact: Any = None) -> Any:
    """Wrap raw field values into {data, metadata} AutoForm envelope."""
    if not isinstance(inp, dict):
        return inp

    # Already fully formed: { data: {…}, metadata: {…} }
    if 'data' in inp and isinstance(inp.get('data'), dict) and 'metadata' in inp:
        return inp

    # Has data wrapper (object) but no metadata -> add metadata
    if 'data' in inp and isinstance(inp.get('data'), dict):
        return {'data': inp['data'], 'metadata': auto_form_metadata(len(inp['data']))}

    # data is a string -> wrong type, let validation report it
    if 'data' in inp and isinstance(inp.get('data'), str):
        return inp

    # Plain field values -> wrap in { data, metadata }
    if len(inp) == 0:
        return inp
    return {'data': inp, 'metadata': auto_form_metadata(len(inp))}


def _preprocess_general_connector(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize bare connector ID string to {connectorId}."""
    if isinstance(inp, str):
        inp = {'connectorId': inp}
    return inp


def _preprocess_create_or_select_connectors(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize bare connector ID string to {connectorId, connectorType}.

    Raises ValueError if connectorType is missing — the LLM must provide it
    by inspecting the connector via get_resource(resource="connector").
    """
    if isinstance(inp, str):
        inp = {'connectorId': inp}
    if isinstance(inp, dict) and 'connectorType' not in inp:
        raise ValueError(
            'connectorType is required. Use get_resource with resource="connector" '
            "and the connectorId to look up the connector's connectorType, "
            'then include it in your response as {"connectorId": "...", "connectorType": "..."}.'
        )
    return inp


def _preprocess_display_only(inp: Any = None, agent_artifact: Any = None) -> Any:
    """Return empty object for display-only components."""
    return {}


def _preprocess_file_upload_v2(inp: Any, agent_artifact: Any = None) -> Any:
    """Wrap a single artifact object into an array for FileUploadV2."""
    # Single object -> wrap in array
    if isinstance(inp, dict) and 'artifactId' in inp:
        return [inp]
    return inp


def _preprocess_file_upload_component(inp: Any, agent_artifact: Any = None) -> Any:
    """Wrap a bare array into {uploadedFile: [...]} for FileUploadComponent."""
    # Bare array -> wrap in { uploadedFile }
    if isinstance(inp, list):
        return {'uploadedFile': inp}
    return inp


def _preprocess_dotnet_repo_access_error(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize boolean to {resolved: bool} for DotnetRepositoryAccessError."""
    if isinstance(inp, bool):
        return {'resolved': inp}
    return inp


def _preprocess_dotnet_post_transformation_error(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize boolean to {resolved: bool} for DotnetPostTransformationError."""
    if isinstance(inp, bool):
        return {'resolved': inp}
    return inp


def _preprocess_dotnet_deployment_automation(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize bare string to {configType: string} for deployment options."""
    if isinstance(inp, str):
        return {'configType': inp}
    return inp


def _preprocess_dotnet_discovered_repo_selector(inp: Any, agent_artifact: Any = None) -> Any:
    """Expand bulk selection and strip transient fields for repo selector."""
    if not isinstance(inp, dict):
        return inp

    obj = inp

    # Expand bulkSelection: "ALL" -> copy discoveredResources into selectedTableResources
    has_selection = (
        isinstance(obj.get('selectedTableResources'), list)
        and len(obj['selectedTableResources']) > 0
    )
    if obj.get('bulkSelection') == 'ALL' and not has_selection:
        discovered = obj.get('discoveredResources')
        if isinstance(discovered, list) and len(discovered) > 0:
            obj['selectedTableResources'] = discovered

    # Strip fields the LLM shouldn't set
    obj.pop('retryOption', None)
    obj.pop('QT_REFRESH', None)

    # Normalize customFileUpload
    cf = obj.get('customFileUpload')
    if isinstance(cf, dict):
        if not cf.get('fileName') or cf.get('fileName') == '':
            obj['customFileUpload'] = None

    return obj


def _preprocess_specify_assets_location(inp: Any, agent_artifact: Any = None) -> Any:
    """Remap artifact value field to assetLocation and add defaults."""
    if isinstance(inp, str):
        obj: Dict[str, Any] = {'assetLocation': inp}
    elif isinstance(inp, dict):
        obj = {**inp}
        # LLM might use artifact field name "value" -> remap to "assetLocation"
        if 'value' in obj and 'assetLocation' not in obj:
            value = obj.pop('value')
            obj = {'assetLocation': value, **obj}
    else:
        return inp

    if 'optInChatBox' not in obj:
        obj['optInChatBox'] = False
    if 'enableFeatures' not in obj:
        obj['enableFeatures'] = []
    return obj


def _preprocess_mainframe_smf_configure(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize bare S3 path string to {sourceCodeS3Path: string}."""
    if isinstance(inp, str):
        return {'sourceCodeS3Path': inp}
    return inp


def _preprocess_mainframe_test_data_add(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize bare S3 path string to {s3Path: string} for test data."""
    if isinstance(inp, str):
        return {'s3Path': inp}
    return inp


def _preprocess_mainframe_test_scripts_provide(inp: Any, agent_artifact: Any = None) -> Any:
    """Normalize bare S3 path string to {s3Path: string} for test scripts."""
    if isinstance(inp, str):
        return {'s3Path': inp}
    return inp


def _preprocess_delete_qt_refresh(inp: Any, agent_artifact: Any = None) -> Any:
    """Strip the transient QT_REFRESH field from the response object."""
    if not isinstance(inp, dict):
        return inp
    obj = inp
    obj.pop('QT_REFRESH', None)
    return obj


def _preprocess_eba_candidate(inp: Any, agent_artifact: Any = None) -> Any:
    """Add default metadata block to EBA candidate application list."""
    if not isinstance(inp, dict):
        return inp
    if 'metadata' in inp:
        return inp
    return {
        **inp,
        'metadata': {
            'schemaVersion': '1.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'totalApplications': 0,
        },
    }


# ── CUSTOMIZATIONS dict ──────────────────────────────────────────────────

CUSTOMIZATIONS: Dict[str, ComponentCustomization] = {
    'TextInput': ComponentCustomization(
        template={'data': '<your text here>'},
        hint='Provide a string value. You can send just a plain string or {"data": "your text"}.',
        preprocess=_preprocess_text_input,
    ),
    'AutoForm': ComponentCustomization(
        template={'<fieldName>': '<value>'},
        hint='Provide form field values as a JSON object (e.g. {"assetLocation": "file.zip"}). Server auto-wraps in {data: ...} and adds metadata.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_auto_form,
    ),
    'GeneralConnector': ComponentCustomization(
        template={'connectorId': '<connector-id>'},
        hint='Provide the connector ID.',
        merge_with_artifact=False,
        preprocess=_preprocess_general_connector,
    ),
    'CreateOrSelectConnectors': ComponentCustomization(
        template={
            'connectorId': '<connector-id>',
            'connectorType': '<connector-type>',
        },
        hint='Provide both connectorId and connectorType. Use get_resource(resource="connector") to look up the connectorType for your connector.',
        merge_with_artifact=False,
        preprocess=_preprocess_create_or_select_connectors,
    ),
    'MarkdownRendererComponent': ComponentCustomization(
        template={},
        hint='No response data needed. Server submits an empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'FileUploadV2': ComponentCustomization(
        template=[{'artifactId': '<id>', 'name': '<filename>', 'mimeType': '<mime-type>'}],
        hint='Provide an array of uploaded artifact objects with artifactId, name, and mimeType.',
        preprocess=_preprocess_file_upload_v2,
    ),
    'FileUploadComponent': ComponentCustomization(
        template={'uploadedFile': [{'content': '<base64>', 'name': '<filename>', 'isZip': False}]},
        hint='Provide file data in the uploadedFile array. Each item needs content (base64), name, and isZip.',
        preprocess=_preprocess_file_upload_component,
    ),
    'TableComponent': ComponentCustomization(
        template={'id': '<element-id>'},
        hint='Provide the table element data with at least an "id" field. Additional properties are allowed.',
    ),
    'DynamicHITLRenderEngine': ComponentCustomization(
        template={'<fieldId>': '<value>'},
        hint='Provide field values as a flat JSON object mapping each fieldId to its value (e.g. {"myField": "hello"}). Check _responseTemplate for concrete field names.',
    ),
    # ── Dotnet components ──────────────────────────────────────────────
    'DotnetCFNDownload': ComponentCustomization(
        template={'skipDeployment': True},
        hint='Provide {"skipDeployment": true} to skip deployment or {"runValidation": true} to trigger validation. Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
    ),
    'DotnetRepositoryAccessError': ComponentCustomization(
        template={'resolved': True},
        hint='Acknowledge the error. Send {"resolved": true} (optionally include "error" with the error type). Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
        preprocess=_preprocess_dotnet_repo_access_error,
    ),
    'DotnetPostTransformationError': ComponentCustomization(
        template={'resolved': True},
        hint='Acknowledge the error. Send {"resolved": true} (optionally include "errorType"). Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
        preprocess=_preprocess_dotnet_post_transformation_error,
    ),
    'DotnetSetUpInfra': ComponentCustomization(
        template={
            'selectedOption': 'EXISTING',
            's3Bucket': 'arn:aws:s3:::bucket-name',
            'selectedRegion': 'us-east-1',
            'kmsARN': '',
        },
        hint='Provide selectedOption, s3Bucket (ARN), selectedRegion, and kmsARN (empty string if none). Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
    ),
    'DotnetDeploymentAutomationOptions': ComponentCustomization(
        template={'configType': 'PROVISION'},
        hint='Provide configType ("PROVISION", "COMMIT", or "SKIP"). Add nextHITL: true for PROVISION/COMMIT, or closeJobAndQuit: true to exit. Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
        preprocess=_preprocess_dotnet_deployment_automation,
    ),
    'DotnetConfigInfra': ComponentCustomization(
        template={
            'deployableApplications': [
                {'id': '<app-id>', 'projectAssemblyName': '<name>', 'infraParameters': {}}
            ]
        },
        hint='Provide the full deployableApplications array with infrastructure parameters. Add closeJobAndQuit: true to exit. Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
    ),
    'DotnetProvisionApplication': ComponentCustomization(
        template={
            'deployableApplications': [
                {
                    'id': '<app-id>',
                    'projectAssemblyName': '<name>',
                    'provision': True,
                    'commitToGit': True,
                }
            ],
        },
        hint='Provide the full deployableApplications array with provision and commitToGit flags set. Add closeJobAndQuit: true to exit. Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
    ),
    'DotnetResourceSelector': ComponentCustomization(
        template={'userSelectionType': 'TABLE', 'selectedTableResources': []},
        hint='Provide userSelectionType and selectedTableResources (or customFileUploadResources + customFileUpload for FILE). Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
    ),
    'DotnetReviewAndConfirm': ComponentCustomization(
        template={'selectedRepos': ['<copy from artifact>']},
        hint='Provide only fields you want to change (e.g. selectedRepos). Server merges onto artifact.',
        merge_with_artifact=True,
    ),
    'DotnetMissingPackages': ComponentCustomization(
        template={
            'uploadedArtifactIds': [
                {'artifactId': '<id>', 'name': '<name>', 'lastModified': 0, 'size': 0}
            ]
        },
        hint='Provide uploadedArtifactIds (to upload packages) or removedPackages (to remove packages). Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
    ),
    'DotnetDiscoveredRepoSelector': ComponentCustomization(
        template={'selectedTableResources': ['<copy from discoveredResources in artifact>']},
        hint='Provide selectedTableResources (array of {name, id, sourceBranch}). Send {"bulkSelection": "ALL"} to select all repos. Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_dotnet_discovered_repo_selector,
    ),
    'DotnetCrossRepoSelector': ComponentCustomization(
        template={'userSelectionType': 'RECOMMENDED', 'selectedTableResources': []},
        hint='Provide userSelectionType ("RECOMMENDED" or "CUSTOMIZED") and selectedTableResources. Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
    ),
    'SpecifyAssetsLocation': ComponentCustomization(
        template={'assetLocation': '<s3-path-or-location>'},
        hint='Provide assetLocation (string). Note: the artifact uses "value" but the output field is "assetLocation". Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_specify_assets_location,
    ),
    # ── Mainframe display components ─────────────────────────────────
    'MainframeAnalysisResults': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeTransformationResults': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeReforgeOutputComponent': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeDocGenResultComponent': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeBreResultComponent': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeDataLineageResultComponent': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeSMFAnalysisComponent': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeTestDataCollectionReviewComponent': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeTestScriptsGenerationReviewComponent': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeTestToolsComponent': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeAccessRestrictedDisplay': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    'MainframeUpdateServiceQuota': ComponentCustomization(
        template={},
        hint='Display-only. Server submits empty response automatically.',
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_display_only,
    ),
    # ── Mainframe S3 path input components ─────────────────────────
    'MainframeAssessmentConfigurationComponent': ComponentCustomization(
        template={
            'sourceCodeS3Path': 's3://bucket/source/',
            'smfRecordsS3Path': 's3://bucket/smf/',
        },
        hint='Provide S3 paths for source code and SMF records. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    'MainframeSMFConfigureComponent': ComponentCustomization(
        template={'sourceCodeS3Path': 's3://bucket/path/'},
        hint='Provide S3 path for source code. Only include fields you want to change.',
        merge_with_artifact=True,
        preprocess=_preprocess_mainframe_smf_configure,
    ),
    'MainframeTestDataCollectionAddComponent': ComponentCustomization(
        template={'s3Path': 's3://bucket/path/'},
        hint='Provide S3 path for test data. Only include fields you want to change.',
        merge_with_artifact=True,
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_mainframe_test_data_add,
    ),
    'MainframeTestPlanConfigureComponent': ComponentCustomization(
        template={
            'businessLogicS3Path': 's3://bucket/logic/',
            'documentationOutputS3Path': 's3://bucket/docs/',
        },
        hint='Provide S3 paths for business logic and documentation output. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    'MainframeTestScriptsGenerationProvideComponent': ComponentCustomization(
        template={'s3Path': 's3://bucket/path/'},
        hint='Provide S3 path for test scripts. Only include fields you want to change.',
        merge_with_artifact=True,
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_mainframe_test_scripts_provide,
    ),
    'MainframeTestDataCollectionConfigurationComponent': ComponentCustomization(
        template={
            'datasetsFilePath': '',
            'jsonFilePath': '',
            'dbJclFilePath': '',
            'vsamJclFilePath': '',
            'seqJclFilePath': '',
        },
        hint='Provide file paths for test data collection configuration. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    'MainframeReforgeInputComponent': ComponentCustomization(
        template={
            'buildableCodeS3Path': 's3://bucket/code/',
            'businessLogicS3Path': 's3://bucket/logic/',
        },
        hint='Provide S3 paths for buildable code and business logic. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    # ── Mainframe selection components ─────────────────────────────
    'MainframeReforgeSelectComponent': ComponentCustomization(
        template={'selectedClasses': [{'className': '<name>', 'packageName': '<pkg>', 'loc': 0}]},
        hint='Provide selectedClasses array. Copy items from artifact reforgeSelect list. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    'MainframeDocGenInputComponent': ComponentCustomization(
        template={'selectedFiles': ['<file>']},
        hint='Provide selectedFiles array. Copy items from artifact docGenInput list. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    'MainframeBreInputComponent': ComponentCustomization(
        template={'selectedFiles': ['<file>']},
        hint='Provide selectedFiles array. Copy items from artifact breInput list. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    'MainframeTestPlanCreateComponent': ComponentCustomization(
        template={'selectedEntryPoints': ['<entry-point>']},
        hint='Provide selectedEntryPoints array. Copy items from artifact entryPointGroups. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    'MainframeTestDataCollectionSelectionComponent': ComponentCustomization(
        template={'selectedItems': ['<item>']},
        hint='Provide selectedItems array. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    # ── Mainframe complex components ───────────────────────────────
    'MainframeDecomposition': ComponentCustomization(
        template={
            'domains': [
                {
                    'id': '<domain-id>',
                    'name': '<domain-name>',
                    'files': [{'id': '<file-id>', 'name': '<name>', 'seeds': True}],
                },
            ],
        },
        hint='Provide updated domains array with file-to-domain assignments. Copy domain/file IDs from artifact. Only include fields you want to change.',
        merge_with_artifact=True,
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_delete_qt_refresh,
    ),
    'MainframeMigrationSequencePlanning': ComponentCustomization(
        template={'domainsWithSequence': [{'id': '<id>', 'sequence': 1}]},
        hint='Provide domainsWithSequence array with updated sequence numbers. Copy domain entries from artifact and change sequence values.',
        merge_with_artifact=True,
    ),
    'MainframeTransformationLaunchComponent': ComponentCustomization(
        template={'selectedDomains': ['<domain-id>'], 'transformationEngineProperties': {}},
        hint='Provide selectedDomains (array of domain IDs to transform) and optionally transformationEngineProperties overrides. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    'MainframeTestPlanValidateComponent': ComponentCustomization(
        template={'newTestCase': {'name': '<name>', 'description': '<desc>'}},
        hint=(
            'Send ONE operation per call. Operations: '
            '{newTestCase: {name, description}} | '
            '{deleteTestCases: {testCaseIds: ["id1"]}} | '
            '{mergeTestCases: {testCaseIds: ["id1","id2"], mergedName: "..."}} | '
            '{preferredOrderTestCase: {testCaseId: "...", preferredOrder: 1}} | '
            '{resetTestCaseOrder: true} | '
            '{removeEntryPointRecord: {testCaseId: "...", entrypointIndexes: [0]}} | '
            '{newEntryPointTestCaseRecord: {testCaseId: "...", entrypointIndex: 0}} | '
            '{splitEntryPointRecord: {testCaseId: "...", entrypointIndex: 0, splitName: "..."}}'
        ),
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_delete_qt_refresh,
    ),
    'MainframeTestScriptsGenerationSelectComponent': ComponentCustomization(
        template={'selectedFiles': ['<file>']},
        hint='Provide selectedFiles array. Only include fields you want to change.',
        merge_with_artifact=True,
    ),
    # ── Other components ─────────────────────────────────────────
    'EBACandidateApplicationList': ComponentCustomization(
        template={
            'selectedApplication': {'name': '<app-name>', 'businessCriticality': 50},
            'assessmentType': 'deep_assessment',
        },
        hint='Provide selectedApplication and assessmentType. Server auto-fills metadata. Only provide fields you want to change -- server merges onto artifact.',
        merge_with_artifact=True,
        skip_validation_after_preprocess=True,
        preprocess=_preprocess_eba_candidate,
    ),
}


# ── DynamicHITLRenderEngine field extraction ─────────────────────────────

INPUT_COMPONENT_TYPES = {'Input', 'Textarea', 'RadioGroup', 'FileUpload'}


class DynamicHITLField:
    """Metadata for a single input field in a DynamicHITLRenderEngine DOM tree."""

    __slots__ = ('field_id', 'type', 'options', 'label')

    def __init__(
        self,
        *,
        field_id: str,
        type: str,
        options: Optional[List[str]] = None,
        label: Optional[str] = None,
    ) -> None:
        """Initialize DynamicHITLField."""
        self.field_id = field_id
        self.type = type
        self.options = options
        self.label = label


def extract_dynamic_hitl_fields_rich(
    node: Any,
    parent_label: Optional[str] = None,
) -> List[DynamicHITLField]:
    """Walk a DynamicHITLRenderEngine JSON DOM tree and collect rich metadata for all input nodes."""
    if not node or not isinstance(node, dict):
        return []

    fields: List[DynamicHITLField] = []
    node_type = node.get('type')
    props = node.get('props', {})
    if not isinstance(props, dict):
        props = {}

    # Track FormField label to pass down to child input components
    label_for_children = parent_label
    if node_type == 'FormField' and isinstance(props.get('label'), str):
        label_for_children = props['label']

    # Check if this node is an input component with a fieldId
    if node_type and node_type in INPUT_COMPONENT_TYPES and isinstance(props.get('fieldId'), str):
        field = DynamicHITLField(
            field_id=props['fieldId'],
            type=node_type,
            label=label_for_children,
        )

        if node_type == 'RadioGroup' and isinstance(props.get('items'), list):
            field.options = [
                item['value']
                for item in props['items']
                if isinstance(item, dict) and isinstance(item.get('value'), str)
            ]

        fields.append(field)

    children = node.get('children')
    if isinstance(children, list):
        for child in children:
            fields.extend(extract_dynamic_hitl_fields_rich(child, label_for_children))

    return fields


def extract_dynamic_hitl_fields(node: Any) -> List[str]:
    """Walk a DynamicHITLRenderEngine JSON DOM tree and collect all fieldId values."""
    return [f.field_id for f in extract_dynamic_hitl_fields_rich(node)]


# ── AutoForm field extraction from agent artifacts ───────────────────────


def extract_auto_form_fields(artifact: Dict[str, Any]) -> List[str]:
    """Try to extract field names from an AutoForm agent artifact."""

    def names_from_fields_array(arr: List[Any]) -> List[str]:
        return [f['name'] for f in arr if isinstance(f, dict) and isinstance(f.get('name'), str)]

    # Pattern 1: SDK serialize() wrapper -- {properties: {fields: [{name: "..."}], ...}}
    props = artifact.get('properties')
    if isinstance(props, dict) and not isinstance(props, list):
        fields_arr = props.get('fields')
        if isinstance(fields_arr, list):
            names = names_from_fields_array(fields_arr)
            if names:
                return names
        # Fallback: JSON Schema style -- properties maps field names to type defs
        return list(props.keys())

    # Pattern 2: nested schema.properties
    schema = artifact.get('schema')
    if isinstance(schema, dict):
        schema_props = schema.get('properties')
        if isinstance(schema_props, dict):
            return list(schema_props.keys())

    # Pattern 3: fields array with name property (top-level)
    fields_arr = artifact.get('fields')
    if isinstance(fields_arr, list):
        names = names_from_fields_array(fields_arr)
        if names:
            return names

    # Pattern 4: formData/data with field keys
    for key in ('formData', 'data', 'defaultValues'):
        sub = artifact.get(key)
        if isinstance(sub, dict):
            keys = list(sub.keys())
            if keys:
                return keys

    return []


# ── Dynamic output schema builder ────────────────────────────────────────


def build_dynamic_output_schema(
    ux_component_id: str,
    agent_artifact: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Build a dynamic JSON Schema from the agent artifact.

    For components whose output fields are defined at runtime (AutoForm, DynamicHITLRenderEngine).
    """
    if ux_component_id == 'AutoForm':
        fields = extract_auto_form_fields(agent_artifact)
        if not fields:
            return None
        properties: Dict[str, Any] = {}
        for f in fields:
            properties[f] = {'type': ['string', 'boolean', 'array']}
        return {
            'type': 'object',
            'description': f'AutoForm with fields: {", ".join(fields)}. Server auto-wraps in {{data: {{...}}, metadata: {{...}}}}.',
            'properties': properties,
            'required': [],
            'additionalProperties': False,
        }

    if ux_component_id == 'DynamicHITLRenderEngine':
        dom_tree = agent_artifact.get('domTreeJson')
        art_props = agent_artifact.get('properties')
        if isinstance(art_props, dict):
            dom_tree = art_props.get('domTreeJson', dom_tree)

        rich_fields = extract_dynamic_hitl_fields_rich(dom_tree)
        if not rich_fields:
            return None

        properties = {}
        for f in rich_fields:
            if f.type == 'RadioGroup' and f.options:
                properties[f.field_id] = {
                    'type': 'string',
                    'enum': f.options,
                    'description': f.label,
                }
            elif f.type == 'FileUpload':
                properties[f.field_id] = {
                    'type': 'object',
                    'description': f.label or 'File upload',
                    'properties': {'uploadedFiles': {'type': 'array'}},
                }
            else:
                properties[f.field_id] = {'type': 'string', 'description': f.label}
        return {
            'type': 'object',
            'description': f'DynamicHITLRenderEngine with fields: {", ".join(f.field_id for f in rich_fields)}',
            'properties': properties,
            'required': [],
            'additionalProperties': False,
        }

    return None


def validate_fields_against_schema(
    content: Any,
    dynamic_schema: Dict[str, Any],
) -> Optional[str]:
    """Validate field names against a dynamic output schema.

    Returns an error string if unknown fields are found, or None if valid.
    """
    if not content or not isinstance(content, dict):
        return None
    schema_props = dynamic_schema.get('properties')
    if (
        not isinstance(schema_props, dict)
        or dynamic_schema.get('additionalProperties') is not False
    ):
        return None

    # For AutoForm: check inside .data wrapper if present
    data = content.get('data')
    field_obj = data if isinstance(data, dict) else content

    valid_set = set(schema_props.keys())
    # Skip metadata keys that the server adds
    bad = [k for k in field_obj if k != 'metadata' and k not in valid_set]
    if not bad:
        return None

    valid_fields = list(schema_props.keys())
    return f'Unknown field(s): {", ".join(bad)}. Valid fields: {", ".join(valid_fields)}'


# ── Task enrichment ──────────────────────────────────────────────────────


def enrich_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a single HITL task with a concrete response template."""
    component_id = task.get('uxComponentId')
    if not component_id:
        return task

    custom = CUSTOMIZATIONS.get(component_id)
    meta = OUTPUT_SCHEMA_META.get(component_id)

    if not custom and not meta:
        return {
            **task,
            '_responseHint': (
                f'Unknown component "{component_id}". Provide only the fields you want to '
                'change as JSON -- the server will merge your changes onto the agent artifact automatically.'
            ),
        }

    # Build template: CUSTOMIZATIONS template wins, then schema example
    template = None
    if custom is not None:
        template = custom.template
    elif meta is not None and meta.examples and len(meta.examples) > 0:
        template = meta.examples[0]

    # Build hint: CUSTOMIZATIONS hint wins, then auto-generate from metadata
    hint = custom.hint if custom else None
    if not hint and meta:
        if meta.display_only:
            hint = 'Display-only component. Server submits empty response automatically.'
        elif meta.merge_with_artifact:
            example_str = json.dumps(meta.examples[0] if meta.examples else {})
            hint = (
                f'Provide only the fields you want to change as JSON -- the server will '
                f'merge your changes onto the agent artifact. Example: {example_str}.'
            )
        elif meta.examples and len(meta.examples) > 1:
            example_lines = '\n'.join(
                f'  {i + 1}. {json.dumps(ex)}' for i, ex in enumerate(meta.examples)
            )
            hint = f'This component accepts multiple response shapes:\n{example_lines}\nCheck _outputSchema for field details.'
        elif meta.examples and len(meta.examples) > 0:
            hint = f'Provide the response as JSON. Example: {json.dumps(meta.examples[0])}.'
        else:
            hint = f'Provide the response as JSON matching the {component_id} output schema.'

    result: Dict[str, Any] = {**task}
    if template is not None:
        result['_responseTemplate'] = template
    if hint:
        result['_responseHint'] = hint
    if meta and meta.json_schema:
        result['_outputSchema'] = meta.json_schema
    if meta and meta.chat_hint:
        result['_chatHint'] = meta.chat_hint
    return result


def enrich_tasks(data: Any) -> Any:
    """Enrich a list of HITL tasks."""
    if not data or not isinstance(data, dict):
        return data

    # GetHitlTask returns { task: {...} }
    if isinstance(data.get('task'), dict):
        return {**data, 'task': enrich_task(data['task'])}

    # ListHitlTasks returns { hitlTasks: [...] }
    hitl_tasks = data.get('hitlTasks')
    if isinstance(hitl_tasks, list):
        return {
            **data,
            'hitlTasks': [enrich_task(t) if isinstance(t, dict) else t for t in hitl_tasks],
        }

    return data


# ── Validate + normalize + auto-fill ─────────────────────────────────────


def format_and_validate(
    ux_component_id: Optional[str],
    raw_content: str,
    agent_artifact: Optional[Dict[str, Any]] = None,
) -> FormatResult:
    """Validate LLM-provided content against the component's output schema.

    Normalize the structure (preprocess) and auto-fill boilerplate.
    """
    try:
        parsed = json.loads(raw_content)
    except (json.JSONDecodeError, ValueError):
        return FormatResult(ok=False, error='content is not valid JSON.')

    if not ux_component_id:
        return FormatResult(ok=True, content=json.dumps(parsed))

    custom = CUSTOMIZATIONS.get(ux_component_id)
    meta = OUTPUT_SCHEMA_META.get(ux_component_id)

    # Display-only components: auto-submit empty response regardless of input.
    # Only use meta.display_only when there's no explicit CUSTOMIZATIONS entry.
    if not custom and meta and meta.display_only:
        return FormatResult(ok=True, content='{}')

    if not custom and not meta:
        # Unknown component -- pass through as-is
        return FormatResult(ok=True, content=json.dumps(parsed))

    # Artifact-diff merge
    should_merge = False
    if custom is not None and custom.merge_with_artifact:
        should_merge = True
    elif meta is not None and meta.merge_with_artifact:
        should_merge = True

    to_preprocess = parsed
    did_merge = bool(should_merge and agent_artifact and isinstance(parsed, dict))
    if did_merge:
        artifact_props = unwrap_artifact_properties(agent_artifact)  # type: ignore[arg-type]
        to_preprocess = merge_artifact_diff(parsed, artifact_props)

    # Preprocess
    if custom and custom.preprocess:
        try:
            normalized = custom.preprocess(to_preprocess, agent_artifact)
        except ValueError as e:
            return FormatResult(ok=False, error=str(e))
    else:
        normalized = to_preprocess

    # Dynamic field validation
    if ux_component_id and agent_artifact:
        dynamic_schema = build_dynamic_output_schema(ux_component_id, agent_artifact)
        if dynamic_schema:
            field_error = validate_fields_against_schema(normalized, dynamic_schema)
            if field_error:
                return FormatResult(ok=False, error=f'{ux_component_id}: {field_error}')

    # When artifact-diff merge is enabled, skip further validation
    if did_merge:
        return FormatResult(ok=True, content=json.dumps(normalized))

    # No Zod in Python -- trust the preprocessed result
    return FormatResult(ok=True, content=json.dumps(normalized))
