# Vonage Nova Sonic on AgentCore

Real-time voice AI for Vonage telephony using Amazon Nova Sonic on Bedrock AgentCore.

## Architecture

```
Vonage Call → API Gateway → Lambda (returns NCCO with presigned WebSocket URL)
                                ↓
                    AgentCore WebSocket (wss://...)
                                ↓
                    FastAPI Server (server.py)
                                ↓
                    Nova Sonic Bridge → Bedrock Nova Sonic
```

## Prerequisites

- AWS CLI configured
- Docker with buildx
- Python 3.12+
- jq
- AWS Account ID

## Setup

### 1. Deploy AgentCore Runtime

```bash
export ACCOUNT_ID=your_aws_account_id
./setup.sh
```

This will:
1. Build and push ARM64 Docker image to ECR
2. Create IAM role with Bedrock permissions
3. Deploy agent to AgentCore
4. Output the Runtime ARN

### 2. Deploy API Gateway and Lambdas

```bash
cd infrastructure
./deploy.sh
```

This will:
1. Create Lambda functions for Vonage webhooks
2. Deploy API Gateway with /answer and /event endpoints
3. Output webhook URLs for Vonage configuration

### 3. Configure Vonage

In your Vonage dashboard:
- Answer URL: `https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/answer`
- Event URL: `https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/event`

### 4. Test

Call your Vonage number and have a conversation with Nova Sonic!

## Features

- **Real-time audio streaming** - 16kHz PCM audio from Vonage
- **Audio resampling** - 24kHz Nova Sonic → 16kHz Vonage
- **Chunk scheduling** - Smooth audio playback with 20ms intervals
- **Interrupt handling** - Clears audio buffer on user interruption
- **Tool integration** - Internet search via Perplexity API
- **IMDS credential refresh** - Automatic credential rotation

## Cleanup

```bash
# Destroy API Gateway and Lambdas
cd infrastructure
cdk destroy

# Cleanup AgentCore resources
cd ..
./cleanup.sh
```

## File Structure

```
.
├── websocket/
│   ├── server.py              # FastAPI WebSocket server
│   ├── nova_sonic_bridge.py   # Nova Sonic bidirectional streaming
│   ├── Dockerfile             # ARM64 container for AgentCore
│   └── requirements.txt       # Python dependencies
├── lambda/
│   ├── answer_handler.py      # Vonage answer webhook handler
│   ├── event_handler.py       # Vonage event webhook handler
│   └── README.md              # Lambda documentation
├── infrastructure/
│   ├── app.py                 # CDK app entry point
│   ├── vonage_api_stack.py    # CDK stack definition
│   ├── deploy.sh              # Deployment script
│   └── requirements.txt       # CDK dependencies
├── setup.sh                   # AgentCore deployment script
├── cleanup.sh                 # Cleanup script
├── agent_role.json            # IAM role policy
└── trust_policy.json          # IAM trust policy
```

## Environment Variables

- `ACCOUNT_ID` - AWS Account ID (required)
- `AWS_REGION` - AWS Region (default: us-east-1)
- `AGENT_NAME` - Agent name (default: vonage_sonic_agent)
- `ECR_REPO_NAME` - ECR repository (default: vonage_sonic_images)
- `IAM_ROLE_NAME` - IAM role name (default: VonageSonicAgentRole)
- `PERPLEXITY_API_KEY` - Perplexity API key for internet search (optional)

## How It Works

1. **Vonage sends binary audio** (16-bit PCM, 16kHz) over WebSocket
2. **Server receives audio** via FastAPI WebSocket endpoint
3. **Nova Sonic processes** audio in real-time with bidirectional streaming
4. **Audio resampled** from 24kHz (Nova Sonic) to 16kHz (Vonage)
5. **Chunks scheduled** at 20ms intervals for smooth playback
6. **Audio sent back** to Vonage as binary frames

## Differences from sonic-demo

- Uses **FastAPI + uvicorn** instead of raw websockets
- Handles **binary audio frames** directly (no JSON wrapping)
- Deployed as **ARM64 container** to AgentCore
- **IMDS credential management** for automatic rotation
- **Health endpoints** for container monitoring
- Simplified for **telephony use case** (no web client)
# sonic2-telephony
