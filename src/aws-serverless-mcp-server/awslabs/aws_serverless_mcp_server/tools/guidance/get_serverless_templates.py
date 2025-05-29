#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import base64
from awslabs.aws_serverless_mcp_server.models import GetServerlessTemplatesRequest
from awslabs.aws_serverless_mcp_server.utils.github import fetch_github_content
from loguru import logger
from typing import Any, Dict


# Global variable to cache the repository tree
repo_tree = None


async def get_serverless_templates(request: GetServerlessTemplatesRequest) -> Dict[str, Any]:
    """Get serverless application templates from the AWS Serverless Patterns GitHub repository.

    Args:
        request: GetServerlessTemplatesRequest object containing template type and runtime

    Returns:
        Dict: Serverless template README content and GitHub link
    """
    global repo_tree

    try:
        # Get file hierarchy of the repo if not already cached
        if not repo_tree:
            serverless_land_repo = (
                'https://api.github.com/repos/aws-samples/serverless-patterns/git/trees/main'
            )
            repo_tree = fetch_github_content(serverless_land_repo)

        # Filter templates based on search terms
        search_terms = []
        if request.template_type:
            search_terms.append(request.template_type.lower())
        if request.runtime:
            search_terms.append(request.runtime.lower())

        # Filter templates based on search terms
        template_names = [
            template
            for template in repo_tree['tree']
            if template.get('path')
            and any(term in template['path'].lower() for term in search_terms)
            and not template['path'].endswith(('.md', '.txt'))
            and not template['path'].startswith(('.', '_'))
        ]

        # Limit to 5 templates to avoid excessive API calls
        limit = 5
        template_names = template_names[:limit]

        # Fetch README.md for each template
        templates = []
        for template in template_names:
            try:
                readme_url = f'https://api.github.com/repos/aws-samples/serverless-patterns/contents/{template["path"]}/README.md'
                readme_file = fetch_github_content(readme_url)

                if readme_file and readme_file.get('content'):
                    decoded_content = base64.b64decode(readme_file['content']).decode('utf-8')

                    template_resource = {
                        'templateName': template['path'],
                        'readMe': decoded_content,
                        'gitHubLink': f'https://github.com/aws-samples/serverless-patterns/tree/main/{template["path"]}',
                    }
                    templates.append(template_resource)
            except Exception as e:
                logger.error(f'Error fetching README for {template["path"]}: {str(e)}')

        # Build response
        if len(templates) == 0:
            return {
                'success': False,
                'message': 'No serverless templates found matching the criteria.',
                'error': 'No templates found',
            }

        return {'templates': templates}
    except Exception as e:
        logger.error(f'Error getting serverless templates: {str(e)}')
        return {
            'success': False,
            'message': f'Failed to fetch serverless templates: {str(e)}',
            'error': str(e),
        }
