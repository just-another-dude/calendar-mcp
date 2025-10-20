# Railway Deployment Checklist

This checklist will guide you through deploying your Google Calendar MCP server to Railway and integrating it with OpenAI Platform.

## ✅ Phase 1: Railway Deployment (15-30 minutes)

### 1.1 Prerequisites
- [ ] Railway account created at [railway.app](https://railway.app)
- [ ] GitHub repository with calendar-mcp code
- [ ] Google Cloud Console project with Calendar API enabled
- [ ] Google OAuth credentials (Client ID & Client Secret)

### 1.2 Deploy to Railway

#### Step 1: Connect Repository
1. [ ] Go to [Railway Dashboard](https://railway.app/dashboard)
2. [ ] Click "New Project"
3. [ ] Select "Deploy from GitHub repo"
4. [ ] Choose your `calendar-mcp` repository
5. [ ] Railway will auto-detect Python and start building

#### Step 2: Configure Environment Variables
In Railway dashboard, go to your project > **Variables** tab and add:

```env
# Required - Google OAuth Credentials
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Required - Calendar API Configuration
CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar

# Production Settings (Railway will set these automatically)
NODE_ENV=production
# PORT and RAILWAY_ENVIRONMENT are set automatically by Railway

# Optional - Webhook Security
WEBHOOK_SECRET_KEY=your_random_secret_key_here
```

#### Step 3: Get Railway URL
- [ ] After deployment, note your Railway URL: `https://your-app-name.up.railway.app`
- [ ] Test basic connectivity: `curl https://your-app-name.up.railway.app/health`

Expected response:
```json
{
  "status": "healthy",
  "message": "Calendar MCP Server is running"
}
```

## ✅ Phase 2: Google Cloud Console Configuration (10-15 minutes)

### 2.1 Update OAuth Credentials for Production

1. [ ] Go to [Google Cloud Console](https://console.cloud.google.com)
2. [ ] Navigate to "APIs & Services" > "Credentials"
3. [ ] Click on your OAuth 2.0 Client ID
4. [ ] Under "Authorized JavaScript origins", add:
   ```
   https://your-app-name.up.railway.app
   ```
5. [ ] Under "Authorized redirect URIs", add:
   ```
   https://your-app-name.up.railway.app/oauth2callback
   ```
6. [ ] Save changes

### 2.2 Verify OAuth Configuration
- [ ] Test OAuth flow: Visit `https://your-app-name.up.railway.app/calendars`
- [ ] Should redirect to Google OAuth consent screen
- [ ] After authorization, should show calendar list

## ✅ Phase 3: Test MCP Implementation (15-20 minutes)

### 3.1 Get Test OAuth Token

#### Option A: Google OAuth 2.0 Playground (Recommended for testing)
1. [ ] Go to [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
2. [ ] Click gear icon, check "Use your own OAuth credentials"
3. [ ] Enter your Client ID and Client Secret
4. [ ] In Step 1, add scope: `https://www.googleapis.com/auth/calendar`
5. [ ] Click "Authorize APIs"
6. [ ] In Step 2, click "Exchange authorization code for tokens"
7. [ ] Copy the "Access token"

#### Option B: Use Your Production OAuth Flow
1. [ ] Visit `https://your-app-name.up.railway.app/calendars`
2. [ ] Complete OAuth authorization
3. [ ] Extract token from stored credentials (for testing only)

### 3.2 Test MCP Endpoints

Test MCP implementation:
```bash
curl -X POST https://your-app-name.up.railway.app/test/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "test_oauth_token": "your_test_oauth_token_here",
    "test_tool": "voice_book_appointment"
  }'
```

Expected response:
```json
{
  "status": "success",
  "message": "MCP implementation test completed",
  "openai_integration_ready": true
}
```

### 3.3 Test Individual Tools

Test voice booking:
```bash
curl -X POST https://your-app-name.up.railway.app/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_oauth_token" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": "test1",
    "params": {
      "name": "voice_book_appointment",
      "arguments": {
        "natural_language_request": "Schedule a test meeting tomorrow at 3 PM"
      }
    }
  }'
```

## ✅ Phase 4: OpenAI Platform Integration (20-30 minutes)

### 4.1 Configure OpenAI MCP Connection

1. [ ] Open OpenAI Platform dashboard
2. [ ] Navigate to MCP connections/integrations section
3. [ ] Add new MCP server with these details:
   - **URL**: `https://your-app-name.up.railway.app/mcp`
   - **Label**: `google_calendar`
   - **Description**: `Google Calendar integration for appointment booking`
   - **Authentication**: `Access token / API key`
   - **Access Token**: Your Google Calendar OAuth token

### 4.2 Test OpenAI Integration

Create a test script:
```python
from openai import OpenAI

client = OpenAI(api_key="your_openai_api_key")

response = client.responses.create(
    model="gpt-5",
    tools=[{
        "type": "mcp",
        "server_label": "google_calendar",
        "server_url": "https://your-app-name.up.railway.app/mcp",
        "authorization": "your_google_calendar_oauth_token",
        "require_approval": "never",
        "allowed_tools": [
            "voice_book_appointment",
            "voice_check_availability",
            "voice_get_upcoming"
        ]
    }],
    input="What's on my calendar today?"
)

print(response.output_text)
```

Expected: OpenAI should successfully connect and list your calendar events.

## ✅ Phase 5: End-to-End Testing (15-20 minutes)

### 5.1 Test Voice Agent Workflows

Test these scenarios with OpenAI:

1. [ ] **Check availability**: "Am I free tomorrow afternoon?"
2. [ ] **Book appointment**: "Schedule a meeting with John tomorrow at 2 PM"
3. [ ] **View upcoming**: "What meetings do I have this week?"
4. [ ] **Complex booking**: "Book a 1-hour doctor appointment next Monday morning"

### 5.2 Verify Calendar Integration

- [ ] Check that events appear in Google Calendar
- [ ] Verify event details are correct
- [ ] Test that voice responses are natural and helpful
- [ ] Confirm multi-user isolation (if testing multiple users)

## ✅ Phase 6: Production Setup (15-30 minutes)

### 6.1 Production OAuth Management

For production use with real users:

1. [ ] Implement proper user authentication in your application
2. [ ] Set up OAuth token refresh logic
3. [ ] Configure user-specific token storage
4. [ ] Add error handling for expired tokens

### 6.2 Monitoring and Security

- [ ] Set up Railway logging monitoring
- [ ] Configure error alerting
- [ ] Review security headers and CORS settings
- [ ] Test rate limiting and error handling

## 🎯 Success Criteria

Your deployment is successful when:

✅ **Railway Deployment**
- [ ] Server responds to health checks
- [ ] All environment variables configured
- [ ] OAuth flow works on production URL

✅ **MCP Integration**
- [ ] MCP test endpoint returns success
- [ ] All calendar tools work via MCP protocol
- [ ] Voice-optimized tools return friendly responses

✅ **OpenAI Integration**
- [ ] OpenAI can connect to MCP server
- [ ] Calendar tools are discovered and callable
- [ ] Voice agent can book appointments successfully

✅ **End-to-End Functionality**
- [ ] Voice input -> calendar booking -> Google Calendar
- [ ] Natural language responses for voice synthesis
- [ ] Error handling and edge cases work properly

## 🚨 Common Issues and Solutions

### Issue: OAuth Redirect Error
**Error**: `redirect_uri_mismatch`
**Solution**: Ensure Railway URL exactly matches redirect URI in Google Cloud Console

### Issue: MCP Connection Fails
**Error**: OpenAI can't connect to MCP server
**Solution**: Check Railway logs, verify `/mcp` endpoint accessibility, confirm HTTPS

### Issue: Token Authentication Fails
**Error**: `Authentication failed - invalid OAuth token`
**Solution**: Regenerate OAuth token, check token permissions and scopes

### Issue: Calendar Operations Fail
**Error**: Google Calendar API errors
**Solution**: Verify OAuth token has calendar permissions, check API quotas

## 📞 Support Resources

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Google Calendar API**: [developers.google.com/calendar](https://developers.google.com/calendar)
- **OpenAI Platform**: [platform.openai.com](https://platform.openai.com)
- **OAuth 2.0 Playground**: [developers.google.com/oauthplayground](https://developers.google.com/oauthplayground)

---

Once you complete this checklist, your Google Calendar MCP server will be fully deployed and integrated with OpenAI Platform for voice-based appointment booking! 🎉