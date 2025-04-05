/**
 * Infrastructure model for CDK Diagram Generator
 * 
 * This file defines the data structures used to represent AWS infrastructure.
 */

export interface Resource {
  id: string;
  type: string;
  name: string;
  properties?: Record<string, any>;
}

export interface Connection {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, any>;
}

export interface VPC {
  id: string;
  name: string;
  resources: Resource[];
}

export interface Infrastructure {
  resources: Resource[];
  connections: Connection[];
  vpcs: VPC[];
}

export function createEmptyInfrastructure(): Infrastructure {
  return {
    resources: [],
    connections: [],
    vpcs: [],
  };
}

export function addResource(infrastructure: Infrastructure, resource: Resource): Infrastructure {
  return {
    ...infrastructure,
    resources: [...infrastructure.resources, resource],
  };
}

export function addConnection(infrastructure: Infrastructure, connection: Connection): Infrastructure {
  return {
    ...infrastructure,
    connections: [...infrastructure.connections, connection],
  };
}

export function addVPC(infrastructure: Infrastructure, vpc: VPC): Infrastructure {
  return {
    ...infrastructure,
    vpcs: [...infrastructure.vpcs, vpc],
  };
}

export function addResourceToVPC(infrastructure: Infrastructure, vpcId: string, resource: Resource): Infrastructure {
  const updatedVPCs = infrastructure.vpcs.map(vpc => {
    if (vpc.id === vpcId) {
      return {
        ...vpc,
        resources: [...vpc.resources, resource],
      };
    }
    return vpc;
  });

  return {
    ...infrastructure,
    vpcs: updatedVPCs,
  };
}
