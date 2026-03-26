# Migration Guide: Nova Canvas MCP Server

This guide helps you migrate from `awslabs.nova-canvas-mcp-server` to the community-maintained [bedrock-image-mcp-server](https://github.com/kalleeh/bedrock-image-mcp-server).

## Why We're Deprecating

The community-maintained `bedrock-image-mcp-server` is a fork of this server that has grown to include significantly more capabilities — 13 tools vs 2. As part of our ongoing effort to reduce overlap and promote well-maintained alternatives, this server will no longer be actively maintained.

## Recommended Alternative: bedrock-image-mcp-server

[bedrock-image-mcp-server](https://github.com/kalleeh/bedrock-image-mcp-server) is an Apache 2.0 licensed, community-maintained server originally forked from this AWS Labs server.

### Installing the Replacement

```json
{
  "mcpServers": {
    "bedrock-image-mcp-server": {
      "command": "uvx",
      "args": ["bedrock-image-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

**Important:** Remove the old `awslabs.nova-canvas-mcp-server` entry from your configuration after adding the new one.

## Tool Migration

| Old Tool | Replacement Tool | Notes |
|---|---|---|
| `generate_image` | `generate_image` | Same API — direct drop-in |
| `generate_image_with_colors` | `generate_image_with_colors` | Same API — direct drop-in |

### New Tools (only in the replacement)

The replacement server includes 11 additional tools:

| Tool | Description |
|---|---|
| `generate_image_sd35` | Text-to-image with Stable Diffusion 3.5 Large (10K char prompts) |
| `transform_image_sd35` | Image-to-image transformation with SD 3.5 |
| `upscale_creative` | AI-enhanced upscaling to 4K with style presets |
| `upscale_conservative` | Detail-preserving upscaling to 4K |
| `upscale_fast` | Quick 4x resolution upscaling |
| `inpaint_image` | Fill masked regions with AI content |
| `outpaint_image` | Extend images beyond boundaries |
| `search_and_replace` | Find and replace objects in images |
| `search_and_recolor` | Recolor specific objects |
| `remove_background` | Remove image backgrounds |
| `replace_background` | Replace image backgrounds |

## Feature Comparison

| Capability | nova-canvas-mcp-server | bedrock-image-mcp-server |
|---|---|---|
| Nova Canvas text-to-image | 1 tool | 1 tool |
| Nova Canvas color-guided | 1 tool | 1 tool |
| Stable Diffusion 3.5 | Not available | 2 tools |
| Stability AI upscaling | Not available | 3 tools |
| Stability AI editing | Not available | 6 tools |
| Total tools | 2 | 13 |
| License | Apache 2.0 | Apache 2.0 |

## Summary

This is a straightforward migration — your existing `generate_image` and `generate_image_with_colors` calls work identically in the replacement. You also gain access to Stable Diffusion 3.5, upscaling, and advanced image editing tools.
