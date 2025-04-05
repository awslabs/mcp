/**
 * Comprehensive test for the TypeScript parser
 * 
 * This test checks that the TypeScript parser correctly identifies all AWS resources
 * and their relationships in CDK code.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { parseTypescriptCdkCode } from '../src/parsers/typescript-parser.js';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const ROOT_DIR = path.resolve(__dirname, '..');
const EXAMPLES_DIR = path.join(ROOT_DIR, 'examples');

// Test TypeScript parser with comprehensive checks
console.log('Running comprehensive TypeScript parser test...');
try {
  const tsExamplePath = path.join(EXAMPLES_DIR, 'simple-example.ts');
  const tsCode = fs.readFileSync(tsExamplePath, 'utf-8');
  
  // Parse the TypeScript code
  const infrastructure = parseTypescriptCdkCode(tsCode);
  
  // Check if the infrastructure object is valid
  if (!infrastructure) {
    throw new Error('Failed to parse TypeScript code');
  }
  
  // Check for resources
  if (!infrastructure.resources || infrastructure.resources.length === 0) {
    throw new Error('No resources found in the parsed TypeScript code');
  }
  
  // Check for specific resource types
  const resourceTypes = infrastructure.resources.map(r => r.type);
  const expectedTypes = ['lambda', 'dynamodb', 's3', 'apigateway'];
  
  for (const expectedType of expectedTypes) {
    if (!resourceTypes.includes(expectedType)) {
      throw new Error(`Expected resource type '${expectedType}' not found`);
    }
  }
  
  // Check for VPCs
  if (!infrastructure.vpcs || infrastructure.vpcs.length === 0) {
    throw new Error('No VPCs found in the parsed TypeScript code');
  }
  
  // Check for connections
  if (!infrastructure.connections || infrastructure.connections.length === 0) {
    throw new Error('No connections found in the parsed TypeScript code');
  }
  
  // Check for specific connections (Lambda to DynamoDB, Lambda to S3)
  const connectionTypes = infrastructure.connections.map(c => c.type);
  if (!connectionTypes.includes('access')) {
    throw new Error(`Expected connection type 'access' not found`);
  }
  
  // Print summary
  console.log('Comprehensive TypeScript parser test passed!');
  console.log(`Found ${infrastructure.resources.length} resources:`);
  infrastructure.resources.forEach(resource => {
    console.log(`- ${resource.type}: ${resource.id}`);
  });
  
  console.log(`\nFound ${infrastructure.vpcs.length} VPCs:`);
  infrastructure.vpcs.forEach(vpc => {
    console.log(`- ${vpc.id} (contains ${vpc.resources.length} resources)`);
  });
  
  console.log(`\nFound ${infrastructure.connections.length} connections:`);
  infrastructure.connections.forEach(connection => {
    console.log(`- ${connection.source} -> ${connection.target} (${connection.type})`);
  });
} catch (error) {
  console.error('Error in comprehensive TypeScript parser test:', error);
  process.exit(1);
}
