# What is Cell-Based Architecture?

## Definition

A cell-based architecture comes from the concept of a bulkhead in a ship, where vertical partition walls subdivide the ship's interior into self-contained, watertight compartments. Bulkheads reduce the extent of seawater flooding in case of damage and provide additional stiffness to the hull girder.

## Bulkhead Pattern

On a ship, bulkheads ensure that a hull breach is contained within one section of the ship. In complex systems, this pattern is often replicated to allow fault isolation. Fault isolated boundaries restrict the effect of a failure within a workload to a limited number of components. Components outside of the boundary are unaffected by the failure.

## Core Concept

A cell-based architecture uses multiple isolated instances of a workload, where each instance is known as a **cell**. Each cell is:
- **Independent** - does not share state with other cells
- **Self-contained** - handles a subset of the overall workload requests
- **Isolated** - reduces the potential impact of failures

## Impact Reduction

If a workload uses 10 cells to service 100 requests, when a failure occurs in one cell, 90% of the overall requests would be unaffected by the failure.

## Partition Key

The overall workload is partitioned by a **partition key**. This key needs to align with the grain of the service, or the natural way that a service's workload can be subdivided with minimal cross-cell interactions. 

Examples of partition keys:
- Customer ID
- Resource ID  
- Any other parameter easily accessible in most API calls

## Cell Router

A **cell routing layer** distributes requests to individual cells based on the partition key and presents a single endpoint to clients.

## Fault Isolation Benefits

With cell-based architectures, many common types of failure are contained within the cell itself, providing additional fault isolation. These fault boundaries can provide resilience against failure types that otherwise are hard to contain, such as:
- Unsuccessful code deployments
- Requests that are corrupted or invoke a specific failure mode (poison pill requests)
- Traffic spikes affecting specific partitions