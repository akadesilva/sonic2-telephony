#!/bin/bash

# AWS Configuration
export AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-318766877259}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

# Agent Configuration
export AGENT_NAME="restaurant-order-agent"
export AGENT_ID="restaurant-order-agent"
export LOG_GROUP="/aws/bedrock-agentcore/runtimes/${AGENT_ID}"
export OTEL_LOG_GROUP="${LOG_GROUP}"  # Pass to server for log stream creation

# Create CloudWatch log group if it doesn't exist
echo "Checking CloudWatch log group: ${LOG_GROUP}"
if ! aws logs describe-log-groups --log-group-name-prefix "${LOG_GROUP}" --query "logGroups[?logGroupName=='${LOG_GROUP}']" --output text | grep -q "${LOG_GROUP}"; then
    echo "Creating log group: ${LOG_GROUP}"
    aws logs create-log-group --log-group-name "${LOG_GROUP}" || echo "Warning: Could not create log group (may already exist or insufficient permissions)"
else
    echo "Log group already exists: ${LOG_GROUP}"
fi

# Enable Observability
export AGENT_OBSERVABILITY_ENABLED=true

# OTEL Configuration for ADOT
export OTEL_PYTHON_DISTRO=aws_distro
export OTEL_PYTHON_CONFIGURATOR=aws_configurator
export OTEL_RESOURCE_ATTRIBUTES="service.name=${AGENT_NAME},aws.log.group.names=${LOG_GROUP},cloud.resource_id=${AGENT_ID}"
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="x-aws-log-group=${LOG_GROUP},x-aws-log-stream=runtime-logs,x-aws-metric-namespace=bedrock-agentcore"
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_TRACES_EXPORTER=otlp

echo "Starting agent with observability enabled..."
echo "Agent Name: ${AGENT_NAME}"
echo "Agent ID: ${AGENT_ID}"
echo "Log Group: ${LOG_GROUP}"

# Run the server with OpenTelemetry instrumentation
opentelemetry-instrument python server.py
