/**
 * Test for the DrawIO generator
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { generateDiagramFromCode } from '../src/generators/drawio-generator.js';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const ROOT_DIR = path.resolve(__dirname, '..');
const OUTPUT_DIR = path.join(ROOT_DIR, 'output');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Test DrawIO generator
console.log('Testing DrawIO generator...');
try {
  // Create a simple infrastructure object
  const infrastructure = {
    resources: [
      {
        id: 'lambda1',
        type: 'lambda',
        name: 'ApiFunction',
        properties: {
          runtime: 'nodejs18.x',
          handler: 'index.handler'
        }
      },
      {
        id: 'dynamodb1',
        type: 'dynamodb',
        name: 'ItemsTable',
        properties: {
          hashKey: 'id'
        }
      }
    ],
    connections: [
      {
        source: 'lambda1',
        target: 'dynamodb1',
        type: 'uses'
      }
    ],
    vpcs: [
      {
        id: 'vpc1',
        name: 'MainVPC',
        resources: [
          {
            id: 'subnet1',
            type: 'subnet',
            name: 'PublicSubnet',
            properties: {
              cidrBlock: '10.0.1.0/24'
            }
          }
        ]
      }
    ]
  };
  
  // Generate the diagram
  const diagramXml = generateDiagramFromCode(infrastructure);
  
  // Check if the diagram XML is valid
  if (!diagramXml) {
    throw new Error('Failed to generate diagram XML');
  }
  
  if (!diagramXml.includes('<mxGraphModel')) {
    throw new Error('Invalid diagram XML: missing mxGraphModel tag');
  }
  
  // Save the diagram to a file
  const outputPath = path.join(OUTPUT_DIR, 'test-diagram.drawio');
  fs.writeFileSync(outputPath, diagramXml);
  
  console.log('DrawIO generator test passed!');
  console.log(`Diagram saved to ${outputPath}`);
  console.log(`Diagram size: ${diagramXml.length} bytes`);
} catch (error) {
  console.error('Error testing DrawIO generator:', error);
  process.exit(1);
}
