/**
 * Draw.io Diagram Generator
 * 
 * This file contains functions for generating draw.io diagrams from the infrastructure model.
 */

import { Infrastructure, Resource, Connection, VPC } from '../models/infrastructure.js';

// Constants for diagram generation
const CELL_WIDTH = 120;
const CELL_HEIGHT = 60;
const CELL_SPACING = 80;
const VPC_PADDING = 40;

// AWS service icons (base64 encoded SVG would go here in a real implementation)
const AWS_ICONS: Record<string, string> = {
  lambda: 'AWS Lambda',
  dynamodb: 'Amazon DynamoDB',
  s3: 'Amazon S3',
  apigateway: 'Amazon API Gateway',
  vpc: 'Amazon VPC',
  default: 'AWS Cloud'
};

/**
 * Generate a draw.io diagram from the infrastructure model
 * 
 * @param infrastructure Infrastructure model
 * @returns draw.io XML diagram
 */
export function generateDiagramFromCode(infrastructure: Infrastructure): string {
  // Start the draw.io XML
  let diagram = '<?xml version="1.0" encoding="UTF-8"?>\n';
  diagram += '<mxfile host="app.diagrams.net" modified="2023-01-01T00:00:00.000Z" agent="CDK Diagram Generator" version="14.6.13">\n';
  diagram += '  <diagram id="cdk-diagram" name="CDK Infrastructure">\n';
  diagram += '    <mxGraphModel dx="1422" dy="798" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">\n';
  diagram += '      <root>\n';
  diagram += '        <mxCell id="0" />\n';
  diagram += '        <mxCell id="1" parent="0" />\n';

  // Track the IDs of cells for connections
  const cellIds: Record<string, string> = {};
  let nextId = 2; // Start from 2 as 0 and 1 are reserved

  // Add VPCs first
  infrastructure.vpcs.forEach((vpc, vpcIndex) => {
    const vpcId = `vpc-${nextId++}`;
    cellIds[vpc.id] = vpcId;
    
    // Calculate VPC size based on resources
    const resourceCount = vpc.resources.length;
    const cols = Math.ceil(Math.sqrt(resourceCount));
    const rows = Math.ceil(resourceCount / cols);
    
    const vpcWidth = cols * CELL_WIDTH + (cols - 1) * CELL_SPACING + 2 * VPC_PADDING;
    const vpcHeight = rows * CELL_HEIGHT + (rows - 1) * CELL_SPACING + 2 * VPC_PADDING;
    
    // Position the VPC
    const vpcX = 100 + vpcIndex * (vpcWidth + CELL_SPACING);
    const vpcY = 100;
    
    // Add the VPC
    diagram += `        <mxCell id="${vpcId}" value="${vpc.name}" style="points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc;strokeColor=#248814;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#AAB7B8;dashed=0;" parent="1" vertex="1">\n`;
    diagram += `          <mxGeometry x="${vpcX}" y="${vpcY}" width="${vpcWidth}" height="${vpcHeight}" as="geometry" />\n`;
    diagram += `        </mxCell>\n`;
    
    // Add resources in the VPC
    vpc.resources.forEach((resource, resourceIndex) => {
      const col = resourceIndex % cols;
      const row = Math.floor(resourceIndex / cols);
      
      const resourceX = VPC_PADDING + col * (CELL_WIDTH + CELL_SPACING);
      const resourceY = VPC_PADDING + row * (CELL_HEIGHT + CELL_SPACING);
      
      const resourceId = `resource-${nextId++}`;
      cellIds[resource.id] = resourceId;
      
      // Add the resource
      diagram += `        <mxCell id="${resourceId}" value="${resource.name}" style="outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#D05C17;strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.${AWS_ICONS[resource.type] || AWS_ICONS.default};" parent="${vpcId}" vertex="1">\n`;
      diagram += `          <mxGeometry x="${resourceX}" y="${resourceY}" width="${CELL_WIDTH}" height="${CELL_HEIGHT}" as="geometry" />\n`;
      diagram += `        </mxCell>\n`;
    });
  });
  
  // Add resources outside VPCs
  infrastructure.resources.forEach((resource, resourceIndex) => {
    const col = resourceIndex % 4; // Arrange in a grid, 4 columns
    const row = Math.floor(resourceIndex / 4);
    
    const resourceX = 100 + col * (CELL_WIDTH + CELL_SPACING);
    const resourceY = 400 + row * (CELL_HEIGHT + CELL_SPACING); // Position below VPCs
    
    const resourceId = `resource-${nextId++}`;
    cellIds[resource.id] = resourceId;
    
    // Add the resource
    diagram += `        <mxCell id="${resourceId}" value="${resource.name}" style="outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#D05C17;strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.${AWS_ICONS[resource.type] || AWS_ICONS.default};" parent="1" vertex="1">\n`;
    diagram += `          <mxGeometry x="${resourceX}" y="${resourceY}" width="${CELL_WIDTH}" height="${CELL_HEIGHT}" as="geometry" />\n`;
    diagram += `        </mxCell>\n`;
  });
  
  // Add connections
  infrastructure.connections.forEach((connection, connectionIndex) => {
    const sourceId = cellIds[connection.source];
    const targetId = cellIds[connection.target];
    
    if (sourceId && targetId) {
      const connectionId = `connection-${nextId++}`;
      
      // Add the connection
      diagram += `        <mxCell id="${connectionId}" value="${connection.type}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;startArrow=none;startFill=0;endArrow=classic;endFill=1;" parent="1" source="${sourceId}" target="${targetId}" edge="1">\n`;
      diagram += `          <mxGeometry relative="1" as="geometry" />\n`;
      diagram += `        </mxCell>\n`;
    }
  });
  
  // Close the draw.io XML
  diagram += '      </root>\n';
  diagram += '    </mxGraphModel>\n';
  diagram += '  </diagram>\n';
  diagram += '</mxfile>';
  
  return diagram;
}
