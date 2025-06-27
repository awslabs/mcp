"""Test configuration constants."""

# Mock AWS credentials for testing purposes only
TEST_AWS_CONFIG = {
    'region': 'us-east-1',
    'test_bucket': 'test-bucket',
    'mock_role': 'MOCK_ROLE_123',  # Using explicit test naming
}

# Mock credentials using explicit test values
TEST_AWS_CREDENTIALS = {
    'AWS_ACCESS_KEY_ID': 'MOCK_KEY_123',  # Using explicit test naming
    'AWS_SECRET_ACCESS_KEY': 'MOCK_SECRET_123',  # Using explicit test naming
    'AWS_SECURITY_TOKEN': 'MOCK_TOKEN_123',  # Using explicit test naming
    'AWS_SESSION_TOKEN': 'MOCK_SESSION_123',  # Using explicit test naming
    'AWS_DEFAULT_REGION': TEST_AWS_CONFIG['region'],
}
