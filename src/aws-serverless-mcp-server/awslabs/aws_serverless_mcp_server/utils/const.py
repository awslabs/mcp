import os
import tempfile


AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
DEPLOYMENT_STATUS_DIR = os.path.join(
    tempfile.gettempdir(), 'aws-serverless-mcp-server-deployments'
)
