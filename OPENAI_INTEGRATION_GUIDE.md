# 🤖 OpenAI Platform MCP Integration Guide

Complete guide to connect your Google Calendar MCP server with OpenAI Platform for voice agent integration.

## 🚀 Quick Testing

### 1. Test Railway Deployment

```bash
python test_railway_deployment.py https://your-app.railway.app
```

### 2. Test MCP Integration

First get a test OAuth token from [Google OAuth Playground](https://developers.google.com/oauthplayground/):
1. Go to OAuth 2.0 Playground
2. Select "Google Calendar API v3"
3. Click "Authorize APIs"
4. Get your access token

Then test:
```bash
python test_openai_mcp_integration.py https://your-app.railway.app YOUR_OAUTH_TOKEN
```

## 🔗 OpenAI Platform Configuration

### MCP Server Details

- **Server URL**: `https://your-app.railway.app/mcp`
- **Protocol**: HTTP/JSON-RPC 2.0
- **Authentication**: OAuth Bearer Token
- **Protocol Version**: 2024-11-05

### Available Tools

Your MCP server provides these voice-optimized tools:

1. **`voice_book_appointment`** - Book appointments using natural language
2. **`voice_check_availability`** - Check availability with conversational responses
3. **`voice_get_upcoming`** - Get upcoming events in voice-friendly format
4. **`list_calendars`** - List user's calendars
5. **`find_events`** - Search and find events
6. **`create_event`** - Create detailed events
7. **`quick_add_event`** - Create events from natural language
8. **`update_event`** - Update existing events
9. **`delete_event`** - Delete events
10. **`check_free_busy`** - Query availability information

## 🎤 Voice Agent Integration

### Recommended Tool Usage for Voice Agents

**For appointment booking:**
```json
{
  "name": "voice_book_appointment",
  "arguments": {
    "natural_language_request": "Schedule a meeting with John tomorrow at 2 PM for one hour",
    "calendar_id": "primary"
  }
}
```

**For checking availability:**
```json
{
  "name": "voice_check_availability",
  "arguments": {
    "time_request": "tomorrow afternoon",
    "duration_minutes": 60
  }
}
```

**For getting upcoming events:**
```json
{
  "name": "voice_get_upcoming",
  "arguments": {
    "calendar_id": "primary",
    "limit": 3
  }
}
```

### Voice-Friendly Responses

All voice tools return structured responses optimized for conversational AI:

```json
{
  "success": true,
  "message": "Perfect! I've scheduled your appointment for Tuesday, October 22 at 2:00 PM.",
  "event_id": "event_123",
  "event_link": "https://calendar.google.com/..."
}
```

## 🔧 OpenAI Platform Setup Steps

### 1. Add MCP Server to OpenAI Platform

1. Go to your OpenAI Platform dashboard
2. Navigate to "MCP Servers" or "Integrations"
3. Add new MCP server:
   - **Name**: Google Calendar
   - **URL**: `https://your-app.railway.app/mcp`
   - **Protocol**: HTTP
   - **Authentication**: OAuth 2.0

### 2. Configure OAuth

In OpenAI Platform, set up OAuth integration:
- **Client ID**: Your Google OAuth Client ID
- **Client Secret**: Your Google OAuth Client Secret
- **Scopes**: `https://www.googleapis.com/auth/calendar`
- **Redirect URI**: `https://platform.openai.com/oauth/callback` (or provided by OpenAI)

### 3. Test Integration

Use the OpenAI Platform test tools to verify:
1. MCP server connection
2. OAuth authentication flow
3. Tool calling functionality

## 📝 Example Voice Agent Prompts

### Booking Appointments
- "Schedule a dentist appointment for next Tuesday at 10 AM"
- "Book a 30-minute call with Sarah tomorrow afternoon"
- "Set up a team meeting on Friday from 2 to 3 PM"

### Checking Availability
- "Am I free tomorrow morning?"
- "What does my schedule look like next week?"
- "Do I have any conflicts on Thursday afternoon?"

### Managing Events
- "What are my upcoming appointments?"
- "Cancel my 3 PM meeting today"
- "Move my lunch meeting to 1 PM"

## 🛠️ Troubleshooting

### Common Issues

**Authentication Errors:**
- Verify OAuth token is valid and not expired
- Check Google Calendar API is enabled
- Ensure proper OAuth scopes are granted

**Tool Call Failures:**
- Check server logs in Railway dashboard
- Verify MCP protocol version compatibility
- Test individual endpoints directly

**Voice Response Issues:**
- Use voice-optimized tools (`voice_*` tools)
- Check response format matches expected structure
- Verify natural language parsing is working

### Debug Commands

Test specific functionality:
```bash
# Test health
curl https://your-app.railway.app/health

# Test MCP initialize
curl -X POST https://your-app.railway.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":"test","params":{}}'

# Test with OAuth
curl -X POST https://your-app.railway.app/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"test","params":{}}'
```

## 🎯 Production Checklist

- [ ] Railway deployment is stable and healthy
- [ ] Google OAuth credentials configured for production
- [ ] MCP server responds to initialize and tools/list
- [ ] Voice tools return proper responses
- [ ] OpenAI Platform MCP connection established
- [ ] OAuth flow working end-to-end
- [ ] Voice agent can successfully call calendar tools
- [ ] Error handling and edge cases tested

## 🚀 Launch!

Once everything is working:
1. Your voice agent can book appointments
2. Users can check availability naturally
3. Calendar management works conversationally
4. Real-time updates via webhooks (optional)

**You now have a production-ready Google Calendar voice agent! 🎉**