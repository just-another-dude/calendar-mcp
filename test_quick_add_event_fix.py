#!/usr/bin/env python3
"""
Test script specifically for the quick_add_event function fix.
This script tests that the function name bug is resolved and proper response format is returned.
"""

import asyncio
import aiohttp
import json
import os
import sys
import random
from datetime import datetime


class QuickAddEventTester:
    def __init__(self):
        """Initialize tester with OAuth token from environment."""
        self.oauth_token = os.getenv("GOOGLE_OAUTH_TOKEN")
        if not self.oauth_token:
            print("❌ GOOGLE_OAUTH_TOKEN environment variable not found")
            sys.exit(1)

        # Test both local and production endpoints
        self.test_endpoints = [
            "http://localhost:5000",  # Local development
            "https://mcp.dipmedia.ai",  # Production
        ]

    async def test_quick_add_event_fix(self, server_url):
        """Test the quick_add_event function with the fix applied."""
        print(f"🧪 Testing quick_add_event fix on {server_url}")

        mcp_url = f"{server_url}/mcp"

        # Test payload for quick_add_event
        payload = {
            "jsonrpc": "2.0",
            "id": random.randint(1000, 9999),
            "method": "tools/call",
            "params": {
                "name": "quick_add_event",
                "arguments": {
                    "calendar_id": "primary",
                    "text": f"Test event fix {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "oauth_token": self.oauth_token,
                },
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.oauth_token}",
                }

                print(f"📤 Sending MCP request to {mcp_url}")
                print(f"📋 Function: {payload['params']['name']}")

                async with session.post(
                    mcp_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    print(f"📥 Response status: {response.status}")

                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ HTTP Error {response.status}: {error_text}")
                        return False

                    result = await response.json()
                    print(f"📊 Response structure: {list(result.keys())}")

                    # Check for the old error (AttributeError for create_quick_add_event)
                    if "error" in result:
                        error_msg = result["error"].get("message", "")
                        if "create_quick_add_event" in error_msg:
                            print(f"❌ OLD BUG STILL PRESENT: {error_msg}")
                            return False
                        else:
                            print(f"❌ Different error: {error_msg}")
                            return False

                    # Check for proper response structure
                    if "result" in result and "content" in result["result"]:
                        content = result["result"]["content"]
                        if isinstance(content, list) and len(content) > 0:
                            text_content = content[0].get("text", "")
                            try:
                                parsed_result = json.loads(text_content)
                                print(f"✅ Parsed response: {parsed_result}")

                                # Check for our new response format
                                if parsed_result.get("success"):
                                    print(f"✅ SUCCESS: {parsed_result.get('message')}")
                                    if parsed_result.get("event_id"):
                                        print(
                                            f"📅 Event ID: {parsed_result['event_id']}"
                                        )
                                    return True
                                else:
                                    print(
                                        f"⚠️  Function failed: {parsed_result.get('error')}"
                                    )
                                    return False

                            except json.JSONDecodeError as e:
                                print(f"❌ JSON parsing failed: {e}")
                                print(f"Raw content: {text_content}")
                                return False

                    print(f"❌ Unexpected response structure: {result}")
                    return False

        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    async def run_tests(self):
        """Run tests on all available endpoints."""
        print("🧪 Testing quick_add_event function fix")
        print("=" * 50)

        results = {}

        for endpoint in self.test_endpoints:
            print(f"\n📍 Testing endpoint: {endpoint}")
            try:
                success = await self.test_quick_add_event_fix(endpoint)
                results[endpoint] = success

                if success:
                    print(f"✅ {endpoint}: quick_add_event fix working!")
                else:
                    print(f"❌ {endpoint}: quick_add_event fix failed!")

            except Exception as e:
                print(f"❌ {endpoint}: Test failed with error: {e}")
                results[endpoint] = False

        print("\n📊 Test Results Summary")
        print("=" * 50)
        for endpoint, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {endpoint}")

        # Overall result
        if any(results.values()):
            print("\n🎉 At least one endpoint is working with the fix!")
            return True
        else:
            print("\n💥 All endpoints failed - fix may need more work")
            return False


async def main():
    """Main test function."""
    tester = QuickAddEventTester()
    success = await tester.run_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
