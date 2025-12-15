# Architecture Overview

## Component Flow

```
┌─────────────┐
│ Vonage Call │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  API Gateway    │
└──────┬──────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Lambda (answer_handler.py)          │
│ - Generates presigned WebSocket URL │
│ - Returns NCCO to Vonage            │
└──────┬──────────────────────────────┘
       │
       │ NCCO with wss:// URL
       ▼
┌─────────────────────────────────────┐
│ Vonage connects to WebSocket        │
│ - Sends binary audio (16kHz PCM)    │
│ - Receives binary audio back        │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ AgentCore Runtime (ARM64 Container) │
│ ┌─────────────────────────────────┐ │
│ │ FastAPI Server (server.py)      │ │
│ │ - /ws endpoint                  │ │
│ │ - Health checks                 │ │
│ │ - IMDS credential refresh       │ │
│ └──────┬──────────────────────────┘ │
│        │                             │
│        ▼                             │
│ ┌─────────────────────────────────┐ │
│ │ Nova Sonic Bridge               │ │
│ │ - Audio resampling (24→16kHz)   │ │
│ │ - Chunk scheduling (20ms)       │ │
│ │ - Interrupt handling            │ │
│ │ - Tool integration              │ │
│ └──────┬──────────────────────────┘ │
└────────┼──────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Bedrock Nova Sonic                  │
│ - Bidirectional streaming           │
│ - Speech-to-speech                  │
│ - Tool use (internet search)        │
└─────────────────────────────────────┘
```

## Key Differences from sonic-demo

### 1. WebSocket Handling
**sonic-demo:**
```python
async for message in websocket:
    if isinstance(message, bytes):
        await nova_bridge.send_audio_chunk(message)
```

**sonic2-telephony:**
```python
message = await websocket.receive()
if "bytes" in message:
    await nova_bridge.send_audio_chunk(message["bytes"])
```

### 2. Server Framework
- **sonic-demo**: Raw `websockets` library
- **sonic2-telephony**: FastAPI + uvicorn (for AgentCore compatibility)

### 3. Deployment
- **sonic-demo**: Standalone Python processes (Flask + WebSocket server)
- **sonic2-telephony**: ARM64 Docker container on AgentCore

### 4. Credential Management
- **sonic-demo**: Static AWS credentials
- **sonic2-telephony**: IMDS with automatic refresh

### 5. Entry Point
- **sonic-demo**: Direct WebSocket connection
- **sonic2-telephony**: Lambda generates presigned URL → Vonage connects

## Audio Flow

```
Vonage → 16kHz PCM → WebSocket → Nova Sonic Bridge → Base64 encode → Nova Sonic
                                                                          ↓
Vonage ← 16kHz PCM ← Chunk Scheduler ← Resample 24→16kHz ← Base64 decode ← Nova Sonic
```

## Deployment Steps

1. **Run setup.sh**
   - Builds Docker image
   - Pushes to ECR
   - Creates IAM role
   - Deploys to AgentCore
   - Returns Agent ARN

2. **Deploy Lambda + API Gateway**
   - Create Lambda functions
   - Configure API Gateway
   - Set AGENT_ARN environment variable

3. **Configure Vonage**
   - Set Answer URL to API Gateway endpoint
   - Set Event URL for call status updates

4. **Test**
   - Call Vonage number
   - Lambda generates presigned URL
   - Vonage connects to AgentCore WebSocket
   - Real-time conversation with Nova Sonic

## Security

- **SigV4 Authentication**: Presigned WebSocket URLs with 1-hour expiration
- **IAM Roles**: Least privilege access for AgentCore runtime
- **IMDS**: Automatic credential rotation every hour
- **Network**: AgentCore runtime in PUBLIC mode (can be changed to VPC)

## Monitoring

- **CloudWatch Logs**: `/aws/bedrock/agentcore/*`
- **Health Endpoints**: `/health`, `/` for container health checks
- **Lambda Logs**: CloudWatch Logs for webhook handlers
- **Vonage Events**: Call status updates via event webhook
