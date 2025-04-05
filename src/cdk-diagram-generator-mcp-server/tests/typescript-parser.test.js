/**
 * Test for the TypeScript parser
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

// Test TypeScript parser
console.log('Testing TypeScript parser...');
try {
  const tsExamplePath = path.join(EXAMPLES_DIR, 'simple-example.ts');
  const tsCode = fs.readFileSync(tsExamplePath, 'utf-8');
  
  // Parse the TypeScript code
  const infrastructure = parseTypescriptCdkCode(tsCode);
  
  // Check if the infrastructure object is valid
  if (!infrastructure) {
    throw new Error('Failed to parse TypeScript code');
  }
  
  if (!infrastructure.resources || infrastructure.resources.length === 0) {
    throw new Error('No resources found in the parsed TypeScript code');
  }
  
  console.log('TypeScript parser test passed!');
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
  console.error('Error testing TypeScript parser:', error);
  process.exit(1);
}
