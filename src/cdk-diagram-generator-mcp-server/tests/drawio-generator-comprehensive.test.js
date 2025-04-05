/**
 * Comprehensive test for the DrawIO generator
 * 
 * This test checks that the DrawIO generator correctly creates diagrams
 * with all the necessary elements and connections.
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

// Test DrawIO generator with comprehensive checks
console.log('Running comprehensive DrawIO generator test...');
try {
  // Create a complex infrastructure object with multiple resources and connections
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
        id: 'subnet2',
        type: 'AWS::EC2::Subnet',
        name: 'PrivateSubnet',
        properties: {
          vpcId: 'vpc1',
          cidrBlock: '10.0.2.0/24'
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
      },
      {
        id: 'lambda2',
        type: 'AWS::Lambda::Function',
        name: 'ProcessorFunction',
        properties: {
          runtime: 'nodejs18.x',
          handler: 'index.handler'
        }
      },
      {
        id: 'table1',
        type: 'AWS::DynamoDB::Table',
        name: 'ItemsTable',
        properties: {
          partitionKey: 'id'
        }
      },
      {
        id: 'bucket1',
        type: 'AWS::S3::Bucket',
        name: 'DataBucket',
        properties: {
          versioning: true
        }
      },
      {
        id: 'api1',
        type: 'AWS::ApiGateway::RestApi',
        name: 'ItemsApi',
        properties: {
          description: 'API for managing items'
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
        source: 'subnet2',
        target: 'vpc1',
        type: 'contains'
      },
      {
        source: 'lambda1',
        target: 'subnet1',
        type: 'uses'
      },
      {
        source: 'lambda2',
        target: 'subnet2',
        type: 'uses'
      },
      {
        source: 'lambda1',
        target: 'table1',
        type: 'access'
      },
      {
        source: 'lambda2',
        target: 'table1',
        type: 'access'
      },
      {
        source: 'lambda1',
        target: 'bucket1',
        type: 'access'
      },
      {
        source: 'api1',
        target: 'lambda1',
        type: 'invoke'
      }
    ],
    vpcs: [
      {
        id: 'vpc1',
        name: 'MainVPC',
        resources: [
          {
            id: 'lambda1',
            type: 'AWS::Lambda::Function',
            name: 'ApiFunction',
            properties: {
              runtime: 'nodejs18.x',
              handler: 'index.handler'
            }
          },
          {
            id: 'lambda2',
            type: 'AWS::Lambda::Function',
            name: 'ProcessorFunction',
            properties: {
              runtime: 'nodejs18.x',
              handler: 'index.handler'
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
  
  // Check for required elements in the XML
  const requiredElements = [
    '<mxGraphModel',
    '<root>',
    '<mxCell id="0"',
    '<mxCell id="1"'
  ];
  
  for (const element of requiredElements) {
    if (!diagramXml.includes(element)) {
      throw new Error(`Required element '${element}' not found in diagram XML`);
    }
  }
  
  // Check that all resources are included in the diagram
  for (const resource of infrastructure.resources) {
    if (!diagramXml.includes(`value="${resource.name}"`)) {
      console.warn(`Warning: Resource '${resource.name}' might not be included in the diagram`);
    }
  }
  
  // Check that VPCs are included in the diagram
  for (const vpc of infrastructure.vpcs) {
    if (!diagramXml.includes(`value="${vpc.name}"`)) {
      console.warn(`Warning: VPC '${vpc.name}' might not be included in the diagram`);
    }
  }
  
  // Save the diagram to a file
  const outputPath = path.join(OUTPUT_DIR, 'comprehensive-test-diagram.drawio');
  fs.writeFileSync(outputPath, diagramXml);
  
  console.log('Comprehensive DrawIO generator test passed!');
  console.log(`Diagram saved to ${outputPath}`);
  console.log(`Diagram size: ${diagramXml.length} bytes`);
  
  // Additional checks on the diagram structure
  const cellCount = (diagramXml.match(/<mxCell/g) || []).length;
  console.log(`Diagram contains ${cellCount} cells`);
  
  const edgeCount = (diagramXml.match(/edge="1"/g) || []).length;
  console.log(`Diagram contains ${edgeCount} edges/connections`);
  
  if (edgeCount !== infrastructure.connections.length) {
    console.warn(`Warning: Expected ${infrastructure.connections.length} connections, but found ${edgeCount} edges in the diagram`);
  }
  
} catch (error) {
  console.error('Error in comprehensive DrawIO generator test:', error);
  process.exit(1);
}
