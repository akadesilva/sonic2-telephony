#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Deploying Vonage API Gateway and Lambdas${NC}"
echo ""

# Check if RUNTIME_ARN is set
if [ -z "$RUNTIME_ARN" ]; then
    # Try to read from setup_config.json
    if [ -f "../setup_config.json" ]; then
        RUNTIME_ARN=$(jq -r '.agent_arn' ../setup_config.json)
        echo -e "${GREEN}✅ Using RUNTIME_ARN from setup_config.json${NC}"
    else
        echo -e "${RED}❌ RUNTIME_ARN not set and setup_config.json not found${NC}"
        echo "Run: export RUNTIME_ARN=<your-runtime-arn>"
        exit 1
    fi
fi

echo "   RUNTIME_ARN: $RUNTIME_ARN"
echo ""

# Check for Vonage signature secret (optional)
if [ -n "$VONAGE_SIGNATURE_SECRET" ]; then
    echo -e "${GREEN}✅ Vonage signature verification enabled${NC}"
    CONTEXT_ARGS="--context runtime_arn=$RUNTIME_ARN --context vonage_signature_secret=$VONAGE_SIGNATURE_SECRET"
else
    echo -e "${YELLOW}⚠️  Vonage signature verification disabled (set VONAGE_SIGNATURE_SECRET to enable)${NC}"
    CONTEXT_ARGS="--context runtime_arn=$RUNTIME_ARN"
fi
echo ""

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install -q -r requirements.txt

# Bootstrap CDK if needed
echo -e "${YELLOW}🔧 Bootstrapping CDK (if needed)...${NC}"
cdk bootstrap 2>/dev/null || true

# Deploy stack
echo -e "${YELLOW}🚀 Deploying CDK stack...${NC}"
cdk deploy $CONTEXT_ARGS --require-approval never

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Copy the Answer URL and Event URL from the outputs above"
echo "2. Configure them in your Vonage application dashboard"
echo "3. Test with a phone call"
