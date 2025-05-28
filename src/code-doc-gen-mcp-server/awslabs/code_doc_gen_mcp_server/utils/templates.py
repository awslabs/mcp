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

"""Document templates and template-related functions."""

from awslabs.code_doc_gen_mcp_server.utils.models import (
    DocumentSection,
    DocumentSpec,
    DocumentTemplate,
)
from loguru import logger


# Mapping of filenames to template types
TEMPLATE_FILE_MAPPING = {
    'README.md': 'README',
    'API.md': 'API',
    'BACKEND.md': 'BACKEND',
    'FRONTEND.md': 'FRONTEND',
    'DEPLOYMENT_GUIDE.md': 'DEPLOYMENT',
}


def get_template_for_file(filename: str) -> str:
    """Get template type for a given filename.

    First tries exact match in TEMPLATE_FILE_MAPPING.
    Then tries to derive from filename if not found.
    Raises ValueError if no template can be determined.
    """
    # Try direct mapping first
    if filename in TEMPLATE_FILE_MAPPING:
        return TEMPLATE_FILE_MAPPING[filename]

    # Try to derive from filename
    template_name = filename.replace('.md', '').upper()
    if template_name in DOCUMENT_TEMPLATES:
        return template_name

    raise ValueError(f'No template found for {filename}')


# Document templates for common documentation types
DOCUMENT_TEMPLATES = {
    'README': DocumentTemplate(
        type='README',
        sections=[
            DocumentSection(
                title='Overview',
                content='',
                level=1,
                message="Provide a concise overview that explains the project's purpose, what problem it solves, and its primary use case. Include a high-level summary of the technology stack used.",
            ),
            DocumentSection(
                title='Features',
                content='',
                level=2,
                message='List the key features of the project as bullet points. Focus on capabilities that solve user problems and highlight unique aspects of the implementation.',
            ),
            DocumentSection(
                title='Prerequisites',
                content='',
                level=2,
                message='Describe what is needed to set up the project',
                subsections=[
                    DocumentSection(
                        title='Required AWS Setup',
                        content='',
                        level=3,
                        message='AWS resources that need to be set up',
                    ),
                    DocumentSection(
                        title='Development Environment',
                        content='',
                        level=3,
                        message='Requirements for the development environment',
                    ),
                ],
            ),
            DocumentSection(
                title='Architecture Diagram',
                content='',
                level=2,
                message='Include an architecture diagram showing the key components and their interactions. Consider using the AWS Diagram MCP Server to generate a visual representation of the system architecture.',
            ),
            DocumentSection(
                title='Project Components',
                content='',
                level=2,
                message='Describe the major components of the project, explaining their purpose, how they interact, and key technical decisions. Reference specific directories in the codebase where each component is implemented.',
            ),
            DocumentSection(
                title='Next Steps',
                content='',
                level=2,
                message='Suggest potential enhancements, extensions, or customizations that users might want to implement. Also include guidance on how to contribute to the project if applicable.',
            ),
            DocumentSection(
                title='Clean Up',
                content='',
                level=2,
                message='Provide specific instructions for removing deployed resources to prevent unnecessary costs. Include commands or steps for each resource type that needs cleanup.',
            ),
            DocumentSection(
                title='Troubleshooting',
                content='',
                level=2,
                message='Document common issues users might encounter, their root causes, and step-by-step solutions. Include error messages and debugging tips where applicable.',
            ),
            DocumentSection(
                title='License',
                content='',
                level=2,
                message='Include license information from the repository. Check for LICENSE or LICENSE.md files, identify the license type (e.g., Apache 2.0, MIT), and add appropriate citation and link.',
            ),
        ],
    ),
    'API': DocumentTemplate(
        type='API',
        sections=[
            DocumentSection(
                title='API Reference', content='', level=1, message='General API documentation'
            ),
            DocumentSection(
                title='Endpoints',
                content='',
                level=2,
                message='Document all available API endpoints, including HTTP methods, URL paths, required parameters, request/response formats, and example requests/responses. Group endpoints logically by resource or function.',
            ),
            DocumentSection(
                title='Authentication',
                content='',
                level=2,
                message='Explain authentication mechanisms',
            ),
            DocumentSection(
                title='Error Handling',
                content='',
                level=2,
                message='Document all possible error codes, their meanings, and how to handle each one. Include HTTP status codes where applicable and provide example error responses.',
            ),
        ],
    ),
    'BACKEND': DocumentTemplate(
        type='BACKEND',
        sections=[
            DocumentSection(
                title='Backend Architecture',
                content='',
                level=1,
                message='Overview of the backend architecture',
            ),
            DocumentSection(
                title='Project Structure',
                content='',
                level=2,
                message='Explain backend project structure',
            ),
            DocumentSection(
                title='Data Flow',
                content='',
                level=2,
                message='Describe how data flows through the system',
            ),
            DocumentSection(
                title='Core Components',
                content='',
                level=2,
                message='Detail the core backend components',
            ),
        ],
    ),
    'FRONTEND': DocumentTemplate(
        type='FRONTEND',
        sections=[
            DocumentSection(
                title='Frontend Architecture',
                content='',
                level=1,
                message='Overview of frontend architecture',
            ),
            DocumentSection(
                title='Key Features',
                content='',
                level=2,
                message='Highlight key frontend features',
            ),
            DocumentSection(
                title='Project Structure',
                content='',
                level=2,
                message='Explain frontend project structure',
            ),
            DocumentSection(
                title='Build & Deploy',
                content='',
                level=2,
                message='Instructions for building and deploying',
            ),
        ],
    ),
    'DEPLOYMENT': DocumentTemplate(
        type='DEPLOYMENT',
        sections=[
            DocumentSection(
                title='Deployment Guide',
                content='',
                level=1,
                message='Comprehensive deployment guide',
            ),
            DocumentSection(
                title='Prerequisites', content='', level=2, message='List required prerequisites'
            ),
            DocumentSection(
                title='Environment Setup',
                content='',
                level=2,
                message='Environment setup instructions',
            ),
            DocumentSection(
                title='Deployment Steps',
                content='',
                level=2,
                message='Step-by-step deployment instructions',
            ),
        ],
    ),
}


def create_doc_from_template(template_name: str, doc_name: str) -> DocumentSpec:
    """Create a DocumentSpec from a template."""
    template = DOCUMENT_TEMPLATES.get(template_name)
    if not template:
        logger.error(
            f'Template {template_name} not found', message=f'Template {template_name} not found'
        )
        raise ValueError(f'Template {template_name} not found')

    return DocumentSpec(
        name=doc_name, type=template.type, template=template_name, sections=template.sections
    )
