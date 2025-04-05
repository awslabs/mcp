/**
 * Run all tests for the CDK Diagram Generator MCP Server
 */

import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const ROOT_DIR = path.resolve(__dirname, '..');

// Test files
const testFiles = [
  // Basic tests
  'typescript-parser.test.js',
  'python-parser.test.js',
  'drawio-generator.test.js',
  'mcp-server.test.js',
  
  // Comprehensive tests
  'typescript-parser-comprehensive.test.js',
  'python-parser-comprehensive.test.js',
  'drawio-generator-comprehensive.test.js',
  'mcp-server-comprehensive.test.js'
];

// Run all tests
console.log('Running all tests...\n');

let allTestsPassed = true;
let failedTests = [];

for (const testFile of testFiles) {
  const testPath = path.join(__dirname, testFile);
  console.log(`Running test: ${testFile}`);
  console.log('='.repeat(50));
  
  try {
    execSync(`node --loader ts-node/esm ${testPath}`, { stdio: 'inherit' });
    console.log(`✅ ${testFile} passed!\n`);
  } catch (error) {
    console.error(`❌ ${testFile} failed!`);
    console.error(error.message);
    console.log('\n');
    
    allTestsPassed = false;
    failedTests.push(testFile);
  }
}

// Print summary
console.log('='.repeat(50));
console.log('Test Summary:');
console.log(`Total tests: ${testFiles.length}`);
console.log(`Passed: ${testFiles.length - failedTests.length}`);
console.log(`Failed: ${failedTests.length}`);

if (failedTests.length > 0) {
  console.log('\nFailed tests:');
  failedTests.forEach(test => console.log(`- ${test}`));
  process.exit(1);
} else {
  console.log('\n✅ All tests passed!');
}
