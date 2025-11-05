import json
import os
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    print('Serving lambda request.')
    
    result = s3.list_buckets()
    
    bucket_count = len(result.get('Buckets', []))
    response_body = f"Hello lambda - found {bucket_count} buckets."
    
    return {
        'statusCode': 200,
        'body': response_body
    }