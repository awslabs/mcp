"""Deploy serverless app help tool for AWS Lambda MCP Server."""

import json
from enum import Enum
from typing import Dict, Any

class ApplicationType(str, Enum):
    """Application types for serverless deployments."""
    EVENT_DRIVEN = "event_driven"
    BACKEND = "backend"
    FULLSTACK = "fullstack"

async def deploy_serverless_app_help(application_type: ApplicationType) -> Dict[str, Any]:
    """
    Provide instructions on how to deploy a serverless application to AWS Lambda.
    
    Args:
        application_type: Type of application to deploy (event_driven, backend, fullstack)
    
    Returns:
        Dict: Deployment instructions
    """
    iac_guidance = (
        "Design the application's serverless architecture and generate the infrastructure as code (IaC) template. "
        "Use the get_iac_guidance tool to decide which IaC tool to use based on the application type. "
        "If using SAM, you can use get_serverless_templates tool to find example SAM template for the Lambda function from ServerlessLand. "
        "Configure Lambda function properties such as memory size, timeout, environment variables, etc. using best practices from AWS documentation. "
        "Consider the application use case and expected scale if that info is available"
    )
    
    if application_type == ApplicationType.EVENT_DRIVEN:
        iac_guidance += " For event driven applications, use an event source mapping (ESM) to trigger the Lambda function."
    elif application_type == ApplicationType.BACKEND:
        iac_guidance += " For backend APIs, you can use API Gateway or Lambda function URLs to expose the Lambda function as an API endpoint."
    elif application_type == ApplicationType.FULLSTACK:
        iac_guidance += (
            " Full stack applications typically involve both frontend and backend components. "
            "For the backend, you can use Lambda functions with API Gateway or Lambda function URLs. "
            "For the frontend, you can use S3 for static hosting. Use CloudFront for CDN and caching."
        )
    
    result = [
        {
            "step": 1,
            "prompt": (
                "Verify that the code structure is compatible with AWS Lambda. Lambda requires a handler method that is the entry point into the function when it is invoked. "
                "The handler method should accept an event object and a context object, and return a response object.\n\n"
                "For event-driven applications, use the get_lambda_event_schemas tool to get the event specific schema for the event source (e.g. SQS, SNS) and ensure the event parameter is using the correct type. "
                "For web servers using frameworks, such as next.js, express.js, SpringBoot, use Lambda Web Adapter (https://github.com/awslabs/aws-lambda-web-adapter) "
                "to avoid needing to modify the code to conform to the Lambda handler format."
            )
        },
        {
            "step": 2,
            "prompt": iac_guidance
        },
        {
            "step": 3,
            "prompt": (
                "Install dependencies using the package's configured dependency manager. For example, python applications use pip to install dependencies, "
                "node.js applications use npm or yarn to install dependencies, and java applications use maven or gradle to build the package.\n\n"
                "If package is using SAM, the sam_build tool automatically installs dependencies and this step can be skipped."
            )
        },
        {
            "step": 4,
            "prompt": (
                "Build the package. Analyze the project structure to determine the build command. "
                "For example, for node.js applications, run `npm run build` or `yarn build`. For python applications, run `python setup.py build` or `pip install -e`.\n\n"
                "If package is using SAM, run the sam_build tool to build the package."
            )
        },
        {
            "step": 5,
            "prompt": (
                "Package the code into the deployment artifact. AWS Lambda accepts deployment packages in direct ZIP upload, S3 bucket, or conatiner image in an ECR repository. "
                "If there is already a Dockerfile in the project directory, then use OCI format. For code packages larger than 250 MB (unzipped), use the AWS Lambda container image support. "
                "For packages smaller than 250MB, use the ZIP format or S3 upload option.\n\n"
                "If package is using SAM, the sam_deploy tool will automatically upload deployment artifacts to S3, and this step can be skipped."
            )
        },
        {
            "step": 6,
            "prompt": (
                "Run the IaC tool commands to perform the deployment. If package is using SAM, use sam_deploy tool to deploy the application. "
                "For Cloudformation and CDK, use the CFN or CDK cli commands."
            )
        }
    ]
    
    return {
        "content": json.dumps(result)
    }
