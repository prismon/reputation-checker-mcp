#!/usr/bin/env python3
"""Example client for testing the URL Reputation Checker MCP server."""

import asyncio
import json
from typing import List, Dict

# Since we're using FASTMCP, we'll simulate MCP client calls
# In a real scenario, you would use an MCP client library

async def test_check_links_reputation():
    """Test the check_links_reputation tool."""
    print("\n=== Testing check_links_reputation ===")
    
    test_urls = [
        "https://github.com",
        "https://google.com",
        "https://example.com",
        "https://this-is-a-fake-domain-12345.com",
        "https://githubcom.fake",  # Typosquatting example
    ]
    
    print(f"Checking {len(test_urls)} URLs...")
    
    # In a real MCP client, you would call:
    # results = await client.call_tool("check_links_reputation", urls=test_urls)
    
    # Simulated results for demonstration
    print("\nResults:")
    for url in test_urls:
        print(f"- {url}")
        print(f"  Status: {'Valid' if 'fake' not in url else 'Invalid'}")
        print(f"  Reputation: {'85/100' if 'github' in url else '60/100'}")
        print(f"  Warnings: {'Possible typosquatting' if 'githubcom' in url else 'None'}")
        print()


async def test_extract_and_check_links():
    """Test the extract_and_check_links tool."""
    print("\n=== Testing extract_and_check_links ===")
    
    html_content = """
    <html>
    <head>
        <title>Test Page</title>
        <link rel="stylesheet" href="https://example.com/style.css">
    </head>
    <body>
        <h1>Link Examples</h1>
        <p>Check out these sites:</p>
        <ul>
            <li><a href="https://github.com">GitHub</a></li>
            <li><a href="https://stackoverflow.com">Stack Overflow</a></li>
            <li><a href="https://fake-academic-paper.edu/2023/05/ai-research.pdf">
                Suspicious Academic Paper
            </a></li>
            <li><a href="https://microsft.com">Microsoft (typo)</a></li>
        </ul>
        
        <p>Also mentioned: https://www.python.org and https://nodejs.org</p>
        
        <img src="https://example.com/image.png" alt="Example">
    </body>
    </html>
    """
    
    print("Extracting links from HTML content...")
    
    # In a real MCP client, you would call:
    # result = await client.call_tool(
    #     "extract_and_check_links",
    #     content=html_content,
    #     content_type="html"
    # )
    
    print("\nExtracted links:")
    print("- https://example.com/style.css")
    print("- https://github.com")
    print("- https://stackoverflow.com")
    print("- https://fake-academic-paper.edu/2023/05/ai-research.pdf")
    print("- https://microsft.com")
    print("- https://www.python.org")
    print("- https://nodejs.org")
    print("- https://example.com/image.png")
    
    print("\nSummary:")
    print("- Total links: 8")
    print("- Valid links: 6")
    print("- Invalid links: 2")
    print("- Average reputation score: 72.5/100")
    print("- Recommendation: Links have moderate reputation - verify important ones")


async def test_validate_url():
    """Test the validate_url tool."""
    print("\n=== Testing validate_url ===")
    
    test_url = "https://github.com/anthropics/fastmcp"
    print(f"Validating: {test_url}")
    
    # In a real MCP client, you would call:
    # result = await client.call_tool("validate_url", url=test_url)
    
    print("\nValidation result:")
    print(f"- Valid: True")
    print(f"- Status code: 200")
    print(f"- Response time: 0.342s")
    print(f"- SSL valid: True")
    print(f"- Content length: 125432 bytes")
    print(f"- Warnings: []")
    print(f"- Confidence level: high")


async def test_get_domain_history():
    """Test the get_domain_history tool."""
    print("\n=== Testing get_domain_history ===")
    
    test_domain = "github.com"
    print(f"Getting history for: {test_domain}")
    
    # In a real MCP client, you would call:
    # result = await client.call_tool("get_domain_history", domain=test_domain)
    
    print("\nDomain history:")
    print(f"- Domain: {test_domain}")
    print(f"- Creation date: 2007-10-09")
    print(f"- Age: 6234 days")
    print(f"- Registrar: MarkMonitor Inc.")
    print(f"- Wayback Machine first snapshot: 2007-10-12")
    print(f"- Total Wayback snapshots: 15,234")


async def test_markdown_content():
    """Test extraction from Markdown content."""
    print("\n=== Testing Markdown content extraction ===")
    
    markdown_content = """
    # My Blog Post
    
    Here are some useful resources:
    
    - [Python Documentation](https://docs.python.org)
    - [FastAPI](https://fastapi.tiangolo.com)
    - [Fake Research Paper](https://university.edu/papers/2024/03/15/ai-breakthrough)
    
    You can also visit https://example.com directly.
    
    Check out this suspicious link: https://g00gle.com (notice the zeros)
    """
    
    print("Extracting links from Markdown content...")
    
    # In a real MCP client, you would call:
    # result = await client.call_tool(
    #     "extract_and_check_links",
    #     content=markdown_content,
    #     content_type="text"
    # )
    
    print("\nExtracted links:")
    print("- https://docs.python.org")
    print("- https://fastapi.tiangolo.com")
    print("- https://university.edu/papers/2024/03/15/ai-breakthrough")
    print("- https://example.com")
    print("- https://g00gle.com")
    
    print("\nWarnings detected:")
    print("- https://university.edu/papers/2024/03/15/ai-breakthrough:")
    print("  - URL pattern commonly seen in AI hallucinations")
    print("- https://g00gle.com:")
    print("  - Possible typosquatting of google.com")


async def main():
    """Run all test examples."""
    print("URL Reputation Checker - Example Client")
    print("=" * 50)
    
    # Run all tests
    await test_check_links_reputation()
    await test_extract_and_check_links()
    await test_validate_url()
    await test_get_domain_history()
    await test_markdown_content()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("\nNote: This is a demonstration client.")
    print("In production, use a proper MCP client library to connect to the server.")


if __name__ == "__main__":
    asyncio.run(main())