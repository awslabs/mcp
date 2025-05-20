# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the logger module."""

import os
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from awslabs.aws_lambda_mcp_server.utils.logger import logger, set_log_directory


class TestLogger:
    """Tests for the logger module."""

    def test_logger_instance(self):
        """Test that logger is an instance of logging.Logger."""
        assert isinstance(logger, logging.Logger)
        assert logger.name == "aws_lambda_mcp_server"

    def test_logger_level(self):
        """Test that logger has the correct level."""
        assert logger.level == logging.INFO

    def test_set_log_directory_creates_directory(self):
        """Test that set_log_directory creates the directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "logs")
            
            # Ensure the directory doesn't exist
            assert not os.path.exists(log_dir)
            
            # Call the function
            result = set_log_directory(log_dir)
            
            # Verify the directory was created
            assert os.path.exists(log_dir)
            assert os.path.isdir(log_dir)
            assert result == log_dir

    def test_set_log_directory_uses_existing_directory(self):
        """Test that set_log_directory uses the existing directory if it exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Call the function
            result = set_log_directory(temp_dir)
            
            # Verify the directory was used
            assert result == temp_dir

    def test_set_log_directory_adds_file_handler(self):
        """Test that set_log_directory adds a file handler to the logger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Get the initial number of handlers
            initial_handlers = len(logger.handlers)
            
            # Call the function
            set_log_directory(temp_dir)
            
            # Verify a handler was added
            assert len(logger.handlers) > initial_handlers
            
            # Verify the handler is a FileHandler
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) > 0
            
            # Verify the handler's file path
            for handler in file_handlers:
                assert temp_dir in handler.baseFilename

    def test_logger_formatting(self):
        """Test that logger uses the correct formatting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            
            # Create a handler with the test log file
            handler = logging.FileHandler(log_file)
            logger.addHandler(handler)
            
            # Log a test message
            test_message = "Test log message"
            logger.info(test_message)
            
            # Remove the handler to ensure the file is closed
            logger.removeHandler(handler)
            
            # Read the log file
            with open(log_file, "r") as f:
                log_content = f.read()
            
            # Verify the message was logged
            assert test_message in log_content
            
            # Verify the log format includes the expected elements
            assert "INFO" in log_content
            assert "aws_lambda_mcp_server" in log_content
