"""Update frontend tool for AWS Lambda MCP Server."""

import os
import boto3
import json
import tempfile
import datetime
from pathlib import Path
from typing import Dict, Any
from awslabs.aws_lambda_mcp_server.models import UpdateFrontendRequest
from awslabs.aws_lambda_mcp_server.utils.logger import logger

# Define the directory where deployment status files will be stored
DEPLOYMENT_STATUS_DIR = os.path.join(tempfile.gettempdir(), 'serverless-web-mcp-deployments')

async def update_frontend(request: UpdateFrontendRequest) -> Dict[str, Any]:
    """
    Update the frontend of a deployed web application.
    
    Args:
        request: UpdateFrontendRequest object containing frontend update parameters
    
    Returns:
        Dict: Frontend update result
    """
    try:
        project_name = request.project_name
        built_assets_path = request.built_assets_path
        invalidate_cache = request.invalidate_cache
        
        logger.info(f"Updating frontend for project {project_name}")
        
        # Get deployment status to find the S3 bucket and CloudFront distribution
        status_file_path = os.path.join(DEPLOYMENT_STATUS_DIR, f'{project_name}.json')
        
        if not os.path.exists(status_file_path):
            return {
                'success': False,
                'message': f"No deployment found for project '{project_name}'",
                'status': 'NOT_FOUND'
            }
        
        with open(status_file_path, 'r') as f:
            status_data = json.load(f)
        
        # Check if the deployment was successful
        if status_data.get('status') != 'DEPLOYED':
            return {
                'success': False,
                'message': f"Deployment for project '{project_name}' is not in DEPLOYED state",
                'status': status_data.get('status')
            }
        
        # Check if the deployment has a frontend component
        deployment_type = status_data.get('deploymentType')
        
        if deployment_type not in ['frontend', 'fullstack']:
            return {
                'success': False,
                'message': f"Project '{project_name}' does not have a frontend component",
                'deploymentType': deployment_type
            }
        
        # Get the S3 bucket name from the deployment status
        s3_bucket_name = status_data.get('outputs', {}).get('WebsiteBucketName')
        
        if not s3_bucket_name:
            return {
                'success': False,
                'message': f"S3 bucket name not found for project '{project_name}'",
                'deploymentType': deployment_type
            }
        
        # Get the CloudFront distribution ID from the deployment status
        cloudfront_distribution_id = status_data.get('outputs', {}).get('CloudFrontDistributionId')
        
        # Initialize AWS clients
        session = boto3.Session(
            region_name=request.region or os.environ.get('AWS_REGION', 'us-east-1'),
            profile_name=os.environ.get('AWS_PROFILE', 'default')
        )
        s3_client = session.client('s3')
        cloudfront_client = session.client('cloudfront')
        
        # Upload the frontend assets to S3
        try:
            # Check if the built assets path exists
            built_assets_path = Path(built_assets_path)
            
            if not built_assets_path.exists():
                return {
                    'success': False,
                    'message': f"Built assets path '{built_assets_path}' does not exist",
                    'error': 'Path not found'
                }
            
            if not built_assets_path.is_dir():
                return {
                    'success': False,
                    'message': f"Built assets path '{built_assets_path}' is not a directory",
                    'error': 'Path is not a directory'
                }
            
            # Upload the files
            uploaded_files = []
            
            for root, dirs, files in os.walk(built_assets_path):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, built_assets_path)
                    
                    # Determine the content type based on the file extension
                    content_type = None
                    
                    if file.endswith('.html'):
                        content_type = 'text/html'
                    elif file.endswith('.css'):
                        content_type = 'text/css'
                    elif file.endswith('.js'):
                        content_type = 'application/javascript'
                    elif file.endswith('.json'):
                        content_type = 'application/json'
                    elif file.endswith('.png'):
                        content_type = 'image/png'
                    elif file.endswith('.jpg') or file.endswith('.jpeg'):
                        content_type = 'image/jpeg'
                    elif file.endswith('.gif'):
                        content_type = 'image/gif'
                    elif file.endswith('.svg'):
                        content_type = 'image/svg+xml'
                    elif file.endswith('.ico'):
                        content_type = 'image/x-icon'
                    
                    # Upload the file
                    extra_args = {}
                    if content_type:
                        extra_args['ContentType'] = content_type
                    
                    s3_client.upload_file(
                        local_path,
                        s3_bucket_name,
                        relative_path,
                        ExtraArgs=extra_args
                    )
                    
                    uploaded_files.append(relative_path)
            
            logger.info(f"Uploaded {len(uploaded_files)} files to S3 bucket {s3_bucket_name}")
            
            # Invalidate CloudFront cache if requested and distribution ID is available
            invalidation_id = None
            
            if invalidate_cache and cloudfront_distribution_id:
                try:
                    response = cloudfront_client.create_invalidation(
                        DistributionId=cloudfront_distribution_id,
                        InvalidationBatch={
                            'Paths': {
                                'Quantity': 1,
                                'Items': ['/*']  # Invalidate all paths
                            },
                            'CallerReference': f"{project_name}-{int(datetime.datetime.now().timestamp())}"
                        }
                    )
                    
                    invalidation_id = response.get('Invalidation', {}).get('Id')
                    
                    logger.info(f"Created CloudFront invalidation {invalidation_id} for distribution {cloudfront_distribution_id}")
                except Exception as e:
                    logger.error(f"Error creating CloudFront invalidation: {str(e)}")
            
            return {
                'success': True,
                'message': f"Updated frontend for project '{project_name}'",
                's3Bucket': s3_bucket_name,
                'uploadedFiles': len(uploaded_files),
                'cloudFrontDistributionId': cloudfront_distribution_id,
                'cacheInvalidated': invalidate_cache and cloudfront_distribution_id is not None,
                'invalidationId': invalidation_id
            }
        except Exception as e:
            logger.error(f"Error updating frontend: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to update frontend for project '{project_name}'",
                'error': str(e)
            }
    except Exception as e:
        logger.error(f"Error in update_frontend: {str(e)}")
        return {
            'success': False,
            'message': f"Failed to update frontend for project '{project_name}'",
            'error': str(e)
        }
