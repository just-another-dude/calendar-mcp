# Google Calendar MCP Server - Railway Deployment Guide for OpenAI Platform

This guide walks you through deploying the Google Calendar MCP server to Railway and integrating it with your OpenAI Realtime voice agent for appointment booking.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Console Setup](#google-cloud-console-setup)
3. [Railway Deployment](#railway-deployment)
4. [Environment Configuration](#environment-configuration)
5. [OpenAI Platform Integration](#openai-platform-integration)
6. [Voice Agent Endpoints](#voice-agent-endpoints)
7. [Webhook Configuration](#webhook-configuration)
8. [Testing Your Deployment](#testing-your-deployment)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting, ensure you have:

- **Google Cloud Account** with Calendar API enabled
- **Railway Account** (free tier available)
- **OpenAI Platform Account** with Realtime API access
- **Git repository** with this calendar-mcp code

## Google Cloud Console Setup

### 1. Enable Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Navigate to **APIs & Services > Library**
4. Search for "Google Calendar API" and enable it

### 2. Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth 2.0 Client IDs**
3. Select **Web application** as application type
4. Configure redirect URIs:
   ```
   https://your-app-name.up.railway.app/oauth2callback
   http://localhost:8080/oauth2callback
   ```
5. Save your **Client ID** and **Client Secret**

### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Choose **External** user type
3. Fill in required fields:
   - App name: "Calendar Voice Agent"
   - User support email: your email
   - Authorized domains: `railway.app`
4. Add scopes: `https://www.googleapis.com/auth/calendar`
5. Add test users (initially) or publish the app

## Railway Deployment

### 1. Connect Repository to Railway

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Choose your calendar-mcp repository
5. Railway will auto-detect Python and deploy

### 2. Configure Environment Variables

In Railway dashboard, go to your project > **Variables** tab and add:

```env
# Required Google OAuth Credentials
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Calendar API Configuration
CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar
TOKEN_FILE_PATH=/app/tokens/saved-tokens.json

# Production Settings
NODE_ENV=production
OAUTH_CALLBACK_PORT=443

# Optional Webhook Security
WEBHOOK_SECRET_KEY=your_random_secret_key_here

# Optional OpenAI Integration
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Get Your Railway URL

After deployment, Railway provides a URL like:
```
https://your-app-name.up.railway.app
```

Update your Google OAuth credentials with this exact URL.

## Environment Configuration

### Railway-Specific Settings

The server automatically detects Railway environment and applies:

- **Host binding**: `0.0.0.0` (required by Railway)
- **Port**: Dynamic from Railway's `$PORT` environment variable
- **Token storage**: Persistent `/app/tokens` directory
- **Production optimizations**: Disabled reload, connection limits
- **Logging**: File-based logging for debugging

### Multi-User OAuth Support

The server supports multiple users with OAuth via the `X-User-ID` header:

```bash
# Each user gets their own token file
# User "alice" -> /app/tokens/saved-tokens-alice.json
# User "bob" -> /app/tokens/saved-tokens-bob.json
curl -H "X-User-ID: alice" https://your-app.railway.app/calendars
```

## OpenAI MCP (Model Context Protocol) Integration

### 1. MCP Server Connection

Your deployed Calendar MCP server is now compatible with OpenAI's Responses API via HTTP/SSE transport. Connect it using:

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5",
    tools=[
        {
            "type": "mcp",
            "server_label": "google_calendar",
            "server_description": "Google Calendar integration for appointment booking and management",
            "server_url": "https://your-app-name.up.railway.app/mcp",
            "authorization": "your_google_calendar_oauth_token_here",
            "require_approval": "never",  # or set approval requirements
            "allowed_tools": [  # Optional: filter specific tools
                "voice_book_appointment",
                "voice_check_availability",
                "voice_get_upcoming",
                "list_calendars",
                "find_events"
            ]
        }
    ],
    input="Schedule a meeting with John tomorrow at 2 PM"
)

print(response.output_text)
```

### 2. Available MCP Tools

Your MCP server exposes these tools for OpenAI integration:

#### Standard Calendar Tools
- `list_calendars` - List user's calendars
- `find_events` - Search for events
- `create_event` - Create detailed events
- `quick_add_event` - Natural language event creation
- `update_event` - Modify existing events
- `delete_event` - Remove events
- `check_free_busy` - Query availability

#### Voice-Optimized Tools (Recommended for Voice Agents)
- `voice_book_appointment` - Natural language booking with voice-friendly responses
- `voice_check_availability` - Conversational availability checking
- `voice_get_upcoming` - Voice-friendly upcoming events list

### 3. OAuth Token Setup for OpenAI

OpenAI passes Google Calendar OAuth tokens in the `authorization` field. To get these tokens:

#### Option 1: Google OAuth 2.0 Playground (Testing)
1. Go to [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
2. Select "Calendar API v3" scope: `https://www.googleapis.com/auth/calendar`
3. Authorize and get access token
4. Use this token in OpenAI MCP configuration

#### Option 2: Your Own OAuth Flow (Production)
```python
# Implement OAuth flow to get user's Google Calendar token
def get_user_calendar_token(user_id):
    # Your OAuth implementation
    # Return access_token for user's Google Calendar
    pass

# Use in OpenAI MCP call
user_token = get_user_calendar_token("user_123")

response = client.responses.create(
    model="gpt-5",
    tools=[{
        "type": "mcp",
        "server_label": "google_calendar",
        "server_url": "https://your-app.railway.app/mcp",
        "authorization": user_token,
        "require_approval": "never"
    }],
    input="What's on my calendar today?"
)
```

### 4. Example OpenAI Voice Agent Integration

```python
# Complete example for OpenAI Realtime voice agent
class CalendarVoiceAgent:
    def __init__(self, calendar_mcp_url, openai_api_key):
        self.mcp_url = calendar_mcp_url
        self.client = OpenAI(api_key=openai_api_key)

    async def handle_voice_request(self, user_input, user_calendar_token):
        """Process voice input and manage calendar via MCP."""

        response = self.client.responses.create(
            model="gpt-5",
            tools=[{
                "type": "mcp",
                "server_label": "calendar",
                "server_url": self.mcp_url,
                "authorization": user_calendar_token,
                "require_approval": "never",
                "allowed_tools": [
                    "voice_book_appointment",
                    "voice_check_availability",
                    "voice_get_upcoming"
                ]
            }],
            input=user_input
        )

        return response.output_text

# Usage
agent = CalendarVoiceAgent(
    calendar_mcp_url="https://your-app.railway.app/mcp",
    openai_api_key="your_openai_api_key"
)

# Voice agent processes: "Schedule a dentist appointment next Tuesday at 10 AM"
result = await agent.handle_voice_request(
    "Schedule a dentist appointment next Tuesday at 10 AM",
    user_calendar_token="user_oauth_token"
)

print(result)  # "Perfect! I've scheduled your dentist appointment for Tuesday, October 28 at 10:00 AM..."
```

### 5. Testing Your MCP Integration

Test your MCP server before connecting to OpenAI:

```bash
# Test MCP endpoint directly
curl -X POST https://your-app.railway.app/test/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "test_oauth_token": "your_test_google_oauth_token",
    "test_tool": "voice_book_appointment"
  }'
```

Expected response:
```json
{
  "status": "success",
  "message": "MCP implementation test completed",
  "openai_integration_ready": true,
  "results": [...]
}
```

### 6. Voice Agent Endpoints (Alternative to MCP)

If you prefer direct REST API integration instead of MCP, the server also provides specialized endpoints for voice agents:

#### Book Appointment
```http
POST /voice/appointment/book
Content-Type: application/json
X-User-ID: user_identifier

{
  "natural_language_request": "Schedule a meeting with John tomorrow at 2 PM for one hour",
  "user_timezone": "America/New_York",
  "calendar_id": "primary"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Perfect! I've scheduled your appointment for Tuesday, October 21 at 02:00 PM. The event 'Meeting with John' has been added to your calendar.",
  "event_id": "event_id_here",
  "event_link": "https://calendar.google.com/event?eid=...",
  "calendar_id": "primary"
}
```

#### Check Availability
```http
POST /voice/appointment/check
Content-Type: application/json
X-User-ID: user_identifier

{
  "time_request": "tomorrow afternoon",
  "duration_minutes": 60,
  "calendar_id": "primary"
}
```

**Response:**
```json
{
  "success": true,
  "message": "You have 2 appointments on Tuesday, October 21, but there's still good availability.",
  "availability": "partial",
  "busy_periods_count": 2
}
```

#### Get Upcoming Appointments
```http
GET /voice/appointment/upcoming?limit=5&calendar_id=primary
X-User-ID: user_identifier
```

**Response:**
```json
{
  "success": true,
  "message": "You have 3 appointments coming up. Your next one is Team Meeting on Tuesday, October 21 at 10:00 AM.",
  "events_count": 3,
  "events": [
    {
      "summary": "Team Meeting",
      "start_time": "Tuesday, October 21 at 10:00 AM",
      "location": "Conference Room A",
      "description": "Weekly team sync"
    }
  ]
}
```

#### Cancel Appointment
```http
POST /voice/appointment/cancel
Content-Type: application/json
X-User-ID: user_identifier

{
  "appointment_description": "meeting with John",
  "calendar_id": "primary"
}
```

### 2. Integration with OpenAI Realtime API

Configure your OpenAI voice agent to call these endpoints:

```javascript
// Example OpenAI function definition
const calendarFunctions = [
  {
    name: "book_appointment",
    description: "Book a calendar appointment using natural language",
    parameters: {
      type: "object",
      properties: {
        request: {
          type: "string",
          description: "Natural language appointment request"
        },
        user_id: {
          type: "string",
          description: "User identifier for multi-user support"
        }
      },
      required: ["request", "user_id"]
    }
  }
];

// Function implementation
async function bookAppointment(request, userId) {
  const response = await fetch('https://your-app.railway.app/voice/appointment/book', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': userId
    },
    body: JSON.stringify({
      natural_language_request: request,
      user_timezone: 'America/New_York',
      calendar_id: 'primary'
    })
  });

  const result = await response.json();
  return result.message; // Return voice-friendly message
}
```

## Webhook Configuration

### 1. Setup Real-time Notifications

Enable webhooks for real-time calendar updates:

```http
POST /webhooks/calendar/setup
Content-Type: application/json
X-User-ID: user_identifier

{
  "calendar_id": "primary",
  "webhook_url": "https://your-app.railway.app/webhooks/calendar/notifications",
  "channel_token": "optional_verification_token"
}
```

### 2. Forward Webhooks to OpenAI

Automatically forward calendar changes to your OpenAI platform:

```http
POST /webhooks/forward/openai
Content-Type: application/json

{
  "webhook_data": {
    "channel_id": "webhook_channel_id",
    "resource_state": "exists",
    "resource_uri": "https://www.googleapis.com/calendar/v3/calendars/primary/events"
  },
  "openai_endpoint": "https://your-openai-webhook-endpoint.com",
  "openai_api_key": "your_openai_api_key"
}
```

### 3. Webhook Security

Configure webhook validation in your environment:

```env
WEBHOOK_SECRET_KEY=your_random_secret_key_here
```

## Testing Your Deployment

### 1. Health Check

Verify your deployment is working:

```bash
curl https://your-app.railway.app/health
```

### 2. API Documentation

Access interactive API docs at:
```
https://your-app.railway.app/docs
```

### 3. Test Voice Endpoints

Test voice-optimized endpoints:

```bash
# Test booking
curl -X POST https://your-app.railway.app/voice/appointment/book \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test_user" \
  -d '{
    "natural_language_request": "Schedule a test meeting tomorrow at 3 PM",
    "calendar_id": "primary"
  }'
```

### 4. Test Authentication Flow

1. Visit: `https://your-app.railway.app/calendars`
2. You'll be redirected to Google OAuth
3. Complete authentication
4. API calls will now work with stored tokens

## OpenAI Platform Configuration

### 1. Add Calendar Server to OpenAI

In your OpenAI Platform dashboard:

1. Go to **API Settings**
2. Add external service:
   - **Name**: "Google Calendar"
   - **Base URL**: `https://your-app.railway.app`
   - **Authentication**: Custom headers (`X-User-ID`)

### 2. Voice Agent Instructions

Configure your OpenAI voice agent with these instructions:

```
You are a calendar assistant that can help users manage their Google Calendar appointments.

You have access to these calendar functions:
- book_appointment: Schedule new appointments using natural language
- check_availability: Check if the user is free at specific times
- get_upcoming: Get the user's upcoming appointments
- cancel_appointment: Cancel existing appointments

Always be conversational and helpful. When booking appointments, confirm the details back to the user in a natural way.

For multi-user scenarios, always include the user_id parameter to ensure each user accesses their own calendar.
```

### 3. Function Calling Setup

Configure function calling in your OpenAI assistant:

```json
{
  "functions": [
    {
      "name": "book_appointment",
      "description": "Book a calendar appointment",
      "parameters": {
        "type": "object",
        "properties": {
          "natural_language_request": {
            "type": "string",
            "description": "The user's appointment request in natural language"
          },
          "user_id": {
            "type": "string",
            "description": "Unique identifier for the user"
          }
        },
        "required": ["natural_language_request", "user_id"]
      }
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### 1. OAuth Redirect Error
**Problem**: "redirect_uri_mismatch" error
**Solution**: Ensure your Railway URL exactly matches the redirect URI in Google Cloud Console

#### 2. Token Storage Issues
**Problem**: Authentication fails after restart
**Solution**: Verify `/app/tokens` directory persists and `TOKEN_FILE_PATH` is correct

#### 3. Multi-User Authentication
**Problem**: Users see each other's calendars
**Solution**: Always include `X-User-ID` header in requests

#### 4. Webhook Failures
**Problem**: Webhooks not received
**Solution**: Check Railway logs, verify webhook URL is accessible, ensure HTTPS

### Logging and Debugging

#### View Railway Logs
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and view logs
railway login
railway logs
```

#### Debug Authentication
Check logs for OAuth flow issues:
```
2024-10-21 10:00:00 - src.auth - INFO - Loaded credentials from token file: /app/tokens/saved-tokens-user123.json
```

#### Monitor Webhook Activity
```
2024-10-21 10:00:00 - src.webhook_utils - INFO - Processing webhook: state=exists, channel=webhook_channel_123
```

### Performance Optimization

#### Railway Resource Limits
- **Memory**: 512MB - 1GB recommended
- **CPU**: Single core sufficient for most use cases
- **Concurrent Users**: ~50-100 with current configuration

#### Scaling Considerations
For high-traffic scenarios:
1. Enable Railway Pro plan for more resources
2. Consider Redis for token caching
3. Implement database for webhook subscriptions
4. Add load balancing for multiple instances

## Security Best Practices

1. **Environment Variables**: Never commit secrets to git
2. **OAuth Scopes**: Use minimal required scopes
3. **Webhook Validation**: Always validate webhook signatures
4. **HTTPS Only**: Ensure all communication uses HTTPS
5. **User Isolation**: Always use `X-User-ID` for multi-user deployments

## Support and Resources

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Google Calendar API**: [developers.google.com/calendar](https://developers.google.com/calendar)
- **OpenAI Platform**: [platform.openai.com](https://platform.openai.com)
- **Project Repository**: Your calendar-mcp GitHub repository

## Example Complete Integration

Here's a complete example of integrating with OpenAI's Realtime API:

```javascript
// OpenAI Realtime API integration example
const calendar = {
  baseUrl: 'https://your-app.railway.app',

  async bookAppointment(request, userId) {
    const response = await fetch(`${this.baseUrl}/voice/appointment/book`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId
      },
      body: JSON.stringify({
        natural_language_request: request,
        calendar_id: 'primary'
      })
    });
    return await response.json();
  },

  async checkAvailability(timeRequest, userId) {
    const response = await fetch(`${this.baseUrl}/voice/appointment/check`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId
      },
      body: JSON.stringify({
        time_request: timeRequest,
        calendar_id: 'primary'
      })
    });
    return await response.json();
  }
};

// Use in your OpenAI voice agent
const result = await calendar.bookAppointment(
  "Schedule a dentist appointment next Tuesday at 10 AM",
  "user_12345"
);

console.log(result.message); // Voice-friendly response
```

## 🎯 Quick Setup Summary for OpenAI Integration

Your calendar MCP server is now **fully compatible with OpenAI's MCP integration**:

### 1. Connection Details
- **MCP URL**: `https://your-app-name.up.railway.app/mcp`
- **Protocol**: HTTP/SSE transport (OpenAI compatible)
- **Authentication**: Google Calendar OAuth tokens

### 2. OpenAI Configuration
```python
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="gpt-5",
    tools=[{
        "type": "mcp",
        "server_label": "google_calendar",
        "server_url": "https://your-app-name.up.railway.app/mcp",
        "authorization": "user_google_calendar_oauth_token",
        "require_approval": "never"
    }],
    input="Schedule a meeting with Sarah tomorrow at 3 PM"
)
```

### 3. Key Features
- ✅ **HTTP/SSE MCP Transport** (OpenAI Responses API compatible)
- ✅ **OAuth Token Authentication** (Google Calendar access tokens)
- ✅ **Voice-Optimized Tools** (`voice_book_appointment`, `voice_check_availability`)
- ✅ **Multi-User Support** (isolated per OAuth token)
- ✅ **Railway Production Ready** (auto-scaling, HTTPS)

### 4. Integration Ready
Your MCP server can be connected directly to OpenAI Platform using the interface shown in your screenshot. Simply use:
- **URL**: `https://your-app-name.up.railway.app/mcp`
- **Authentication**: Your Google Calendar OAuth access token

This deployment guide provides everything needed to successfully deploy your Google Calendar MCP server to Railway and integrate it with OpenAI's Realtime voice agents for seamless appointment booking.