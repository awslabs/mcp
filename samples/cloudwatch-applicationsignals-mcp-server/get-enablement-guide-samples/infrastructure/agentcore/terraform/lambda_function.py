import json
import boto3
import time

def handler(event, context):
    """
    Lambda function to trigger and wait for CodeBuild project completion.
    This corresponds to the CDK build_trigger_lambda.handler function.
    """
    try:
        # Get project name from environment or event
        project_name = event.get('ProjectName')
        if not project_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'ProjectName is required in event payload'
                })
            }
        
        # Initialize CodeBuild client
        codebuild = boto3.client('codebuild')
        
        print(f"Starting build for project: {project_name}")
        
        # Start the build
        response = codebuild.start_build(projectName=project_name)
        build_id = response['build']['id']
        
        print(f"Build started with ID: {build_id}")
        
        # Wait for build completion (max 15 minutes as per lambda timeout)
        max_wait_time = 900  # 15 minutes in seconds
        poll_interval = 30   # Check every 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Get build status
            batch_response = codebuild.batch_get_builds(ids=[build_id])
            build = batch_response['builds'][0]
            build_status = build['buildStatus']
            
            print(f"Build status: {build_status}")
            
            if build_status in ['SUCCEEDED', 'FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT']:
                break
                
            time.sleep(poll_interval)
        
        # Final status check
        final_response = codebuild.batch_get_builds(ids=[build_id])
        final_build = final_response['builds'][0]
        final_status = final_build['buildStatus']
        
        print(f"Final build status: {final_status}")
        
        if final_status == 'SUCCEEDED':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Build completed successfully',
                    'buildId': build_id,
                    'status': final_status
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': f'Build failed with status: {final_status}',
                    'buildId': build_id,
                    'status': final_status
                })
            }
            
    except Exception as e:
        print(f"Error in build trigger: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Lambda execution failed: {str(e)}'
            })
        }
