#!/usr/bin/env python3
"""
Test script for OpenAI integration with Google Calendar MCP server.
This script tests the complete OpenAI Responses API integration.
"""

import sys
from datetime import datetime, timedelta

try:
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI package not installed. Install with: pip install openai")
    sys.exit(1)


class OpenAIMCPTester:
    def __init__(self, openai_api_key, mcp_server_url, google_oauth_token):
        """Initialize OpenAI MCP tester."""
        self.client = OpenAI(api_key=openai_api_key)
        self.mcp_server_url = mcp_server_url
        self.google_oauth_token = google_oauth_token

    def get_mcp_tool_config(self, allowed_tools=None):
        """Get MCP tool configuration for OpenAI."""
        config = {
            "type": "mcp",
            "server_label": "google_calendar",
            "server_description": "Google Calendar integration for appointment booking and management",
            "server_url": self.mcp_server_url,
            "authorization": self.google_oauth_token,
            "require_approval": "never",
        }

        if allowed_tools:
            config["allowed_tools"] = allowed_tools

        return config

    def test_basic_connection(self):
        """Test basic MCP connection to OpenAI."""
        print("🔍 Testing basic MCP connection...")
        try:
            response = self.client.responses.create(
                model="gpt-5",
                tools=[self.get_mcp_tool_config(["list_calendars"])],
                input="List my calendars",
            )

            if response.output_text:
                print("✅ Basic MCP connection successful")
                print(f"   Response: {response.output_text[:100]}...")
                return True
            else:
                print("❌ No response from OpenAI")
                return False

        except Exception as e:
            print(f"❌ Basic connection test failed: {e}")
            return False

    def test_voice_booking(self):
        """Test voice-optimized appointment booking."""
        print("🔍 Testing voice appointment booking...")
        try:
            # Use tomorrow's date to avoid past date issues
            tomorrow = datetime.now() + timedelta(days=1)
            day_name = tomorrow.strftime("%A")

            response = self.client.responses.create(
                model="gpt-5",
                tools=[self.get_mcp_tool_config(["voice_book_appointment"])],
                input=f"Schedule a test meeting {day_name} at 3 PM for 1 hour",
            )

            if response.output_text:
                print("✅ Voice booking test successful")
                print(f"   Response: {response.output_text}")

                # Check if response mentions successful booking
                if any(
                    keyword in response.output_text.lower()
                    for keyword in ["scheduled", "booked", "added", "created"]
                ):
                    print("   ✅ Booking appears successful")
                    return True
                else:
                    print("   ⚠️  Booking may have failed - check response")
                    return False
            else:
                print("❌ No response from voice booking")
                return False

        except Exception as e:
            print(f"❌ Voice booking test failed: {e}")
            return False

    def test_availability_check(self):
        """Test voice-optimized availability checking."""
        print("🔍 Testing availability checking...")
        try:
            response = self.client.responses.create(
                model="gpt-5",
                tools=[self.get_mcp_tool_config(["voice_check_availability"])],
                input="Am I free tomorrow afternoon?",
            )

            if response.output_text:
                print("✅ Availability check successful")
                print(f"   Response: {response.output_text}")

                # Check if response mentions availability
                if any(
                    keyword in response.output_text.lower()
                    for keyword in ["free", "available", "busy", "appointment"]
                ):
                    print("   ✅ Availability information provided")
                    return True
                else:
                    print("   ⚠️  No clear availability information")
                    return False
            else:
                print("❌ No response from availability check")
                return False

        except Exception as e:
            print(f"❌ Availability check failed: {e}")
            return False

    def test_upcoming_events(self):
        """Test retrieving upcoming events."""
        print("🔍 Testing upcoming events retrieval...")
        try:
            response = self.client.responses.create(
                model="gpt-5",
                tools=[self.get_mcp_tool_config(["voice_get_upcoming"])],
                input="What meetings do I have coming up this week?",
            )

            if response.output_text:
                print("✅ Upcoming events test successful")
                print(f"   Response: {response.output_text}")

                # Check if response mentions events or schedule
                if any(
                    keyword in response.output_text.lower()
                    for keyword in [
                        "meeting",
                        "appointment",
                        "event",
                        "schedule",
                        "calendar",
                    ]
                ):
                    print("   ✅ Calendar information provided")
                    return True
                else:
                    print("   ⚠️  No clear calendar information")
                    return False
            else:
                print("❌ No response from upcoming events")
                return False

        except Exception as e:
            print(f"❌ Upcoming events test failed: {e}")
            return False

    def test_complex_interaction(self):
        """Test complex multi-turn interaction."""
        print("🔍 Testing complex interaction...")
        try:
            response = self.client.responses.create(
                model="gpt-5",
                tools=[
                    self.get_mcp_tool_config(
                        [
                            "voice_check_availability",
                            "voice_book_appointment",
                            "voice_get_upcoming",
                        ]
                    )
                ],
                input="Check if I'm free tomorrow at 2 PM, and if so, schedule a doctor appointment then",
            )

            if response.output_text:
                print("✅ Complex interaction successful")
                print(f"   Response: {response.output_text}")

                # Check if response shows logical flow
                response_lower = response.output_text.lower()
                if ("free" in response_lower or "available" in response_lower) and (
                    "scheduled" in response_lower or "booked" in response_lower
                ):
                    print("   ✅ Complex logic executed successfully")
                    return True
                else:
                    print("   ⚠️  Complex interaction may be incomplete")
                    return False
            else:
                print("❌ No response from complex interaction")
                return False

        except Exception as e:
            print(f"❌ Complex interaction failed: {e}")
            return False

    def test_error_handling(self):
        """Test error handling with invalid requests."""
        print("🔍 Testing error handling...")
        try:
            response = self.client.responses.create(
                model="gpt-5",
                tools=[self.get_mcp_tool_config(["voice_book_appointment"])],
                input="Schedule a meeting for yesterday",  # Invalid past date
            )

            if response.output_text:
                print("✅ Error handling test completed")
                print(f"   Response: {response.output_text}")

                # Check if response handles the error gracefully
                response_lower = response.output_text.lower()
                if any(
                    keyword in response_lower
                    for keyword in ["cannot", "unable", "error", "invalid", "past"]
                ):
                    print("   ✅ Error handled gracefully")
                    return True
                else:
                    print("   ⚠️  Error handling unclear")
                    return False
            else:
                print("❌ No response from error handling test")
                return False

        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all OpenAI integration tests."""
        print("🚀 Starting OpenAI MCP Integration Tests")
        print("=" * 60)

        tests = [
            ("Basic Connection", self.test_basic_connection),
            ("Voice Booking", self.test_voice_booking),
            ("Availability Check", self.test_availability_check),
            ("Upcoming Events", self.test_upcoming_events),
            ("Complex Interaction", self.test_complex_interaction),
            ("Error Handling", self.test_error_handling),
        ]

        results = {}
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            print("-" * 40)
            results[test_name] = test_func()

        # Summary
        print("\n" + "=" * 60)
        print("🎯 OPENAI INTEGRATION TEST SUMMARY")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name:20} {status}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL OPENAI INTEGRATION TESTS PASSED!")
            print("Your calendar voice agent is ready for production!")
        else:
            print("⚠️  SOME TESTS FAILED")
            print("Check error messages above and verify:")
            print("- MCP server is accessible from OpenAI")
            print("- OAuth token has proper calendar permissions")
            print("- OpenAI model has access to MCP features")

        return all_passed


def main():
    """Main function to run OpenAI integration tests."""
    if len(sys.argv) != 4:
        print(
            "Usage: python test_openai_integration.py <openai_api_key> <mcp_server_url> <google_oauth_token>"
        )
        print(
            "Example: python test_openai_integration.py sk-... https://your-app.railway.app/mcp ya29.a0..."
        )
        sys.exit(1)

    openai_api_key = sys.argv[1]
    mcp_server_url = sys.argv[2]
    google_oauth_token = sys.argv[3]

    # Validate inputs
    if not openai_api_key.startswith("sk-"):
        print("❌ OpenAI API key should start with 'sk-'")
        sys.exit(1)

    if not mcp_server_url.startswith(("http://", "https://")):
        print("❌ MCP server URL must start with http:// or https://")
        sys.exit(1)

    if len(google_oauth_token) < 20:
        print("❌ Google OAuth token appears to be too short")
        sys.exit(1)

    print(f"OpenAI API Key: {openai_api_key[:10]}...")
    print(f"MCP Server URL: {mcp_server_url}")
    print(f"OAuth Token: {google_oauth_token[:20]}...")
    print()

    # Run tests
    tester = OpenAIMCPTester(openai_api_key, mcp_server_url, google_oauth_token)
    success = tester.run_all_tests()

    if success:
        print("\n🎊 CONGRATULATIONS!")
        print("Your Google Calendar voice agent is fully operational!")
        print("\n🔧 What you can do now:")
        print("- Integrate into your voice application")
        print("- Set up production user authentication")
        print("- Configure webhook notifications for real-time updates")
        print("- Scale to multiple users with individual OAuth tokens")
        sys.exit(0)
    else:
        print("\n🔧 Fix the issues above and run the test again.")
        print("Common solutions:")
        print("- Check MCP server logs in Railway dashboard")
        print("- Verify Google OAuth token is not expired")
        print("- Ensure OpenAI API key has access to Responses API")
        sys.exit(1)


if __name__ == "__main__":
    main()
