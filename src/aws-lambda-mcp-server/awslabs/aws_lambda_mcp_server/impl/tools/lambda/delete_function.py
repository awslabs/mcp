import boto3
import os
import logging
from awslabs.aws_lambda_mcp_server.models import DeleteFunctionRequest

logger = logging.getLogger(__name__)

async def delete_function(request: DeleteFunctionRequest):
    """
    Delete an AWS Lambda function.
    
    Args:
        request: DeleteFunctionRequest object containing function name
    
    Returns:
        Dict: Response from AWS Lambda API
    """
    # Initialize Lambda client
    session = boto3.Session(
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        profile_name=os.environ.get('AWS_PROFILE', 'default')
    )
    lambda_client = session.client('lambda')
    
    # Delete the Lambda function
    try:
        response = lambda_client.delete_function(
            FunctionName=request.function_name
        )
        logger.info(f"Deleted Lambda function: {request.function_name}")
        return {"status": "success", "message": f"Function {request.function_name} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting Lambda function: {str(e)}")
        raise
