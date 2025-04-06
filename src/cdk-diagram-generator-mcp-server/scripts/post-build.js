#!/usr/bin/env node

/**
 * Post-build script for CDK Diagram Generator MCP Server
 * 
 * This script copies files from build to dist for GitHub Actions compatibility.
 */

import { existsSync, mkdirSync, readdirSync, copyFileSync, statSync, chmodSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const rootDir = path.resolve(__dirname, '..');
const buildDir = path.join(rootDir, 'build');
const distDir = path.join(rootDir, 'dist');

// Create dist directory if it doesn't exist
if (!existsSync(distDir)) {
  console.log(`Creating dist directory at ${distDir}`);
  mkdirSync(distDir, { recursive: true });
}

// Function to copy files recursively
function copyFilesRecursively(sourceDir, targetDir) {
  // Create the target directory if it doesn't exist
  if (!existsSync(targetDir)) {
    mkdirSync(targetDir, { recursive: true });
  }
  
  // Read all files and directories in the source directory
  const items = readdirSync(sourceDir);
  
  // Copy each item
  for (const item of items) {
    const sourcePath = path.join(sourceDir, item);
    const targetPath = path.join(targetDir, item);
    
    // Check if the item is a directory
    if (statSync(sourcePath).isDirectory()) {
      // Recursively copy the directory
      copyFilesRecursively(sourcePath, targetPath);
    } else {
      // Copy the file
      copyFileSync(sourcePath, targetPath);
      console.log(`Copied ${sourcePath} to ${targetPath}`);
    }
  }
}

// Check if build directory exists
if (existsSync(buildDir)) {
  console.log(`Copying files from ${buildDir} to ${distDir}`);
  copyFilesRecursively(buildDir, distDir);
  
  // Set executable permission on index.js
  const distIndexPath = path.join(distDir, 'index.js');
  if (existsSync(distIndexPath)) {
    console.log(`Setting executable permission on ${distIndexPath}`);
    chmodSync(distIndexPath, '755');
  }
  
  console.log('Done!');
} else {
  console.error(`Build directory does not exist at ${buildDir}`);
  process.exit(1);
}
