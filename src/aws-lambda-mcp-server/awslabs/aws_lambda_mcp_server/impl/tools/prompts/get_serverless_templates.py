import logging
import base64
from typing import Dict, Any
from awslabs.aws_lambda_mcp_server.models import GetServerlessTemplatesRequest
from awslabs.aws_lambda_mcp_server.utils.github import fetch_github_content

logger = logging.getLogger(__name__)

# Global variable to cache the repository tree
repo_tree = None

async def get_serverless_templates(request: GetServerlessTemplatesRequest) -> Dict[str, Any]:
    """
    Get serverless application templates from the AWS Serverless Patterns GitHub repository.
    
    Args:
        request: GetServerlessTemplatesRequest object containing template type and runtime
    
    Returns:
        Dict: Serverless template information
    """
    global repo_tree
    
    try:
        # Get file hierarchy of the repo if not already cached
        if not repo_tree:
            serverless_land_repo = 'https://api.github.com/repos/aws-samples/serverless-patterns/git/trees/main'
            repo_tree = await fetch_github_content(serverless_land_repo)
        
        # Filter templates based on search terms
        search_terms = []
        if request.template_type:
            search_terms.append(request.template_type.lower())
        if request.runtime:
            search_terms.append(request.runtime.lower())
        
        # If no search terms provided, use default search terms
        if not search_terms:
            search_terms = ["lambda", "api"]
        
        # Filter templates based on search terms
        filtered_templates = [
            template for template in repo_tree["tree"]
            if template.get("path") and 
               any(term in template["path"].lower() for term in search_terms) and
               not template["path"].endswith((".md", ".txt", ".png", ".jpg", ".jpeg", ".gif"))
        ]
        
        # Limit the number of templates to process
        limit = 5  # Limit to 5 templates to avoid excessive API calls
        filtered_templates = filtered_templates[:limit]
        
        # Fetch README.md for each template
        templates = []
        for template in filtered_templates:
            try:
                readme_url = f"https://api.github.com/repos/aws-samples/serverless-patterns/contents/{template['path']}/README.md"
                readme_file = await fetch_github_content(readme_url)
                
                if readme_file and readme_file.get("content"):
                    decoded_content = base64.b64decode(readme_file["content"]).decode("utf-8")
                    
                    template_resource = {
                        "templateName": template["path"],
                        "readMe": decoded_content,
                        "gitHubLink": f"https://github.com/aws-samples/serverless-patterns/tree/main/{template['path']}"
                    }
                    templates.append(template_resource)
            except Exception as e:
                logger.error(f"Error fetching README for {template['path']}: {str(e)}")
        
        # Build response
        response = {
            "templates": templates
        }
        
        return response
    except Exception as e:
        logger.error(f"Error getting serverless templates: {str(e)}")
        raise
