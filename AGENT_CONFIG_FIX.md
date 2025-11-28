# Fix Bedrock Agent Error

## Error Cause
```
Failed to retrieve resource because it doesn't exist
```
This means the `AGENT_ID` or `AGENT_ALIAS` in Lambda environment variables is wrong or not set.

---

## Step 1: Find Your Agent ID

### Option A: AWS Console (Easy)
1. Go to **AWS Console** → **Bedrock** → **Agents**
2. Click on your agent name
3. Copy the **Agent ID** (looks like: `XXXXXXXX` or alphanumeric string)
4. Copy the **Agent alias ID** (likely: `LFSSTBWIHS` or similar)

### Option B: AWS CLI
```powershell
# List all agents
aws bedrock-agent list-agents --region us-east-1

# Output will show:
# "agentId": "YOUR_AGENT_ID"
# "agentAliasId": "YOUR_ALIAS_ID"
```

---

## Step 2: Update Lambda Environment Variables

### Via AWS Console
1. Go to **Lambda** → **Functions** → `ask_agent_prompt`
2. Scroll down to **Environment variables**
3. Edit and set:
   - **AGENT_ID** = `<your-agent-id>`
   - **AGENT_ALIAS** = `LFSSTBWIHS` (or your alias)
4. **Save**

### Via AWS CLI
```powershell
aws lambda update-function-configuration `
  --function-name ask_agent_prompt `
  --environment Variables="{AGENT_ID=YOUR_AGENT_ID,AGENT_ALIAS=LFSSTBWIHS}" `
  --region us-east-1
```

---

## Step 3: Verify IAM Permissions

Your Lambda needs permission to invoke the Bedrock Agent. Ensure the Lambda execution role has this policy:

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

### Add via Console
1. Lambda → **Permissions** tab
2. Click the execution role
3. **Add inline policy**
4. Paste the policy above
5. **Save**

---

## Step 4: Test the Fix

### Using AWS CLI
```powershell
$payload = @{
    prompt = "Test message"
    sessionId = "test-123"
} | ConvertTo-Json

aws lambda invoke `
  --function-name ask_agent_prompt `
  --payload $payload `
  --region us-east-1 `
  response.json

Get-Content response.json
```

### Using Browser Console
```javascript
fetch('https://your-api-endpoint.com/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        prompt: 'Test message',
        sessionId: 'test-123'
    })
})
.then(r => r.json())
.then(d => console.log(JSON.stringify(d, null, 2)))
.catch(e => console.error(e));
```

---

## Expected Response (Success)
```json
{
    "status": "success",
    "message": "Agent's response here",
    "sessionId": "test-123",
    "timestamp": "2025-11-28T17:30:00"
}
```

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Still getting ResourceNotFoundException | AGENT_ID doesn't exist - verify in Bedrock console |
| "not authorized" error | Check IAM policy allows `bedrock-agent-runtime:InvokeAgent` |
| Empty environment variables | Lambda env vars not saved - check Lambda config page |
| Agent exists but still failing | Try using agent alias ID instead of just agent ID |

---

## Common Agent ID Formats

✅ Correct:
- `A4EY2J0JY4` (10 alphanumeric)
- `AGENT-ABC123` (with prefix)
- Agent alias: `LFSSTBWIHS`

❌ Wrong:
- Agent name (e.g., "MyAgent") 
- ARN (e.g., `arn:aws:bedrock:...`)
- Empty or `yourAgentId`

---

## Next Steps

1. Find your Bedrock Agent ID in AWS Console
2. Update Lambda environment variables with correct ID
3. Test using CLI or browser console
4. Frontend should now work!
