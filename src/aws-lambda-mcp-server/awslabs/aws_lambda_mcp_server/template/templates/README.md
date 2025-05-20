# Deployment Templates

This directory contains Handlebars templates for different types of deployments.

## Available Templates

- `backend.hbs`: Template for backend applications (Express.js, Flask, FastAPI, etc.)
- `frontend.hbs`: Template for frontend web applications (React, Vue, Angular, static)
- `fullstack.hbs`: Template for fullstack applications combining backend and frontend

## Template System

The templates use Handlebars syntax for dynamic content generation. The template processor injects deployment configuration parameters into these templates to generate AWS CloudFormation/SAM templates for deployment.

For detailed documentation on the template system, including how templates are selected, processed, and extended, see [Template System Documentation](../docs/template-system.md).

## Template Structure

Each template includes:

- Resources for the specific deployment type
- Parameters derived from deployment configuration
- Outputs for resource information and endpoints
- Conditional sections based on deployment options

## Usage

Templates are processed by the template system in `src/template/` and are not used directly. The deployment service selects the appropriate template based on the `deploymentType` parameter and processes it with the provided configuration.

## Extending Templates

To add support for new frameworks or deployment types:

1. Create a new template or modify an existing one
2. Update the template registry in `src/template/registry.ts`
3. Add any necessary processing logic in `src/template/processor.ts`

For more detailed instructions on extending the template system, refer to the [Template System Documentation](../docs/template-system.md).
