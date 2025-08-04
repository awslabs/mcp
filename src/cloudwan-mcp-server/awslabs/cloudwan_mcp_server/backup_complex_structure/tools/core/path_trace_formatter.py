"""
Rich console formatter for path tracing results.

This module provides formatting capabilities for presenting path trace results
in a rich console format with tables, panels, and color-coding.
"""

from typing import Dict, Any, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


class PathTraceFormatter:
    """Formatter for path tracing results with rich console output."""

    def __init__(self, console: Console = None):
        """Initialize the formatter with an optional console."""
        self.console = console or Console()

    def format_path_trace_results(self, analysis: Dict[str, Any]) -> str:
        """Format the path trace results with rich console output."""
        output_parts = []

        # Get key components from analysis
        source_ctx = analysis.get("source_context", {})
        dest_ctx = analysis.get("destination_context", {})
        core_networks = analysis.get("core_networks", [])
        tgw_analysis = analysis.get("transit_gateway_analysis", {})
        routing = analysis.get("routing_analysis", {})
        path_analysis = analysis.get("path_analysis", {})

        # Format Summary Table
        summary_table = self._format_summary_table(
            analysis["source_ip"], analysis["destination_ip"], source_ctx, dest_ctx
        )
        output_parts.append(summary_table)

        # Format Core Networks Table
        if core_networks:
            cn_table = self._format_core_networks_table(core_networks)
            output_parts.append(cn_table)

        # Format TGW Tables
        if tgw_analysis:
            tgw_tables = self._format_tgw_tables(tgw_analysis)
            output_parts.extend(tgw_tables)

        # Format Path Analysis Summary
        path_summary = self._format_path_summary(
            analysis["source_ip"],
            analysis["destination_ip"],
            source_ctx,
            dest_ctx,
            routing,
            path_analysis,
        )
        output_parts.append(path_summary)

        # Render all parts to string
        with self.console.capture() as capture:
            for part in output_parts:
                self.console.print(part)
                self.console.print()

        return capture.get()

    def _format_summary_table(
        self,
        source_ip: str,
        dest_ip: str,
        source_ctx: Dict[str, Any],
        dest_ctx: Dict[str, Any],
    ) -> Table:
        """Format the summary table with source and destination information."""
        summary_table = Table(title="Path Trace Summary", box=box.ROUNDED)
        summary_table.add_column("Attribute", style="cyan")
        summary_table.add_column("Source", style="green")
        summary_table.add_column("Destination", style="yellow")

        summary_table.add_row("IP Address", source_ip, dest_ip)
        summary_table.add_row(
            "Status",
            "✅ Found" if source_ctx.get("found") else "❌ Not Found",
            "✅ Found" if dest_ctx.get("found") else "❌ Not Found",
        )

        if source_ctx.get("found"):
            summary_table.add_row(
                "Region",
                source_ctx.get("region", "N/A"),
                dest_ctx.get("region", "N/A") if dest_ctx.get("found") else "N/A",
            )
            summary_table.add_row(
                "VPC",
                source_ctx.get("vpc_id", "N/A"),
                dest_ctx.get("vpc_id", "N/A") if dest_ctx.get("found") else "N/A",
            )
            summary_table.add_row(
                "Subnet",
                source_ctx.get("subnet_id", "N/A"),
                dest_ctx.get("subnet_id", "N/A") if dest_ctx.get("found") else "N/A",
            )

            # Add CloudWAN segment information
            source_segment = source_ctx.get("segment_info", {}).get("segment_name", "Unknown")
            dest_segment = (
                dest_ctx.get("segment_info", {}).get("segment_name", "Unknown")
                if dest_ctx.get("found")
                else "N/A"
            )
            summary_table.add_row("CloudWAN Segment", source_segment, dest_segment)

        return summary_table

    def _format_core_networks_table(self, core_networks: List[Dict[str, Any]]) -> Table:
        """Format the Core Networks table."""
        cn_table = Table(title="Core Networks", box=box.ROUNDED)
        cn_table.add_column("Core Network ID", style="cyan")
        cn_table.add_column("Global Network ID", style="green")
        cn_table.add_column("State", style="yellow")
        cn_table.add_column("Description", style="magenta")

        for cn in core_networks:
            cn_table.add_row(
                cn.get("core_network_id", ""),
                cn.get("global_network_id", ""),
                cn.get("state", ""),
                cn.get("description", ""),
            )

        return cn_table

    def _format_tgw_tables(self, tgw_analysis: Dict[str, Any]) -> List[Table]:
        """Format Transit Gateway tables for each region."""
        tgw_tables = []

        for region, data in tgw_analysis.items():
            if data.get("transit_gateways"):
                tgw_table = Table(title=f"Transit Gateways - {region}", box=box.ROUNDED)
                tgw_table.add_column("TGW ID", style="cyan")
                tgw_table.add_column("Name", style="green")
                tgw_table.add_column("State", style="yellow")
                tgw_table.add_column("ASN", style="magenta")
                tgw_table.add_column("Peering Connections", style="blue")

                for tgw in data["transit_gateways"]:
                    tgw_table.add_row(
                        tgw.get("transit_gateway_id", ""),
                        tgw.get("name", ""),
                        tgw.get("state", ""),
                        str(tgw.get("asn", "")),
                        str(tgw.get("peering_connections", 0)),
                    )

                tgw_tables.append(tgw_table)

        return tgw_tables

    def _format_path_summary(
        self,
        source_ip: str,
        dest_ip: str,
        source_ctx: Dict[str, Any],
        dest_ctx: Dict[str, Any],
        routing: Dict[str, Any],
        path_analysis: Dict[str, Any],
    ) -> Panel:
        """Format the path analysis summary as a panel."""
        summary_lines = []

        # Path Type
        path_type = path_analysis.get("path_type", "Unknown")
        summary_lines.append(f"🔗 Path Type: {path_type}")

        # CloudWAN path type
        cloudwan_path_type = path_analysis.get("cloudwan_path_type")
        if cloudwan_path_type:
            if cloudwan_path_type == "Intra-segment":
                segments = path_analysis.get("cloudwan_segments", "")
                summary_lines.append(f"🔷 CloudWAN: Intra-segment communication ({segments})")
            elif cloudwan_path_type == "Inter-segment":
                segments = path_analysis.get("cloudwan_segments", "")
                summary_lines.append(f"🔷 CloudWAN: Inter-segment communication ({segments})")
            elif cloudwan_path_type == "Partial-segment":
                source_segment = path_analysis.get("source_segment", "Unknown")
                dest_segment = path_analysis.get("destination_segment", "Unknown")

                if source_segment != "Unknown":
                    summary_lines.append(f"🔷 CloudWAN: Source in {source_segment} segment")
                if dest_segment != "Unknown":
                    summary_lines.append(f"🔷 CloudWAN: Destination in {dest_segment} segment")

        # Routing analysis
        if routing.get("matching_routes"):
            best_route = routing["matching_routes"][0]
            target = best_route.get("target", "")

            if target.startswith("tgw-"):
                summary_lines.append("🚇 Transit Gateway routing detected")
            elif target.startswith("igw-"):
                summary_lines.append("🌐 Internet Gateway routing detected")
            elif target.startswith("nat-"):
                summary_lines.append("🔀 NAT Gateway routing detected")
            elif target == "local":
                summary_lines.append("🏠 Local VPC routing")

            summary_lines.append(
                f"📋 Best matching route: {best_route.get('destination_cidr')} -> {target}"
            )

        # Recommendations
        recommendations = []
        if not source_ctx.get("found"):
            recommendations.append("Verify source IP address is correct and accessible")
        if not dest_ctx.get("found"):
            recommendations.append("Verify destination IP address is correct and accessible")

        if routing.get("matching_routes"):
            best_route = routing["matching_routes"][0]
            if best_route.get("target", "").startswith("tgw-"):
                recommendations.append("Check Transit Gateway route tables and security groups")

        if path_type == "Inter-VPC, cross-region":
            recommendations.append(
                "Review cross-region traffic patterns for potential optimization"
            )

        if recommendations:
            summary_lines.append("\n💡 Recommendations:")
            for rec in recommendations:
                summary_lines.append(f"   • {rec}")

        return Panel("\n".join(summary_lines), title="Path Analysis Summary", style="green")
