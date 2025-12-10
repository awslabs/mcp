"""AWS Well-Architected Best Practices MCP Server."""

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP(
    "AWS Well-Architected Framework Best Practices - Architecture Review, Design Principles, WAF, Well-Architected Assessment"
)

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
    """Search AWS Well-Architected Framework best practices and recommendations.
    
    KEYWORDS: well-architected, well architected, AWS Well-Architected Framework, WAF, 
    architecture review, best practices, design principles, pillar, security pillar, 
    reliability pillar, performance efficiency, cost optimization, operational excellence, 
    sustainability pillar, architecture assessment, framework review, well architected review.
    
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
    """Get detailed AWS Well-Architected Framework best practice by ID.
    
    KEYWORDS: well-architected, well architected, best practice, design principle, 
    framework guidance, architecture pattern, AWS Well-Architected Framework.
    
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
    # Find the BP directly from data
    bp = None
    for practices in BEST_PRACTICES.values():
        for practice in practices:
            if practice.get("id") == id:
                bp = practice
                break
        if bp:
            break
    
    if not bp:
        return []
@mcp.tool()
def well_architected_framework_review() -> dict[str, Any]:
    """Complete AWS Well-Architected Framework review and assessment.
    
    KEYWORDS: well-architected, well architected, AWS Well-Architected Framework, WAF review, 
    architecture review, framework review, well architected review, architecture assessment, 
    design principles, pillar review, best practices review, framework assessment.
    
    Returns:
        Comprehensive Well-Architected Framework overview with all pillars and key practices
    """
    review = {
        "framework": "AWS Well-Architected Framework",
        "pillars": {},
        "total_practices": 0,
        "key_areas": [],
        "assessment_guidance": []
    }
    
    # Aggregate data by pillar
    pillar_mapping = {
        "operational_excellence": "Operational Excellence",
        "security": "Security", 
        "reliability": "Reliability",
        "performance_efficiency": "Performance Efficiency",
        "cost_optimization": "Cost Optimization",
        "sustainability": "Sustainability"
    }
    
    for key, practices in BEST_PRACTICES.items():
        if key in pillar_mapping:
            pillar_name = pillar_mapping[key]
            review["pillars"][pillar_name] = {
                "practice_count": len(practices),
                "high_risk_practices": [p for p in practices if p.get("risk") == "HIGH"],
                "key_practices": practices[:5]  # Top 5 practices
            }
            review["total_practices"] += len(practices)
    
    review["key_areas"] = [
        "Identity and Access Management",
        "Data Protection", 
        "Infrastructure Protection",
        "Incident Response",
        "Application Security",
        "Monitoring and Logging",
        "Cost Management",
        "Performance Optimization"
    ]
    
    review["assessment_guidance"] = [
        "Start with Security pillar for foundational protection",
        "Review Operational Excellence for monitoring and automation",
        "Assess Reliability for fault tolerance and recovery",
        "Evaluate Performance Efficiency for optimal resource usage",
        "Analyze Cost Optimization for financial efficiency",
        "Consider Sustainability for environmental impact"
    ]
    
    return review

    
    related_ids = bp.get("relatedIds", [])
    results = []
    
    # Find related BPs directly from data
    for rid in related_ids:
        for practices in BEST_PRACTICES.values():
            for practice in practices:
                if practice.get("id") == rid:
                    results.append(practice)
                    break
    
    return results

def main():
    """Run the MCP server."""
    mcp.run()

if __name__ == '__main__':
    main()
