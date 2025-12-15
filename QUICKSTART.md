# Quick Start Guide

## Step 1: Deploy to AgentCore

```bash
cd /Users/akalanka/Documents/dev/agentcore/projects/sonic2-telephony

# Set your AWS account ID
export ACCOUNT_ID=123456789012

# Optional: customize these
export AWS_REGION=us-east-1
export AGENT_NAME=vonage_sonic_agent

# Run setup
./setup.sh
```

**Output:** You'll get a Runtime ARN like:
```
arn:aws:bedrock:us-east-1:123456789012:agent-runtime/vonage_sonic_agent_a1b2
```

Save this ARN - you'll need it for Lambda configuration.

## Step 2: Deploy API Gateway and Lambda Functions

```bash
cd infrastructure
./deploy.sh
```

This will automatically:
- Read the Runtime ARN from `setup_config.json`
- Create Lambda functions with correct environment variables
- Deploy API Gateway with `/answer` and `/event` endpoints
- Output the webhook URLs

**Output:**
```
Outputs:
VonageApiStack.AnswerUrl = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/answer
VonageApiStack.EventUrl = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/event
```

## Step 3: Configure Vonage

1. Go to [Vonage Dashboard](https://dashboard.nexmo.com/)
2. Navigate to your application
3. Set webhooks:
   - **Answer URL**: `https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/answer`
   - **Event URL**: `https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/event`
   - **HTTP Method**: POST

## Step 4: Test

Call your Vonage number and have a conversation with Nova Sonic!

## Troubleshooting

### Check AgentCore Logs
```bash
aws logs tail /aws/bedrock/agentcore/vonage_sonic_agent --follow
```

### Check Lambda Logs
```bash
aws logs tail /aws/lambda/vonage-answer-webhook --follow
```

### Test Lambda Locally
```bash
python3 -c "
import answer_handler
import os
os.environ['RUNTIME_ARN'] = 'your-runtime-arn'
os.environ['AWS_REGION'] = 'us-east-1'
print(answer_handler.lambda_handler({}, {}))
"
```

## Cleanup

```bash
# Delete API Gateway and Lambda functions
cd infrastructure
cdk destroy

# Delete AgentCore resources
cd ..
./cleanup.sh
```
