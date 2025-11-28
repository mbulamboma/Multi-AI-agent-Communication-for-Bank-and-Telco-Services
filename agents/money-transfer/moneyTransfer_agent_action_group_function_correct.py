import os
import json
import logging
from typing import Any, Dict, Optional
from http import HTTPStatus
import urllib.request
import urllib.error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_BASE_URL_ENV = "API_BASE_URL"
API_KEY_ENV = "API_KEY"
DEFAULT_API_BASE_URL = "https://w39lzo6tk7.execute-api.us-east-1.amazonaws.com/prod"


def _build_url(path: str) -> str:
    base = os.getenv(API_BASE_URL_ENV, DEFAULT_API_BASE_URL).rstrip('/')
    if not os.getenv(API_BASE_URL_ENV):
        logger.warning("Environment variable %s not set — using default API base URL %s", API_BASE_URL_ENV, DEFAULT_API_BASE_URL)
    if not path.startswith('/'):
        path = '/' + path
    return base + path


def _make_api_call(path: str, method: str = 'POST', body: Optional[Dict[str, Any]] = None, timeout: int = 10) -> Dict[str, Any]:
    url = _build_url(path)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    api_key = os.getenv(API_KEY_ENV)
    if api_key:
        headers['x-api-key'] = api_key
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode('utf-8')
            try:
                parsed = json.loads(resp_body) if resp_body else None
            except Exception:
                parsed = resp_body
            return {
                'statusCode': resp.getcode(),
                'body': parsed
            }
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode('utf-8')
            parsed = json.loads(err_body) if err_body else None
        except Exception:
            parsed = err_body
        return {
            'statusCode': e.code,
            'body': parsed,
            'error': str(e)
        }
    except urllib.error.URLError as e:
        return {
            'statusCode': HTTPStatus.BAD_GATEWAY,
            'body': None,
            'error': str(e)
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        logger.info('Received event: %s', json.dumps(event, default=str))
        
        action_group = event['actionGroup']
        api_path = event['apiPath']
        http_method = event.get('httpMethod', 'POST').upper()
        message_version = event.get('messageVersion', 1)
        
        # Extract parameters from requestBody (Bedrock action group format)
        parameters = []
        if 'requestBody' in event:
            request_body = event['requestBody']
            if 'content' in request_body:
                content = request_body['content']
                if 'application/json' in content:
                    app_json = content['application/json']
                    # Bedrock sends {"properties": [...]} format
                    if isinstance(app_json, dict) and 'properties' in app_json:
                        parameters = app_json['properties']
                    else:
                        parameters = app_json
                    logger.info('Extracted parameters from requestBody: %s', json.dumps(parameters))
        
        # Fallback to top-level parameters if requestBody not present
        if not parameters:
            parameters = event.get('parameters', [])
            logger.info('Using top-level parameters: %s', json.dumps(parameters))

        # Parse parameters from Bedrock format (array of {name, type, value})
        if isinstance(parameters, list):
            params_dict = {}
            for param in parameters:
                if isinstance(param, dict) and 'name' in param and 'value' in param:
                    params_dict[param['name']] = param['value']
            parameters = params_dict
            logger.info('Parsed parameters to dict: %s', json.dumps(parameters))
        elif not isinstance(parameters, dict):
            parameters = {}

        # Map parameters to match backend Lambda expectations
        backend_params = parameters.copy()
        logger.info('Initial backend_params: %s', json.dumps(backend_params))
        
        # For /transferMoney: map sourcePhone -> source_phone, targetPhone -> target_phone
        if api_path.rstrip('/').endswith('/transferMoney') or api_path == '/transferMoney':
            # Map sourcePhone to source_phone
            if 'sourcePhone' in backend_params:
                backend_params['source_phone'] = backend_params.pop('sourcePhone')
                logger.info('Mapped sourcePhone to source_phone')
            
            # Map targetPhone to target_phone
            if 'targetPhone' in backend_params:
                backend_params['target_phone'] = backend_params.pop('targetPhone')
                logger.info('Mapped targetPhone to target_phone')
            
            # Amount stays as-is (both use 'amount')
            logger.info('Amount parameter kept as-is')
        
        logger.info('Final backend_params to send to API: %s', json.dumps(backend_params))
        api_result = _make_api_call(api_path, method=http_method, body=backend_params)

        # Normalize result
        status_code = api_result.get('statusCode', HTTPStatus.INTERNAL_SERVER_ERROR)
        body = api_result.get('body')
        error = api_result.get('error') if api_result.get('error') else None

        # Determine actionStatus and shouldRetry heuristics
        action_status = 'FAILED'
        should_retry = False
        details: Dict[str, Any] = {'rawBody': body}

        # If success HTTP code
        if 200 <= int(status_code) < 300:
            # Default to success when HTTP 2xx
            action_status = 'COMPLETED'
            should_retry = False
        elif 500 <= int(status_code) < 600:
            # Server error -> allow retry
            action_status = 'FAILED'
            should_retry = True
        else:
            # Client error or other -> don't retry by default
            action_status = 'FAILED'
            should_retry = False

        # Add semantic hints for known endpoints to help the agent
        try:
            if isinstance(body, dict):
                # transferMoney endpoint returns success/error status
                if api_path.rstrip('/').endswith('/transferMoney') or api_path == '/transferMoney':
                    if body.get('status') == 'success':
                        action_status = 'COMPLETED'
                        should_retry = False
                        # Extract transfer details from message if available
                        message = body.get('message', '')
                        details['transfer_message'] = message
                        details['transfer_status'] = 'success'
                        
                        # Try to extract amount and target from message
                        # Message format: "Transfert de {amount} vers {target_phone} effectué..."
                        try:
                            if 'Transfert de' in message:
                                parts = message.split()
                                if len(parts) > 2:
                                    details['amount_transferred'] = parts[2]
                                if 'vers' in message:
                                    target_idx = parts.index('vers') + 1
                                    if target_idx < len(parts):
                                        details['recipient'] = parts[target_idx]
                        except Exception:
                            pass
                            
                    elif body.get('status') == 'error':
                        action_status = 'FAILED'
                        error_msg = body.get('message', '')
                        details['error_message'] = error_msg
                        details['transfer_status'] = 'error'
                        
                        # Check for specific error types
                        if 'Solde insuffisant' in error_msg or 'insuffisant' in error_msg.lower():
                            should_retry = False  # Don't retry on insufficient balance
                            details['error_type'] = 'insufficient_balance'
                        elif 'compte destinataire invalide' in error_msg.lower() or 'invalide' in error_msg.lower():
                            should_retry = False  # Don't retry on invalid recipient
                            details['error_type'] = 'invalid_recipient'
                        elif 'Transfert invalide' in error_msg:
                            should_retry = False  # Don't retry on invalid transfer (same account, negative amount)
                            details['error_type'] = 'invalid_transfer'
                        else:
                            should_retry = True  # Retry on other errors (might be temporary)
                            details['error_type'] = 'unknown'
        except Exception:
            # keep defaults on any parsing error
            pass

        # Build tool text for agent visibility
        tool_text = json.dumps({
            'actionStatus': action_status,
            'shouldRetry': should_retry,
            'httpStatusCode': status_code,
            'details': details,
            'responseBody': body,
            'error': error
        }, default=str)

        action_response = {
            'actionGroup': action_group,
            'apiPath': api_path,
            'httpMethod': http_method,
            'httpStatusCode': status_code,
            'responseBody': {
                'TEXT': {
                    'body': tool_text
                }
            }
        }

        response = {
            'messageVersion': message_version,
            'response': action_response
        }

        logger.info('Lambda response: %s', json.dumps(response))
        return response

    except KeyError as e:
        logger.error('Missing required field: %s', str(e))
        return {
            'messageVersion': event.get('messageVersion', 1),
            'response': {
                'actionGroup': event.get('actionGroup'),
                'apiPath': event.get('apiPath'),
                'httpMethod': event.get('httpMethod'),
                'httpStatusCode': HTTPStatus.BAD_REQUEST,
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps({'error': f'Missing required field: {str(e)}'})
                    }
                }
            }
        }
    except RuntimeError as e:
        logger.error('Configuration error: %s', str(e))
        return {
            'messageVersion': event.get('messageVersion', 1),
            'response': {
                'actionGroup': event.get('actionGroup'),
                'apiPath': event.get('apiPath'),
                'httpMethod': event.get('httpMethod'),
                'httpStatusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps({'error': str(e)})
                    }
                }
            }
        }
    except Exception as e:
        logger.exception('Unexpected error')
        return {
            'messageVersion': event.get('messageVersion', 1),
            'response': {
                'actionGroup': event.get('actionGroup'),
                'apiPath': event.get('apiPath'),
                'httpMethod': event.get('httpMethod'),
                'httpStatusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps({'error': 'Internal server error'})
                    }
                }
            }
        }
