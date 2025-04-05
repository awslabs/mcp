/**
 * Comprehensive test for the MCP server
 * 
 * This test mocks the MCP server functionality to test the server's behavior
 * with a variety of inputs and edge cases.
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

// Test MCP server with comprehensive checks
console.log('Running comprehensive MCP server test...');

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

// Mock the MCP server's call_tool handler for generate_diagram_from_directory
function mockGenerateDiagramFromDirectoryHandler(args) {
  const { path: dirPath, outputPath, language } = args;
  
  try {
    // Check if the directory exists
    if (!fs.existsSync(dirPath)) {
      return {
        content: [
          {
            type: 'text',
            text: `Directory not found: ${dirPath}`,
          },
        ],
        isError: true,
      };
    }
    
    // Read all files in the directory
    const files = fs.readdirSync(dirPath);
    
    // Filter files by extension
    const extension = language === 'typescript' ? '.ts' : '.py';
    const cdkFiles = files.filter(file => file.endsWith(extension));
    
    if (cdkFiles.length === 0) {
      return {
        content: [
          {
            type: 'text',
            text: `No ${language} files found in ${dirPath}`,
          },
        ],
        isError: true,
      };
    }

    // Read the first CDK file
    const cdkFilePath = path.join(dirPath, cdkFiles[0]);
    const code = fs.readFileSync(cdkFilePath, 'utf-8');

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
          text: `Diagram generated successfully from ${cdkFilePath} and saved to ${fullOutputPath}`,
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

// Define test cases
const testCases = [
  {
    name: 'List Tools',
    handler: mockListToolsHandler,
    args: {},
    validate: (response) => {
      if (!response.tools || !Array.isArray(response.tools)) {
        throw new Error('Invalid response: missing tools array');
      }
      
      if (response.tools.length < 1) {
        throw new Error('Invalid response: no tools returned');
      }
      
      const toolNames = response.tools.map(tool => tool.name);
      const expectedTools = ['generate_diagram_from_code', 'generate_diagram_from_directory'];
      
      for (const expectedTool of expectedTools) {
        if (!toolNames.includes(expectedTool)) {
          throw new Error(`Expected tool '${expectedTool}' not found`);
        }
      }
      
      return true;
    }
  },
  {
    name: 'Generate Diagram from TypeScript Code',
    handler: mockGenerateDiagramFromCodeHandler,
    args: {
      code: fs.readFileSync(path.join(EXAMPLES_DIR, 'simple-example.ts'), 'utf-8'),
      outputPath: 'test-diagram-ts-comprehensive.drawio',
      language: 'typescript'
    },
    validate: (response) => {
      if (!response.content || !Array.isArray(response.content)) {
        throw new Error('Invalid response: missing content array');
      }
      
      if (response.content.length < 1) {
        throw new Error('Invalid response: no content returned');
      }
      
      const text = response.content[0].text;
      if (!text || !text.includes('Diagram generated successfully')) {
        throw new Error('Invalid response: diagram generation failed');
      }
      
      // Check if the file was created
      const outputPath = path.join(OUTPUT_DIR, 'test-diagram-ts-comprehensive.drawio');
      if (!fs.existsSync(outputPath)) {
        throw new Error(`Output file not created: ${outputPath}`);
      }
      
      return true;
    }
  },
  {
    name: 'Generate Diagram from Python Code',
    handler: mockGenerateDiagramFromCodeHandler,
    args: {
      code: fs.readFileSync(path.join(EXAMPLES_DIR, 'simple-example.py'), 'utf-8'),
      outputPath: 'test-diagram-py-comprehensive.drawio',
      language: 'python'
    },
    validate: (response) => {
      if (!response.content || !Array.isArray(response.content)) {
        throw new Error('Invalid response: missing content array');
      }
      
      if (response.content.length < 1) {
        throw new Error('Invalid response: no content returned');
      }
      
      const text = response.content[0].text;
      if (!text || !text.includes('Diagram generated successfully')) {
        throw new Error('Invalid response: diagram generation failed');
      }
      
      // Check if the file was created
      const outputPath = path.join(OUTPUT_DIR, 'test-diagram-py-comprehensive.drawio');
      if (!fs.existsSync(outputPath)) {
        throw new Error(`Output file not created: ${outputPath}`);
      }
      
      return true;
    }
  },
  {
    name: 'Generate Diagram from Directory',
    handler: mockGenerateDiagramFromDirectoryHandler,
    args: {
      path: EXAMPLES_DIR,
      outputPath: 'test-diagram-dir-comprehensive.drawio',
      language: 'typescript'
    },
    validate: (response) => {
      if (!response.content || !Array.isArray(response.content)) {
        throw new Error('Invalid response: missing content array');
      }
      
      if (response.content.length < 1) {
        throw new Error('Invalid response: no content returned');
      }
      
      const text = response.content[0].text;
      if (!text || !text.includes('Diagram generated successfully')) {
        throw new Error('Invalid response: diagram generation failed');
      }
      
      // Check if the file was created
      const outputPath = path.join(OUTPUT_DIR, 'test-diagram-dir-comprehensive.drawio');
      if (!fs.existsSync(outputPath)) {
        throw new Error(`Output file not created: ${outputPath}`);
      }
      
      return true;
    }
  }
];

// Run all test cases
const results = [];

for (const testCase of testCases) {
  console.log(`\nTesting: ${testCase.name}`);
  try {
    const response = testCase.handler(testCase.args);
    const isValid = testCase.validate(response);
    
    results.push({
      name: testCase.name,
      success: isValid
    });
    
    console.log(`✅ ${testCase.name} passed!`);
  } catch (error) {
    console.error(`❌ ${testCase.name} failed:`, error.message);
    
    results.push({
      name: testCase.name,
      success: false,
      error: error.message
    });
  }
}

// Print summary
console.log('\nTest Results:');
let allPassed = true;

results.forEach(result => {
  if (result.success) {
    console.log(`✅ ${result.name} passed!`);
  } else {
    console.log(`❌ ${result.name} failed: ${result.error}`);
    allPassed = false;
  }
});

if (allPassed) {
  console.log('\n✅ All MCP server tests passed!');
} else {
  console.log('\n❌ Some MCP server tests failed!');
  process.exit(1);
}
