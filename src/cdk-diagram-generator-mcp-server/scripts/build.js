#!/usr/bin/env node

/**
 * Build script for CDK Diagram Generator MCP Server
 * 
 * This script sets the executable permission on the built index.js file.
 */

import { chmodSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to the built index.js file
const indexPath = path.resolve(__dirname, '../build/index.js');

console.log(`Setting executable permission on ${indexPath}`);
chmodSync(indexPath, '755');
console.log('Done!');
