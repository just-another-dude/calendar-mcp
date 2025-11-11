#!/usr/bin/env python3
"""
Main entry point for Railway deployment.
Railway automatically detects and runs main.py files.
"""

import uvicorn
import os
import sys
import logging
from dotenv import load_dotenv

# Add the current directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to start the server."""
    # Load environment variables
    load_dotenv()

    # Railway deployment settings
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
    is_production = os.getenv("NODE_ENV") == "production" or is_railway

    if is_railway:
        host = "0.0.0.0"  # Railway requires this
        port = int(os.getenv("PORT", 8000))  # Railway provides this
        reload = False  # Disable reload in production
        logger.info("Railway deployment detected - using production settings")

        # Create persistent token directory for Railway
        tokens_dir = "/app/tokens"
        os.makedirs(tokens_dir, exist_ok=True)
        os.environ["TOKEN_FILE_PATH"] = f"{tokens_dir}/saved-tokens.json"
        logger.info(f"Railway: Set token directory to {tokens_dir}")
    else:
        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", 8000))
        reload = os.getenv("RELOAD", "true").lower() == "true" and not is_production

    logger.info(f"Starting FastAPI server on {host}:{port}")
    logger.info(f"Environment: {'Railway' if is_railway else 'Local'}")
    logger.info(f"Reload mode: {'Enabled' if reload else 'Disabled'}")

    # Start the FastAPI server
    uvicorn.run("src.server:app", host=host, port=port, reload=reload, access_log=True)


if __name__ == "__main__":
    main()
