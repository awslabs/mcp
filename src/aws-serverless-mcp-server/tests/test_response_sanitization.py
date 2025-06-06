#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Tests for the response sanitization framework."""

import unittest
from awslabs.aws_serverless_mcp_server.utils.security import ResponseSanitizer


class TestResponseSanitizer(unittest.TestCase):
    """Tests for the ResponseSanitizer class."""

    def test_sanitize_string(self):
        """Test sanitizing a string with various sensitive patterns."""
        # Test AWS access key
        text = 'My access key is AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
        sanitized = ResponseSanitizer._sanitize_string(text)
        self.assertNotIn('AKIAIOSFODNN7EXAMPLE', sanitized)
        self.assertIn('[REDACTED AWS_ACCESS_KEY]', sanitized)

        # Test AWS secret key
        text = (
            'My secret key is wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # pragma: allowlist secret
        )
        sanitized = ResponseSanitizer._sanitize_string(text)
        self.assertNotIn(
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', sanitized
        )  # pragma: allowlist secret
        self.assertIn('[REDACTED AWS_SECRET_KEY]', sanitized)

        # Test password
        text = 'password=mysecretpassword'
        sanitized = ResponseSanitizer._sanitize_string(text)
        self.assertNotIn('password=mysecretpassword', sanitized)
        self.assertIn('[REDACTED PASSWORD]', sanitized)

        # Test AWS account ID
        text = 'Account ID: 123456789012'
        sanitized = ResponseSanitizer._sanitize_string(text)
        self.assertNotIn('123456789012', sanitized)
        self.assertIn('[REDACTED AWS_ACCOUNT_ID]', sanitized)

        # Test API key
        text = 'api_key=sk-proj-abcdef123456'
        sanitized = ResponseSanitizer._sanitize_string(text)
        self.assertNotIn('api_key=sk-proj-abcdef123456', sanitized)
        self.assertIn('[REDACTED API_KEY]', sanitized)

    def test_sanitize_cloudwatch_logs(self):
        """Test sanitizing CloudWatch logs output."""
        logs = """
        2024-01-15 10:30:00 START RequestId: 123e4567-e89b-12d3-a456-426614174000
        2024-01-15 10:30:01 Environment variables: AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        2024-01-15 10:30:01 Environment variables: AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        2024-01-15 10:30:02 Processing account 123456789012
        2024-01-15 10:30:03 API_KEY=sk-proj-abcdef123456
        2024-01-15 10:30:04 END RequestId: 123e4567-e89b-12d3-a456-426614174000
        """

        sanitized = ResponseSanitizer._sanitize_string(logs)

        # Check that sensitive data is redacted
        self.assertNotIn('AKIAIOSFODNN7EXAMPLE', sanitized)
        self.assertNotIn('wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', sanitized)
        self.assertNotIn('123456789012', sanitized)
        self.assertNotIn('sk-proj-abcdef123456', sanitized)

        # Check that redacted markers are present
        self.assertIn('[REDACTED AWS_ACCESS_KEY]', sanitized)
        self.assertIn('[REDACTED AWS_SECRET_KEY]', sanitized)
        self.assertIn('[REDACTED AWS_ACCOUNT_ID]', sanitized)
        self.assertIn('[REDACTED API_KEY]', sanitized)

        # Check that non-sensitive data is preserved
        self.assertIn('START RequestId', sanitized)
        self.assertIn('END RequestId', sanitized)
        self.assertIn('Environment variables', sanitized)

    def test_sanitize_dict(self):
        """Test sanitizing a dictionary with nested sensitive data."""
        data = {
            'success': True,
            'message': 'Function executed successfully',
            'output': 'Account 123456789012 processed',
            'environment': {
                'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                'API_KEY': 'api_key=sk-proj-abcdef123456',  # pragma: allowlist secret
            },
            'logs': [
                'Processing started',
                'Found password=mysecretpassword',
                'Processing complete',
            ],
        }

        sanitized = ResponseSanitizer.sanitize(data)

        # Check that structure is preserved
        self.assertEqual(sanitized['success'], True)
        self.assertEqual(sanitized['message'], 'Function executed successfully')

        # Check that sensitive data is redacted
        self.assertIn('[REDACTED AWS_ACCOUNT_ID]', sanitized['output'])
        self.assertIn('[REDACTED AWS_ACCESS_KEY]', sanitized['environment']['AWS_ACCESS_KEY_ID'])
        self.assertIn(
            '[REDACTED AWS_SECRET_KEY]', sanitized['environment']['AWS_SECRET_ACCESS_KEY']
        )
        self.assertIn('[REDACTED API_KEY]', sanitized['environment']['API_KEY'])
        self.assertIn('[REDACTED PASSWORD]', sanitized['logs'][1])

        # Check that non-sensitive data is preserved
        self.assertEqual(sanitized['logs'][0], 'Processing started')
        self.assertEqual(sanitized['logs'][2], 'Processing complete')

    def test_sanitize_lambda_invocation_response(self):
        """Test sanitizing a typical Lambda invocation response."""
        response = {
            'success': True,
            'message': "Successfully invoked resource 'MyFunction' locally.",
            'logs': """START RequestId: 123e4567-e89b-12d3-a456-426614174000 Version: $LATEST
[INFO] 2024-01-15 10:30:00 Connecting to database with password=db_secret_password
[INFO] 2024-01-15 10:30:01 Using API key: api-key=1234567890abcdef
[INFO] 2024-01-15 10:30:02 Processing account 123456789012
END RequestId: 123e4567-e89b-12d3-a456-426614174000
REPORT RequestId: 123e4567-e89b-12d3-a456-426614174000 Duration: 150.00 ms Billed Duration: 200 ms Memory Size: 128 MB Max Memory Used: 64 MB""",
            'function_output': {
                'statusCode': 200,
                'body': 'Success',
                'headers': {
                    'X-Account-Id': '123456789012',
                    'X-Api-Key': 'Bearer AKIAIOSFODNN7EXAMPLE',
                },
            },
        }

        sanitized = ResponseSanitizer.sanitize(response)

        # Check that sensitive data in logs is redacted
        self.assertNotIn('db_secret_password', str(sanitized))
        self.assertNotIn('1234567890abcdef', str(sanitized))
        self.assertNotIn('123456789012', str(sanitized))
        self.assertNotIn('AKIAIOSFODNN7EXAMPLE', str(sanitized))

        # Check that redacted markers are present
        self.assertIn('[REDACTED PASSWORD]', sanitized['logs'])
        self.assertIn('[REDACTED API_KEY]', sanitized['logs'])
        self.assertIn('[REDACTED AWS_ACCOUNT_ID]', sanitized['logs'])
        self.assertIn('[REDACTED AWS_ACCESS_KEY]', str(sanitized['function_output']))

        # Check that non-sensitive data is preserved
        self.assertEqual(sanitized['success'], True)
        self.assertEqual(sanitized['function_output']['statusCode'], 200)
        self.assertEqual(sanitized['function_output']['body'], 'Success')
        self.assertIn('START RequestId', sanitized['logs'])
        self.assertIn('REPORT RequestId', sanitized['logs'])

    def test_sanitize_list(self):
        """Test sanitizing a list with sensitive data."""
        data = [
            'Regular log entry',
            'Found AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            {'password': 'password=secret123'},  # pragma: allowlist secret
            ['Account', '123456789012', 'processed'],
        ]

        sanitized = ResponseSanitizer.sanitize(data)

        # Check that sensitive data is redacted
        self.assertNotIn('AKIAIOSFODNN7EXAMPLE', str(sanitized))
        self.assertNotIn('secret123', str(sanitized))
        self.assertNotIn('123456789012', str(sanitized))

        # Check that redacted markers are present
        self.assertIn('[REDACTED AWS_ACCESS_KEY]', sanitized[1])
        self.assertIn('[REDACTED PASSWORD]', str(sanitized[2]))
        self.assertIn('[REDACTED AWS_ACCOUNT_ID]', sanitized[3][1])

        # Check that non-sensitive data is preserved
        self.assertEqual(sanitized[0], 'Regular log entry')
        self.assertEqual(sanitized[3][0], 'Account')
        self.assertEqual(sanitized[3][2], 'processed')

    def test_sanitize_non_string_types(self):
        """Test that non-string types pass through unchanged."""
        # Test integers
        self.assertEqual(ResponseSanitizer.sanitize(123), 123)

        # Test floats
        self.assertEqual(ResponseSanitizer.sanitize(123.45), 123.45)

        # Test booleans
        self.assertEqual(ResponseSanitizer.sanitize(True), True)
        self.assertEqual(ResponseSanitizer.sanitize(False), False)

        # Test None
        self.assertEqual(ResponseSanitizer.sanitize(None), None)

    def test_sanitize_empty_structures(self):
        """Test sanitizing empty structures."""
        # Empty string
        self.assertEqual(ResponseSanitizer.sanitize(''), '')

        # Empty dict
        self.assertEqual(ResponseSanitizer.sanitize({}), {})

        # Empty list
        self.assertEqual(ResponseSanitizer.sanitize([]), [])


if __name__ == '__main__':
    unittest.main()
