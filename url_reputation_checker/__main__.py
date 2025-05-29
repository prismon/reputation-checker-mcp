"""Entry point for the URL Reputation Checker MCP server."""

import asyncio
import logging
import signal
import sys

from .server import mcp

# Configure logging to suppress non-critical errors during shutdown
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, exiting...")
    sys.exit(0)


async def main():
    """Run the MCP server with proper error handling."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await mcp.run_async()
    except asyncio.CancelledError:
        # This is expected during shutdown
        logger.debug("Server tasks cancelled during shutdown")
    except Exception as e:
        # Ignore BrokenResourceError and similar stream errors during shutdown
        error_name = type(e).__name__
        if error_name in [
            "BrokenResourceError",
            "BrokenPipeError",
            "ConnectionResetError",
        ]:
            logger.debug(f"Expected stream error during shutdown: {error_name}")
        else:
            logger.error(f"Unexpected error: {e}")
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        sys.exit(0)
    except SystemExit:
        # Normal exit
        pass
