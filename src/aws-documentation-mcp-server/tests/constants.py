from awslabs.aws_documentation_mcp_server.server_utils import DEFAULT_USER_AGENT


TEST_USER_AGENT = DEFAULT_USER_AGENT.replace(
    '(AWS Documentation Server)', '(AWS Documentation Tests)'
)
