#!/usr/bin/env python3
"""
Example MCP client that connects to the URL Reputation Checker server via STDIO.
This demonstrates how to interact with the MCP server programmatically.
"""

import json
import subprocess
import asyncio
from typing import Dict, Any, Optional

class MCPClient:
    """Simple MCP client for STDIO communication."""
    
    def __init__(self, server_command: list):
        self.server_command = server_command
        self.process: Optional[subprocess.Popen] = None
        self._message_id = 0
    
    async def connect(self):
        """Start the MCP server process."""
        self.process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        # Read and handle initialization messages
        await self._read_initialization()
    
    async def _read_initialization(self):
        """Read initialization messages from the server."""
        # MCP servers typically send initialization messages
        # We'll read them but not process them in this simple example
        pass
    
    def _next_id(self) -> str:
        """Generate next message ID."""
        self._message_id += 1
        return f"msg_{self._message_id}"
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the server and wait for response."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Not connected to server")
        
        # Add JSON-RPC fields
        if "id" not in message:
            message["id"] = self._next_id()
        if "jsonrpc" not in message:
            message["jsonrpc"] = "2.0"
        
        # Send message
        json_msg = json.dumps(message)
        self.process.stdin.write(json_msg + "\n")
        self.process.stdin.flush()
        
        # Read response
        if self.process.stdout:
            response_line = self.process.stdout.readline()
            if response_line:
                return json.loads(response_line)
        
        return {}
    
    async def initialize(self):
        """Send initialization request."""
        message = {
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "example-client",
                    "version": "1.0.0"
                }
            }
        }
        return await self.send_message(message)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the server."""
        message = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        return await self.send_message(message)
    
    async def close(self):
        """Close the connection to the server."""
        if self.process:
            self.process.terminate()
            await asyncio.sleep(0.1)
            if self.process.poll() is None:
                self.process.kill()


async def test_url_validation():
    """Test URL validation functionality."""
    print("=== URL Reputation Checker MCP Client Example ===\n")
    
    # Create client
    client = MCPClient(["python3", "-m", "url_reputation_checker.server"])
    
    try:
        print("Connecting to MCP server...")
        await client.connect()
        
        print("Initializing connection...")
        init_response = await client.initialize()
        print(f"Server initialized: {init_response.get('result', {}).get('serverInfo', {})}\n")
        
        # Test 1: Validate a single URL
        print("Test 1: Validating https://github.com")
        result = await client.call_tool("validate_url", {
            "url": "https://github.com"
        })
        print(f"Result: {json.dumps(result, indent=2)}\n")
        
        # Test 2: Check multiple links
        print("Test 2: Checking multiple URLs")
        urls = [
            "https://github.com",
            "https://google.com",
            "https://fake-site-12345.com"
        ]
        result = await client.call_tool("check_links_reputation", {
            "urls": urls
        })
        print(f"Result: {json.dumps(result, indent=2)}\n")
        
        # Test 3: Extract and check links from content
        print("Test 3: Extracting links from HTML content")
        html_content = """
        <html>
        <body>
            <a href="https://python.org">Python</a>
            <a href="https://nodejs.org">Node.js</a>
            <p>Visit https://example.com for more info</p>
        </body>
        </html>
        """
        result = await client.call_tool("extract_and_check_links", {
            "content": html_content,
            "content_type": "html"
        })
        print(f"Result: {json.dumps(result, indent=2)}\n")
        
        # Test 4: Get domain history
        print("Test 4: Getting domain history for github.com")
        result = await client.call_tool("get_domain_history", {
            "domain": "github.com"
        })
        print(f"Result: {json.dumps(result, indent=2)}\n")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Closing connection...")
        await client.close()


if __name__ == "__main__":
    # Note: This example assumes the server is not already running
    # In production, you might connect to an already-running server
    asyncio.run(test_url_validation())