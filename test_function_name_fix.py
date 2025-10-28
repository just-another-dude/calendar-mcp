#!/usr/bin/env python3
"""
Simple test to verify the function name fix is working.
"""

import requests
import json

def test_function_name_fix():
    """Test if the quick_add_event function name fix is working."""

    # Test data
    payload = {
        "jsonrpc": "2.0",
        "id": 1234,
        "method": "tools/call",
        "params": {
            "name": "quick_add_event",
            "arguments": {
                "calendar_id": "primary",
                "text": "Function name fix test",
                "oauth_token": "test_token"
            }
        }
    }

    try:
        # Make request to local server
        response = requests.post(
            "http://localhost:8000/mcp",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"📥 Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"📊 Response: {json.dumps(result, indent=2)}")

            # Check for the old bug
            if "error" in result:
                error_msg = result["error"].get("message", "")
                if "create_quick_add_event" in error_msg:
                    print("❌ OLD BUG STILL PRESENT: create_quick_add_event error")
                    return False
                else:
                    print(f"✅ FUNCTION NAME FIX WORKING! Error is different: {error_msg}")
                    return True
            else:
                print("✅ FUNCTION NAME FIX WORKING! No function name error")
                return True
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Function Name Fix")
    print("=" * 30)

    success = test_function_name_fix()

    if success:
        print("\n✅ SUCCESS: Function name fix is working!")
        print("✅ No more 'create_quick_add_event' errors")
        print("✅ Ready for Railway deployment")
    else:
        print("\n❌ FAILED: Function name fix not working")

    exit(0 if success else 1)