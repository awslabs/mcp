#!/usr/bin/env python3
"""Direct test of data loading."""

import json
from pathlib import Path

data_dir = Path('src/well_architected_bp_mcp_server/data')
best_practices = {}

# Load framework pillars
for pillar_file in ["operational_excellence", "security", "reliability", 
                    "performance_efficiency", "cost_optimization", "sustainability"]:
    file_path = data_dir / f"{pillar_file}.json"
    if file_path.exists():
        with open(file_path) as f:
            best_practices[pillar_file] = json.load(f)

# Load lens data
lens_dir = data_dir / "lens" / "generative-ai"
if lens_dir.exists():
    for lens_file in lens_dir.glob("*.json"):
        key = f"genai_{lens_file.stem}"
        with open(lens_file) as f:
            best_practices[key] = json.load(f)

# Count by pillar
pillar_counts = {}
for practices in best_practices.values():
    for bp in practices:
        pillar = bp.get("pillar", "UNKNOWN")
        pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1

print("=== Pillar Counts ===")
for pillar, count in sorted(pillar_counts.items()):
    print(f"{pillar}: {count}")
print(f"\nTotal: {sum(pillar_counts.values())}")

# Test search
print("\n=== High-Risk Security Practices ===")
high_risk_sec = []
for practices in best_practices.values():
    for bp in practices:
        if bp.get("pillar") == "SECURITY" and bp.get("risk") == "HIGH":
            high_risk_sec.append(bp)

print(f"Found {len(high_risk_sec)} high-risk security practices")
for bp in high_risk_sec[:3]:
    print(f"  - {bp['id']}: {bp['title']}")

print("\n✅ Data loaded successfully!")
