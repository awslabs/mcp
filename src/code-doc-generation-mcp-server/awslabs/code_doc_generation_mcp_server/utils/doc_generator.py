# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Document generation module for handling document creation workflow."""

from awslabs.code_doc_generation_mcp_server.utils.models import (
    DocumentationContext,
    DocumentationPlan,
    DocumentSection,
    DocumentSpec,
    ProjectAnalysis,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pathlib import Path
from typing import List, Optional


class DocumentGenerator:
    """Handles document generation workflow."""

    async def generate_docs(
        self, plan: DocumentationPlan, context: DocumentationContext, ctx: Optional[Context] = None
    ) -> List[str]:
        """Generate all documentation files based on the plan."""
        # ctx parameter is kept for logging purposes but not stored in context
        generated_files = []

        # Generate README first
        readme_spec = next((doc for doc in plan.docs_outline if doc.name == 'README.md'), None)
        if readme_spec:
            content = await self._generate_content(readme_spec, context)
            path = Path(context.repomix_path) / readme_spec.name
            await self._write_file(path, content)
            generated_files.append(str(path))

        # Generate other documentation files
        for doc_spec in plan.docs_outline:
            if doc_spec.name != 'README.md':
                content = await self._generate_content(doc_spec, context)
                path = Path(context.repomix_path) / doc_spec.name
                await self._write_file(path, content)
                generated_files.append(str(path))

        return generated_files

    async def _write_file(self, path: Path, content: str) -> None:
        """Write content to file, creating directories if needed."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            logger.info(f'Generated documentation file: {path}')
        except Exception as e:
            logger.error(f'Error writing file {path}: {e}', message=f'Error writing file {path}: {e}')
            raise

    def _get_component_summary(self, analysis: ProjectAnalysis) -> str:
        """Get a text summary of components for placeholder text."""
        summary = []
        if analysis and analysis.frontend:
            summary.append('- Frontend')
            if isinstance(analysis.frontend, dict) and analysis.frontend.get('framework'):
                summary[-1] += f' ({analysis.frontend["framework"]})'

        if analysis and analysis.backend:
            summary.append('- Backend')
            if isinstance(analysis.backend, dict):
                if analysis.backend.get('framework'):
                    summary[-1] += f' ({analysis.backend["framework"]})'
                if analysis.backend.get('database'):
                    db_value = analysis.backend['database']
                    if isinstance(db_value, dict) and db_value.get('type'):
                        summary.append(f'  - Database: {db_value.get("type")}')
                    else:
                        # Handle case where database is a string instead of dict
                        summary.append(f'  - Database: {db_value}')

        if analysis and analysis.apis:
            summary.append('- API Layer')
            if isinstance(analysis.apis, dict):
                api_type = analysis.apis.get('type', 'Unknown')
                summary[-1] += f' ({api_type})'

        return '\n'.join(summary)

    def _get_key_components(self, analysis: ProjectAnalysis) -> List[str]:
        """Get list of key components for overview."""
        components = []
        if analysis and analysis.frontend:
            components.append('Frontend')
        if analysis and analysis.backend:
            components.append('Backend')
        if analysis and analysis.apis:
            components.append('API')
        return components

    def _generate_diagram_placeholder(self, diagram_type: str, analysis: ProjectAnalysis) -> str:
        """Generate a placeholder for diagrams that will be created with AWS Diagram MCP Server.

        This method creates a simple placeholder with instructions for the MCP client to replace it
        with a proper diagram generated using the AWS Diagram MCP Server.

        Args:
            diagram_type: Type of diagram to generate ('architecture', 'overview', or 'dataflow')
            analysis: Project analysis data

        Returns:
            Markdown placeholder with instructions for using AWS Diagram MCP Server
        """
        if diagram_type == 'architecture':
            return (
                '<!-- PLACEHOLDER: Replace this with an AWS architecture diagram generated using AWS Diagram MCP Server -->\n'
                '## AWS Architecture\n\n'
                '```\n'
                'This is a placeholder for the AWS architecture diagram.\n'
                'Use the awslabs.aws-diagram-mcp-server to generate a proper AWS diagram showing:\n'
                + self._get_component_summary(analysis)
                + '```'
            )
        elif diagram_type == 'dataflow':
            return (
                '<!-- PLACEHOLDER: Replace this with a data flow diagram generated using AWS Diagram MCP Server -->\n'
                '## Data Flow Diagram\n\n'
                '```\n'
                'This is a placeholder for the data flow diagram.\n'
                'Use the awslabs.aws-diagram-mcp-server to generate a proper data flow diagram showing how data moves through the system.\n'
                + self._get_component_summary(analysis)
                + '```'
            )
        else:  # overview
            return (
                '<!-- PLACEHOLDER: Replace this with an AWS architecture diagram generated using AWS Diagram MCP Server -->\n'
                '## System Architecture\n\n'
                '```\n'
                f'Project Type: {analysis and analysis.project_type or "unknown"}\n'
                'Key Components: ' + ', '.join(self._get_key_components(analysis) or []) + '\n'
                'Generate an AWS architecture diagram using awslabs.aws-diagram-mcp-server to visualize this structure.\n'
                '```'
            )

    async def _generate_content(
        self, doc_spec: DocumentSpec, context: DocumentationContext
    ) -> str:
        """Generate document structure with diagrams when appropriate."""
        content = []

        # Define add_section function at the beginning of the method
        def add_section(section: DocumentSection, level: int) -> None:
            """Add a section heading at the specified level."""
            # Add heading
            heading = '#' * level
            content.append(f'{heading} {section.title}\n')

            # Add section content if present
            if section.content:
                content.append(f'{section.content}\n')
            else:
                # Add prompt for MCP client to fill this section
                content.append('<!-- MCP Client: Write concise content for this section -->\n')

            # Add subsections
            if section.subsections is not None:
                for subsection in section.subsections:
                    add_section(subsection, level + 1)

        # Add header comment to remind the MCP client to fill content
        content.append('<!--')
        content.append(
            'IMPORTANT: The MCP client must fill in the content for each section below!'
        )
        content.append('1. Write concise content for each section')
        content.append('2. Do not leave any sections empty')
        content.append('3. Use your analysis to create accurate content')
        content.append(
            '4. If relevant, use AWS Diagram MCP Server to generate AWS architecture diagram in README.md'
        )
        content.append(
            '5. If relevant, use AWS Diagram MCP Server to generate data flow chart in BACKEND.md'
        )
        content.append('-->\n')

        # Generate diagrams based on document type
        if context.analysis_result:
            # Add diagram instructions for README.md Architecture section
            if doc_spec.name == 'README.md' and 'Architecture' in [
                section.title for section in doc_spec.sections
            ]:
                # Add detailed instructions for MCP client to use AWS Diagram MCP Server
                content.append(
                    '<!-- MCP Client: Generate an AWS architecture diagram using AWS Diagram MCP Server'
                )
                content.append(
                    'This should be an AWS architecture diagram showing the components and their relationships.'
                )
                content.append('Use the following example code as a starting point:')
                content.append('```python')
                content.append('from diagrams import Diagram, Cluster, Edge')
                content.append('from diagrams.aws.compute import Lambda')
                content.append('from diagrams.aws.database import Dynamodb')
                content.append('from diagrams.aws.network import APIGateway')
                content.append('from diagrams.aws.ml import Textract')
                content.append('from diagrams.aws.security import Cognito')
                content.append('from diagrams.custom import Custom')
                content.append('# How to Use AWS ML Services - examples')
                content.append('textract = Textract("Amazon Textract")')
                content.append(
                    '# You need to use the built-in Bedrock helper function for Bedrock'
                )
                content.append('bedrock = Bedrock("Amazon Bedrock")')
                content.append('')
                content.append('# Get the current workspace directory')
                content.append('workspace_dir = "project_directory"')
                content.append('')
                content.append('# Create an AWS architecture diagram')
                content.append(
                    'with Diagram("AWS Architecture", show=False, filename="aws_architecture_diagram"):'
                )

                # Add dynamic content based on project analysis
                if context.analysis_result and context.analysis_result.frontend:
                    content.append('    with Cluster("Frontend"):')
                    if isinstance(
                        context.analysis_result.frontend, dict
                    ) and context.analysis_result.frontend.get('framework'):
                        content.append(
                            f'        ui = Custom("{context.analysis_result.frontend.get("framework")} Frontend")'
                        )
                    else:
                        content.append('        ui = Custom("Frontend")')

                if context.analysis_result and context.analysis_result.backend:
                    content.append('    with Cluster("Backend"):')
                    # Use AWS-specific components when appropriate
                    content.append('        api_gateway = APIGateway("API Gateway")')
                    if isinstance(
                        context.analysis_result.backend, dict
                    ) and context.analysis_result.backend.get('framework'):
                        if (
                            'lambda'
                            in str(context.analysis_result.backend.get('framework', '')).lower()
                        ):
                            content.append('        lambda_function = Lambda("Lambda Function")')
                        else:
                            content.append(
                                f'        backend = Custom("{context.analysis_result.backend.get("framework")} Backend")'
                            )
                    else:
                        content.append('        backend = Custom("Backend Service")')

                    if isinstance(
                        context.analysis_result.backend, dict
                    ) and context.analysis_result.backend.get('database'):
                        db_value = context.analysis_result.backend.get('database')
                        if isinstance(db_value, dict) and db_value.get('type'):
                            db_type = db_value.get('type')
                        else:
                            # Handle case where database is a string
                            db_type = str(db_value)

                        if 'dynamo' in str(db_type).lower():
                            content.append('        db = DynamoDB("DynamoDB")')
                        else:
                            content.append(f'        db = Custom("{db_type}")')

                # Add connections
                if (
                    context.analysis_result
                    and context.analysis_result.frontend
                    and context.analysis_result.backend
                ):
                    content.append('    ui >> api_gateway')
                    content.append('    api_gateway >> backend')
                    if isinstance(
                        context.analysis_result.backend, dict
                    ) and context.analysis_result.backend.get('database'):
                        content.append('    backend >> db')

                content.append('    # Add authentication if needed')
                content.append('    auth = Cognito("Authentication")')
                content.append('    ui >> auth')
                content.append('')
                content.append(
                    'After generating the AWS architecture diagram with the AWS Diagram MCP Server, replace the image reference below with the path to the generated diagram.'
                )
                content.append('-->')

                # Add placeholder diagram markdown
                placeholder = self._generate_diagram_placeholder(
                    'overview', context.analysis_result
                )
                content.append(f'\n{placeholder}\n')
                content.append(
                    '<!-- Describe what this AWS architecture diagram shows below -->\n'
                )

            # Add diagram instructions for BACKEND.md Data Flow section
            elif doc_spec.name == 'BACKEND.md' and 'Data Flow' in [
                section.title for section in doc_spec.sections
            ]:
                # Find the Data Flow section index
                data_flow_index = next(
                    (
                        i
                        for i, section in enumerate(doc_spec.sections)
                        if section.title == 'Data Flow'
                    ),
                    -1,
                )

                if data_flow_index >= 0:
                    # Process sections up to Data Flow
                    for i in range(data_flow_index):
                        add_section(doc_spec.sections[i], doc_spec.sections[i].level)

                    # Add Data Flow section with diagram instructions
                    heading = '#' * doc_spec.sections[data_flow_index].level
                    content.append(f'{heading} {doc_spec.sections[data_flow_index].title}\n')

                    # Add detailed instructions for MCP client to use AWS Diagram MCP Server for data flow diagram
                    content.append(
                        '<!-- MCP Client: Generate a data flow diagram using AWS Diagram MCP Server'
                    )
                    content.append(
                        'This should be a diagram showing how data flows through the system components.'
                    )
                    content.append('# Get the current workspace directory')
                    content.append('workspace_dir = "project_directory"')
                    content.append('')
                    content.append('# Create a data flow diagram')
                    content.append(
                        'with Diagram("Data Flow", show=False, filename="data_flow_diagram"):'
                    )

                    # Add dynamic content based on project analysis
                    if context.analysis_result and context.analysis_result.backend:
                        content.append('    # Define data sources')
                        content.append('    api_gateway = APIGateway("API Gateway")')

                        if isinstance(context.analysis_result.backend, dict):
                            # Add processing components
                            content.append('    # Define processing components')
                            if (
                                'lambda'
                                in str(
                                    context.analysis_result.backend.get('framework', '')
                                ).lower()
                            ):
                                content.append('    processor = Lambda("Lambda Function")')
                            else:
                                content.append(
                                    f'    processor = Custom("{context.analysis_result.backend.get("framework", "Backend")} Service")'
                                )

                            # Add data stores
                            content.append('    # Define data stores')
                            if context.analysis_result.backend.get('database'):
                                db_value = context.analysis_result.backend.get('database')
                                if isinstance(db_value, dict) and db_value.get('type'):
                                    db_type = db_value.get('type')
                                else:
                                    # Handle case where database is a string
                                    db_type = str(db_value)

                                if 'dynamo' in str(db_type).lower():
                                    content.append('    data_store = DynamoDB("DynamoDB")')
                                else:
                                    content.append(f'    data_store = Custom("{db_type}")')

                            # Add messaging if applicable
                            content.append('    # Add messaging components if applicable')
                            content.append('    queue = SQS("Message Queue")')
                            content.append('    topic = SNS("Notification Topic")')

                    # Add data flow connections
                    content.append('    # Show data flow with labeled edges')
                    content.append('    api_gateway >> Edge(label="JSON request") >> processor')
                    content.append('    processor >> Edge(label="Query/Write") >> data_store')
                    content.append('    processor >> Edge(label="Publish event") >> topic')
                    content.append('    topic >> Edge(label="Notify") >> queue')

                    content.append('```')
                    content.append('')
                    content.append(
                        'After generating the data flow diagram with the AWS Diagram MCP Server, replace the image reference below with the path to the generated diagram.'
                    )
                    content.append('-->')

                    # Add placeholder diagram markdown
                    placeholder = self._generate_diagram_placeholder(
                        'dataflow', context.analysis_result
                    )
                    content.append(f'\n{placeholder}\n')
                    content.append('<!-- Describe what this data flow diagram shows below -->\n')

                    # Add any subsections
                    if doc_spec.sections[data_flow_index].subsections is not None:
                        for subsection in doc_spec.sections[data_flow_index].subsections:
                            add_section(subsection, doc_spec.sections[data_flow_index].level + 1)

                    # Process remaining sections
                    for i in range(data_flow_index + 1, len(doc_spec.sections)):
                        add_section(doc_spec.sections[i], doc_spec.sections[i].level)

                    # Return the content since we've processed all sections manually
                    return '\n'.join(content)

        # Process all sections (unless we've already processed them for BACKEND.md)
        if not (
            doc_spec.name == 'BACKEND.md'
            and 'Data Flow' in [section.title for section in doc_spec.sections]
        ):
            for section in doc_spec.sections:
                add_section(section, section.level)

        return '\n'.join(content)
