"""Document templates and template-related functions."""

from ai3_document_expert.models import DocumentSection, DocumentSpec, DocumentTemplate


# Mapping of filenames to template types
TEMPLATE_FILE_MAPPING = {
    'README.md': 'README',
    'API.md': 'API',
    'BACKEND.md': 'BACKEND',
    'FRONTEND.md': 'FRONTEND',
    'REQUIREMENTS.md': 'BUSINESS_REQUIREMENTS',
    'PATH_TO_PRODUCTION.md': 'PATH_TO_PRODUCTION',
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
            DocumentSection(title='Overview', content='', level=1),
            DocumentSection(title='Features', content='', level=2),
            DocumentSection(
                title='Prerequisites',
                content='',
                level=2,
                subsections=[
                    DocumentSection(title='Required AWS Setup', content='', level=3),
                    DocumentSection(title='Development Environment', content='', level=3),
                ],
            ),
            DocumentSection(title='Architecture Diagram', content='', level=2),
            DocumentSection(title='Project Components', content='', level=2),
            DocumentSection(title='Next Steps', content='', level=2),
            DocumentSection(title='Clean Up', content='', level=2),
            DocumentSection(title='Troubleshooting', content='', level=2),
            DocumentSection(title='License', content='Amazon Software License 1.0', level=2),
        ],
    ),
    'API': DocumentTemplate(
        type='API',
        sections=[
            DocumentSection(title='API Reference', content='', level=1),
            DocumentSection(title='Endpoints', content='', level=2),
            DocumentSection(title='Authentication', content='', level=2),
            DocumentSection(title='Error Handling', content='', level=2),
        ],
    ),
    'BACKEND': DocumentTemplate(
        type='BACKEND',
        sections=[
            DocumentSection(title='Backend Architecture', content='', level=1),
            DocumentSection(title='Project Structure', content='', level=2),
            DocumentSection(title='Data Flow', content='', level=2),
            DocumentSection(title='CDK Stacks', content='', level=2),
            DocumentSection(title='Deployment', content='', level=2),
        ],
    ),
    'FRONTEND': DocumentTemplate(
        type='FRONTEND',
        sections=[
            DocumentSection(title='Frontend Architecture', content='', level=1),
            DocumentSection(title='Key Features', content='', level=2),
            DocumentSection(title='Project Structure', content='', level=2),
            DocumentSection(title='Build & Deploy', content='', level=2),
        ],
    ),
    'PATH_TO_PRODUCTION': DocumentTemplate(
        type='PATH_TO_PRODUCTION',
        sections=[
            DocumentSection(title='Path to Production', content='', level=1),
            DocumentSection(title='Overview', content='', level=2),
            DocumentSection(title='Development Environment', content='', level=2),
            DocumentSection(title='Deployment Pipeline', content='', level=2),
            DocumentSection(title='Monitoring and Maintenance', content='', level=2),
        ],
    ),
    'BUSINESS_REQUIREMENTS': DocumentTemplate(
        type='BUSINESS_REQUIREMENTS',
        sections=[
            DocumentSection(title='Business Requirements', content='', level=1),
            DocumentSection(title='Executive Summary', content='', level=2),
            DocumentSection(title='Project Goals', content='', level=2),
            DocumentSection(title='Key Features', content='', level=2),
            DocumentSection(title='Success Criteria', content='', level=2),
        ],
    ),
}


def create_doc_from_template(template_name: str, doc_name: str) -> DocumentSpec:
    """Create a DocumentSpec from a template."""
    template = DOCUMENT_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f'Template {template_name} not found')

    return DocumentSpec(
        name=doc_name, type=template.type, template=template_name, sections=template.sections
    )
