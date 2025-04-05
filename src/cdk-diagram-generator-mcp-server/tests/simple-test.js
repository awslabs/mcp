#!/usr/bin/env node

/**
 * Simple test script for CDK Diagram Generator MCP Server
 * 
 * This script tests the diagram generator by generating diagrams from the example files.
 */

import path from 'path';
import fs from 'fs';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const ROOT_DIR = path.resolve(__dirname, '..');
const EXAMPLES_DIR = path.join(ROOT_DIR, 'examples');
const OUTPUT_DIR = path.join(ROOT_DIR, 'output');
const BUILD_DIR = path.join(ROOT_DIR, 'build');
const SERVER_PATH = path.join(BUILD_DIR, 'index.js');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Test TypeScript example
console.log('Testing TypeScript example...');
try {
  const tsExamplePath = path.join(EXAMPLES_DIR, 'simple-example.ts');
  const tsOutputPath = path.join(OUTPUT_DIR, 'typescript-example.drawio');
  
  // Create a temporary JSON file with the request
  const tsRequestPath = path.join(OUTPUT_DIR, 'ts-request.json');
  const tsRequest = {
    jsonrpc: '2.0',
    id: '1',
    method: 'call_tool',
    params: {
      name: 'generate_diagram_from_code',
      arguments: {
        code: fs.readFileSync(tsExamplePath, 'utf-8'),
        outputPath: tsOutputPath,
        language: 'typescript'
      }
    }
  };
  fs.writeFileSync(tsRequestPath, JSON.stringify(tsRequest, null, 2));
  
  // Execute the server with the request
  console.log(`Generating diagram from ${tsExamplePath}...`);
  console.log(`Command: echo '${JSON.stringify(tsRequest)}' | node ${SERVER_PATH}`);
  try {
    execSync(`echo '${JSON.stringify(tsRequest)}' | node ${SERVER_PATH}`, { stdio: 'inherit' });
  } catch (error) {
    console.error('Error executing server:', error);
    throw error;
  }
  
  // Check if the output file exists
  if (fs.existsSync(tsOutputPath)) {
    console.log(`TypeScript diagram generated successfully: ${tsOutputPath}`);
  } else {
    console.error(`Failed to generate TypeScript diagram: ${tsOutputPath}`);
    process.exit(1);
  }
} catch (error) {
  console.error('Error testing TypeScript example:', error);
  process.exit(1);
}

// Test Python example
console.log('\nTesting Python example...');
try {
  const pyExamplePath = path.join(EXAMPLES_DIR, 'simple-example.py');
  const pyOutputPath = path.join(OUTPUT_DIR, 'python-example.drawio');
  
  // Create a temporary JSON file with the request
  const pyRequestPath = path.join(OUTPUT_DIR, 'py-request.json');
  const pyRequest = {
    jsonrpc: '2.0',
    id: '2',
    method: 'call_tool',
    params: {
      name: 'generate_diagram_from_code',
      arguments: {
        code: fs.readFileSync(pyExamplePath, 'utf-8'),
        outputPath: pyOutputPath,
        language: 'python'
      }
    }
  };
  fs.writeFileSync(pyRequestPath, JSON.stringify(pyRequest, null, 2));
  
  // Execute the server with the request
  console.log(`Generating diagram from ${pyExamplePath}...`);
  console.log(`Command: echo '${JSON.stringify(pyRequest)}' | node ${SERVER_PATH}`);
  try {
    execSync(`echo '${JSON.stringify(pyRequest)}' | node ${SERVER_PATH}`, { stdio: 'inherit' });
  } catch (error) {
    console.error('Error executing server:', error);
    throw error;
  }
  
  // Check if the output file exists
  if (fs.existsSync(pyOutputPath)) {
    console.log(`Python diagram generated successfully: ${pyOutputPath}`);
  } else {
    console.error(`Failed to generate Python diagram: ${pyOutputPath}`);
    process.exit(1);
  }
} catch (error) {
  console.error('Error testing Python example:', error);
  process.exit(1);
}

console.log('\nAll tests passed!');
