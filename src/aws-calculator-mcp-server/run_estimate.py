"""Run estimate from a JSON config file."""

import asyncio
import json
import sys

sys.path.insert(0, ".")
from awslabs.aws_calculator_mcp_server.calculator import AWSCalculatorAutomation


async def main(config_path: str):
    with open(config_path) as f:
        config = json.load(f)

    print("=" * 70)
    print(f" {config['name']}")
    print(f" Region: {config['region']}")
    print("=" * 70)

    calc = AWSCalculatorAutomation(headless=True)
    try:
        result = await calc.create_estimate(config["services"])

        print(f"\n URL: {result.get('estimate_url', 'FAILED')}")
        print(f" Total: {result.get('monthly_cost', 'Unknown')}")
        print(f"\n {'Service':<42} {'Cost':>12}")
        print(f" {'-'*42} {'-'*12}")
        for svc in result.get("services", []):
            s = svc.get("status", "?")
            c = svc.get("monthly_cost", "?")
            n = svc.get("service_name", "?")
            mark = "✓" if s == "added" else "✗"
            print(f" {mark} {n:<40} ${c:>10}")
        added = sum(1 for s in result.get("services", []) if s.get("status") == "added")
        print(f"\n {added}/{len(config['services'])} services added")
        print("=" * 70)

        output = {
            "config": config_path,
            "estimate_url": result.get("estimate_url"),
            "monthly_cost": result.get("monthly_cost"),
            "services": result.get("services"),
        }
        with open("/tmp/par_mec_result.json", "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n Result saved to /tmp/par_mec_result.json")

    finally:
        await calc.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "par_mec_config.json"
    asyncio.run(main(path))
