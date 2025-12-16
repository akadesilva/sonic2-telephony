import json
import os
import boto3
from urllib.parse import urlparse
from botocore.auth import SigV4QueryAuth
from botocore.awsrequest import AWSRequest
import jwt
from jwt.exceptions import InvalidTokenError

def verify_vonage_jwt(token, signature_secret):
    """Verify Vonage JWT signature"""
    try:
        decoded = jwt.decode(
            token,
            signature_secret,
            algorithms=['HS256']
        )
        return True, decoded
    except InvalidTokenError as e:
        return False, str(e)

def generate_presigned_url(runtime_arn, region, caller, expires=3600):
    """Generate presigned WebSocket URL for AgentCore"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Construct WebSocket URL with caller as query parameter
    ws_url = f"wss://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtime_arn}/ws?qualifier=DEFAULT&caller={caller}"
    https_url = ws_url.replace("wss://", "https://")
    
    parsed_url = urlparse(https_url)
    request = AWSRequest(
        method='GET',
        url=https_url,
        headers={'Host': parsed_url.netloc}
    )
    
    SigV4QueryAuth(credentials, 'bedrock-agentcore', region, expires=expires).add_auth(request)
    
    return request.url.replace("https://", "wss://")

def lambda_handler(event, context):
    """Handle Vonage answer webhook"""
    runtime_arn = os.environ['RUNTIME_ARN']
    region = os.environ.get('AWS_REGION', context.invoked_function_arn.split(':')[3])
    signature_secret = os.environ.get('VONAGE_SIGNATURE_SECRET')
    allowed_caller = os.environ.get('ALLOWED_CALLER_NUMBER')
    
    # Parse request body
    body = json.loads(event.get('body', '{}'))
    caller = body.get('from', '')
    
    # Check if caller is allowed (if ALLOWED_CALLER_NUMBER is set)
    if allowed_caller and caller != allowed_caller:
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'Caller not authorized'})
        }
    
    # Verify JWT if signature secret is configured
    if signature_secret:
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Missing or invalid Authorization header'})
            }
        
        token = auth_header.replace('Bearer ', '')
        valid, result = verify_vonage_jwt(token, signature_secret)
        
        if not valid:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': f'Invalid JWT: {result}'})
            }
    
    print(event)
    # Generate presigned WebSocket URL
    ws_url = generate_presigned_url(runtime_arn, region, caller)
    print(ws_url)
    # Return NCCO to connect call to WebSocket
    ncco = [
        {
            "action": "connect",
            "endpoint": [
                {
                    "type": "websocket",
                    "uri": ws_url,
                    "content-type": "audio/l16;rate=16000"
                }
            ]
        }
    ]
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(ncco)
    }
