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
        
        # For /getSubscriptionRecommendation: map customerId -> phone_number
        if api_path.rstrip('/').endswith('/getSubscriptionRecommendation') or api_path == '/getSubscriptionRecommendation':
            if 'customerId' in backend_params:
                backend_params['phone_number'] = backend_params.pop('customerId')
                logger.info('Mapped customerId to phone_number')
        
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
                # getSubscriptionRecommendation endpoint returns recommendation
                if api_path.rstrip('/').endswith('/getSubscriptionRecommendation') or api_path == '/getSubscriptionRecommendation':
                    if body.get('status') == 'success':
                        action_status = 'COMPLETED'
                        should_retry = False
                        # Extract recommendation details
                        if 'recommendation' in body:
                            rec = body['recommendation']
                            details['recommendation_id'] = rec.get('id')
                            details['recommendation_name'] = rec.get('name')
                            details['recommendation_price'] = rec.get('price')
                            details['recommendation_description'] = rec.get('description')
                            details['currency'] = 'FC'
                    elif body.get('status') == 'error':
                        action_status = 'FAILED'
                        should_retry = False
                    elif body.get('status') == 'info':
                        # No specific recommendation but not an error
                        action_status = 'COMPLETED'
                        should_retry = False
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
