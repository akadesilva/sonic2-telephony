import boto3
import json
import os

def get_secret(secret_name, region='us-east-1'):
    """Get secret from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        return None

def setup_credentials():
    """Setup credentials from AWS services"""
    # Get Perplexity API key
    perplexity_key = get_secret('sonic2-telephony/perplexity-api-key')
    if perplexity_key:
        os.environ['PERPLEXITY_API_KEY'] = perplexity_key
    
    # Get Google token.json
    google_token = get_secret('sonic2-telephony/google-token')
    if google_token:
        with open('/tmp/token.json', 'w') as f:
            f.write(google_token)
        os.environ['GOOGLE_TOKEN_PATH'] = '/tmp/token.json'
