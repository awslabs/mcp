#!/bin/sh

if [ "$(lsof +c 0 -p 1 | grep -e grep -e "^awslabs\..*\s1\s.*\unix\s.*socket$" | wc -l)" -ne "0" ]; then
  echo -n "$(lsof +c 0 -p 1 | grep -e grep -e "^awslabs\..*\s1\s.*\unix\s.*socket$" | wc -l) awslabs.* streams found";
  exit 0;
else
  echo -n "Zero awslabs.* streams found";
  # For OpenAPI MCP Server, we'll check if the process is running as a fallback
  if pgrep -f "python -m awslabs.openapi_mcp_server.server" > /dev/null; then
    echo -n " but server process is running";
    exit 0;
  fi;
  exit 1;
fi;

echo -n "Never should reach here";
exit 99;
