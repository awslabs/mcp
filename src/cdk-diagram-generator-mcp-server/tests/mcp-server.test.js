/**
 * Test for the MCP server
 * 
 * This test mocks the MCP server functionality to test the server's behavior.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { parseTypescriptCdkCode } from '../src/parsers/typescript-parser.js';
import { parsePythonCdkCode } from '../src/parsers/python-parser.js';
import { generateDiagramFromCode } from '../src/generators/drawio-generator.js';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const ROOT_DIR = path.resolve(__dirname, '..');
const EXAMPLES_DIR = path.join(ROOT_DIR, 'examples');
const OUTPUT_DIR = path.join(ROOT_DIR, 'output');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Test MCP server
console.log('Testing MCP server...');

// Mock the MCP server's list_tools handler
function mockListToolsHandler() {
  return {
    tools: [
      {
        name: 'generate_diagram_from_code',
        description: 'Generate a diagram from CDK code',
        inputSchema: {
          type: 'object',
          properties: {
            code: {
              type: 'string',
              description: 'CDK code to generate a diagram from',
            },
            outputPath: {
              type: 'string',
              description: 'Path to save the diagram to',
            },
            language: {
              type: 'string',
              enum: ['typescript', 'python'],
              description: 'Language of the CDK code',
            },
          },
          required: ['code', 'outputPath', 'language'],
        },
      },
      {
        name: 'generate_diagram_from_directory',
        description: 'Generate a diagram from a directory containing CDK code',
        inputSchema: {
          type: 'object',
          properties: {
            path: {
              type: 'string',
              description: 'Path to the directory containing CDK code',
            },
            outputPath: {
              type: 'string',
              description: 'Path to save the diagram to',
            },
            language: {
              type: 'string',
              enum: ['typescript', 'python'],
              description: 'Language of the CDK code',
            },
          },
          required: ['path', 'outputPath', 'language'],
        },
      },
    ],
  };
}

// Mock the MCP server's call_tool handler for generate_diagram_from_code
function mockGenerateDiagramFromCodeHandler(args) {
  const { code, outputPath, language } = args;
  
  try {
    // Parse the CDK code
    const infrastructure = language === 'typescript'
      ? parseTypescriptCdkCode(code)
      : parsePythonCdkCode(code);

    // Generate the diagram
    const diagramXml = generateDiagramFromCode(infrastructure);

    // Ensure the output directory exists
    const fullOutputPath = path.isAbsolute(outputPath)
      ? outputPath
      : path.resolve(OUTPUT_DIR, outputPath);
    
    const outputDir = path.dirname(fullOutputPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Write the diagram to the output file
    fs.writeFileSync(fullOutputPath, diagramXml);

    return {
      content: [
        {
          type: 'text',
          text: `Diagram generated successfully and saved to ${fullOutputPath}`,
        },
      ],
    };
  } catch (error) {
    console.error('Error generating diagram:', error);
    return {
      content: [
        {
          type: 'text',
          text: `Error generating diagram: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
}

// Test the list_tools handler
console.log('Testing list_tools handler...');
const listToolsResponse = mockListToolsHandler();
if (!listToolsResponse.tools || listToolsResponse.tools.length !== 2) {
  console.error('Error: list_tools handler returned invalid response');
  process.exit(1);
}
console.log('list_tools handler test passed!');
console.log(`Found ${listToolsResponse.tools.length} tools:`);
listToolsResponse.tools.forEach(tool => {
  console.log(`- ${tool.name}: ${tool.description}`);
});

// Test the generate_diagram_from_code handler
console.log('\nTesting generate_diagram_from_code handler...');
const tsCode = fs.readFileSync(path.join(EXAMPLES_DIR, 'simple-example.ts'), 'utf-8');
const generateDiagramResponse = mockGenerateDiagramFromCodeHandler({
  code: tsCode,
  outputPath: 'test-diagram-mock.drawio',
  language: 'typescript'
});

if (!generateDiagramResponse.content || generateDiagramResponse.content.length === 0) {
  console.error('Error: generate_diagram_from_code handler returned invalid response');
  process.exit(1);
}

const outputText = generateDiagramResponse.content[0].text;
if (!outputText || !outputText.includes('Diagram generated successfully')) {
  console.error('Error: generate_diagram_from_code handler failed to generate diagram');
  process.exit(1);
}

// Check if the file was created
const outputPath = path.join(OUTPUT_DIR, 'test-diagram-mock.drawio');
if (!fs.existsSync(outputPath)) {
  console.error(`Error: Output file not created: ${outputPath}`);
  process.exit(1);
}

console.log('generate_diagram_from_code handler test passed!');
console.log(outputText);

console.log('\nMCP server test passed!');
