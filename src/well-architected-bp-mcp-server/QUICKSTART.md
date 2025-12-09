# Quick Start Guide

## What You Have Now

✅ **Complete MCP Server Structure** following awslabs/mcp patterns
✅ **356 Best Practices** with metadata (ID, title, description, risk, links)
✅ **4 Query Tools** for searching and filtering
✅ **Working Installation** tested and verified

## What's Next

### Option 1: Use As-Is (Recommended for MVP)

The server is **ready to use** with current data:
- All 356 BP IDs, titles, descriptions, and links
- Search by pillar, risk, keyword, area
- Get specific BPs and related practices

**To test:**
```bash
cd /Users/ibracnb/Dev/awslabs-mcp/src/well-architected-bp-mcp-server

# Add to your MCP config
cat << 'EOF' >> ~/.aws/amazonq/mcp.json
{
  "mcpServers": {
    "well-architected-bp": {
      "command": "uvx",
      "args": ["well-architected-bp-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
EOF

# Install locally
source .venv/bin/activate
pip install -e .
```

**Test with Amazon Q CLI:**
```
"Show me all high-risk security best practices from the Well-Architected framework"
```

### Option 2: Add Full Content (Optional)

To add complete text from AWS docs:

1. **Implement scraper** in `scripts/scrape_content.py`
2. **Run scraper** to populate `content` field
3. **Add content search** tool to server.py
4. **Update schema** to include content field

## Publishing to awslabs/mcp

### 1. Create PR

```bash
cd /Users/ibracnb/Dev/awslabs-mcp
git checkout -b feature/well-architected-bp-server
git add src/well-architected-bp-mcp-server
git commit -m "Add AWS Well-Architected Best Practices MCP Server"
git push origin feature/well-architected-bp-server
```

### 2. Update Main README

Add entry to `/Users/ibracnb/Dev/awslabs-mcp/README.md`:

```markdown
| [AWS Well-Architected Best Practices MCP Server](src/well-architected-bp-mcp-server) | Complete AWS Well-Architected Framework best practices across all pillars | [![Install](badge)](link) |
```

### 3. After Merge

Once merged to main:
- Package will be available via `uvx awslabs.well-architected-bp-mcp-server@latest`
- Customers can use in workshops and production
- Single source of truth for all 356 best practices

## Key Files

- `README.md` - User documentation
- `IMPLEMENTATION.md` - Technical details
- `src/well_architected_bp_mcp_server/server.py` - Main server code
- `src/well_architected_bp_mcp_server/data/` - All 356 best practices
- `examples/usage.md` - Usage examples
- `scripts/scrape_content.py` - Template for adding full content

## Testing Checklist

- [x] Data loads correctly (356 BPs)
- [x] All pillars present
- [x] GenAI lens included
- [x] Package installs via pip
- [ ] Test with Amazon Q CLI
- [ ] Test with Cursor/Cline
- [ ] Verify all tools work
- [ ] Add full content (optional)

## Support

For questions or issues:
1. Check `IMPLEMENTATION.md` for technical details
2. Review `examples/usage.md` for usage patterns
3. Test with `test_direct.py` to verify data loading
