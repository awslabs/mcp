"""AWS Well-Architected Best Practices MCP Server."""

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("AWS Well-Architected Best Practices")

# Load best practices data
DATA_DIR = Path(__file__).parent / "data"
BEST_PRACTICES: dict[str, list[dict[str, Any]]] = {}

def load_data():
    """Load all best practices from JSON files."""
    global BEST_PRACTICES
    
    # Load framework pillars
    for pillar_file in ["operational_excellence", "security", "reliability", 
                        "performance_efficiency", "cost_optimization", "sustainability"]:
        file_path = DATA_DIR / f"{pillar_file}.json"
        if file_path.exists():
            with open(file_path) as f:
                BEST_PRACTICES[pillar_file] = json.load(f)
    
    # Load lens data
    lens_dir = DATA_DIR / "lens" / "generative-ai"
    if lens_dir.exists():
        for lens_file in lens_dir.glob("*.json"):
            key = f"genai_{lens_file.stem}"
            with open(lens_file) as f:
                BEST_PRACTICES[key] = json.load(f)

load_data()

@mcp.tool()
def search_best_practices(
    pillar: str | None = None,
    risk: str | None = None,
    lens: str | None = None,
    keyword: str | None = None,
    area: str | None = None
) -> list[dict[str, Any]]:
    """Search and filter AWS Well-Architected best practices.
    
    Args:
        pillar: Filter by pillar (OPERATIONAL_EXCELLENCE, SECURITY, RELIABILITY, 
                PERFORMANCE_EFFICIENCY, COST_OPTIMIZATION, SUSTAINABILITY)
        risk: Filter by risk level (HIGH, MEDIUM, LOW)
        lens: Filter by lens (FRAMEWORK, GENERATIVE_AI)
        keyword: Search in title and description
        area: Filter by practice area
    
    Returns:
        List of matching best practices
    """
    results = []
    
    for practices in BEST_PRACTICES.values():
        for bp in practices:
            # Apply filters
            if pillar and bp.get("pillar") != pillar:
                continue
            if risk and bp.get("risk") != risk:
                continue
            if lens and bp.get("lens", "FRAMEWORK") != lens:
                continue
            if area and area.lower() not in " ".join(bp.get("area", [])).lower():
                continue
            if keyword:
                kw = keyword.lower()
                if kw not in bp.get("title", "").lower() and kw not in bp.get("description", "").lower():
                    continue
            
            results.append(bp)
    
    return results

@mcp.tool()
def get_best_practice(id: str) -> dict[str, Any] | None:
    """Get detailed information about a specific best practice.
    
    Args:
        id: Best practice ID (e.g., "SEC01-BP01")
    
    Returns:
        Best practice details or None if not found
    """
    for practices in BEST_PRACTICES.values():
        for bp in practices:
            if bp.get("id") == id:
                return bp
    return None

@mcp.tool()
def list_pillars() -> dict[str, int]:
    """List all available pillars with their best practice counts.
    
    Returns:
        Dictionary mapping pillar names to practice counts
    """
    pillar_counts = {}
    for practices in BEST_PRACTICES.values():
        for bp in practices:
            pillar = bp.get("pillar", "UNKNOWN")
            pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1
    return pillar_counts

@mcp.tool()
def get_related_practices(id: str) -> list[dict[str, Any]]:
    """Get all best practices related to a specific practice.
    
    Args:
        id: Best practice ID
    
    Returns:
        List of related best practices
    """
    bp = get_best_practice(id)
    if not bp:
        return []
    
    related_ids = bp.get("relatedIds", [])
    results = []
    
    for rid in related_ids:
        related = get_best_practice(rid)
        if related:
            results.append(related)
    
    return results

def main():
    """Run the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
