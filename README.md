# URL Reputation and Validity Checker

A FASTMCP 2.0-based service that validates URLs and checks their reputation to help identify AI hallucinations and verify web page authenticity.

## Features

- **URL Validation**: Verify that URLs resolve to actual web pages
- **Reputation Scoring**: 0-100 score based on domain age, web archive presence, and technical factors
- **Link Extraction**: Extract and validate links from HTML or text content
- **Historical Analysis**: Check domain age via WHOIS and Wayback Machine
- **AI Hallucination Detection**: Identify patterns common in AI-generated URLs
- **Caching**: Redis-based caching for improved performance
- **Docker Support**: Easy deployment with Docker and docker-compose

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd reputation-and-validity-checker
```

2. Start the services:
```bash
docker-compose up -d
```

The MCP server will be available at `http://localhost:5000`.

### Local Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Redis (optional, for caching):
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

3. Run the server:
```bash
python -m url_reputation_checker.server
```

## MCP Tools

### `check_links_reputation`
Check reputation for a list of URLs.

**Parameters:**
- `urls`: List of URLs to validate

**Returns:**
- List of validation results with reputation scores

**Example:**
```python
result = await check_links_reputation([
    "https://example.com",
    "https://github.com"
])
```

### `extract_and_check_links`
Extract links from content and check their reputation.

**Parameters:**
- `content`: HTML or text content
- `content_type`: "html", "text", or "auto" (default: "auto")

**Returns:**
- Extracted links with validation results and summary

**Example:**
```python
result = await extract_and_check_links(
    "<a href='https://example.com'>Link</a>",
    content_type="html"
)
```

### `validate_url`
Validate a single URL.

**Parameters:**
- `url`: URL to validate

**Returns:**
- Detailed validation information

### `get_domain_history`
Get historical information about a domain.

**Parameters:**
- `domain`: Domain name or URL

**Returns:**
- Domain creation date, WHOIS info, and Wayback Machine data

## Reputation Scoring

The reputation score (0-100) is calculated based on:

- **Domain Age** (0-30 points):
  - 5+ years: 30 points
  - 2-5 years: 20 points
  - 1-2 years: 15 points
  - 6-12 months: 10 points
  - 3-6 months: 5 points
  - <3 months: 2 points

- **Web Archive Presence** (0-20 points):
  - 100+ snapshots: 20 points
  - 50-99 snapshots: 15 points
  - 20-49 snapshots: 10 points
  - 5-19 snapshots: 5 points
  - 1-4 snapshots: 2 points

- **Technical Factors** (0-25 points):
  - Valid SSL: 10 points
  - Fast response (<1s): 10 points
  - HTTP 200 status: 5 points

- **Consistency** (0-25 points):
  - No warnings: 25 points
  - 1 warning: 15 points
  - 2 warnings: 10 points
  - 3 warnings: 5 points

## AI Hallucination Detection

The service checks for patterns commonly seen in AI-generated URLs:

- Overly specific blog paths (e.g., `/blog/2023/03/15/specific-topic`)
- Version-specific API documentation URLs
- Excessive path depth (>6 levels)
- Over-hyphenated product names
- Typosquatting attempts
- Excessive subdomains

## Configuration

Environment variables:

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `MCP_SERVER_HOST`: Server host (default: `0.0.0.0`)
- `MCP_SERVER_PORT`: Server port (default: `5000`)

## Development

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Format code:
```bash
black url_reputation_checker/
```

4. Lint code:
```bash
ruff url_reputation_checker/
```

## Docker Build

Build the Docker image:
```bash
docker build -t url-reputation-checker .
```

Run with docker-compose:
```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f
```

## Example Usage

### Python Client Example

```python
import asyncio
from fastmcp import FastMCPClient

async def main():
    async with FastMCPClient("http://localhost:5000") as client:
        # Check a list of URLs
        results = await client.call_tool(
            "check_links_reputation",
            urls=[
                "https://github.com",
                "https://example-fake-site-12345.com"
            ]
        )
        
        for result in results:
            print(f"{result['url']}: {result['reputation_score']}/100")
        
        # Extract and check links from HTML
        html_content = """
        <html>
            <body>
                <a href="https://google.com">Google</a>
                <a href="https://fake-news-site.com">Fake News</a>
            </body>
        </html>
        """
        
        extraction_result = await client.call_tool(
            "extract_and_check_links",
            content=html_content,
            content_type="html"
        )
        
        print(f"Found {extraction_result['summary']['total_links']} links")
        print(f"Average reputation: {extraction_result['summary']['average_reputation_score']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## API Endpoints

The MCP server exposes tools that can be called via the MCP protocol. Additionally, it provides resources:

- `/url_validation_report`: Get a formatted report of all validated URLs
- `/cache_stats`: Get cache statistics

## Troubleshooting

### Redis Connection Issues
If Redis is not available, the service will continue to work without caching. To disable Redis entirely, set:
```bash
export REDIS_URL=""
```

### WHOIS Lookup Failures
Some domains may not have WHOIS information available due to privacy protection or registry limitations. The service will continue with other checks.

### Wayback Machine Rate Limiting
The Wayback Machine API may rate limit requests. The service handles this gracefully and will skip historical data if unavailable.

## License

MIT License - see LICENSE file for details.