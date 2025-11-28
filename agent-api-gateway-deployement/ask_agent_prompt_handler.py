import json
import boto3
import os
import uuid
from datetime import datetime

bedrock_client = boto3.client("bedrock-agent-runtime")


def lambda_handler(event, context):
    """
    Handles chatbot prompts from the frontend.
    Receives user input, invokes Bedrock Agent, and returns response.
    """
    
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
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Prompt is required'
                })
            }
    
    except Exception as e:
        print(f"Error parsing request: {e}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'error',
                'message': 'Invalid request format'
            })
        }

    # Invoke Bedrock Agent
    try:
        agent_id = os.environ.get('AGENT_ID', 'A4EY2J0JY4')
        agent_alias = os.environ.get('AGENT_ALIAS', 'v1')
        
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
        
        # Collect the response text
        agent_response = ""
        for event_item in response.get("completion", []):
            if event_item["type"] == "text":
                agent_response += event_item.get("text", "")
        
        if not agent_response:
            agent_response = str(response.get("completion", "No response from agent"))
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'success',
                'message': agent_response,
                'sessionId': session_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    except Exception as e:
        print(f"Error invoking agent: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'error',
                'message': 'Failed to process your request',
                'error': str(e)
            })
        }
