# Infrastructure Deployment

CDK stack to deploy API Gateway and Lambda functions for Vonage webhooks.

## Prerequisites

- AWS CDK CLI installed: `npm install -g aws-cdk`
- Python 3.12+
- Runtime ARN from AgentCore deployment

## Quick Deploy

```bash

# Specify RUNTIME_ARN
export RUNTIME_ARN="arn:aws:bedrock:us-east-1:123456789012:agent-runtime/vonage_sonic_agent_xxxx"
./deploy.sh

# Optional: Specify RUNTIME_ARN with Vonage signature verification (recommended)
export RUNTIME_ARN="arn:aws:bedrock:us-east-1:123456789012:agent-runtime/vonage_sonic_agent_xxxx"
export VONAGE_SIGNATURE_SECRET="your_signature_secret_from_vonage_dashboard"
./deploy.sh
```

## What Gets Deployed

- **Lambda Functions**:
  - `AnswerWebhook` - Generates presigned WebSocket URLs
  - `EventWebhook` - Handles call status events
  
- **API Gateway**:
  - REST API with `/answer` and `/event` endpoints
  - Lambda integrations
  - Automatic deployment

- **IAM Role**:
  - Lambda execution role with CloudWatch Logs permissions and Agent Core invocation permission

## Outputs

After deployment, you'll see:
```
Outputs:
VonageApiStack.ApiUrl = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/
VonageApiStack.AnswerUrl = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/answer
VonageApiStack.EventUrl = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/event
```

## Configure Vonage

In your Vonage dashboard:
1. Navigate to your application
2. Set **Answer URL** to the `AnswerUrl` output
3. Set **Event URL** to the `EventUrl` output
4. Set HTTP method to **POST**


## Cleanup

```bash
cdk destroy
```

