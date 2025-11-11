#!/usr/bin/env python3
"""
Test script for MCP integration with Google Calendar server.
This script tests the MCP protocol implementation and OAuth token handling.
"""

import requests
import json
import sys


class MCPTester:
    def __init__(self, server_url, oauth_token):
        """Initialize MCP tester with server URL and OAuth token."""
        self.server_url = server_url.rstrip("/")
        self.oauth_token = oauth_token
        self.mcp_url = f"{self.server_url}/mcp"
        self.test_url = f"{self.server_url}/test/mcp"

    def test_health(self):
        """Test server health endpoint."""
        print("🔍 Testing server health...")
        try:
            response = requests.get(f"{self.server_url}/health")
            if response.status_code == 200:
                print("✅ Server health check passed")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    def test_mcp_implementation(self):
        """Test MCP implementation using the test endpoint."""
        print("🔍 Testing MCP implementation...")
        try:
            payload = {
                "test_oauth_token": self.oauth_token,
                "test_tool": "list_calendars",
            }

            response = requests.post(
                self.test_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    print("✅ MCP implementation test passed")
                    print(
                        f"   OpenAI integration ready: {result.get('openai_integration_ready')}"
                    )
                    return True
                else:
                    print(f"❌ MCP implementation test failed: {result.get('message')}")
                    return False
            else:
                print(f"❌ MCP test endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ MCP implementation test error: {e}")
            return False

    def test_mcp_protocol(self):
        """Test MCP protocol directly."""
        print("🔍 Testing MCP protocol...")

        tests = [
            {
                "name": "Initialize",
                "request": {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": "test_init",
                    "params": {},
                },
            },
            {
                "name": "List Tools",
                "request": {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": "test_tools",
                    "params": {},
                },
            },
            {
                "name": "Call Voice Tool",
                "request": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "id": "test_voice",
                    "params": {"name": "voice_get_upcoming", "arguments": {"limit": 3}},
                },
            },
        ]

        all_passed = True
        for test in tests:
            try:
                print(f"   Testing {test['name']}...")
                response = requests.post(
                    self.mcp_url,
                    json=test["request"],
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.oauth_token}",
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    if "error" in result:
                        print(
                            f"   ❌ {test['name']} failed: {result['error']['message']}"
                        )
                        all_passed = False
                    else:
                        print(f"   ✅ {test['name']} passed")
                else:
                    print(f"   ❌ {test['name']} HTTP error: {response.status_code}")
                    all_passed = False

            except Exception as e:
                print(f"   ❌ {test['name']} error: {e}")
                all_passed = False

        return all_passed

    def test_voice_tools(self):
        """Test voice-optimized tools specifically."""
        print("🔍 Testing voice-optimized tools...")

        voice_tests = [
            {
                "tool": "voice_check_availability",
                "args": {"time_request": "tomorrow afternoon"},
            },
            {"tool": "voice_get_upcoming", "args": {"limit": 5}},
        ]

        all_passed = True
        for test in voice_tests:
            try:
                print(f"   Testing {test['tool']}...")
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "id": f"test_{test['tool']}",
                    "params": {"name": test["tool"], "arguments": test["args"]},
                }

                response = requests.post(
                    self.mcp_url,
                    json=request,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.oauth_token}",
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    if "error" in result:
                        print(
                            f"   ❌ {test['tool']} failed: {result['error']['message']}"
                        )
                        all_passed = False
                    else:
                        # Check if result contains voice-friendly response
                        content = result.get("result", {}).get("content", [])
                        if content and isinstance(content[0], dict):
                            text = content[0].get("text", "")
                            try:
                                parsed = json.loads(text)
                                if "message" in parsed:
                                    print(
                                        f"   ✅ {test['tool']} passed with voice response"
                                    )
                                    print(
                                        f"      Message: {parsed['message'][:100]}..."
                                    )
                                else:
                                    print(f"   ✅ {test['tool']} passed")
                            except json.JSONDecodeError:
                                print(f"   ✅ {test['tool']} passed")
                        else:
                            print(f"   ✅ {test['tool']} passed")
                else:
                    print(f"   ❌ {test['tool']} HTTP error: {response.status_code}")
                    all_passed = False

            except Exception as e:
                print(f"   ❌ {test['tool']} error: {e}")
                all_passed = False

        return all_passed

    def run_all_tests(self):
        """Run all tests and provide summary."""
        print("🚀 Starting MCP Integration Tests")
        print("=" * 50)

        tests = [
            ("Server Health", self.test_health),
            ("MCP Implementation", self.test_mcp_implementation),
            ("MCP Protocol", self.test_mcp_protocol),
            ("Voice Tools", self.test_voice_tools),
        ]

        results = {}
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            print("-" * 30)
            results[test_name] = test_func()

        # Summary
        print("\n" + "=" * 50)
        print("🎯 TEST SUMMARY")
        print("=" * 50)

        all_passed = True
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name:20} {status}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 50)
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
            print("Your MCP server is ready for OpenAI integration!")
        else:
            print("⚠️  SOME TESTS FAILED")
            print(
                "Please check the error messages above and fix issues before OpenAI integration."
            )

        return all_passed


def main():
    """Main function to run MCP tests."""
    if len(sys.argv) != 3:
        print("Usage: python test_mcp_integration.py <server_url> <oauth_token>")
        print(
            "Example: python test_mcp_integration.py https://your-app.railway.app ya29.a0..."
        )
        sys.exit(1)

    server_url = sys.argv[1]
    oauth_token = sys.argv[2]

    # Validate inputs
    if not server_url.startswith(("http://", "https://")):
        print("❌ Server URL must start with http:// or https://")
        sys.exit(1)

    if len(oauth_token) < 20:
        print("❌ OAuth token appears to be too short. Please check your token.")
        sys.exit(1)

    # Run tests
    tester = MCPTester(server_url, oauth_token)
    success = tester.run_all_tests()

    if success:
        print("\n🔗 Next Steps:")
        print("1. Use this server URL in OpenAI Platform:")
        print(f"   {server_url}/mcp")
        print("2. Use your OAuth token in the authorization field")
        print("3. Test voice agent integration with calendar booking!")
        sys.exit(0)
    else:
        print("\n🔧 Fix the issues above and run the test again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
