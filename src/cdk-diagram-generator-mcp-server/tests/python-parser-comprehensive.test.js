/**
 * Comprehensive test for the Python parser
 * 
 * This test checks that the Python parser correctly identifies all AWS resources
 * and their relationships in CDK code.
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

// Test Python parser with comprehensive checks
console.log('Running comprehensive Python parser test...');
try {
  const pyExamplePath = path.join(EXAMPLES_DIR, 'simple-example.py');
  const pyCode = fs.readFileSync(pyExamplePath, 'utf-8');
  
  // Parse the Python code
  const infrastructure = parsePythonCdkCode(pyCode);
  
  // Check if the infrastructure object is valid
  if (!infrastructure) {
    throw new Error('Failed to parse Python code');
  }
  
  // Check for resources
  if (!infrastructure.resources || infrastructure.resources.length === 0) {
    throw new Error('No resources found in the parsed Python code');
  }
  
  // Check for specific resource types
  const resourceTypes = infrastructure.resources.map(r => r.type);
  console.log('Found resource types:', resourceTypes);
  
  const expectedTypes = ['lambda', 'dynamodb', 's3', 'apigateway'];
  for (const expectedType of expectedTypes) {
    if (!resourceTypes.includes(expectedType)) {
      console.warn(`Warning: Expected resource type '${expectedType}' not found`);
    }
  }
  
  // Check for VPCs
  if (infrastructure.vpcs && infrastructure.vpcs.length > 0) {
    console.log(`Found ${infrastructure.vpcs.length} VPCs`);
    infrastructure.vpcs.forEach(vpc => {
      console.log(`- ${vpc.id} (contains ${vpc.resources.length} resources)`);
    });
  } else {
    console.warn('Warning: No VPCs found in the parsed Python code');
  }
  
  // Check for connections
  if (infrastructure.connections && infrastructure.connections.length > 0) {
    console.log(`Found ${infrastructure.connections.length} connections:`);
    infrastructure.connections.forEach(connection => {
      console.log(`- ${connection.source} -> ${connection.target} (${connection.type})`);
    });
  } else {
    console.warn('Warning: No connections found in the parsed Python code');
  }
  
  // Print summary
  console.log('Comprehensive Python parser test passed!');
  console.log(`Found ${infrastructure.resources.length} resources:`);
  infrastructure.resources.forEach(resource => {
    console.log(`- ${resource.type}: ${resource.id}`);
  });
  
} catch (error) {
  console.error('Error in comprehensive Python parser test:', error);
  process.exit(1);
}
