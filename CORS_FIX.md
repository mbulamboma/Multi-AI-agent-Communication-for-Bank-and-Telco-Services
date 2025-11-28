# CORS Fix - Quick Setup Guide

## What was Fixed

### 1. ✅ API Gateway Configuration (`agent-api-gateway.json`)
- Added CORS response headers for POST method
- Added OPTIONS (preflight) handler with CORS configuration
- Enables proper CORS communication between frontend and backend

### 2. ✅ Lambda Handler (`ask_agent_prompt_handler.py`)
- Centralized CORS headers in `CORS_HEADERS` constant
- Handles OPTIONS preflight requests
- Returns CORS headers in all responses (success/error)
- Includes all necessary CORS header types

### 3. ✅ Frontend (`script.js`)
- Already configured to handle CORS responses correctly
- Sends proper Content-Type header

---

## How to Deploy the CORS Fix

### Step 1: Update API Gateway
```bash
# Deploy the updated OpenAPI spec
aws apigateway import-rest-api \
  --body fileb://agent-api-gateway.json \
  --parameters endpointConfigurationTypes=REGIONAL
```

Or use AWS Console:
1. Go to API Gateway → Your API
2. Actions → Import API
3. Upload the updated `agent-api-gateway.json`
4. Deploy to stage

### Step 2: Update Lambda
```bash
# Package and deploy the updated handler
cd agent-api-gateway-deployement/
zip function.zip ask_agent_prompt_handler.py
aws lambda update-function-code \
  --function-name ask_agent_prompt \
  --zip-file fileb://function.zip
```

### Step 3: Redeploy API
1. In AWS Console → API Gateway
2. Click "Deploy API"
3. Select stage (e.g., "prod" or "dev")
4. Deploy

---

## CORS Headers Explained

| Header | Purpose | Value |
|--------|---------|-------|
| `Access-Control-Allow-Origin` | Allows browser to accept response | `*` (all origins) |
| `Access-Control-Allow-Methods` | Specifies allowed HTTP methods | `GET, POST, PUT, DELETE, OPTIONS` |
| `Access-Control-Allow-Headers` | Specifies allowed request headers | `Content-Type, Authorization, etc.` |

---

## Testing CORS

### Test with curl
```bash
# Test preflight request
curl -X OPTIONS https://your-api-endpoint.com/ \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"

# Test POST request
curl -X POST https://your-api-endpoint.com/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "sessionId": "test-123"}'
```

### Test in Browser Console
```javascript
const API_ENDPOINT = 'https://your-api-endpoint.com/';

fetch(API_ENDPOINT, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        prompt: 'Test message',
        sessionId: 'session-123'
    })
})
.then(r => r.json())
.then(data => console.log('Success:', data))
.catch(err => console.error('Error:', err));
```

---

## Common CORS Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `No 'Access-Control-Allow-Origin' header` | Missing CORS headers from backend | ✅ Already fixed in Lambda |
| `Method not allowed in CORS policy` | OPTIONS not handled | ✅ Added OPTIONS handler |
| `Preflight request failed` | API Gateway not configured for CORS | ✅ Updated agent-api-gateway.json |
| `credentials mode is 'include'` | Frontend sending credentials | Remove credentials from fetch if not needed |

---

## Configuration Checklist

- [ ] Lambda has CORS_HEADERS constant
- [ ] Lambda handles OPTIONS requests
- [ ] Lambda returns CORS headers in all responses
- [ ] API Gateway has OPTIONS method defined
- [ ] API Gateway POST has CORS response headers
- [ ] API Gateway is deployed to stage
- [ ] Frontend has correct API_ENDPOINT URL
- [ ] Test request works in browser console

---

## Verify the Fix

1. **Check API Gateway**
   - Go to AWS Console → API Gateway
   - Select your API
   - Check that "/" path has both POST and OPTIONS methods

2. **Check Lambda Logs**
   - CloudWatch Logs for Lambda function
   - Look for successful invocations

3. **Test in Browser**
   - Open frontend in browser
   - Open Developer Tools (F12) → Network tab
   - Send a message
   - Check response headers for `Access-Control-Allow-Origin: *`

---

## If Issues Persist

### Option 1: Clear Browser Cache
```javascript
// In browser console
fetch('https://your-api-endpoint.com/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({prompt: 'test'})
})
```

### Option 2: Check Lambda Environment Variables
Ensure these are set:
- `AGENT_ID` - Your Bedrock Agent ID
- `AGENT_ALIAS` - Your agent alias

### Option 3: Enable API Gateway Logging
1. API Gateway → Settings
2. Enable CloudWatch Logs
3. Check logs for detailed error messages

### Option 4: Use CORS Proxy (Temporary)
For testing, you can use a CORS proxy:
```javascript
const API_ENDPOINT = 'https://cors-anywhere.herokuapp.com/https://your-api-endpoint.com/';
```
⚠️ Not recommended for production

---

## Next Steps

1. Deploy the fixed files
2. Test the connection using browser console
3. Verify the frontend can send/receive messages
4. Monitor CloudWatch logs for any errors

Your CORS issue should now be resolved!
