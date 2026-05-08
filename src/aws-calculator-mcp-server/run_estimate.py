"""Run estimate from a JSON config file and save results.

Usage:
    uv run python run_estimate.py <config.json> [--output result.json]

If --output is not specified, saves to <config>-result.json in the same directory.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from awslabs.aws_calculator_mcp_server.calculator import AWSCalculatorAutomation


async def main(config_path: str, output_path: str = None):
    with open(config_path) as f:
        config = json.load(f)

    name = config.get("name", "AWS Estimate")
    region = config.get("region", "US East (N. Virginia)")
    services = config.get("services", [])

    print(f"{'='*70}")
    print(f"  {name}")
    print(f"  Region: {region}")
    print(f"  Services: {len(services)}")
    print(f"{'='*70}\n")

    calc = AWSCalculatorAutomation(headless=True)
    try:
        result = await calc.create_estimate(services)
    finally:
        await calc.close()

    # Build output
    output = {
        "name": name,
        "region": region,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_file": str(Path(config_path).resolve()),
        "estimate_url": result.get("estimate_url", ""),
        "monthly_cost": result.get("monthly_cost", ""),
        "services": [],
    }

    print(f"\n  URL: {result.get('estimate_url', 'FAILED')}")
    print(f"  Total: {result.get('monthly_cost', 'Unknown')}")
    print(f"\n  {'Service':<45} {'Cost':>12}")
    print(f"  {'-'*45} {'-'*12}")

    for i, svc in enumerate(result.get("services", [])):
        svc_config = services[i] if i < len(services) else {}
        status = svc.get("status", "?")
        cost = svc.get("monthly_cost", "?")
        svc_name = svc.get("service_name", "?")
        desc = svc_config.get("description", "")
        mark = "✓" if status == "added" else "✗"

        print(f"  {mark} {svc_name:<43} ${cost:>10}")

        output["services"].append({
            "service_name": svc_name,
            "description": desc,
            "status": status,
            "monthly_cost_usd": float(cost.replace(",", "")) if cost != "?" else 0,
        })

    added = sum(1 for s in result.get("services", []) if s.get("status") == "added")
    print(f"\n  {added}/{len(services)} services added")
    print(f"{'='*70}")

    # Determine output path
    if not output_path:
        config_p = Path(config_path)
        output_path = str(config_p.parent / f"{config_p.stem}-result.json")

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  Result saved: {output_path}")
    return output


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config.json> [--output result.json]")
        sys.exit(1)

    config_file = sys.argv[1]
    out_file = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        out_file = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None

    asyncio.run(main(config_file, out_file))
