# Frontend & Lambda Deployment Guide

## Overview
- **Frontend**: ChatGPT-like HTML/CSS/JS interface hosted on S3
- **Lambda Handler**: Updated to receive prompts from frontend and invoke Bedrock Agent
- **Architecture**: Frontend → API Gateway → Lambda → Bedrock Agent

---

## Frontend Files

### 1. `index.html`
ChatGPT-style interface with:
- Message display area
- User input field with send button
- Quick action buttons
- Phone number input (optional)
- Session tracking

### 2. `style.css`
Modern purple gradient UI with:
- Responsive design
- Smooth animations
- Custom scrollbars
- Mobile-friendly layout

### 3. `script.js`
JavaScript logic for:
- Sending messages to Lambda API
- Session management
- Loading indicators
- Error handling
- Auto-scroll to latest messages

---

## Lambda Handler: `ask_agent_prompt_handler.py`

### Features
✅ Receives JSON payload from frontend with:
- `prompt` or `message` - User input text
- `sessionId` - Chat session identifier
- `phoneNumber` (optional) - User's phone for context

✅ Invokes Bedrock Agent with:
- User's phone number in context (if provided)
- Persistent session ID for conversation continuity

✅ Returns properly formatted JSON response:
```json
{
  "status": "success",
  "message": "Agent response text",
  "sessionId": "session-abc123",
  "timestamp": "2025-11-28T17:30:00"
}
```

✅ Includes CORS headers for browser access

✅ Environment variables:
- `AGENT_ID` - Bedrock Agent ID
- `AGENT_ALIAS` - Agent alias (default: "v1")

---

## Deployment Steps

### Step 1: Deploy Frontend to S3

1. Create S3 bucket:
```bash
aws s3 mb s3://telco-agent-frontend
```

2. Upload files:
```bash
aws s3 cp index.html s3://telco-agent-frontend/
aws s3 cp style.css s3://telco-agent-frontend/
aws s3 cp script.js s3://telco-agent-frontend/
```

3. Enable static website hosting:
   - Go to S3 bucket → Properties → Static website hosting
   - Enable it
   - Index document: `index.html`
   - Copy the endpoint URL

4. Set bucket policy for public access:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::telco-agent-frontend/*"
    }
  ]
}
```

### Step 2: Deploy/Update Lambda

1. Update Lambda environment variables:
   - `AGENT_ID`: Your Bedrock Agent ID
   - `AGENT_ALIAS`: Your agent alias (e.g., "v1")

2. Deploy the handler:
```bash
cd agent-api-gateway-deployement/
zip function.zip ask_agent_prompt_handler.py
aws lambda update-function-code \
  --function-name ask_agent_prompt \
  --zip-file fileb://function.zip
```

3. Attach IAM policy for Bedrock agent invocation:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agent-runtime:InvokeAgent"
      ],
      "Resource": "arn:aws:bedrock:us-east-1:*:agent/*"
    }
  ]
}
```

### Step 3: Configure API Gateway

1. Update the API Gateway endpoint in `script.js`:
```javascript
const API_ENDPOINT = 'https://your-api-id.execute-api.us-east-1.amazonaws.com/';
```

2. Enable CORS on the POST endpoint:
   - Access-Control-Allow-Origin: * (or specific domain)
   - Access-Control-Allow-Headers: Content-Type
   - Access-Control-Allow-Methods: POST

### Step 4: Update Frontend

Update the S3 files with the correct API endpoint:
```bash
# Edit script.js with your API endpoint, then re-upload
aws s3 cp script.js s3://telco-agent-frontend/
```

---

## Testing

### Local Frontend Testing
1. Open `index.html` in browser (or serve locally with simple HTTP server)
2. Update `API_ENDPOINT` in `script.js` to your Lambda API endpoint
3. Test messages:
   - "Activate a 1GB plan for me"
   - "Check my balance"
   - "Transfer money to +243859876543"

### Test Payload
```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Activate a 1GB plan for me",
    "sessionId": "session-test-123",
    "phoneNumber": "+243891234567"
  }'
```

---

## Features

### Chat Features
- ✅ Real-time message streaming
- ✅ Session persistence (maintains conversation context)
- ✅ Quick action buttons for common queries
- ✅ Phone number context (optional)
- ✅ Loading indicators
- ✅ Error handling with user-friendly messages
- ✅ Mobile responsive design
- ✅ Auto-scroll to latest messages
- ✅ Clear chat history option

### Agent Context
- User's phone number included in agent prompt
- Session ID maintained for multi-turn conversations
- Timestamp tracking for all interactions

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS error in browser | Ensure API Gateway CORS headers are enabled |
| 401 Unauthorized | Check Lambda IAM permissions for Bedrock |
| Agent not responding | Verify `AGENT_ID` and `AGENT_ALIAS` environment variables |
| Blank messages | Check browser console for JavaScript errors |
| Slow responses | Check Lambda timeout (increase if needed) |

---

## Configuration

### API Endpoint
Update in `script.js`:
```javascript
const API_ENDPOINT = 'https://your-actual-endpoint.execute-api.us-east-1.amazonaws.com/';
```

### Lambda Timeout
Recommended: 60 seconds (Agent invocation can take time)

### S3 Static Hosting
Your frontend will be available at:
```
http://telco-agent-frontend.s3-website-us-east-1.amazonaws.com
```

---

## Next Steps

1. Deploy frontend to CloudFront for better performance
2. Add authentication (Cognito) for user sessions
3. Add typing indicators
4. Implement message persistence to DynamoDB
5. Add file upload capability for receipts, etc.
