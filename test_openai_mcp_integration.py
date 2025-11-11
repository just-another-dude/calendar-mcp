#!/usr/bin/env python3
"""
Test script for OpenAI Platform MCP integration.
This simulates how OpenAI will connect to your Calendar MCP server.
"""

import requests
import sys
import os
from datetime import datetime


def test_mcp_with_oauth(base_url: str, oauth_token: str):
    """Test MCP integration with OAuth token (simulating OpenAI)."""
    print("🧪 Testing OpenAI MCP Integration")
    print(f"🌐 Server: {base_url}")
    print(
        f"🔑 OAuth Token: {oauth_token[:20]}..."
        if oauth_token
        else "❌ No token provided"
    )
    print("=" * 60)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth_token}",
    }

    results = []

    # Test 1: MCP Initialize
    print("\n1️⃣ Testing MCP Initialize...")
    try:
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": "openai_init",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}},
        }

        response = requests.post(
            f"{base_url}/mcp", json=request, headers=headers, timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            print(
                f"   ✅ Initialize successful: {data.get('result', {}).get('protocolVersion')}"
            )
            results.append(("Initialize", True, data))
        else:
            print(f"   ❌ Initialize failed: {response.status_code} - {response.text}")
            results.append(
                ("Initialize", False, f"{response.status_code}: {response.text}")
            )

    except Exception as e:
        print(f"   ❌ Initialize error: {e}")
        results.append(("Initialize", False, str(e)))

    # Test 2: Tools List
    print("\n2️⃣ Testing Tools List...")
    try:
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": "openai_tools",
            "params": {},
        }

        response = requests.post(
            f"{base_url}/mcp", json=request, headers=headers, timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            tools = data.get("result", {}).get("tools", [])
            tool_names = [tool["name"] for tool in tools]
            print(f"   ✅ Found {len(tools)} tools: {', '.join(tool_names[:5])}")
            results.append(("Tools List", True, f"{len(tools)} tools"))
        else:
            print(f"   ❌ Tools list failed: {response.status_code} - {response.text}")
            results.append(
                ("Tools List", False, f"{response.status_code}: {response.text}")
            )

    except Exception as e:
        print(f"   ❌ Tools list error: {e}")
        results.append(("Tools List", False, str(e)))

    # Test 3: Voice-Optimized Tool Call
    print("\n3️⃣ Testing Voice Tool (voice_get_upcoming)...")
    try:
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": "openai_voice_test",
            "params": {
                "name": "voice_get_upcoming",
                "arguments": {"calendar_id": "primary", "limit": 3},
            },
        }

        response = requests.post(
            f"{base_url}/mcp", json=request, headers=headers, timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                print(f"   ⚠️  Tool returned error: {error_msg}")
                results.append(("Voice Tool", False, error_msg))
            else:
                content = data.get("result", {}).get("content", [])
                print(f"   ✅ Voice tool successful: {len(content)} response items")
                results.append(("Voice Tool", True, f"{len(content)} items"))
        else:
            print(f"   ❌ Voice tool failed: {response.status_code} - {response.text}")
            results.append(
                ("Voice Tool", False, f"{response.status_code}: {response.text}")
            )

    except Exception as e:
        print(f"   ❌ Voice tool error: {e}")
        results.append(("Voice Tool", False, str(e)))

    # Test 4: Calendar List Tool Call
    print("\n4️⃣ Testing Calendar Tool (list_calendars)...")
    try:
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": "openai_calendar_test",
            "params": {"name": "list_calendars", "arguments": {}},
        }

        response = requests.post(
            f"{base_url}/mcp", json=request, headers=headers, timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                print(f"   ⚠️  Calendar tool returned error: {error_msg}")
                results.append(("Calendar Tool", False, error_msg))
            else:
                content = data.get("result", {}).get("content", [])
                print(f"   ✅ Calendar tool successful: {len(content)} response items")
                results.append(("Calendar Tool", True, f"{len(content)} items"))
        else:
            print(
                f"   ❌ Calendar tool failed: {response.status_code} - {response.text}"
            )
            results.append(
                ("Calendar Tool", False, f"{response.status_code}: {response.text}")
            )

    except Exception as e:
        print(f"   ❌ Calendar tool error: {e}")
        results.append(("Calendar Tool", False, str(e)))

    # Summary
    print("\n" + "=" * 60)
    print("🎯 OPENAI MCP INTEGRATION TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for test_name, success, details in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:15} {status} - {details}")

    print(f"\nPassed: {passed}/{total}")

    if passed >= 2:  # Initialize and Tools List are critical
        print("\n🎉 MCP INTEGRATION READY!")
        print("Your server is ready for OpenAI Platform voice agent integration!")

        # OpenAI Platform Configuration
        print("\n🤖 OpenAI Platform Configuration:")
        print(f"   MCP Server URL: {base_url}/mcp")
        print("   Protocol: HTTP/JSON-RPC 2.0")
        print("   Authentication: OAuth Bearer Token")
        print(
            f"   Available Tools: {len(tools) if 'tools' in locals() else 'Check tools/list response'}"
        )

        return True
    else:
        print("\n❌ MCP INTEGRATION NEEDS WORK")
        print("Check OAuth token and server configuration.")
        return False


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print(
            "Usage: python test_openai_mcp_integration.py <RAILWAY_URL> [OAUTH_TOKEN]"
        )
        print(
            "Example: python test_openai_mcp_integration.py https://your-app.railway.app your_oauth_token"
        )
        print("\nYou can also set GOOGLE_OAUTH_TOKEN environment variable")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    oauth_token = sys.argv[2] if len(sys.argv) > 2 else os.getenv("GOOGLE_OAUTH_TOKEN")

    if not oauth_token:
        print("❌ OAuth token required!")
        print(
            "Either provide it as second argument or set GOOGLE_OAUTH_TOKEN environment variable"
        )
        print("\nTo get an OAuth token:")
        print(
            "1. Go to Google OAuth 2.0 Playground: https://developers.google.com/oauthplayground/"
        )
        print("2. Select Google Calendar API v3")
        print("3. Authorize and get access token")
        sys.exit(1)

    print("Google Calendar MCP Server - OpenAI Integration Test")
    print("=" * 60)
    print(f"Testing at: {base_url}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    success = test_mcp_with_oauth(base_url, oauth_token)

    if success:
        print("\n🚀 Next Steps for OpenAI Platform:")
        print("1. Copy your MCP endpoint URL")
        print("2. Configure OAuth in OpenAI Platform")
        print("3. Test with voice agent")
        print("4. Deploy to production!")
        sys.exit(0)
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Verify OAuth token is valid")
        print("2. Check Google Calendar API permissions")
        print("3. Ensure server OAuth configuration is correct")
        sys.exit(1)


if __name__ == "__main__":
    main()
