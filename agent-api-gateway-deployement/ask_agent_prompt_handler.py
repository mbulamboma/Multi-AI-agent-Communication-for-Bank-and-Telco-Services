import json
import boto3
import os
import uuid
from datetime import datetime

bedrock_client = boto3.client("bedrock-agent-runtime")

# CORS headers
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
}


def lambda_handler(event, context):
    """
    Handles chatbot prompts from the frontend.
    Receives user input, invokes Bedrock Agent, and returns response.
    """
    
    # Handle preflight requests
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'OK'})
        }
    
    # Parse the incoming request
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        user_prompt = body.get('prompt') or body.get('message')
        session_id = body.get('sessionId') or str(uuid.uuid4())
        phone_number = body.get('phoneNumber') or body.get('phone')
        
        if not user_prompt:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Prompt is required'
                })
            }
    
    except Exception as e:
        print(f"Error parsing request: {e}")
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'status': 'error',
                'message': 'Invalid request format'
            })
        }

    # Invoke Bedrock Agent
    try:
        agent_id = 'A4EY2J0JY4'
        agent_alias =  'N3TXZ4PIC6'
        
        # Include phone number context in the prompt if provided
        if phone_number:
            context_prompt = f"User phone: {phone_number}\n\nUser request: {user_prompt}"
        else:
            context_prompt = user_prompt
        
        response = bedrock_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias,
            sessionId=session_id,
            inputText=context_prompt
        )
        
        # Parse the response - it's a streaming response
        agent_response = ""
        
        # The response is an event stream
        if "completion" in response:
            for event in response["completion"]:
                # Handle different event types
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        agent_response += chunk["bytes"].decode('utf-8')
                elif isinstance(event, dict) and "text" in event:
                    agent_response += event.get("text", "")
        
        # Fallback: try to get the response as a string
        if not agent_response:
            agent_response = str(response.get("completion", "No response from agent"))
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'status': 'success',
                'message': agent_response.strip(),
                'sessionId': session_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    except Exception as e:
        print(f"Error invoking agent: {e}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'status': 'error',
                'message': 'Failed to process your request',
                'error': str(e)
            })
        }
