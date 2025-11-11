import boto3
import json
import logging
import time
import urllib3

# Note: cfnresponse is only available for inline Lambda code in CloudFormation.
# When using CDK with Code.from_asset(), we need to include our own copy.
# This is the standard AWS-provided cfnresponse module embedded directly.

class cfnresponse:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    
    @staticmethod
    def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
        responseUrl = event['ResponseURL']
        print(responseUrl)

        responseBody = {
            'Status': responseStatus,
            'Reason': reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
            'PhysicalResourceId': physicalResourceId or context.log_stream_name,
            'StackId': event['StackId'],
            'RequestId': event['RequestId'],
            'LogicalResourceId': event['LogicalResourceId'],
            'NoEcho': noEcho,
            'Data': responseData
        }

        json_responseBody = json.dumps(responseBody)
        print("Response body:")
        print(json_responseBody)

        headers = {
            'content-type': '',
            'content-length': str(len(json_responseBody))
        }

        try:
            http = urllib3.PoolManager()
            response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
            print("Status code:", response.status)
        except Exception as e:
            print("send(..) failed executing http.request(..):", e)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info('Received event: %s', json.dumps(event))
    
    try:
        if event['RequestType'] == 'Delete':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            return
            
        project_name = event['ResourceProperties']['ProjectName']
        
        codebuild = boto3.client('codebuild')
        
        # Start build
        response = codebuild.start_build(projectName=project_name)
        build_id = response['build']['id']
        logger.info(f"Started build: {build_id}")
        
        # Wait for completion
        max_wait_time = context.get_remaining_time_in_millis() / 1000 - 30
        start_time = time.time()
        
        while True:
            if time.time() - start_time > max_wait_time:
                cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': 'Build timeout'})
                return
                
            build_response = codebuild.batch_get_builds(ids=[build_id])
            build_status = build_response['builds'][0]['buildStatus']
            
            if build_status == 'SUCCEEDED':
                logger.info(f"Build {build_id} succeeded")
                cfnresponse.send(event, context, cfnresponse.SUCCESS, {'BuildId': build_id})
                return
            elif build_status in ['FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT']:
                logger.error(f"Build {build_id} failed with status: {build_status}")
                cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': f'Build failed: {build_status}'})
                return
                
            logger.info(f"Build {build_id} status: {build_status}")
            time.sleep(30)
            
    except Exception as e:
        logger.error('Error: %s', str(e))
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
