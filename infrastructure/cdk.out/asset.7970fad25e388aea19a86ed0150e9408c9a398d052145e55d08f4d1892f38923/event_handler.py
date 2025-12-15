import json

def lambda_handler(event, context):
    """Handle Vonage event webhook"""
    body = json.loads(event.get('body', '{}'))
    print(f"Vonage event: {json.dumps(body)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'ok'})
    }
