# Restaurant Agent Observability Setup

## Overview
This agent is instrumented with AWS Distro for OpenTelemetry (ADOT) to send observability data to CloudWatch.

## Prerequisites

1. **Enable CloudWatch Transaction Search** (one-time setup):
   ```bash
   # Add resource policy for X-Ray to write to CloudWatch Logs
   aws logs put-resource-policy \
     --policy-name AgentCoreTransactionSearch \
     --policy-document '{
       "Version": "2012-10-17",
       "Statement": [{
         "Sid": "TransactionSearchXRayAccess",
         "Effect": "Allow",
         "Principal": {"Service": "xray.amazonaws.com"},
         "Action": "logs:PutLogEvents",
         "Resource": [
           "arn:aws:logs:us-east-1:318766877259:log-group:aws/spans:*",
           "arn:aws:logs:us-east-1:318766877259:log-group:/aws/application-signals/data:*"
         ],
         "Condition": {
           "ArnLike": {"aws:SourceArn": "arn:aws:xray:us-east-1:318766877259:*"},
           "StringEquals": {"aws:SourceAccount": "318766877259"}
         }
       }]
     }'

   # Configure trace destination
   aws xray update-trace-segment-destination --destination CloudWatchLogs

   # (Optional) Set sampling percentage
   aws xray update-indexing-rule --name "Default" --rule '{"Probabilistic": {"DesiredSamplingPercentage": 100}}'
   ```

2. **Create CloudWatch Log Group**:
   ```bash
   aws logs create-log-group --log-group-name /aws/bedrock-agentcore/runtimes/restaurant-order-agent
   ```

## Environment Variables

The following OTEL environment variables are configured:

```bash
AGENT_OBSERVABILITY_ENABLED=true
OTEL_PYTHON_DISTRO=aws_distro
OTEL_PYTHON_CONFIGURATOR=aws_configurator
OTEL_RESOURCE_ATTRIBUTES=service.name=restaurant-order-agent,aws.log.group.names=/aws/bedrock-agentcore/runtimes/restaurant-order-agent
OTEL_EXPORTER_OTLP_LOGS_HEADERS=x-aws-log-group=/aws/bedrock-agentcore/runtimes/restaurant-order-agent,x-aws-log-stream=runtime-logs,x-aws-metric-namespace=bedrock-agentcore
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_EXPORTER=otlp
```

## Running with Observability

### Local Development
```bash
./run_with_observability.sh
```

### Docker
The Dockerfile is already configured with OTEL instrumentation:
```bash
docker build -t restaurant-agent .
docker run -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
  -e OTEL_RESOURCE_ATTRIBUTES="service.name=restaurant-order-agent,aws.log.group.names=/aws/bedrock-agentcore/runtimes/restaurant-order-agent" \
  -e OTEL_EXPORTER_OTLP_LOGS_HEADERS="x-aws-log-group=/aws/bedrock-agentcore/runtimes/restaurant-order-agent,x-aws-log-stream=runtime-logs,x-aws-metric-namespace=bedrock-agentcore" \
  restaurant-agent
```

## Viewing Observability Data

### CloudWatch GenAI Observability Dashboard
https://console.aws.amazon.com/cloudwatch/home#gen-ai-observability

### CloudWatch Logs
https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups/log-group/$252Faws$252Fbedrock-agentcore$252Fruntimes$252Frestaurant-order-agent

### CloudWatch Transaction Search
https://console.aws.amazon.com/cloudwatch/home#application-signals:transaction-search

## What Gets Tracked

1. **Service Metrics**:
   - Request count
   - Latency
   - Error rates

2. **Traces**:
   - Tool invocations
   - Nova Sonic model calls
   - WebSocket connections

3. **Spans**:
   - Individual tool executions
   - Order creation flow
   - Reservation flow

4. **Logs**:
   - Tool call parameters and results
   - Agent responses
   - Error messages

## Session ID Propagation

To track sessions across requests, set the session ID in OTEL baggage:

```python
from opentelemetry import baggage
from opentelemetry.context import attach

ctx = baggage.set_baggage("session.id", session_id)
attach(ctx)
```
