/**
 * Comprehensive test for the MCP server
 * 
 * This test checks that the MCP server correctly handles various requests
 * and returns the expected responses.
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
const SERVER_PATH = path.join(ROOT_DIR, 'src/index.js');
const EXAMPLES_DIR = path.join(ROOT_DIR, 'examples');
const OUTPUT_DIR = path.join(ROOT_DIR, 'output');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Test MCP server with comprehensive checks
console.log('Running comprehensive MCP server test...');

// Define test requests
const testRequests = [
  {
    name: 'List Tools',
    request: {
      jsonrpc: '2.0',
      id: '1',
      method: 'list_tools'
    },
    validate: (response) => {
      if (!response.result || !response.result.tools || !Array.isArray(response.result.tools)) {
        throw new Error('Invalid response: missing tools array');
      }
      
      if (response.result.tools.length < 1) {
        throw new Error('Invalid response: no tools returned');
      }
      
      const toolNames = response.result.tools.map(tool => tool.name);
      const expectedTools = ['generate_diagram_from_code', 'generate_diagram_from_directory'];
      
      for (const expectedTool of expectedTools) {
        if (!toolNames.includes(expectedTool)) {
          throw new Error(`Expected tool '${expectedTool}' not found`);
        }
      }
      
      return true;
    }
  },
  {
    name: 'Generate Diagram from Code',
    request: {
      jsonrpc: '2.0',
      id: '2',
      method: 'call_tool',
      params: {
        name: 'generate_diagram_from_code',
        arguments: {
          code: fs.readFileSync(path.join(EXAMPLES_DIR, 'simple-example.ts'), 'utf-8'),
          outputPath: 'test-diagram-from-code.drawio',
          language: 'typescript'
        }
      }
    },
    validate: (response) => {
      if (!response.result || !response.result.content || !Array.isArray(response.result.content)) {
        throw new Error('Invalid response: missing content array');
      }
      
      if (response.result.content.length < 1) {
        throw new Error('Invalid response: no content returned');
      }
      
      const text = response.result.content[0].text;
      if (!text || !text.includes('Diagram generated successfully')) {
        throw new Error('Invalid response: diagram generation failed');
      }
      
      // Check if the file was created
      const outputPath = path.join(OUTPUT_DIR, 'test-diagram-from-code.drawio');
      if (!fs.existsSync(outputPath)) {
        throw new Error(`Output file not created: ${outputPath}`);
      }
      
      return true;
    }
  }
];

// Create a promise to handle the server response
const runServerTest = () => {
  return new Promise((resolve, reject) => {
    // Spawn the server process with ts-node
    const server = spawn('node', ['--loader', 'ts-node/esm', SERVER_PATH]);
    
    let stdout = '';
    let stderr = '';
    let currentRequestIndex = 0;
    let results = [];
    
    // Handle server output
    server.stdout.on('data', (data) => {
      stdout += data.toString();
      
      // Check if we received a response
      try {
        const lines = stdout.split('\n');
        for (const line of lines) {
          if (line.trim() && line.includes('"jsonrpc":"2.0"')) {
            const response = JSON.parse(line);
            
            // Validate the response
            const currentRequest = testRequests[currentRequestIndex];
            if (response.id === currentRequest.request.id) {
              console.log(`Received response for: ${currentRequest.name}`);
              
              try {
                const isValid = currentRequest.validate(response);
                results.push({
                  name: currentRequest.name,
                  success: isValid,
                  response
                });
                
                // Move to the next request
                currentRequestIndex++;
                
                // If we have more requests, send the next one
                if (currentRequestIndex < testRequests.length) {
                  console.log(`Sending request: ${testRequests[currentRequestIndex].name}`);
                  server.stdin.write(JSON.stringify(testRequests[currentRequestIndex].request) + '\n');
                } else {
                  // We're done with all requests
                  console.log('All requests completed');
                  server.kill();
                  resolve(results);
                }
              } catch (error) {
                console.error(`Validation error for ${currentRequest.name}:`, error);
                results.push({
                  name: currentRequest.name,
                  success: false,
                  error: error.message
                });
                
                // Move to the next request
                currentRequestIndex++;
                
                // If we have more requests, send the next one
                if (currentRequestIndex < testRequests.length) {
                  console.log(`Sending request: ${testRequests[currentRequestIndex].name}`);
                  server.stdin.write(JSON.stringify(testRequests[currentRequestIndex].request) + '\n');
                } else {
                  // We're done with all requests
                  console.log('All requests completed');
                  server.kill();
                  resolve(results);
                }
              }
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
        
        // Send the first request
        console.log(`Sending request: ${testRequests[0].name}`);
        server.stdin.write(JSON.stringify(testRequests[0].request) + '\n');
      }
    });
    
    server.on('close', (code) => {
      if (currentRequestIndex < testRequests.length) {
        reject(new Error(`Server exited with code ${code} before completing all requests`));
      }
    });
    
    // Set a timeout
    setTimeout(() => {
      if (currentRequestIndex < testRequests.length) {
        server.kill();
        reject(new Error('Timeout waiting for server responses'));
      }
    }, 10000);
  });
};

// Run the test
runServerTest()
  .then((results) => {
    console.log('\nTest Results:');
    let allPassed = true;
    
    results.forEach(result => {
      if (result.success) {
        console.log(`✅ ${result.name} passed!`);
      } else {
        console.log(`❌ ${result.name} failed: ${result.error}`);
        allPassed = false;
      }
    });
    
    if (allPassed) {
      console.log('\n✅ All MCP server tests passed!');
    } else {
      console.log('\n❌ Some MCP server tests failed!');
      process.exit(1);
    }
  })
  .catch((error) => {
    console.error('Error in comprehensive MCP server test:', error);
    process.exit(1);
  });
