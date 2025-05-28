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

"""awslabs code-doc-gen MCP Server implementation.

Key capabilities:
- Analyzes repository structure and code patterns
- Generates comprehensive documentation based on project type
- Creates architecture diagrams automatically
- Supports multiple documentation types (API, Backend, Frontend, etc.)
- Integrates with diagrams-expert for visual documentation
"""

import subprocess
import sys
import time
from awslabs.code_doc_gen_mcp_server.utils.doc_generator import DocumentGenerator
from awslabs.code_doc_gen_mcp_server.utils.models import (
    DocStructure,
    DocumentationContext,
    DocumentationPlan,
    GeneratedDocument,
    ProjectAnalysis,
)
from awslabs.code_doc_gen_mcp_server.utils.repomix_manager import RepomixManager
from awslabs.code_doc_gen_mcp_server.utils.templates import (
    create_doc_from_template,
    get_template_for_file,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional


logger.remove()  # Remove default handler
logger.configure(
    handlers=[
        {'sink': sys.stderr, 'level': 'INFO'},
    ]
)


class _ProjectInfo(BaseModel):
    """Project information model.

    Contains basic information about the project like name and path.

    Note: This is an internal model not intended for direct client use.
    """

    name: str = Field(..., description='Project name')
    path: str = Field(..., description='Project path')


class _AnalysisResult(BaseModel):
    """Analysis result with project info and repomix output.

    Contains the output paths, project information, and repomix output from the repository analysis.

    Note: This is an internal model not intended for direct client use.
    """

    output_dir: str = Field(..., description='Output directory')
    repomix_output: str = Field(..., description='Raw repomix output')
    project_info: _ProjectInfo = Field(..., description='Project information')
    directory_structure: Optional[str] = Field(None, description='Extracted directory structure')


def create_documentation_context(
    project_root: str, analysis: Optional[ProjectAnalysis] = None
) -> DocumentationContext:
    """Create an initial DocumentationContext from a project root path.

    This helper function simplifies the creation of a DocumentationContext
    by automatically setting up the basic fields from just the project root path.

    Args:
        project_root: Path to the code repository
        analysis: Optional ProjectAnalysis to include in the context

    Returns:
        A DocumentationContext with basic fields initialized
    """
    project_name = Path(project_root).name
    context = DocumentationContext(
        project_name=project_name,
        working_dir=project_root,
        repomix_path=f'{project_root}/generated-docs',
        status='initialized',
        current_step='analysis',
        analysis_result=analysis,
    )

    return context


mcp = FastMCP(
    'awslabs.code-doc-gen-mcp-server',
    instructions="""Use this server to generate comprehensive code documentation.

WORKFLOW:
1. prepare_repository:
- Extracts directory structure from the repository
- Returns empty ProjectAnalysis template
- Provides directory structure in file_structure["directory_structure"]
- Provides repository statistics in file_structure["statistics"]
- You analyze the directory structure to identify key files

2. Use read_file:
- After analyzing the directory structure, use read_file to access specific files
- Examine package.json, README.md, or other important files you identify
- Build your understanding of the project from these key files
- If you detect AWS CDK or Terraform code, set has_infrastructure_as_code=True

3. create_context:
- Creates a DocumentationContext from your completed ProjectAnalysis
- This context is needed for the next steps

4. plan_documentation:
- Takes the DocumentationContext with your analysis
- Determines what documentation types are needed
- Returns a DocumentationPlan with appropriate sections

5. generate_documentation:
- Takes the DocumentationPlan and DocumentationContext
- Creates document structure with empty sections
- Returns documents that YOU MUST FILL with content
- YOU are responsible for writing all document content

IMPORTANT:
- prepare_repository provides directory structure in file_structure["directory_structure"] and statistics in file_structure["statistics"]
- You must use read_file to examine key files you identify from the structure
- You must analyze the files to fill out the ProjectAnalysis fields
- Use create_context to create a DocumentationContext from your analysis
- When generate_documentation returns documents, YOU MUST:
  1. Write detailed content for each section
  2. Include code examples and explanations
  3. Fill in ALL empty sections
  4. Ensure comprehensive coverage
  5. Use your analysis to create accurate content

RECOMMENDED COMPANION MCP SERVERS:
- awslabs.aws-diagram-mcp-server: For generating architecture diagrams

This companion server is not required but will enhance the documentation with visual diagrams.""",
    dependencies=['pydantic', 'loguru', 'repomix'],
)


@mcp.tool(name='prepare_repository')
async def prepare_repository(
    project_root: str = Field(..., description='Path to the code repository'),
    ctx: Optional[Context] = None,
) -> ProjectAnalysis:
    """Prepare repository for the MCP client's analysis.

    This tool:
    1. Extracts directory structure from the repository
    2. Returns an EMPTY ProjectAnalysis for you to fill out
    3. Provides directory structure in file_structure["directory_structure"]
    4. Provides repository statistics in file_structure["statistics"] (file count, character count, etc.)

    You should:
    1. Review the directory structure in file_structure["directory_structure"]
    2. Use read_file to examine key files you identify from the structure
    3. Fill out the empty fields in ProjectAnalysis based on your analysis
    4. Set has_infrastructure_as_code=True if you detect CDK, Terraform, or other infrastructure as code
    5. Use create_context to create a DocumentationContext from your analysis
    6. Use the DocumentationContext with plan_documentation

    NOTE: This tool does NOT analyze the code - that's your job!
    The tool only extracts the directory structure and statistics to help you identify important files.
    """
    try:
        # Set up output paths
        project_path = Path(project_root)
        output_path = project_path / 'generated-docs'

        # Initialize RepomixManager and prepare repository
        repomix = RepomixManager()
        raw_analysis = await repomix.prepare_repository(project_root, output_path, ctx)

        # Get project structure for analysis
        repomix_output = await _analyze_project_structure(raw_analysis, output_path, ctx)
        logger.info('Retrieved project structure for analysis')

        # Extract directory structure with fallbacks
        dir_structure = repomix_output.get('directory_structure')

        # Try fallback to raw_analysis if not found
        if dir_structure is None and 'directory_structure' in raw_analysis:
            dir_structure = raw_analysis['directory_structure']

        # Log basic info about structure
        if dir_structure:
            logger.info(f'Found directory structure ({len(dir_structure)} chars)')
        else:
            logger.warning('Directory structure not found in output')

        # Get statistics from raw analysis
        stats = raw_analysis.get('metadata', {}).get('summary', {})

        # Return ProjectAnalysis with directory structure and statistics for MCP client to analyze
        return ProjectAnalysis(
            project_type='',  # The MCP client will fill this
            features=[],  # The MCP client will fill this
            file_structure={  # Basic structure to start
                'root': [project_root],
                'directory_structure': dir_structure,  # Use our local variable with logging
                'statistics': stats,  # Include statistics from repomix
            },
            dependencies={},  # The MCP client will fill this
            primary_languages=[],  # The MCP client will fill this
            apis=None,  # Optional - The MCP client will fill if found
            backend=None,  # Optional - The MCP client will fill if found
            frontend=None,  # Optional - The MCP client will fill if found
            has_infrastructure_as_code=False,  # The MCP client will set to True if CDK, Terraform, or other IaC is detected
        )

    except subprocess.CalledProcessError as e:
        error_msg = f'Repomix preparation failed: {e.stderr}'
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        raise
    except Exception as e:
        error_msg = f'Error preparing repository: {e}'
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        raise


async def _analyze_project_structure(
    raw_analysis: dict, docs_dir: Path, ctx: Optional[Context] = None
) -> dict:
    """Prepares project structure for inclusion in ProjectAnalysis.

    This simplified function:
    1. Gets the directory structure from the raw analysis
    2. Packages it with project info and metadata
    3. Returns a dict containing the directory structure and metadata

    The directory_structure will be included in ProjectAnalysis.file_structure["directory_structure"]
    for the MCP client to understand the project organization and identify important files.

    Note: This is an internal function not intended for direct client use.
    """
    # Get directory structure directly from raw_analysis
    directory_structure = raw_analysis.get('directory_structure')

    # Check if we should fall back to file_structure for directory structure
    if not directory_structure and 'file_structure' in raw_analysis:
        if (
            isinstance(raw_analysis['file_structure'], dict)
            and 'directory_structure' in raw_analysis['file_structure']
        ):
            directory_structure = raw_analysis['file_structure']['directory_structure']

    # Log whether we found directory_structure
    if directory_structure:
        logger.info(
            f'Directory structure found in raw_analysis (length: {len(directory_structure)})'
        )
    else:
        logger.warning('Directory structure not found in raw_analysis')

    # Return simplified analysis data
    return {
        'project_info': raw_analysis['project_info'],
        'metadata': raw_analysis.get('metadata', {}),
        'output_dir': str(docs_dir),
        'directory_structure': directory_structure,
    }


@mcp.tool(name='create_context')
async def create_context(
    project_root: str = Field(..., description='Path to the code repository'),
    analysis: ProjectAnalysis = Field(
        ..., description='Completed ProjectAnalysis from prepare_repository'
    ),
    ctx: Optional[Context] = None,
) -> DocumentationContext:
    """Create a DocumentationContext from a ProjectAnalysis.

    This tool simplifies the creation of a DocumentationContext for use with
    plan_documentation and generate_documentation tools.

    Args:
        project_root: Path to the code repository
        analysis: Completed ProjectAnalysis from prepare_repository
        ctx: Optional MCP context for logging and progress reporting

    Returns:
        A DocumentationContext ready for use with other tools
    """
    start_time = time.time()
    logger.debug(f'CONTEXT TIMING: Starting create_context at {start_time}')

    try:
        # Create context object
        doc_context = create_documentation_context(project_root, analysis)

        end_time = time.time()
        duration = end_time - start_time
        logger.debug(f'CONTEXT TIMING: Finished create_context in {duration:.2f}s')

        if ctx:
            await ctx.info(f'Created documentation context in {duration:.2f}s')

        return doc_context
    except Exception as e:
        end_time = time.time()
        logger.error(
            f'CONTEXT TIMING: Failed create_context after {end_time - start_time:.2f}s with error: {str(e)}'
        )
        if ctx:
            await ctx.error(f'Error creating documentation context: {str(e)}')
        raise


@mcp.tool(name='plan_documentation')
async def plan_documentation(
    doc_context: DocumentationContext,
    ctx: Optional[Context] = None,
) -> DocumentationPlan:
    """Third step: Create documentation plan using analysis.

    Using your analysis from prepare_repository and the DocumentationContext from create_context:
    1. Review the ProjectAnalysis in doc_context containing:
       - Project type and purpose
       - Key features and capabilities
       - Programming languages and dependencies
       - APIs and interfaces
    2. Determine what documentation types are needed
    3. Create appropriate documentation structure
    4. Return documentation plan
    """
    start_time = time.time()
    logger.debug(f'PLAN TIMING: Starting plan_documentation at {start_time}')

    try:
        # Update context status
        doc_context.status = 'ready_to_plan'
        doc_context.current_step = 'planning'

        # Collect all needed documents
        needed_docs = ['README.md']  # Always include README

        # Add component-specific docs
        if doc_context.analysis_result and doc_context.analysis_result.backend:
            needed_docs.append('BACKEND.md')
        if doc_context.analysis_result and doc_context.analysis_result.frontend:
            needed_docs.append('FRONTEND.md')
        if doc_context.analysis_result and doc_context.analysis_result.apis:
            needed_docs.append('API.md')

        # Add deployment docs for projects with infrastructure as code
        if doc_context.analysis_result and doc_context.analysis_result.has_infrastructure_as_code:
            needed_docs.append('DEPLOYMENT_GUIDE.md')

        # Create both tree and outline from needed docs
        doc_tree = {
            'root': needed_docs
        }  # Use 'root' instead of 'docs' to avoid creating empty directory
        docs_outline = []

        # Create DocumentSpec for each needed doc using template mapping
        for doc_name in needed_docs:
            template_type = get_template_for_file(doc_name)
            docs_outline.append(create_doc_from_template(template_type, doc_name))

        # Log what documentation will be generated
        if ctx:
            await ctx.info(f'Creating documentation structure with {len(docs_outline)} documents:')
            for doc in docs_outline:
                await ctx.info(f'- {doc.name} ({doc.type})')

        return DocumentationPlan(
            structure=DocStructure(root_doc='README.md', doc_tree=doc_tree),
            docs_outline=docs_outline,
        )

    except Exception as e:
        error_msg = f'Error in plan_documentation: {str(e)}'
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool(name='generate_documentation')
async def generate_documentation(
    plan: DocumentationPlan,
    doc_context: DocumentationContext,
    ctx: Optional[Context] = None,
) -> List[GeneratedDocument]:
    """Final step: Generate documentation content.

    Using your analysis and documentation plan:
    1. Generate document structures with empty sections
    2. YOU (MCP Client) MUST then:
       - Write detailed content for each section
       - Include relevant code examples and explanations
       - Fill in ALL empty sections with comprehensive content
       - Cover all aspects:
         * Project setup and installation
         * Architecture and design
         * Features and capabilities
         * APIs and interfaces (if any)
         * Dependencies and requirements
    3. Return document structures for you to fill with content

    IMPORTANT: When you receive the generated documents, it is YOUR responsibility
    to write comprehensive content for each section. Do not leave sections empty
    or wait for further instructions - YOU must fill them in!
    """
    start_time = time.time()
    logger.debug(f'GENERATE TIMING: Starting generate_documentation at {start_time}')

    try:
        # Update context status
        doc_context.status = 'ready_to_generate'
        doc_context.current_step = 'generation'

        # Log MCP context information
        if ctx:
            await ctx.error(f'MCP context being passed: {ctx is not None}')

        # Initialize document generator for file operations
        generator = DocumentGenerator()

        # Log generation start
        if ctx:
            await ctx.error(f'Preparing documentation structure for {doc_context.project_name}')
            await ctx.error(
                f'Project type: {doc_context.analysis_result and doc_context.analysis_result.project_type or "unknown"}'
            )

        # Generate documentation files with diagrams
        generated_files = await generator.generate_docs(plan, doc_context)

        # Return document objects with messages for the MCP client
        generated_docs = []
        for file_path in generated_files:
            path = Path(file_path)
            doc_type = 'docs' if path.name != 'README.md' else 'readme'
            message = f'Please fill the {path.name} with comprehensive content based on the project analysis. Include detailed explanations and code examples where appropriate.'

            # Add specialized messages based on file type
            if path.name == 'README.md':
                message = "Create a comprehensive README with installation instructions, usage examples, and a concise overview of the project's purpose and capabilities. When possible, enhance the Architecture Diagram section by using the AWS Diagram MCP Server (awslabs.aws-diagram-mcp-server) to create visual representations of the system architecture."
            elif path.name == 'API.md':
                message = 'Document all API endpoints, request/response formats, and provide usage examples. Include authentication requirements if applicable.'
            elif path.name == 'BACKEND.md':
                message = 'Explain the backend architecture, database schema, and key components. The Data Flow section contains guidance for creating diagrams. When possible, enhance your documentation by using the AWS Diagram MCP Server (awslabs.aws-diagram-mcp-server) to create visual representations of data flow and component relationships.'
            elif path.name == 'FRONTEND.md':
                message = 'Document the frontend structure, components, and state management approach. Include screenshots of key UI elements if available.'

            # Add suggestions for companion MCP servers
            if 'architecture' in str(path).lower():
                message += '\n\nTo add architecture diagrams, consider using the AWS Diagram MCP Server (awslabs.aws-diagram-mcp-server).'

            doc = GeneratedDocument(
                path=str(path),
                content='',  # Empty content for the MCP client to fill
                type=doc_type,
                message=message,
            )
            generated_docs.append(doc)

        # Add notification about recommended MCP servers
        if ctx:
            await ctx.info(
                'Documentation structure generated successfully. '
                'For enhanced documentation with architecture diagrams, '
                "it's recommended to also use the following MCP server:\n"
                '- awslabs.aws-diagram-mcp-server: For generating architecture diagrams'
            )

        # Update context status
        doc_context.status = 'structure_ready'
        doc_context.current_step = 'awaiting_content'

        if ctx:
            await ctx.info(f'Created {len(generated_docs)} document structures')

        return generated_docs

    except Exception as e:
        error_msg = f'Error in generate_documentation: {str(e)}'
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg)


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
