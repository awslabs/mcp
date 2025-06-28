import time
import unittest
from awslabs.aws_mcp_server.core.aws.token_manager import TokenManager
from unittest.mock import patch


class TestTokenManager(unittest.TestCase):
    """Test cases for the TokenManager class."""

    def setUp(self):
        """Set up a new TokenManager instance for each test."""
        self.token_manager = TokenManager(token_expiry_seconds=300)
        self.test_command = 'aws ec2 describe-instances'

    def test_init(self):
        """Test the initialization of TokenManager."""
        self.assertEqual(self.token_manager._token_expiry_seconds, 300)
        self.assertEqual(self.token_manager._tokens, {})

        # Test with default expiry time
        default_manager = TokenManager()
        self.assertEqual(
            default_manager._token_expiry_seconds, TokenManager.EXPIRY_TIME_IN_SECONDS
        )

    def test_extract_command_signature(self):
        """Test the extraction of command signatures."""
        # Test with a standard command
        signature = self.token_manager._extract_command_signature('aws ec2 describe-instances')
        self.assertEqual(signature, 'aws ec2 describe-instances')

        # Test with a command that has parameters
        signature = self.token_manager._extract_command_signature(
            'aws ec2 describe-instances --region us-west-2'
        )
        self.assertEqual(signature, 'aws ec2 describe-instances')

        # Test with a command that has fewer than 3 tokens
        signature = self.token_manager._extract_command_signature('aws ec2')
        self.assertEqual(signature, 'aws ec2')

        # Test with an empty command
        signature = self.token_manager._extract_command_signature('')
        self.assertEqual(signature, '')

    def test_generate_token(self):
        """Test token generation."""
        token = self.token_manager.generate_token(self.test_command)

        # Verify token is a string with expected length (32 chars for 16 bytes hex)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 32)

        # Verify token is stored with correct command signature
        self.assertIn(token, self.token_manager._tokens)
        expiry_time, command_signature = self.token_manager._tokens[token]
        self.assertEqual(command_signature, 'aws ec2 describe-instances')

        # Verify expiry time is set correctly
        expected_expiry_time = time.time() + 300
        self.assertAlmostEqual(expiry_time, expected_expiry_time, delta=1)

    def test_validate_token(self):
        """Test token validation."""
        # Generate a token
        token = self.token_manager.generate_token(self.test_command)

        # Test with valid token and matching command
        self.assertTrue(self.token_manager.validate_token(token, self.test_command))

        # Test with valid token but different command
        self.assertFalse(self.token_manager.validate_token(token, 'aws s3 ls'))

        # Test with non-existent token
        self.assertFalse(
            self.token_manager.validate_token('non-existent-token', self.test_command)
        )

    def test_validate_token_expiry(self):
        """Test token validation with expired token."""
        # Generate a token
        token = self.token_manager.generate_token(self.test_command)

        # Mock time to simulate token expiration
        with patch('time.time', return_value=time.time() + 301):
            self.assertFalse(self.token_manager.validate_token(token, self.test_command))
            # Verify expired token is removed
            self.assertNotIn(token, self.token_manager._tokens)

    def test_find_valid_token_for_command(self):
        """Test finding a valid token for a command."""
        # Generate a token
        token = self.token_manager.generate_token(self.test_command)

        # Test finding token for the same command
        found_token = self.token_manager.find_valid_token_for_command(self.test_command)
        self.assertEqual(found_token, token)

        # Test finding token for a different command
        found_token = self.token_manager.find_valid_token_for_command('aws s3 ls')
        self.assertIsNone(found_token)

        # Test with expired token
        with patch('time.time', return_value=time.time() + 301):
            found_token = self.token_manager.find_valid_token_for_command(self.test_command)
            self.assertIsNone(found_token)

    def test_has_valid_token_for_command(self):
        """Test checking if a valid token exists for a command."""
        # Initially no valid token
        self.assertFalse(self.token_manager.has_valid_token_for_command(self.test_command))

        # Generate a token
        self.token_manager.generate_token(self.test_command)

        # Now there should be a valid token
        self.assertTrue(self.token_manager.has_valid_token_for_command(self.test_command))

        # Test with a different command
        self.assertFalse(self.token_manager.has_valid_token_for_command('aws s3 ls'))

        # Test with expired token
        with patch('time.time', return_value=time.time() + 301):
            self.assertFalse(self.token_manager.has_valid_token_for_command(self.test_command))

    def test_invalidate_token(self):
        """Test token invalidation."""
        # Generate a token
        token = self.token_manager.generate_token(self.test_command)

        # Verify token exists
        self.assertIn(token, self.token_manager._tokens)

        # Invalidate the token
        self.token_manager.invalidate_token(token)

        # Verify token no longer exists
        self.assertNotIn(token, self.token_manager._tokens)

        # Test invalidating a non-existent token (should not raise an error)
        self.token_manager.invalidate_token('non-existent-token')

    def test_cleanup_expired_tokens(self):
        """Test cleaning up expired tokens."""
        # Generate multiple tokens
        token1 = self.token_manager.generate_token(self.test_command)
        token2 = self.token_manager.generate_token('aws s3 ls')

        # Manually set one token to be expired
        expiry_time, command_signature = self.token_manager._tokens[token1]
        self.token_manager._tokens[token1] = (time.time() - 1, command_signature)

        # Clean up expired tokens
        self.token_manager.cleanup_expired_tokens()

        # Verify expired token is removed
        self.assertNotIn(token1, self.token_manager._tokens)

        # Verify non-expired token still exists
        self.assertIn(token2, self.token_manager._tokens)

    def test_multiple_tokens_same_command(self):
        """Test generating multiple tokens for the same command."""
        # Generate two tokens for the same command
        token1 = self.token_manager.generate_token(self.test_command)
        token2 = self.token_manager.generate_token(self.test_command)

        # Verify both tokens are different
        self.assertNotEqual(token1, token2)

        # Verify both tokens are valid for the same command
        self.assertTrue(self.token_manager.validate_token(token1, self.test_command))
        self.assertTrue(self.token_manager.validate_token(token2, self.test_command))
