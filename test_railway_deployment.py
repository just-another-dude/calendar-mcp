#!/usr/bin/env python3
"""
Test script to verify Railway deployment is working correctly.
Run this script with your Railway URL to test all endpoints.
"""

import requests
import sys
from datetime import datetime


def test_railway_deployment(base_url: str):
    """Test the Railway deployment endpoints."""
    print(f"🧪 Testing Railway deployment at: {base_url}")
    print("=" * 60)

    results = []

    # Test 1: Health Check
    print("\n1️⃣ Testing Health Endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed: {data}")
            results.append(("Health Check", True, data))
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            results.append(("Health Check", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        results.append(("Health Check", False, str(e)))

    # Test 2: MCP Initialize
    print("\n2️⃣ Testing MCP Initialize...")
    try:
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": "test_init",
            "params": {},
        }
        response = requests.post(
            f"{base_url}/mcp",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ MCP initialize passed: {data}")
            results.append(("MCP Initialize", True, data))
        else:
            print(f"   ❌ MCP initialize failed: {response.status_code}")
            results.append(("MCP Initialize", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ MCP initialize error: {e}")
        results.append(("MCP Initialize", False, str(e)))

    # Test 3: MCP Tools List
    print("\n3️⃣ Testing MCP Tools List...")
    try:
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": "test_tools",
            "params": {},
        }
        response = requests.post(
            f"{base_url}/mcp",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            tools_count = len(data.get("result", {}).get("tools", []))
            print(f"   ✅ MCP tools list passed: Found {tools_count} tools")
            results.append(("MCP Tools List", True, f"{tools_count} tools available"))
        else:
            print(f"   ❌ MCP tools list failed: {response.status_code}")
            results.append(("MCP Tools List", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ MCP tools list error: {e}")
        results.append(("MCP Tools List", False, str(e)))

    # Test 4: API Documentation
    print("\n4️⃣ Testing API Documentation...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=10)
        if response.status_code == 200:
            print("   ✅ API docs accessible")
            results.append(("API Documentation", True, "Docs accessible"))
        else:
            print(f"   ❌ API docs failed: {response.status_code}")
            results.append(
                ("API Documentation", False, f"Status: {response.status_code}")
            )
    except Exception as e:
        print(f"   ❌ API docs error: {e}")
        results.append(("API Documentation", False, str(e)))

    # Test 5: OpenAPI Schema
    print("\n5️⃣ Testing OpenAPI Schema...")
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=10)
        if response.status_code == 200:
            schema = response.json()
            endpoints_count = len(schema.get("paths", {}))
            print(
                f"   ✅ OpenAPI schema accessible: {endpoints_count} endpoints defined"
            )
            results.append(("OpenAPI Schema", True, f"{endpoints_count} endpoints"))
        else:
            print(f"   ❌ OpenAPI schema failed: {response.status_code}")
            results.append(("OpenAPI Schema", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ OpenAPI schema error: {e}")
        results.append(("OpenAPI Schema", False, str(e)))

    # Summary
    print("\n" + "=" * 60)
    print("🎯 RAILWAY DEPLOYMENT TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for test_name, success, details in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:20} {status} - {details}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("Your Railway deployment is ready for OpenAI Platform integration!")
        print(f"\n🔗 Your MCP endpoint: {base_url}/mcp")
        print(f"📚 API docs: {base_url}/docs")
        return True
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Check the Railway logs for more details.")
        return False


def main():
    """Main function to run deployment tests."""
    if len(sys.argv) != 2:
        print("Usage: python test_railway_deployment.py <RAILWAY_URL>")
        print("Example: python test_railway_deployment.py https://your-app.railway.app")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")

    print("Google Calendar MCP Server - Railway Deployment Test")
    print("=" * 60)
    print(f"Testing deployment at: {base_url}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    success = test_railway_deployment(base_url)

    if success:
        print("\n🚀 Next Steps:")
        print("1. Copy your MCP endpoint URL for OpenAI Platform")
        print("2. Configure your OpenAI Platform integration")
        print("3. Test voice agent integration")
        sys.exit(0)
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check Railway deployment logs")
        print("2. Verify environment variables are set")
        print("3. Ensure health endpoint returns 200")
        sys.exit(1)


if __name__ == "__main__":
    main()
