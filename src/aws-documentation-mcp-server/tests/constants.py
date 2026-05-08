from awslabs.aws_documentation_mcp_server.server_utils import get_default_user_agent


TEST_USER_AGENT = get_default_user_agent().replace(
    '(AWS Documentation Server)', '(AWS Documentation Tests)'
)
