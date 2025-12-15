# Lambda Functions for Vonage Webhooks

These Lambda functions handle Vonage webhook callbacks and generate presigned WebSocket URLs for AgentCore.

## Functions

### answer_handler.py
Handles incoming call webhook from Vonage. Returns NCCO with presigned WebSocket URL to connect the call to AgentCore.

### event_handler.py
Handles call event webhooks from Vonage (call status updates, etc.).

## Deployment

### 1. Create Lambda Functions

```bash
# Set your Runtime ARN from setup.sh output
export RUNTIME_ARN="arn:aws:bedrock:us-east-1:123456789012:agent-runtime/vonage_sonic_agent_xxxx"
export AWS_REGION="us-east-1"

# Create answer webhook Lambda
aws lambda create-function \
  --function-name vonage-answer-webhook \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler answer_handler.lambda_handler \
  --zip-file fileb://answer_handler.zip \
  --environment Variables="{RUNTIME_ARN=$RUNTIME_ARN,AWS_REGION=$AWS_REGION}" \
  --region $AWS_REGION

# Create event webhook Lambda
aws lambda create-function \
  --function-name vonage-event-webhook \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler event_handler.lambda_handler \
  --zip-file fileb://event_handler.zip \
  --region $AWS_REGION
```

### 2. Create API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name vonage-webhooks \
  --region $AWS_REGION

# Create resources and methods for /answer and /event
# Integrate with Lambda functions
# Deploy to stage
```

### 3. Configure Vonage Application

In your Vonage dashboard:
- Answer URL: `https://your-api-gateway-url/answer`
- Event URL: `https://your-api-gateway-url/event`

## IAM Permissions

The Lambda execution role needs:
- `bedrock:InvokeModel` for AgentCore
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` for CloudWatch

## Testing

```bash
# Test answer webhook locally
python3 -c "
import answer_handler
import os
os.environ['RUNTIME_ARN'] = 'your-runtime-arn'
os.environ['AWS_REGION'] = 'us-east-1'
result = answer_handler.lambda_handler({}, {})
print(result)
"
```
