# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

URL Reputation and Validity Checker - A FastMCP 2.0-based service that validates URLs, provides reputation scores, and detects AI-generated URL hallucinations. The service uses WHOIS lookups, Wayback Machine data, and various heuristics to assess URL trustworthiness.

## Development Commands

### Essential Commands
```bash
# Install development dependencies
make dev-install

# Run the service (Docker)
make run

# Run tests
make test

# Lint and type check
make lint

# Format code
make format

# View logs
make logs

# Clean up (stop services and remove volumes)
make clean
```

### Running Without Docker
```bash
# Start Redis (required for caching)
redis-server

# Run the MCP server
python -m url_reputation_checker.server
```

## Architecture

### Core Components
- **server.py**: FastMCP server exposing 4 tools (check_links_reputation, extract_and_check_links, validate_url, get_domain_history) and 2 resources
- **validators.py**: URL validation with 3 levels (BASIC, STANDARD, COMPREHENSIVE), SSL checks, typosquatting detection, AI hallucination pattern detection
- **history.py**: Domain reputation scoring (0-100) based on age, Wayback presence, and technical factors
- **extractors.py**: Link extraction from HTML/text content using BeautifulSoup and regex
- **cache.py**: Redis caching layer with graceful degradation
- **models.py**: Data models with JSON serialization support

### Key Patterns
- **Async-first**: All I/O operations are async
- **Graceful degradation**: External services (Redis, WHOIS, Wayback) fail gracefully
- **Progressive validation**: Three validation levels balance thoroughness vs performance
- **MCP STDIO transport**: Server communicates via standard input/output

### Testing
- pytest with pytest-asyncio for async tests
- Test examples in `examples/test_client.py` and `mcp_client_example.py`
- Run individual tests: `pytest path/to/test.py::test_function_name`

### External Dependencies
- Redis for caching (optional but recommended)
- WHOIS lookups via python-whois
- Wayback Machine API via waybackpy
- HTTP validation via httpx

## Important Notes
- The service uses STDIO transport for MCP communication
- Redis connection defaults to localhost:6379
- External API calls (WHOIS, Wayback) can be slow - caching is crucial
- Docker setup includes both the MCP server and Redis containers