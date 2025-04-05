/**
 * Test for the Python parser
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { parsePythonCdkCode } from '../src/parsers/python-parser.js';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const ROOT_DIR = path.resolve(__dirname, '..');
const EXAMPLES_DIR = path.join(ROOT_DIR, 'examples');

// Test Python parser
console.log('Testing Python parser...');
try {
  const pyExamplePath = path.join(EXAMPLES_DIR, 'simple-example.py');
  const pyCode = fs.readFileSync(pyExamplePath, 'utf-8');
  
  // Parse the Python code
  const infrastructure = parsePythonCdkCode(pyCode);
  
  // Check if the infrastructure object is valid
  if (!infrastructure) {
    throw new Error('Failed to parse Python code');
  }
  
  if (!infrastructure.resources || infrastructure.resources.length === 0) {
    throw new Error('No resources found in the parsed Python code');
  }
  
  console.log('Python parser test passed!');
  console.log(`Found ${infrastructure.resources.length} resources:`);
  infrastructure.resources.forEach(resource => {
    console.log(`- ${resource.type}: ${resource.id}`);
  });
  
  console.log('\nFound connections:');
  if (infrastructure.connections && infrastructure.connections.length > 0) {
    infrastructure.connections.forEach(connection => {
      console.log(`- ${connection.source} -> ${connection.target}`);
    });
  } else {
    console.log('No connections found');
  }
} catch (error) {
  console.error('Error testing Python parser:', error);
  process.exit(1);
}
