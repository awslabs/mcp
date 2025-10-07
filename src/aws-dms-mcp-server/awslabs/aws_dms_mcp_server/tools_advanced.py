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

"""Advanced DMS Tools - Metadata Model, Fleet Advisor, and Recommendations.

This module contains the MCP tool definitions for advanced DMS features.
"""

from .exceptions.dms_exceptions import DMSMCPException
from .utils.response_formatter import ResponseFormatter
from typing import Any, Dict, List, Optional


# Note: This module is imported and tools are registered in server.py


def register_metadata_model_tools(mcp, config, metadata_model_manager):
    """Register all metadata model operation tools."""

    @mcp.tool()
    def describe_conversion_configuration(migration_project_arn: str) -> Dict[str, Any]:
        """Get conversion configuration for a migration project."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('Operation requires write access')
            )
        try:
            return metadata_model_manager.describe_conversion_configuration(
                arn=migration_project_arn
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def modify_conversion_configuration(
        migration_project_arn: str, conversion_configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify conversion configuration."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('modify_conversion_configuration not available in read-only mode')
            )
        try:
            return metadata_model_manager.modify_conversion_configuration(
                arn=migration_project_arn, configuration=conversion_configuration
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_extension_pack_associations(
        migration_project_arn: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List extension pack associations."""
        try:
            return metadata_model_manager.describe_extension_pack_associations(
                arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def start_extension_pack_association(migration_project_arn: str) -> Dict[str, Any]:
        """Start extension pack association."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('start_extension_pack_association not available in read-only mode')
            )
        try:
            return metadata_model_manager.start_extension_pack_association(
                arn=migration_project_arn
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_metadata_model_assessments(
        migration_project_arn: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List metadata model assessments."""
        try:
            return metadata_model_manager.describe_metadata_model_assessments(
                arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def start_metadata_model_assessment(
        migration_project_arn: str, selection_rules: str
    ) -> Dict[str, Any]:
        """Start metadata model assessment."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('start_metadata_model_assessment not available in read-only mode')
            )
        try:
            return metadata_model_manager.start_metadata_model_assessment(
                arn=migration_project_arn, selection_rules=selection_rules
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_metadata_model_conversions(
        migration_project_arn: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List metadata model conversions."""
        try:
            return metadata_model_manager.describe_metadata_model_conversions(
                arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def start_metadata_model_conversion(
        migration_project_arn: str, selection_rules: str
    ) -> Dict[str, Any]:
        """Start metadata model conversion."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('start_metadata_model_conversion not available in read-only mode')
            )
        try:
            return metadata_model_manager.start_metadata_model_conversion(
                arn=migration_project_arn, selection_rules=selection_rules
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_metadata_model_exports_as_script(
        migration_project_arn: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List metadata model script exports."""
        try:
            return metadata_model_manager.describe_metadata_model_exports_as_script(
                arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def start_metadata_model_export_as_script(
        migration_project_arn: str,
        selection_rules: str,
        origin: str,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start metadata model export as script."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException(
                    'start_metadata_model_export_as_script not available in read-only mode'
                )
            )
        try:
            return metadata_model_manager.start_metadata_model_export_as_script(
                arn=migration_project_arn,
                selection_rules=selection_rules,
                origin=origin,
                file_name=file_name,
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_metadata_model_exports_to_target(
        migration_project_arn: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List metadata model target exports."""
        try:
            return metadata_model_manager.describe_metadata_model_exports_to_target(
                arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def start_metadata_model_export_to_target(
        migration_project_arn: str,
        selection_rules: str,
        overwrite_extension_pack: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Start metadata model export to target."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException(
                    'start_metadata_model_export_to_target not available in read-only mode'
                )
            )
        try:
            return metadata_model_manager.start_metadata_model_export_to_target(
                arn=migration_project_arn,
                selection_rules=selection_rules,
                overwrite_extension_pack=overwrite_extension_pack,
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_metadata_model_imports(
        migration_project_arn: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List metadata model imports."""
        try:
            return metadata_model_manager.describe_metadata_model_imports(
                arn=migration_project_arn, filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def start_metadata_model_import(
        migration_project_arn: str, selection_rules: str, origin: str
    ) -> Dict[str, Any]:
        """Start metadata model import."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('start_metadata_model_import not available in read-only mode')
            )
        try:
            return metadata_model_manager.start_metadata_model_import(
                arn=migration_project_arn, selection_rules=selection_rules, origin=origin
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def export_metadata_model_assessment(
        migration_project_arn: str,
        selection_rules: str,
        file_name: Optional[str] = None,
        assessment_report_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Export metadata model assessment."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('export_metadata_model_assessment not available in read-only mode')
            )
        try:
            return metadata_model_manager.export_metadata_model_assessment(
                arn=migration_project_arn,
                selection_rules=selection_rules,
                file_name=file_name,
                assessment_report_types=assessment_report_types,
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)


def register_fleet_advisor_tools(mcp, config, fleet_advisor_manager):
    """Register all Fleet Advisor operation tools."""

    @mcp.tool()
    def create_fleet_advisor_collector(
        collector_name: str, description: str, service_access_role_arn: str, s3_bucket_name: str
    ) -> Dict[str, Any]:
        """Create Fleet Advisor collector."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('create_fleet_advisor_collector not available in read-only mode')
            )
        try:
            return fleet_advisor_manager.create_collector(
                name=collector_name,
                description=description,
                service_access_role_arn=service_access_role_arn,
                s3_bucket_name=s3_bucket_name,
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def delete_fleet_advisor_collector(collector_referenced_id: str) -> Dict[str, Any]:
        """Delete Fleet Advisor collector."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('delete_fleet_advisor_collector not available in read-only mode')
            )
        try:
            return fleet_advisor_manager.delete_collector(ref=collector_referenced_id)
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_fleet_advisor_collectors(
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List Fleet Advisor collectors."""
        try:
            return fleet_advisor_manager.list_collectors(
                filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def delete_fleet_advisor_databases(database_ids: List[str]) -> Dict[str, Any]:
        """Delete Fleet Advisor databases."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('delete_fleet_advisor_databases not available in read-only mode')
            )
        try:
            return fleet_advisor_manager.delete_databases(database_ids=database_ids)
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_fleet_advisor_databases(
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List Fleet Advisor databases."""
        try:
            return fleet_advisor_manager.list_databases(
                filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_fleet_advisor_lsa_analysis(
        max_results: int = 100, marker: Optional[str] = None
    ) -> Dict[str, Any]:
        """Describe Fleet Advisor LSA analysis."""
        try:
            return fleet_advisor_manager.describe_lsa_analysis(
                max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def run_fleet_advisor_lsa_analysis() -> Dict[str, Any]:
        """Run Fleet Advisor LSA analysis."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('run_fleet_advisor_lsa_analysis not available in read-only mode')
            )
        try:
            return fleet_advisor_manager.run_lsa_analysis()
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_fleet_advisor_schema_object_summary(
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Describe Fleet Advisor schema object summary."""
        try:
            return fleet_advisor_manager.describe_schema_object_summary(
                filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_fleet_advisor_schemas(
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List Fleet Advisor schemas."""
        try:
            return fleet_advisor_manager.list_schemas(
                filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)


def register_recommendation_tools(mcp, config, recommendation_manager):
    """Register all recommendation operation tools."""

    @mcp.tool()
    def describe_recommendations(
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List migration recommendations."""
        try:
            return recommendation_manager.list_recommendations(
                filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def describe_recommendation_limitations(
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List recommendation limitations."""
        try:
            return recommendation_manager.list_recommendation_limitations(
                filters=filters, max_results=max_results, marker=marker
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def start_recommendations(database_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Start generating recommendations."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('start_recommendations not available in read-only mode')
            )
        try:
            return recommendation_manager.start_recommendations(
                database_id=database_id, settings=settings
            )
        except Exception as e:
            return ResponseFormatter.format_error(e)

    @mcp.tool()
    def batch_start_recommendations(data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Batch start recommendations for multiple databases."""
        if config.read_only_mode:
            return ResponseFormatter.format_error(
                DMSMCPException('batch_start_recommendations not available in read-only mode')
            )
        try:
            return recommendation_manager.batch_start_recommendations(data=data)
        except Exception as e:
            return ResponseFormatter.format_error(e)
