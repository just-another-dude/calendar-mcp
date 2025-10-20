#!/usr/bin/env python3
"""
Complete OpenAI Platform Integration Setup
This script sets up everything needed for OpenAI Platform integration.
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)

def print_step(step_num, title, description=""):
    """Print a formatted step."""
    print(f"\n{step_num}️⃣ {title}")
    if description:
        print(f"   {description}")

def check_environment():
    """Check if environment is set up correctly."""
    print_header("Environment Check")

    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Creating template .env file...")

        env_template = """# Google OAuth Configuration for OpenAI Platform Integration
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar
TOKEN_FILE_PATH=.gcp-saved-tokens.json

# Railway Deployment (if using Railway)
# PORT=8000
# HOST=0.0.0.0
"""

        with open(".env", "w") as f:
            f.write(env_template)

        print("✅ Created .env template")
        print("   Please edit .env with your Google OAuth credentials")
        return False

    print("✅ .env file found")

    # Check if credentials are configured
    from dotenv import load_dotenv
    load_dotenv()

    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    if not client_id or client_id == 'your_client_id_here':
        print("❌ GOOGLE_CLIENT_ID not configured in .env")
        return False

    if not client_secret or client_secret == 'your_client_secret_here':
        print("❌ GOOGLE_CLIENT_SECRET not configured in .env")
        return False

    print(f"✅ OAuth credentials configured")
    print(f"   Client ID: {client_id[:20]}...")
    return True

def setup_google_oauth():
    """Guide user through Google OAuth setup."""
    print_header("Google Cloud Console Setup")

    print("If you haven't set up Google OAuth credentials yet:")
    print("\n1. Go to Google Cloud Console:")
    print("   https://console.cloud.google.com/")

    print("\n2. Create or select a project")

    print("\n3. Enable Google Calendar API:")
    print("   - Go to APIs & Services → Library")
    print("   - Search for 'Google Calendar API'")
    print("   - Click 'Enable'")

    print("\n4. Create OAuth 2.0 Credentials:")
    print("   - Go to APIs & Services → Credentials")
    print("   - Click '+ CREATE CREDENTIALS' → OAuth 2.0 Client ID")
    print("   - Choose 'Desktop Application'")
    print("   - Give it a name like 'OpenAI Platform Integration'")

    print("\n5. Add your credentials to .env file")

    input("\n📝 Press Enter when you've completed the Google Cloud Console setup...")

def generate_production_token():
    """Generate production token for OpenAI Platform."""
    print_header("Generate Production Token")

    print("Generating OAuth token for OpenAI Platform...")

    try:
        # Run the token generation script
        result = subprocess.run([sys.executable, "get_openai_token.py"],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Token generation completed successfully!")
            print("\nOutput:")
            print(result.stdout)
            return True
        else:
            print("❌ Token generation failed")
            print("Error:", result.stderr)
            return False

    except Exception as e:
        print(f"❌ Error running token generator: {e}")
        return False

def test_deployment():
    """Test the Railway deployment."""
    print_header("Test Deployment")

    print("Testing your Railway deployment...")

    try:
        import requests

        # Test health endpoint
        response = requests.get("https://mcp.dipmedia.ai/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")

        # Test token status endpoint
        response = requests.get("https://mcp.dipmedia.ai/token-status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Token status endpoint available")
            print(f"   Token manager: {data.get('token_manager', 'unknown')}")
        else:
            print(f"⚠️  Token status endpoint returned: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ Deployment test failed: {e}")
        return False

def deploy_updates():
    """Deploy updates to Railway."""
    print_header("Deploy Updates")

    print("Deploying authentication updates to Railway...")

    try:
        # Git add
        subprocess.run(["git", "add", "."], check=True)

        # Git commit
        commit_message = """🔐 Add production OAuth token management for OpenAI Platform

✅ Features Added:
- Production token manager with automatic refresh
- Long-lived OAuth token support for OpenAI Platform
- Fallback authentication for compatibility
- Token status monitoring endpoint
- Setup scripts for easy configuration

🎯 OpenAI Platform Ready:
- Automatic token refresh prevents expiration
- Production-grade authentication
- Compatible with OpenAI Platform MCP integration

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        # Git push
        subprocess.run(["git", "push", "origin", "main"], check=True)

        print("✅ Updates deployed to Railway successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        return False

def show_openai_setup_guide():
    """Show the final OpenAI Platform setup guide."""
    print_header("OpenAI Platform Setup Guide")

    print("Your MCP server is ready for OpenAI Platform integration!")

    print("\n📋 OpenAI Platform Configuration:")
    print("   Server URL: https://mcp.dipmedia.ai/mcp")
    print("   Protocol: HTTP/JSON-RPC 2.0")
    print("   Authentication: Bearer Token")

    print("\n🔑 Access Token:")
    print("   Use the token from the previous step (starts with 'ya29.')")
    print("   The server will automatically refresh this token when needed")

    print("\n🧪 Test Commands:")
    print("   - 'Schedule a meeting tomorrow at 2 PM'")
    print("   - 'What's on my calendar today?'")
    print("   - 'Am I free Friday afternoon?'")

    print("\n📊 Monitoring:")
    print("   Token Status: https://mcp.dipmedia.ai/token-status")
    print("   Health Check: https://mcp.dipmedia.ai/health")
    print("   API Docs: https://mcp.dipmedia.ai/docs")

def main():
    """Main setup function."""
    print_header("OpenAI Platform Integration Setup")
    print("This script will set up your Google Calendar MCP server for OpenAI Platform")

    success = True

    # Step 1: Check environment
    print_step(1, "Check Environment")
    if not check_environment():
        print("\n⚠️  Please configure your .env file and run this script again")
        print("   Make sure to add your Google OAuth Client ID and Secret")
        return

    # Step 2: Google OAuth setup guide
    print_step(2, "Google OAuth Setup")
    setup_google_oauth()

    # Step 3: Generate production token
    print_step(3, "Generate Production Token")
    if not generate_production_token():
        print("\n⚠️  Token generation failed. Please check your OAuth configuration")
        success = False

    # Step 4: Deploy updates
    print_step(4, "Deploy Updates")
    if not deploy_updates():
        print("\n⚠️  Deployment failed. Please check git status and try manually")
        success = False

    # Step 5: Test deployment
    print_step(5, "Test Deployment")
    if not test_deployment():
        print("\n⚠️  Deployment test failed. Check Railway logs")
        success = False

    # Final setup guide
    if success:
        show_openai_setup_guide()
        print_header("Setup Complete! 🎉")
        print("Your voice assistant calendar integration is ready for OpenAI Platform!")
    else:
        print_header("Setup Issues Detected")
        print("Some steps failed. Please review the errors above and retry.")

if __name__ == "__main__":
    main()