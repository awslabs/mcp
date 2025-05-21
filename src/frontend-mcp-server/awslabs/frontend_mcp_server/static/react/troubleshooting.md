# Solutions to common issues when generating code for the application

- Always check for guidance from the awslabs.frontend-mcp-server MCP server when implementing new features or adding new pages
- Routing - always the already installed react-router v7 in Declarative mode for routing. Do not use the outdated react-router-dom package
- Components - always look for existing shadcn components before attempting to create new custom components
- Copying/Moving files - the user might be on Windows, try cross-platform commands
- Generating Images - a minimum resolution of 320x320 is required for Nova Canvas MCP server to generate images
- Creating Charts - Use shadcn charts for any charting https://ui.shadcn.com/charts

In addition:
- You MUST carefully analyze the current patterns and packages before suggesting structural or dependency changes
- Avoid changing existing layouts, login.tsx, app-sidebar.tsx, and authentication and keep any required changes minimal
- When adding new features, don't complete the analysis prematurely, continue analyzing even if you think you found a solution
- Ensure the code is complete and pages and components for new features are implemented fully and connected with the rest of the application
