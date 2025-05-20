import boto3
import os
import logging
from awslabs.aws_lambda_mcp_server.models import ListFunctionsRequest

logger = logging.getLogger(__name__)

async def list_functions(request: ListFunctionsRequest):
    """
    List AWS Lambda functions.
    
    Args:
        request: ListFunctionsRequest object containing listing parameters
    
    Returns:
        Dict: Response from AWS Lambda API
    """
    # Initialize Lambda client
    session = boto3.Session(
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        profile_name=os.environ.get('AWS_PROFILE', 'default')
    )
    lambda_client = session.client('lambda')
    
    # Prepare list parameters
    list_params = {
        'MaxItems': request.max_items,
        'FunctionVersion': request.function_version or 'ALL'
    }
    
    # Add marker if provided
    if request.marker:
        list_params['Marker'] = request.marker
    
    # List Lambda functions
    try:
        response = lambda_client.list_functions(**list_params)
        
        # Process the response
        functions = []
        for function in response.get('Functions', []):
            # Extract relevant information for each function
            function_info = {
                'FunctionName': function.get('FunctionName'),
                'FunctionArn': function.get('FunctionArn'),
                'Runtime': function.get('Runtime'),
                'Role': function.get('Role'),
                'Handler': function.get('Handler'),
                'CodeSize': function.get('CodeSize'),
                'Description': function.get('Description'),
                'Timeout': function.get('Timeout'),
                'MemorySize': function.get('MemorySize'),
                'LastModified': function.get('LastModified'),
                'Version': function.get('Version'),
                'State': function.get('State'),
                'LastUpdateStatus': function.get('LastUpdateStatus')
            }
            
            # Add environment variables if present
            if 'Environment' in function and 'Variables' in function['Environment']:
                function_info['Environment'] = function['Environment']['Variables']
            
            # Add VPC configuration if present
            if 'VpcConfig' in function:
                function_info['VpcConfig'] = {
                    'SubnetIds': function['VpcConfig'].get('SubnetIds', []),
                    'SecurityGroupIds': function['VpcConfig'].get('SecurityGroupIds', []),
                    'VpcId': function['VpcConfig'].get('VpcId')
                }
            
            # Add architectures if present
            if 'Architectures' in function:
                function_info['Architectures'] = function['Architectures']
            
            functions.append(function_info)
        
        result = {
            'Functions': functions,
            'NextMarker': response.get('NextMarker')
        }
        
        logger.info(f"Listed {len(functions)} Lambda functions")
        return result
    except Exception as e:
        logger.error(f"Error listing Lambda functions: {str(e)}")
        raise
