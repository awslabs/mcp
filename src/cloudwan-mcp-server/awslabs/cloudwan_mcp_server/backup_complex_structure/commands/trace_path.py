"""CloudWAN MCP Trace Path Command Implementation.

This module provides comprehensive path tracing functionality for CloudWAN networks,
integrating with the PathTracingEngine to discover and analyze network paths.
"""

import asyncio
import json
from typing import Dict, Any, Optional

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from ..engines.path_tracing_engine import (
    PathTracingEngine,
    PathDiscoveryAlgorithm,
    RouteResolutionEngine,
)
from ..engines.tgw_peering_discovery_engine import TGWPeeringDiscoveryEngine
from ..engines.network_function_group_analyzer import NetworkFunctionGroupAnalyzer
from ..engines.cloudwan_policy_evaluator import CloudWANPolicyEvaluator


async def trace_path_async(
    source_ip: str,
    destination_ip: str,
    algorithm: str = "bfs",
    max_paths: int = 10,
    max_hops: int = 15,
    include_cross_account: bool = True,
    include_performance: bool = True,
    regions: Optional[list] = None,
    aws_profile: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trace network paths between two IP addresses asynchronously.
    
    Args:
        source_ip: Source IP address
        destination_ip: Destination IP address
        algorithm: Path discovery algorithm (bfs, dfs, dijkstra, a_star)
        max_paths: Maximum number of paths to discover
        max_hops: Maximum hops per path
        include_cross_account: Include cross-account paths
        include_performance: Include performance metrics
        regions: List of AWS regions to search
        aws_profile: AWS profile to use
        
    Returns:
        Dict containing path analysis results
    """
    # Initialize configuration and AWS client
    config = CloudWANConfig()
    if aws_profile:
        config.aws.default_profile = aws_profile
    if regions:
        config.aws.regions = regions
        
    aws_manager = AWSClientManager(profile=config.aws.default_profile, config=config)
    
    # Initialize engines
    route_engine = RouteResolutionEngine(aws_manager, config)
    peering_engine = TGWPeeringDiscoveryEngine(aws_manager, config)
    nfg_analyzer = NetworkFunctionGroupAnalyzer(aws_manager, config)
    policy_evaluator = CloudWANPolicyEvaluator(aws_manager, config)
    
    # Initialize path tracing engine
    path_engine = PathTracingEngine(
        aws_manager=aws_manager,
        config=config,
        route_engine=route_engine,
        peering_engine=peering_engine,
        nfg_analyzer=nfg_analyzer,
        policy_evaluator=policy_evaluator,
    )
    
    # Map algorithm string to enum
    algorithm_map = {
        "bfs": PathDiscoveryAlgorithm.BFS,
        "dfs": PathDiscoveryAlgorithm.DFS,
        "dijkstra": PathDiscoveryAlgorithm.DIJKSTRA,
        "a_star": PathDiscoveryAlgorithm.A_STAR,
    }
    algo = algorithm_map.get(algorithm.lower(), PathDiscoveryAlgorithm.BFS)
    
    try:
        # Discover paths
        path_analysis = await path_engine.discover_paths(
            source_ip=source_ip,
            destination_ip=destination_ip,
            algorithm=algo,
            max_paths=max_paths,
            max_hops=max_hops,
            include_cross_account=include_cross_account,
        )
        
        # Get detailed trace if requested
        detailed_trace = None
        if include_performance and path_analysis.primary_path:
            detailed_trace = await path_engine.trace_detailed_path(
                source_ip=source_ip,
                destination_ip=destination_ip,
                include_performance_metrics=True,
            )
        
        # Format results
        result = {
            "success": True,
            "source_ip": source_ip,
            "destination_ip": destination_ip,
            "algorithm": algorithm,
            "paths_found": len(path_analysis.discovered_paths),
            "primary_path": None,
            "alternative_paths": [],
            "detailed_trace": detailed_trace,
            "analysis_metadata": {
                "total_time_ms": path_analysis.total_analysis_time_ms,
                "max_paths_analyzed": path_analysis.max_paths_analyzed,
                "path_diversity_score": path_analysis.path_diversity_score,
                "load_balancing_capable": path_analysis.load_balancing_capable,
            },
        }
        
        # Format primary path
        if path_analysis.primary_path:
            primary = path_analysis.primary_path
            result["primary_path"] = {
                "path_type": primary.path_type.value,
                "hop_count": primary.hop_count,
                "total_latency_ms": primary.total_latency_ms,
                "total_cost": primary.total_cost,
                "reliability_score": primary.reliability_score,
                "confidence_score": primary.confidence_score,
                "nodes": [
                    {
                        "node_id": node.node_id,
                        "node_type": node.node_type,
                        "region": node.region,
                        "account_id": node.account_id,
                        "ip_range": node.ip_range,
                        "segment_name": node.segment_name,
                    }
                    for node in primary.path_nodes
                ],
                "edges": [
                    {
                        "source": edge.source_node,
                        "destination": edge.destination_node,
                        "edge_type": edge.edge_type,
                        "connection_id": edge.connection_id,
                        "latency_ms": edge.latency_ms,
                        "cost": edge.cost,
                    }
                    for edge in primary.path_edges
                ],
                "inspection_points": primary.inspection_points,
                "warnings": primary.warnings,
            }
        
        # Format alternative paths
        for alt_path in path_analysis.alternative_paths[:5]:  # Limit to 5 alternatives
            result["alternative_paths"].append({
                "path_type": alt_path.path_type.value,
                "hop_count": alt_path.hop_count,
                "total_latency_ms": alt_path.total_latency_ms,
                "reliability_score": alt_path.reliability_score,
                "summary": f"{alt_path.hop_count} hops via {alt_path.path_type.value}",
            })
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "source_ip": source_ip,
            "destination_ip": destination_ip,
        }
    finally:
        # Cleanup
        await path_engine.cleanup()


def trace_path(args):
    """
    Trace the full path between endpoints.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    # Extract arguments
    source_ip = getattr(args, 'source_ip', None)
    destination_ip = getattr(args, 'destination_ip', None)
    algorithm = getattr(args, 'algorithm', 'bfs')
    max_paths = getattr(args, 'max_paths', 10)
    max_hops = getattr(args, 'max_hops', 15)
    include_cross_account = getattr(args, 'cross_account', True)
    include_performance = getattr(args, 'performance', True)
    regions = getattr(args, 'regions', None)
    aws_profile = getattr(args, 'profile', None)
    output_format = getattr(args, 'format', 'pretty')
    
    # Validate required arguments
    if not source_ip or not destination_ip:
        print("Error: Both source and destination IP addresses are required")
        print("Usage: trace path <source_ip> <destination_ip> [options]")
        return
    
    # Run the async function
    result = asyncio.run(trace_path_async(
        source_ip=source_ip,
        destination_ip=destination_ip,
        algorithm=algorithm,
        max_paths=max_paths,
        max_hops=max_hops,
        include_cross_account=include_cross_account,
        include_performance=include_performance,
        regions=regions,
        aws_profile=aws_profile,
    ))
    
    # Format output
    if output_format == 'json':
        print(json.dumps(result, indent=2))
    else:
        # Pretty print format
        if result["success"]:
            print("\nPath Trace Results")
            print("==================")
            print(f"Source: {result['source_ip']}")
            print(f"Destination: {result['destination_ip']}")
            print(f"Algorithm: {result['algorithm'].upper()}")
            print(f"Paths Found: {result['paths_found']}")
            
            if result['primary_path']:
                primary = result['primary_path']
                print("\nPrimary Path:")
                print(f"  Type: {primary['path_type']}")
                print(f"  Hops: {primary['hop_count']}")
                print(f"  Latency: {primary['total_latency_ms']:.2f}ms")
                print(f"  Reliability: {primary['reliability_score']:.2%}")
                print(f"  Confidence: {primary['confidence_score']:.2%}")
                
                print("\n  Path Details:")
                for i, node in enumerate(primary['nodes']):
                    print(f"    {i+1}. {node['node_type']} - {node['node_id']}")
                    if node['segment_name']:
                        print(f"       Segment: {node['segment_name']}")
                    print(f"       Region: {node['region']}, Account: {node['account_id']}")
                    
                    if i < len(primary['edges']):
                        edge = primary['edges'][i]
                        print(f"       ↓ {edge['edge_type']} ({edge['latency_ms']}ms)")
                
                if primary['warnings']:
                    print("\n  Warnings:")
                    for warning in primary['warnings']:
                        print(f"    - {warning}")
            
            if result['alternative_paths']:
                print("\nAlternative Paths:")
                for i, alt in enumerate(result['alternative_paths'], 1):
                    print(f"  {i}. {alt['summary']} (latency: {alt['total_latency_ms']:.2f}ms)")
            
            if result['detailed_trace'] and result['detailed_trace'].get('trace_hops'):
                print("\nDetailed Hop Analysis:")
                for hop in result['detailed_trace']['trace_hops'][:10]:  # Limit to 10 hops
                    print(f"  Hop {hop['hop_number']}: {hop['node_type']} - {hop['node_id']}")
                    if 'performance_metrics' in hop:
                        metrics = hop['performance_metrics']
                        print(f"    Latency: {metrics['latency_ms']}ms, "
                              f"Reliability: {metrics['reliability_score']:.2%}")
            
            print(f"\nAnalysis completed in {result['analysis_metadata']['total_time_ms']:.2f}ms")
        else:
            print(f"\nPath trace failed: {result.get('error', 'Unknown error')}")