# Railway Environment Variables Configuration

## 🚨 **URGENT: Fix Railway Deployment Failure**

Your Railway deployment is failing because it's missing required OAuth environment variables. Here's exactly what you need to configure:

## 📋 **Required Environment Variables for Railway**

Add these environment variables in your Railway project dashboard:

```bash
# Google OAuth 2.0 Client Credentials (CRITICAL)
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET_HERE

# Token storage configuration
TOKEN_FILE_PATH=/app/tokens/saved-tokens.json

# Google Calendar API Scopes
CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar

# OAuth callback configuration (Railway production)
OAUTH_CALLBACK_PORT=443

# Node environment (Railway production)
NODE_ENV=production

# Webhook configuration
WEBHOOK_SECRET_KEY=webhook_secret_key_12345_calendar_mcp_railway

# Railway will automatically set these:
# RAILWAY_ENVIRONMENT=production
# PORT=<dynamic>
```

## 🔧 **How to Configure Railway Environment Variables**

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Select your MCP Calendar project**
3. **Click on "Variables" tab**
4. **Add each environment variable** listed above
5. **Deploy the changes**

## ✅ **What This Will Fix**

- ✅ **Railway deployment will succeed** (no more healthcheck failures)
- ✅ **OAuth authentication will work** (no more credential errors)
- ✅ **MCP function name fix will be active** (already committed)
- ✅ **All calendar operations will work** without fallback

## 🧪 **Testing After Configuration**

Once you've added the environment variables to Railway:

1. **Redeploy** will happen automatically
2. **Check healthchecks** - should pass now
3. **Test the fix** with this command:

```bash
# Test the production server
GOOGLE_OAUTH_TOKEN="YOUR_OAUTH_TOKEN_HERE" python test_quick_add_event_fix.py
```

## 🎯 **Expected Results**

After configuration, you should see:
- ✅ Railway deployment succeeds
- ✅ Health endpoint returns 200 OK
- ✅ No more "Invalid MCP response format" errors
- ✅ All 4 calendar operations working (schedule, availability, list, reschedule)

## 🚨 **CRITICAL NEXT STEPS**

1. **Configure environment variables in Railway** (use the exact values above)
2. **Wait for automatic redeployment** (should take 2-3 minutes)
3. **Test the production endpoint** with the test script
4. **Verify Hebrew calendar agent works** without errors

The OAuth credentials are already working locally, so they'll work in Railway once configured properly.