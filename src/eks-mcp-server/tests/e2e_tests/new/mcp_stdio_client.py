#!/usr/bin/env python3
"""MCP client using stdio communication."""

import json
import logging
import subprocess
import threading
import uuid
import time
from typing import Dict, Any, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPStdioClient:
    """MCP client using stdio communication with a subprocess."""
    
    def __init__(self, cmd: List[str], env: Optional[Dict[str, str]] = None):
        """Initialize the client.
        
        Args:
            cmd: Command to start the MCP server
            env: Environment variables for the server process
        """
        self.cmd = cmd
        self.env = env or {}
        self.server_process = None
        self.request_id_counter = 0
        self.response_buffer = ""
        self.responses = {}
        self.notifications = []
        self.reader_thread = None
        self.running = False
        self.session_id = None
        self.initialized = False
    
    def start_server(self) -> bool:
        """Start the MCP server subprocess.
        
        Returns:
            bool: True if server started successfully, False otherwise
        """
        logger.info(f"Starting MCP server with command: {' '.join(self.cmd)}")
        
        try:
            # Start the server process
            self.server_process = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
                text=True,
                bufsize=1,  # Line buffered
            )
            
            # Start the reader thread
            self.running = True
            self.reader_thread = threading.Thread(target=self._read_output)
            self.reader_thread.daemon = True
            self.reader_thread.start()
            
            # Give the server a moment to start
            time.sleep(2)
            
            # Check if the process is still running
            if self.server_process.poll() is not None:
                stderr = self.server_process.stderr.read()
                logger.error(f"Server failed to start. Exit code: {self.server_process.returncode}")
                logger.error(f"Server stderr: {stderr}")
                return False
            
            logger.info("Server started successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error starting server: {str(e)}")
            return False
    
    def _read_output(self):
        """Read output from the server process."""
        while self.running and self.server_process and self.server_process.stdout:
            try:
                # Read a line from stdout
                line = self.server_process.stdout.readline()
                if not line:
                    # End of stream
                    if self.server_process.poll() is not None:
                        logger.warning(f"Server process exited with code {self.server_process.returncode}")
                    break
                
                # Process the line
                self._process_line(line.strip())
                
                # Also check stderr for any errors
                if self.server_process.stderr and self.server_process.stderr.readable():
                    error = self.server_process.stderr.readline()
                    if error:
                        logger.error(f"Server error: {error.strip()}")
            
            except Exception as e:
                logger.error(f"Error reading server output: {str(e)}")
                break
    
    def _process_line(self, line: str):
        """Process a line of output from the server.
        
        Args:
            line: Line of output
        """
        if not line:
            return
        
        try:
            # Try to parse as JSON
            message = json.loads(line)
            
            # Check if it's a response or notification
            if "id" in message:
                # It's a response to a request
                request_id = message["id"]
                self.responses[request_id] = message
                logger.debug(f"Received response for request {request_id}: {json.dumps(message, indent=2)}")
            elif "method" in message:
                # It's a notification
                self.notifications.append(message)
                logger.debug(f"Received notification: {json.dumps(message, indent=2)}")
            else:
                # Unknown message type
                logger.warning(f"Received unknown message: {line}")
        
        except json.JSONDecodeError:
            # Not a JSON message, might be a log or other output
            if "[ERROR]" in line or "error" in line.lower():
                logger.error(f"Server log: {line}")
            else:
                logger.info(f"Server log: {line}")
    
    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the server and wait for the response.
        
        Args:
            method: Method name
            params: Method parameters
        
        Returns:
            Dict[str, Any]: Response from the server
        
        Raises:
            Exception: If the server is not running or if the request fails
        """
        if not self.server_process or self.server_process.poll() is not None:
            raise Exception("Server is not running")
        
        # Generate a request ID
        request_id = str(uuid.uuid4())
        
        # Build the request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        if self.session_id:
            request["sessionId"] = self.session_id
        
        # Serialize the request
        request_str = json.dumps(request) + "\n"
        
        # Send the request
        try:
            logger.debug(f"Sending request: {request_str.strip()}")
            self.server_process.stdin.write(request_str)
            self.server_process.stdin.flush()
        except Exception as e:
            raise Exception(f"Error sending request: {str(e)}")
        
        # Wait for the response
        start_time = time.time()
        timeout = 30  # seconds
        
        while request_id not in self.responses and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if request_id not in self.responses:
            raise Exception(f"Timeout waiting for response to request {request_id}")
        
        # Get and remove the response
        response = self.responses.pop(request_id)
        
        # Check for errors
        if "error" in response:
            error = response["error"]
            error_msg = error.get("message", "Unknown error")
            error_code = error.get("code", -1)
            raise Exception(f"Error in response: {error_msg} (code {error_code})")
        
        return response
    
    def _send_notification(self, method: str, params: Dict[str, Any]):
        """Send a notification to the server.
        
        Args:
            method: Method name
            params: Method parameters
        
        Raises:
            Exception: If the server is not running or if the notification fails
        """
        if not self.server_process or self.server_process.poll() is not None:
            raise Exception("Server is not running")
        
        # Build the notification
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        if self.session_id:
            notification["sessionId"] = self.session_id
        
        # Serialize the notification
        notification_str = json.dumps(notification) + "\n"
        
        # Send the notification
        try:
            logger.debug(f"Sending notification: {notification_str.strip()}")
            self.server_process.stdin.write(notification_str)
            self.server_process.stdin.flush()
        except Exception as e:
            raise Exception(f"Error sending notification: {str(e)}")
    
    def initialize(self) -> Dict[str, Any]:
        """Perform the MCP protocol handshake.
        
        Returns:
            Dict[str, Any]: Initialization response
        
        Raises:
            Exception: If the handshake fails
        """
        logger.info("Performing MCP protocol handshake...")
        
        try:
            # List available tools
            logger.info("Listing available tools...")
            tools_response = self._send_request("tools/list", {})
            logger.info("Tools list request successful")
            
            if "result" in tools_response and "tools" in tools_response["result"]:
                tools = tools_response["result"]["tools"]
                logger.info(f"Found {len(tools)} available tools")
                for tool in tools:
                    logger.info(f"Tool: {tool.get('name')} - {tool.get('description', '')[:30]}...")
            
            # Set initialized flag
            self.initialized = True
            return tools_response
            
        except Exception as e:
            logger.error(f"Handshake failed: {str(e)}")
            raise
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information.
        
        Returns:
            Dict[str, Any]: Server information
        """
        # Ensure we've initialized
        if not self.initialized:
            self.initialize()
        
        # We need to send a custom request to get server info
        try:
            # For the stdio transport, we'll use the tools/list endpoint as server info
            server_info_response = self._send_request("tools/list", {})
            if "result" in server_info_response:
                return server_info_response["result"]
            return server_info_response
        except Exception as e:
            logger.error(f"Error getting server info: {str(e)}")
            raise
    
    def use_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Use a tool.
        
        Args:
            tool_name: Name of the tool to use
            arguments: Tool arguments
        
        Returns:
            Dict[str, Any]: Tool response
        """
        # Ensure we've initialized
        if not self.initialized:
            self.initialize()
        
        logger.info(f"Using tool: {tool_name}")
        
        # Build the tool execution parameters
        execute_params = {
            "name": tool_name,
            "arguments": arguments
        }
        
        try:
            # Send the tool execution request using the correct method name
            response = self._send_request("tools/call", execute_params)
            
            # Extract the result
            if "result" in response:
                return response["result"]
            
            return response
            
        except Exception as e:
            logger.error(f"Error using tool {tool_name}: {str(e)}")
            raise
    
    def stop(self):
        """Stop the client and server process."""
        logger.info("Stopping MCP client...")
        
        # Stop the reader thread
        self.running = False
        
        # Stop the server process
        if self.server_process:
            logger.info("Stopping server process...")
            
            try:
                # Try to send a shutdown request
                if self.initialized:
                    try:
                        self._send_request("shutdown", {})
                        logger.info("Shutdown request sent")
                    except Exception as e:
                        logger.warning(f"Error sending shutdown request: {str(e)}")
                
                # Give the process a moment to shut down
                time.sleep(1)
                
                # Check if the process is still running
                if self.server_process.poll() is None:
                    # Try to terminate gracefully
                    self.server_process.terminate()
                    
                    try:
                        # Wait for the process to terminate
                        self.server_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning("Process did not terminate gracefully, killing...")
                        self.server_process.kill()
                
                # Read any remaining output
                stdout, stderr = self.server_process.communicate()
                if stdout:
                    logger.info(f"Server final output: {stdout}")
                if stderr:
                    logger.error(f"Server final error: {stderr}")
                
            except Exception as e:
                logger.error(f"Error stopping server process: {str(e)}")
        
        logger.info("MCP client stopped")
