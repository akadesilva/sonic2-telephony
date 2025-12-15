# Complete Deployment Guide

## Overview

This project deploys a complete Vonage telephony system using Amazon Nova Sonic on Bedrock AgentCore.

## Architecture

```
Vonage Call → API Gateway → Lambda → Presigned WebSocket URL
                                            ↓
                                    AgentCore Runtime
                                            ↓
                                    FastAPI WebSocket Server
                                            ↓
                                    Nova Sonic Bridge
                                            ↓
                                    Bedrock Nova Sonic
```

## Prerequisites

1. **AWS CLI** configured with credentials
2. **Docker** with buildx support
3. **Python 3.12+**
4. **Node.js** (for AWS CDK)
5. **jq** for JSON parsing
6. **AWS CDK CLI**: `npm install -g aws-cdk`

## Step-by-Step Deployment

### Step 1: Deploy AgentCore Runtime

```bash
cd /Users/akalanka/Documents/dev/agentcore/projects/sonic2-telephony

export ACCOUNT_ID=123456789012
./setup.sh
```

**What happens:**
- Builds ARM64 Docker image with FastAPI server
- Pushes to ECR
- Creates IAM role with Bedrock permissions
- Deploys to AgentCore
- Saves configuration to `setup_config.json`

**Output:**
```
Agent ARN: arn:aws:bedrock:us-east-1:123456789012:agent-runtime/vonage_sonic_agent_xxxx
```

### Step 2: Deploy API Gateway and Lambda

```bash
cd infrastructure
./deploy.sh
```

**What happens:**
- Reads Runtime ARN from `setup_config.json`
- Creates Lambda execution role
- Deploys two Lambda functions:
  - `AnswerWebhook` - Generates presigned WebSocket URLs
  - `EventWebhook` - Handles call events
- Creates API Gateway with `/answer` and `/event` endpoints
- Configures Lambda integrations

**Output:**
```
VonageApiStack.AnswerUrl = https://abc123.execute-api.us-east-1.amazonaws.com/prod/answer
VonageApiStack.EventUrl = https://abc123.execute-api.us-east-1.amazonaws.com/prod/event
```

### Step 3: Configure Vonage

1. Go to [Vonage Dashboard](https://dashboard.nexmo.com/)
2. Navigate to your application
3. Configure webhooks:
   - **Answer URL**: Use the `AnswerUrl` from CDK output
   - **Event URL**: Use the `EventUrl` from CDK output
   - **HTTP Method**: POST

### Step 4: Test

Call your Vonage number and have a conversation with Nova Sonic!

## Monitoring

### AgentCore Logs
```bash
aws logs tail /aws/bedrock/agentcore/vonage_sonic_agent --follow
```

### Lambda Logs
```bash
# Answer webhook
aws logs tail /aws/lambda/VonageApiStack-AnswerWebhook --follow

# Event webhook
aws logs tail /aws/lambda/VonageApiStack-EventWebhook --follow
```

### API Gateway Logs
Enable in API Gateway console for detailed request/response logging.

## Troubleshooting

### Issue: Lambda returns 500 error

**Check:**
- Lambda logs for errors
- RUNTIME_ARN environment variable is set correctly
- Lambda has permissions to call Bedrock

### Issue: WebSocket connection fails

**Check:**
- AgentCore runtime is in ACTIVE state
- Presigned URL is valid (not expired)
- Network connectivity from Vonage to AWS

### Issue: No audio response

**Check:**
- AgentCore logs for Nova Sonic errors
- Audio format is correct (16kHz PCM)
- Chunk scheduler is running

## Cleanup

```bash
# Delete API Gateway and Lambda
cd infrastructure
cdk destroy

# Delete AgentCore runtime
cd ..
./cleanup.sh
```

## Cost Estimation

**AgentCore Runtime:**
- Container running 24/7: ~$50-100/month (depending on instance size)

**Lambda:**
- Pay per invocation: ~$0.20 per 1M requests
- Minimal cost for typical call volumes

**API Gateway:**
- Pay per request: ~$3.50 per 1M requests

**Bedrock Nova Sonic:**
- Pay per audio duration: Check AWS Bedrock pricing

**Total:** Approximately $50-150/month for moderate usage (100-500 calls/day)

## Security Best Practices

1. **Presigned URLs**: Expire after 1 hour
2. **IAM Roles**: Least privilege access
3. **VPC**: Consider deploying AgentCore in VPC for production
4. **API Gateway**: Add API keys or OAuth for production
5. **Secrets**: Use AWS Secrets Manager for API keys

## Production Considerations

1. **High Availability**: Deploy AgentCore in multiple AZs
2. **Monitoring**: Set up CloudWatch alarms for errors
3. **Logging**: Enable detailed logging for debugging
4. **Rate Limiting**: Configure API Gateway throttling
5. **Error Handling**: Add retry logic in Lambda
6. **Testing**: Set up automated integration tests

## Support

For issues or questions:
- Check CloudWatch Logs
- Review ARCHITECTURE.md for detailed flow
- See QUICKSTART.md for simplified instructions
