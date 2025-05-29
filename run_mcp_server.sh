#!/bin/bash
# Run the MCP server with STDIO transport

echo "Starting URL Reputation Checker MCP Server..."
echo "This server uses STDIO transport for MCP protocol communication."
echo "To connect: use an MCP client that supports STDIO transport"
echo "=============================================="

# Export Redis URL to use local Redis
export REDIS_URL=${REDIS_URL:-redis://localhost:6379}

# Run the server
cd "$(dirname "$0")"
python3 -m url_reputation_checker.server