/**
 * Test for the MCP server
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const ROOT_DIR = path.resolve(__dirname, '..');
const BUILD_DIR = path.join(ROOT_DIR, 'build');
const SERVER_PATH = path.join(ROOT_DIR, 'src/index.js');
const OUTPUT_DIR = path.join(ROOT_DIR, 'output');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Test MCP server
console.log('Testing MCP server...');

// Create a simple request
const request = {
  jsonrpc: '2.0',
  id: '1',
  method: 'list_tools'
};

// Create a promise to handle the server response
const runServerTest = () => {
  return new Promise((resolve, reject) => {
    // Spawn the server process with ts-node
    const server = spawn('node', ['--loader', 'ts-node/esm', SERVER_PATH]);
    
    let stdout = '';
    let stderr = '';
    let responseReceived = false;
    
    // Handle server output
    server.stdout.on('data', (data) => {
      stdout += data.toString();
      
      // Check if we received a response
      try {
        const lines = stdout.split('\n');
        for (const line of lines) {
          if (line.trim() && line.includes('"jsonrpc":"2.0"')) {
            const response = JSON.parse(line);
            if (response.id === '1' && response.result && response.result.tools) {
              responseReceived = true;
              console.log('Server responded with tools list:');
              for (const tool of response.result.tools) {
                console.log(`- ${tool.name}: ${tool.description}`);
              }
              
              // Kill the server after receiving the response
              server.kill();
              resolve(response);
            }
          }
        }
      } catch (error) {
        // Ignore parsing errors
      }
    });
    
    server.stderr.on('data', (data) => {
      stderr += data.toString();
      // Check for the server startup message
      if (stderr.includes('CDK Diagram Generator MCP server running on stdio')) {
        console.log('Server started successfully');
        
        // Send the request
        server.stdin.write(JSON.stringify(request) + '\n');
      }
    });
    
    server.on('close', (code) => {
      if (!responseReceived) {
        reject(new Error(`Server exited with code ${code} before sending a response`));
      }
    });
    
    // Set a timeout
    setTimeout(() => {
      if (!responseReceived) {
        server.kill();
        reject(new Error('Timeout waiting for server response'));
      }
    }, 5000);
  });
};

// Run the test
runServerTest()
  .then(() => {
    console.log('MCP server test passed!');
  })
  .catch((error) => {
    console.error('Error testing MCP server:', error);
    process.exit(1);
  });
