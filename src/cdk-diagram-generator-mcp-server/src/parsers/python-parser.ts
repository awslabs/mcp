/**
 * Python CDK Parser
 * 
 * This file contains functions for parsing Python CDK code and extracting AWS resources.
 */

import {
  Infrastructure,
  Resource,
  Connection,
  VPC,
  createEmptyInfrastructure,
  addResource,
  addConnection,
  addVPC,
  addResourceToVPC
} from '../models/infrastructure.js';

/**
 * Parse Python CDK code and extract AWS resources
 * 
 * @param code Python CDK code
 * @returns Infrastructure model
 */
export function parsePythonCdkCode(code: string): Infrastructure {
  // Create an empty infrastructure model
  let infrastructure = createEmptyInfrastructure();

  try {
    // Extract VPCs
    const vpcRegex = /ec2\.Vpc\s*\(\s*self\s*,\s*["']([^"']+)["']/g;
    let vpcMatch;
    while ((vpcMatch = vpcRegex.exec(code)) !== null) {
      const vpcId = vpcMatch[1];
      const vpc: VPC = {
        id: vpcId,
        name: vpcId,
        resources: []
      };
      infrastructure = addVPC(infrastructure, vpc);
    }

    // Extract Lambda functions
    const lambdaRegex = /lambda_\.Function\s*\(\s*self\s*,\s*["']([^"']+)["']/g;
    let lambdaMatch;
    while ((lambdaMatch = lambdaRegex.exec(code)) !== null) {
      const lambdaId = lambdaMatch[1];
      
      // Check if the Lambda is in a VPC
      const vpcRegex = new RegExp(`${lambdaId}[\\s\\S]*?vpc\\s*=\\s*([\\w]+)`, 'm');
      const vpcMatch = code.match(vpcRegex);
      
      const lambdaResource: Resource = {
        id: lambdaId,
        type: 'lambda',
        name: lambdaId
      };
      
      if (vpcMatch) {
        const vpcVarName = vpcMatch[1];
        // Find the VPC ID
        const vpcIdRegex = new RegExp(`${vpcVarName}\\s*=\\s*ec2\\.Vpc\\s*\\(\\s*self\\s*,\\s*["']([^"']+)["'](.|\\s)*?\\)`, 'm');
        const vpcIdMatch = code.match(vpcIdRegex);
        
        if (vpcIdMatch) {
          const vpcId = vpcIdMatch[1];
          infrastructure = addResourceToVPC(infrastructure, vpcId, lambdaResource);
        } else {
          infrastructure = addResource(infrastructure, lambdaResource);
        }
      } else {
        infrastructure = addResource(infrastructure, lambdaResource);
      }
    }

    // Extract DynamoDB tables
    const dynamoRegex = /dynamodb\.Table\s*\(\s*self\s*,\s*["']([^"']+)["']/g;
    let dynamoMatch;
    while ((dynamoMatch = dynamoRegex.exec(code)) !== null) {
      const tableId = dynamoMatch[1];
      const tableResource: Resource = {
        id: tableId,
        type: 'dynamodb',
        name: tableId
      };
      infrastructure = addResource(infrastructure, tableResource);
    }

    // Extract S3 buckets
    const s3Regex = /s3\.Bucket\s*\(\s*self\s*,\s*["']([^"']+)["']/g;
    let s3Match;
    while ((s3Match = s3Regex.exec(code)) !== null) {
      const bucketId = s3Match[1];
      const bucketResource: Resource = {
        id: bucketId,
        type: 's3',
        name: bucketId
      };
      infrastructure = addResource(infrastructure, bucketResource);
    }

    // Extract API Gateway
    const apiGatewayRegex = /apigateway\.RestApi\s*\(\s*self\s*,\s*["']([^"']+)["']/g;
    let apiGatewayMatch;
    while ((apiGatewayMatch = apiGatewayRegex.exec(code)) !== null) {
      const apiId = apiGatewayMatch[1];
      const apiResource: Resource = {
        id: apiId,
        type: 'apigateway',
        name: apiId
      };
      infrastructure = addResource(infrastructure, apiResource);
    }

    // Extract connections between Lambda and DynamoDB
    const grantReadWriteRegex = /(\w+)\.grant_read_write_data\s*\(\s*(\w+)\s*\)/g;
    let grantMatch;
    while ((grantMatch = grantReadWriteRegex.exec(code)) !== null) {
      const sourceId = grantMatch[1];
      const targetId = grantMatch[2];
      
      const connection: Connection = {
        source: sourceId,
        target: targetId,
        type: 'access'
      };
      infrastructure = addConnection(infrastructure, connection);
    }

    // Extract connections between Lambda and S3
    const grantReadWriteS3Regex = /(\w+)\.grant_read_write\s*\(\s*(\w+)\s*\)/g;
    let grantS3Match;
    while ((grantS3Match = grantReadWriteS3Regex.exec(code)) !== null) {
      const sourceId = grantS3Match[1];
      const targetId = grantS3Match[2];
      
      const connection: Connection = {
        source: sourceId,
        target: targetId,
        type: 'access'
      };
      infrastructure = addConnection(infrastructure, connection);
    }

    // Extract connections between API Gateway and Lambda
    const lambdaIntegrationRegex = /apigateway\.LambdaIntegration\s*\(\s*(\w+)\s*\)/g;
    let lambdaIntegrationMatch;
    while ((lambdaIntegrationMatch = lambdaIntegrationRegex.exec(code)) !== null) {
      const lambdaId = lambdaIntegrationMatch[1];
      
      // Find the API Gateway that uses this integration
      const apiMethodRegex = new RegExp(`(\\w+)\\.add_method\\s*\\([^\\)]*${lambdaId}`, 'm');
      const apiMethodMatch = code.match(apiMethodRegex);
      
      if (apiMethodMatch) {
        const resourceId = apiMethodMatch[1];
        
        // Find the API Gateway that owns this resource
        const apiResourceRegex = new RegExp(`${resourceId}\\s*=\\s*(\\w+)\\.\\w+\\.add_resource`, 'm');
        const apiResourceMatch = code.match(apiResourceRegex);
        
        if (apiResourceMatch) {
          const apiId = apiResourceMatch[1];
          
          const connection: Connection = {
            source: apiId,
            target: lambdaId,
            type: 'invoke'
          };
          infrastructure = addConnection(infrastructure, connection);
        }
      }
    }

  } catch (error) {
    console.error('Error parsing Python CDK code:', error);
  }

  return infrastructure;
}
