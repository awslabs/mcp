import os
import boto3 

def get_effective_region(region_arg=None):
    """
    Determine the AWS region in the following order of priority:
    1. Region passed as an argument
    2. AWS_REGION or AWS_DEFAULT_REGION environment variable
    3. Region from the current boto3 session/profile
    4. Default fallback: 'us-east-1'
    """
    if region_arg:
        return region_arg

    env_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if env_region:
        return env_region

    session = boto3.Session()
    if session.region_name:
        return session.region_name

    return "us-east-1"	

