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

"""Metadata Model Manager.

Handles business logic for AWS DMS metadata model and schema conversion operations.
"""

from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class MetadataModelManager:
    """Manager for metadata model and schema conversion operations."""

    def __init__(self, client: DMSClient):
        """Initialize metadata model manager."""
        self.client = client
        logger.debug('Initialized MetadataModelManager')

    # Conversion Configuration
    def describe_conversion_configuration(self, arn: str) -> Dict[str, Any]:
        """Get conversion configuration for a migration project."""
        response = self.client.call_api(
            'describe_conversion_configuration', MigrationProjectArn=arn
        )
        return {
            'success': True,
            'data': {'conversion_configuration': response.get('ConversionConfiguration', {})},
            'error': None,
        }

    def modify_conversion_configuration(
        self, arn: str, configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify conversion configuration."""
        response = self.client.call_api(
            'modify_conversion_configuration',
            MigrationProjectArn=arn,
            ConversionConfiguration=configuration,
        )
        return {
            'success': True,
            'data': {
                'conversion_configuration': response.get('ConversionConfiguration', {}),
                'message': 'Conversion configuration modified',
            },
            'error': None,
        }

    # Extension Pack
    def describe_extension_pack_associations(
        self,
        arn: str,
        filters: Optional[List[Dict]] = None,
        marker: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List extension pack associations."""
        params: Dict[str, Any] = {'MigrationProjectArn': arn, 'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker
        response = self.client.call_api('describe_extension_pack_associations', **params)
        associations = response.get('ExtensionPackAssociations', [])
        result = {
            'success': True,
            'data': {'extension_pack_associations': associations, 'count': len(associations)},
            'error': None,
        }
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']
        return result

    def start_extension_pack_association(self, arn: str) -> Dict[str, Any]:
        """Start extension pack association."""
        response = self.client.call_api(
            'start_extension_pack_association', MigrationProjectArn=arn
        )
        return {
            'success': True,
            'data': {
                'extension_pack_association': response.get('ExtensionPackAssociation', {}),
                'message': 'Extension pack association started',
            },
            'error': None,
        }

    # Metadata Model Assessments
    def describe_metadata_model_assessments(
        self,
        arn: str,
        filters: Optional[List[Dict]] = None,
        marker: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List metadata model assessments."""
        params: Dict[str, Any] = {'MigrationProjectArn': arn, 'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker
        response = self.client.call_api('describe_metadata_model_assessments', **params)
        assessments = response.get('MetadataModelAssessments', [])
        result = {
            'success': True,
            'data': {'metadata_model_assessments': assessments, 'count': len(assessments)},
            'error': None,
        }
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']
        return result

    def start_metadata_model_assessment(self, arn: str, selection_rules: str) -> Dict[str, Any]:
        """Start metadata model assessment."""
        response = self.client.call_api(
            'start_metadata_model_assessment',
            MigrationProjectArn=arn,
            SelectionRules=selection_rules,
        )
        return {
            'success': True,
            'data': {
                'metadata_model_assessment': response.get('MetadataModelAssessment', {}),
                'message': 'Metadata model assessment started',
            },
            'error': None,
        }

    # Metadata Model Conversions
    def describe_metadata_model_conversions(
        self,
        arn: str,
        filters: Optional[List[Dict]] = None,
        marker: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List metadata model conversions."""
        params: Dict[str, Any] = {'MigrationProjectArn': arn, 'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker
        response = self.client.call_api('describe_metadata_model_conversions', **params)
        conversions = response.get('MetadataModelConversions', [])
        result = {
            'success': True,
            'data': {'metadata_model_conversions': conversions, 'count': len(conversions)},
            'error': None,
        }
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']
        return result

    def start_metadata_model_conversion(self, arn: str, selection_rules: str) -> Dict[str, Any]:
        """Start metadata model conversion."""
        response = self.client.call_api(
            'start_metadata_model_conversion',
            MigrationProjectArn=arn,
            SelectionRules=selection_rules,
        )
        return {
            'success': True,
            'data': {
                'metadata_model_conversion': response.get('MetadataModelConversion', {}),
                'message': 'Metadata model conversion started',
            },
            'error': None,
        }

    # Metadata Model Exports (Script)
    def describe_metadata_model_exports_as_script(
        self,
        arn: str,
        filters: Optional[List[Dict]] = None,
        marker: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List metadata model script exports."""
        params: Dict[str, Any] = {'MigrationProjectArn': arn, 'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker
        response = self.client.call_api('describe_metadata_model_exports_as_script', **params)
        exports = response.get('MetadataModelExportsAsScript', [])
        result = {
            'success': True,
            'data': {'metadata_model_exports': exports, 'count': len(exports)},
            'error': None,
        }
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']
        return result

    def start_metadata_model_export_as_script(
        self, arn: str, selection_rules: str, origin: str, file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start metadata model export as script."""
        params: Dict[str, Any] = {
            'MigrationProjectArn': arn,
            'SelectionRules': selection_rules,
            'Origin': origin,
        }
        if file_name:
            params['FileName'] = file_name
        response = self.client.call_api('start_metadata_model_export_as_script', **params)
        return {
            'success': True,
            'data': {
                'metadata_model_export': response.get('MetadataModelExportAsScript', {}),
                'message': 'Metadata model export as script started',
            },
            'error': None,
        }

    # Metadata Model Exports (Target)
    def describe_metadata_model_exports_to_target(
        self,
        arn: str,
        filters: Optional[List[Dict]] = None,
        marker: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List metadata model target exports."""
        params: Dict[str, Any] = {'MigrationProjectArn': arn, 'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker
        response = self.client.call_api('describe_metadata_model_exports_to_target', **params)
        exports = response.get('MetadataModelExportsToTarget', [])
        result = {
            'success': True,
            'data': {'metadata_model_exports': exports, 'count': len(exports)},
            'error': None,
        }
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']
        return result

    def start_metadata_model_export_to_target(
        self, arn: str, selection_rules: str, overwrite_extension_pack: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Start metadata model export to target."""
        params: Dict[str, Any] = {'MigrationProjectArn': arn, 'SelectionRules': selection_rules}
        if overwrite_extension_pack is not None:
            params['OverwriteExtensionPack'] = overwrite_extension_pack
        response = self.client.call_api('start_metadata_model_export_to_target', **params)
        return {
            'success': True,
            'data': {
                'metadata_model_export': response.get('MetadataModelExportToTarget', {}),
                'message': 'Metadata model export to target started',
            },
            'error': None,
        }

    # Metadata Model Imports
    def describe_metadata_model_imports(
        self,
        arn: str,
        filters: Optional[List[Dict]] = None,
        marker: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List metadata model imports."""
        params: Dict[str, Any] = {'MigrationProjectArn': arn, 'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker
        response = self.client.call_api('describe_metadata_model_imports', **params)
        imports = response.get('MetadataModelImports', [])
        result = {
            'success': True,
            'data': {'metadata_model_imports': imports, 'count': len(imports)},
            'error': None,
        }
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']
        return result

    def start_metadata_model_import(
        self, arn: str, selection_rules: str, origin: str
    ) -> Dict[str, Any]:
        """Start metadata model import."""
        response = self.client.call_api(
            'start_metadata_model_import',
            MigrationProjectArn=arn,
            SelectionRules=selection_rules,
            Origin=origin,
        )
        return {
            'success': True,
            'data': {
                'metadata_model_import': response.get('MetadataModelImport', {}),
                'message': 'Metadata model import started',
            },
            'error': None,
        }

    # Export Assessment
    def export_metadata_model_assessment(
        self,
        arn: str,
        selection_rules: str,
        file_name: Optional[str] = None,
        assessment_report_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Export metadata model assessment."""
        params: Dict[str, Any] = {'MigrationProjectArn': arn, 'SelectionRules': selection_rules}
        if file_name:
            params['FileName'] = file_name
        if assessment_report_types:
            params['AssessmentReportTypes'] = assessment_report_types
        response = self.client.call_api('export_metadata_model_assessment', **params)
        return {
            'success': True,
            'data': {
                'metadata_model_assessment_export': response.get(
                    'MetadataModelAssessmentExport', {}
                ),
                'message': 'Metadata model assessment exported',
            },
            'error': None,
        }
