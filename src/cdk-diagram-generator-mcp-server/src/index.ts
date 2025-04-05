#!/usr/bin/env node

/**
 * CDK Diagram Generator MCP Server
 * 
 * This server generates architectural diagrams from AWS CDK code.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { generateDiagramFromCode } from './generators/drawio-generator.js';
import { parseTypescriptCdkCode } from './parsers/typescript-parser.js';
import { parsePythonCdkCode } from './parsers/python-parser.js';

// Get the directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Default output directory
const DEFAULT_OUTPUT_DIR = process.env.CDK_DIAGRAM_OUTPUT_DIR || path.resolve(__dirname, '../output');

class CdkDiagramGeneratorServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: 'cdk-diagram-generator',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
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
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      switch (request.params.name) {
        case 'generate_diagram_from_code': {
          const { code, outputPath, language } = request.params.arguments as {
            code: string;
            outputPath: string;
            language: 'typescript' | 'python';
          };

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
              : path.resolve(DEFAULT_OUTPUT_DIR, outputPath);
            
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

        case 'generate_diagram_from_directory': {
          const { path: dirPath, outputPath, language } = request.params.arguments as {
            path: string;
            outputPath: string;
            language: 'typescript' | 'python';
          };

          try {
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
              : path.resolve(DEFAULT_OUTPUT_DIR, outputPath);
            
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

        default:
          throw new McpError(
            ErrorCode.MethodNotFound,
            `Unknown tool: ${request.params.name}`
          );
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('CDK Diagram Generator MCP server running on stdio');
  }
}

const server = new CdkDiagramGeneratorServer();
server.run().catch(console.error);
