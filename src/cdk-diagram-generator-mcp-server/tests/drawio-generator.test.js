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
        id: 'vpc1',
        type: 'AWS::EC2::VPC',
        name: 'MainVPC',
        properties: {
          cidrBlock: '10.0.0.0/16'
        }
      },
      {
        id: 'subnet1',
        type: 'AWS::EC2::Subnet',
        name: 'PublicSubnet',
        properties: {
          vpcId: 'vpc1',
          cidrBlock: '10.0.1.0/24'
        }
      },
      {
        id: 'lambda1',
        type: 'AWS::Lambda::Function',
        name: 'ApiFunction',
        properties: {
          runtime: 'nodejs18.x',
          handler: 'index.handler'
        }
      }
    ],
    connections: [
      {
        source: 'subnet1',
        target: 'vpc1',
        type: 'contains'
      },
      {
        source: 'lambda1',
        target: 'subnet1',
        type: 'uses'
      }
    ],
    vpcs: []
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
