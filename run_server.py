import uvicorn
import os
import sys
import logging
import threading
from dotenv import load_dotenv

# Configure basic logging for the runner script itself
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to run the MCP server in a separate thread
def run_mcp_server():
    # Redirect stdout logs to a file when in MCP mode
    import sys
    import logging
    
    # Configure logging to file only when in MCP mode
    file_handler = logging.FileHandler('calendar_mcp.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Replace console handlers with file handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)
    root_logger.addHandler(file_handler)
    
    # Ensure uvicorn logs also go to file
    uvicorn_logger = logging.getLogger("uvicorn")
    for handler in uvicorn_logger.handlers[:]:
        uvicorn_logger.removeHandler(handler)
    uvicorn_logger.addHandler(file_handler)
    
    logger.info("Redirected logs to file for MCP mode")
    
    # Import and run MCP server
    from src.mcp_bridge import create_mcp_server
    mcp = create_mcp_server()
    logger.info("Starting MCP server with stdio transport")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    # Add the current directory to the Python path to ensure src is importable
    project_dir = os.path.dirname(os.path.abspath(__file__))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
        logger.info(f"Added {project_dir} to Python path")
    
    # Force PYTHONPATH to include the current directory for the reloader processes
    os.environ["PYTHONPATH"] = f"{project_dir}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"
    logger.info(f"Set PYTHONPATH to include {project_dir}")
    
    # Ensure environment variables are loaded
    load_dotenv()

    # Start MCP server in a separate thread if stdin is available
    if not os.isatty(0):  # Check if stdin is piped (MCP client is connecting)
        logger.info("MCP client detected: Starting MCP server")
        mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
        mcp_thread.start()
        logger.info("MCP server thread started")
    else:
        logger.info("Running in HTTP-only mode (no MCP client detected)")

    # Get host and port from environment variables or use defaults
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))  # FastAPI server port
    reload = os.getenv("RELOAD", "true").lower() == "true"

    logger.info(f"Starting FastAPI server on {host}:{port}...")
    logger.info(f"Reload mode: {'Enabled' if reload else 'Disabled'}")

    # Run the Uvicorn server
    try:
        uvicorn.run("src.server:app", host=host, port=port, reload=reload, log_level="error") 
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1) 