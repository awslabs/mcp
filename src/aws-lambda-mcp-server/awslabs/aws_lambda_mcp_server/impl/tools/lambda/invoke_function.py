import boto3
import os
import json
import base64
import logging
from awslabs.aws_lambda_mcp_server.models import InvokeFunctionRequest

logger = logging.getLogger(__name__)

async def invoke_function(request: InvokeFunctionRequest):
    """
    Invoke an AWS Lambda function.
    
    Args:
        request: InvokeFunctionRequest object containing function name and payload
    
    Returns:
        Dict: Response from AWS Lambda API
    """
    # Initialize Lambda client
    session = boto3.Session(
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        profile_name=os.environ.get('AWS_PROFILE', 'default')
    )
    lambda_client = session.client('lambda')
    
    # Prepare invocation parameters
    invoke_params = {
        'FunctionName': request.function_name,
        'InvocationType': request.invocation_type or 'RequestResponse',
        'LogType': request.log_type or 'None'
    }
    
    # Add payload if provided
    if request.payload:
        invoke_params['Payload'] = json.dumps(request.payload)
    
    # Invoke the Lambda function
    try:
        response = lambda_client.invoke(**invoke_params)
        
        # Process the response
        result = {
            'StatusCode': response.get('StatusCode'),
            'ExecutedVersion': response.get('ExecutedVersion')
        }
        
        # Process payload if present
        if 'Payload' in response:
            payload = response['Payload'].read().decode('utf-8')
            try:
                result['Payload'] = json.loads(payload)
            except json.JSONDecodeError:
                result['Payload'] = payload
        
        # Process logs if present
        if 'LogResult' in response and response['LogResult']:
            result['LogResult'] = base64.b64decode(response['LogResult']).decode('utf-8')
        
        # Process function error if present
        if 'FunctionError' in response:
            result['FunctionError'] = response['FunctionError']
        
        logger.info(f"Invoked Lambda function: {request.function_name}")
        return result
    except Exception as e:
        logger.error(f"Error invoking Lambda function: {str(e)}")
        raise
