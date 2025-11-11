#!/usr/bin/env python3
"""
Get a long-lived OAuth token for OpenAI Platform integration.
This script generates a refresh token and provides an access token
that can be automatically refreshed by the MCP server.
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add the current directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from src.auth import get_credentials


def get_production_token():
    """Get a production-ready OAuth token for OpenAI Platform."""
    print("🔐 Google Calendar OAuth Setup for OpenAI Platform")
    print("=" * 60)

    # Load environment variables
    load_dotenv()

    # Check required environment variables
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ Missing Google OAuth credentials!")
        print("\nPlease set these environment variables:")
        print("- GOOGLE_CLIENT_ID")
        print("- GOOGLE_CLIENT_SECRET")
        print("\nYou can get these from Google Cloud Console:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Navigate to APIs & Services > Credentials")
        print("3. Create OAuth 2.0 Client ID")
        return None

    print("✅ Found OAuth credentials")
    print(f"   Client ID: {client_id[:20]}...")
    print(f"   Client Secret: {client_secret[:10]}...")

    # Get credentials using the existing auth system
    print("\n🔄 Initiating OAuth flow...")
    try:
        credentials = get_credentials(user_id="openai-platform")

        if not credentials:
            print("❌ Failed to get OAuth credentials")
            return None

        print("✅ Successfully obtained OAuth credentials!")

        # Display token information
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        expires_at = credentials.expiry

        print("\n" + "=" * 60)
        print("🎯 OPENAI PLATFORM CONFIGURATION")
        print("=" * 60)

        print("\n📋 MCP Server Settings:")
        print("   Server URL: https://mcp.dipmedia.ai/mcp")
        print("   Protocol: HTTP/JSON-RPC 2.0")
        print("   Authentication: Bearer Token")

        print("\n🔑 Access Token (for OpenAI Platform):")
        print(f"   {access_token}")

        if expires_at:
            print(f"\n⏰ Token Expires: {expires_at}")
            time_left = expires_at - datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
            if time_left.total_seconds() > 0:
                hours_left = time_left.total_seconds() / 3600
                print(f"   Time remaining: {hours_left:.1f} hours")
            else:
                print("   ⚠️  Token has expired")

        if refresh_token:
            print("\n🔄 Refresh Token Available: ✅")
            print("   The MCP server can automatically refresh this token")
        else:
            print("\n🔄 Refresh Token Available: ❌")
            print("   ⚠️  You may need to re-authenticate when token expires")

        # Save token info for the server
        token_info = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "client_id": client_id,
            "client_secret": client_secret,
            "created_for": "openai-platform",
            "created_at": datetime.utcnow().isoformat(),
        }

        token_file = "openai_platform_token.json"
        with open(token_file, "w") as f:
            json.dump(token_info, f, indent=2)

        print(f"\n💾 Token info saved to: {token_file}")

        print("\n" + "=" * 60)
        print("🚀 NEXT STEPS")
        print("=" * 60)
        print("1. Copy the Access Token above")
        print("2. Paste it into OpenAI Platform 'Access Token / API Key' field")
        print("3. Set MCP Server URL to: https://mcp.dipmedia.ai/mcp")
        print("4. Test your voice assistant!")

        print("\n⏳ Token Validity:")
        if expires_at:
            if time_left.total_seconds() > 3600:  # More than 1 hour
                print(f"   ✅ Good for {hours_left:.1f} hours")
            else:
                print("   ⚠️  Expires soon - consider refreshing")

        print("\n🔄 Auto-Refresh:")
        if refresh_token:
            print("   ✅ Enabled - token will refresh automatically")
        else:
            print("   ❌ Not available - manual re-auth needed")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "token_file": token_file,
        }

    except Exception as e:
        print(f"❌ Error during OAuth flow: {e}")
        return None


def refresh_existing_token():
    """Refresh an existing token if possible."""
    token_file = "openai_platform_token.json"

    if not os.path.exists(token_file):
        print(f"❌ Token file {token_file} not found")
        return None

    try:
        with open(token_file, "r") as f:
            token_info = json.load(f)

        refresh_token = token_info.get("refresh_token")
        if not refresh_token:
            print("❌ No refresh token available")
            return None

        print("🔄 Refreshing existing token...")

        # Use the auth system to refresh
        credentials = get_credentials(user_id="openai-platform")

        if credentials and credentials.valid:
            print("✅ Token refreshed successfully!")

            # Update token file
            token_info.update(
                {
                    "access_token": credentials.token,
                    "expires_at": credentials.expiry.isoformat()
                    if credentials.expiry
                    else None,
                    "refreshed_at": datetime.utcnow().isoformat(),
                }
            )

            with open(token_file, "w") as f:
                json.dump(token_info, f, indent=2)

            print("\n🔑 New Access Token:")
            print(f"   {credentials.token}")

            return credentials.token
        else:
            print("❌ Token refresh failed")
            return None

    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
        return None


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        refresh_existing_token()
    else:
        get_production_token()


if __name__ == "__main__":
    main()
