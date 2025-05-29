# MCP Server Connection Guide

## Overview

The URL Reputation Checker MCP server uses STDIO transport for communication. This guide shows how to connect to the server using various methods.

## Prerequisites

1. Ensure Redis is running (the Docker setup includes this)
2. Install the project dependencies:
   ```bash
   pip install -e .
   ```

## Connection Methods

### Method 1: Direct STDIO Connection (Local Development)

Run the server directly:

```bash
# Using the provided script
./run_mcp_server.sh

# Or directly with Python
REDIS_URL=redis://localhost:6379 python -m url_reputation_checker.server
```

### Method 2: Docker Container with STDIO

The Docker container is configured to keep STDIO open:

```bash
# Start the services
docker compose up -d

# Connect to the running container's STDIO
docker attach url-reputation-checker
```

### Method 3: Claude Desktop Integration

1. Copy the configuration to Claude Desktop's config directory:

   **macOS:**
   ```bash
   mkdir -p ~/Library/Application\ Support/Claude/
   cp claude_desktop_config.json ~/Library/Application\ Support/Claude/config.json
   ```

   **Windows:**
   ```powershell
   mkdir -p %APPDATA%\Claude
   copy claude_desktop_config.json %APPDATA%\Claude\config.json
   ```

   **Linux:**
   ```bash
   mkdir -p ~/.config/Claude
   cp claude_desktop_config.json ~/.config/Claude/config.json
   ```

2. Restart Claude Desktop

3. The URL Reputation Checker should now be available in Claude Desktop

### Method 4: Programmatic Access

Use the provided client example:

```bash
python mcp_client_example.py
```

Or create your own client:

```python
import subprocess
import json

# Start the server
process = subprocess.Popen(
    ["python", "-m", "url_reputation_checker.server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

# Send MCP protocol messages
message = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {}
    }
}

process.stdin.write(json.dumps(message) + "\n")
process.stdin.flush()

# Read response
response = process.stdout.readline()
print(json.loads(response))
```

## Available Tools

Once connected, you can use these tools:

1. **validate_url** - Validate a single URL
   ```json
   {
     "name": "validate_url",
     "arguments": {
       "url": "https://example.com"
     }
   }
   ```

2. **check_links_reputation** - Check multiple URLs
   ```json
   {
     "name": "check_links_reputation",
     "arguments": {
       "urls": ["https://github.com", "https://google.com"]
     }
   }
   ```

3. **extract_and_check_links** - Extract and validate links from content
   ```json
   {
     "name": "extract_and_check_links",
     "arguments": {
       "content": "<html>...</html>",
       "content_type": "html"
     }
   }
   ```

4. **get_domain_history** - Get domain registration and archive history
   ```json
   {
     "name": "get_domain_history",
     "arguments": {
       "domain": "example.com"
     }
   }
   ```

## Resources

The server also provides these resources:

1. **report://validation** - Get a report of all validated URLs
2. **stats://cache** - Get cache statistics

## Troubleshooting

### Server not starting
- Check Redis is running: `redis-cli ping`
- Check logs: `docker compose logs mcp-server`

### Connection issues
- Ensure the server is running
- Check the REDIS_URL environment variable
- Verify Python path is correct in configuration

### STDIO communication issues
- Messages must be valid JSON
- Each message must end with a newline
- Follow the MCP protocol specification

## Environment Variables

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `PYTHONPATH`: Should include the project directory

## Testing

Run the test client to verify everything is working:

```bash
python mcp_client_example.py
```

This will test all available tools and show example outputs.