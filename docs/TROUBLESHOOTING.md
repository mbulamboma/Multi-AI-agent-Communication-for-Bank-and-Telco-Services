# Troubleshooting Guide

## Common Issues and Solutions

### 1. CORS Errors

**Symptom:** Browser console shows "No 'Access-Control-Allow-Origin' header"

**Solution:**
1. Check API Gateway has OPTIONS method configured
2. Verify Lambda returns CORS headers in all responses:
```python
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
}
```
3. Redeploy API Gateway after changes

### 2. Agent Not Found Error

**Symptom:** 
```json
{
  "error": "Failed to retrieve resource because it doesn't exist"
}
```

**Solution:**
Get your correct Agent ID and Alias:
```bash
# List agents
aws bedrock-agent list-agents --region us-east-1

# List agent aliases
aws bedrock-agent list-agent-aliases --agent-id YOUR_AGENT_ID
```

Update Lambda environment variables:
```bash
aws lambda update-function-configuration \
  --function-name ask_agent_prompt \
  --environment Variables="{AGENT_ID=A4EY2J0JY4,AGENT_ALIAS=N3TXZ4PIC6}"
```

### 3. Empty Agent Response

**Symptom:** Lambda returns empty message or "No response from agent"

**Cause:** Bedrock Agent response parsing issue

**Solution:** The response is a streaming event. Use this code:
```python
agent_response = ""
if "completion" in response:
    for event in response["completion"]:
        if "chunk" in event:
            chunk = event["chunk"]
            if "bytes" in chunk:
                agent_response += chunk["bytes"].decode('utf-8')
```

### 4. IAM Permission Errors

**Lambda needs:**
- `bedrock-agent-runtime:InvokeAgent` for Bedrock
- `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, `dynamodb:Query` for DynamoDB
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` for CloudWatch

**Example policy:**
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
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/TelcoData",
        "arn:aws:dynamodb:us-east-1:*:table/Catalog"
      ]
    }
  ]
}
```

### 5. Frontend Not Loading Agent Response

**Check:**
1. Browser console for JavaScript errors
2. API endpoint in `script.js` is correct
3. Response format matches expected structure

**Debug in browser console:**
```javascript
fetch('https://your-api-endpoint.com/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        prompt: 'test',
        sessionId: 'test-123'
    })
})
.then(r => r.json())
.then(d => console.log(JSON.stringify(d, null, 2)))
```

### 6. DynamoDB Insufficient Balance Error

**Symptom:** "balance_credit >= 0" condition fails

**Cause:** User doesn't have enough credit

**Solution:** Add credit to test user:
```bash
aws dynamodb update-item \
  --table-name TelcoData \
  --key '{"PK":{"S":"USER#+243891234567"},"SK":{"S":"METADATA"}}' \
  --update-expression "SET balance_credit = :val" \
  --expression-attribute-values '{":val":{"N":"100"}}'
```

### 7. Action Group Not Working

**Check:**
1. API Gateway URL in action group is correct
2. Lambda has permission to be invoked by API Gateway
3. OpenAPI spec matches actual API structure

**Test action directly:**
```bash
curl -X POST https://your-business-api.com/checkBalance \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+243891234567"}'
```

## Debug Commands

```bash
# Watch Lambda logs live
aws logs tail /aws/lambda/ask_agent_prompt --follow

# Test Lambda directly
aws lambda invoke \
  --function-name ask_agent_prompt \
  --payload '{"body":"{\"prompt\":\"test\"}"}' \
  response.json && cat response.json

# Check DynamoDB table
aws dynamodb scan --table-name TelcoData --max-items 5

# Test API Gateway endpoint
curl -X POST https://your-api.com/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"hello","sessionId":"test"}'
```

## Still Stuck?

1. Check CloudWatch Logs for all Lambdas
2. Verify all environment variables are set
3. Ensure all services are in the same region
4. Try recreating the agent alias in Bedrock
5. Test each component independently (DynamoDB → Lambda → API → Agent)
