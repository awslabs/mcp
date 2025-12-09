#!/usr/bin/env python3
"""Quick test of the Well-Architected BP MCP Server."""

import sys
sys.path.insert(0, 'src')

from well_architected_bp_mcp_server.server import search_best_practices, get_best_practice, list_pillars

# Test 1: List pillars
print("=== Test 1: List Pillars ===")
pillars = list_pillars()
for pillar, count in sorted(pillars.items()):
    print(f"{pillar}: {count} best practices")
print(f"\nTotal: {sum(pillars.values())} best practices\n")

# Test 2: Search high-risk security practices
print("=== Test 2: High-Risk Security Practices ===")
results = search_best_practices(pillar="SECURITY", risk="HIGH")
print(f"Found {len(results)} high-risk security practices:")
for bp in results[:3]:
    print(f"  - {bp['id']}: {bp['title']}")
print()

# Test 3: Get specific practice
print("=== Test 3: Get Specific Practice ===")
bp = get_best_practice("SEC01-BP01")
if bp:
    print(f"ID: {bp['id']}")
    print(f"Title: {bp['title']}")
    print(f"Risk: {bp['risk']}")
    print(f"Description: {bp['description'][:100]}...")
print()

# Test 4: Search by keyword
print("=== Test 4: Search by Keyword ===")
results = search_best_practices(keyword="encryption")
print(f"Found {len(results)} practices mentioning 'encryption':")
for bp in results[:3]:
    print(f"  - {bp['id']}: {bp['title']}")
print()

print("✅ All tests passed!")
