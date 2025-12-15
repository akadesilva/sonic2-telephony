#!/bin/bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Vonage Nova Sonic AgentCore Setup${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
for cmd in jq python3 docker aws; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ $cmd is not installed"
        exit 1
    fi
done
echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# Validate environment
if [ -z "$ACCOUNT_ID" ]; then
    echo "❌ ACCOUNT_ID environment variable is required"
    echo "Usage: export ACCOUNT_ID=<your-aws-account-id> && ./setup.sh"
    exit 1
fi

export AWS_REGION=${AWS_REGION:-us-east-1}
export AGENT_NAME=${AGENT_NAME:-vonage_sonic_agent}
export ECR_REPO_NAME=${ECR_REPO_NAME:-vonage_sonic_images}
export IAM_ROLE_NAME=${IAM_ROLE_NAME:-VonageSonicAgentRole}

echo -e "${YELLOW}🔧 Configuration:${NC}"
echo "   AWS_REGION: $AWS_REGION"
echo "   ACCOUNT_ID: $ACCOUNT_ID"
echo "   AGENT_NAME: $AGENT_NAME"
echo ""

# Build and push Docker image
echo -e "${YELLOW}🐳 Building and pushing Docker image...${NC}"
aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION} 2>/dev/null || true
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.${AWS_REGION}.amazonaws.com

cd ./agent
docker buildx build --platform linux/arm64 -t $ACCOUNT_ID.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${AGENT_NAME} --push .
cd ..
echo -e "${GREEN}✅ Docker image built and pushed${NC}"
echo ""

# Create IAM role
echo -e "${YELLOW}🔐 Creating IAM role...${NC}"
if aws iam get-role --role-name $IAM_ROLE_NAME >/dev/null 2>&1; then
    echo "   ℹ️  IAM role already exists"
    ROLE_ARN=$(aws iam get-role --role-name $IAM_ROLE_NAME --query 'Role.Arn' --output text)
else
    AGENT_ROLE_POLICY=$(cat ./agent_role.json | sed "s/\${ACCOUNT_ID}/$ACCOUNT_ID/g")
    aws iam create-role --role-name $IAM_ROLE_NAME --assume-role-policy-document file://trust_policy.json --output json > /dev/null
    aws iam put-role-policy --role-name $IAM_ROLE_NAME --policy-name ${IAM_ROLE_NAME}Policy --policy-document "$AGENT_ROLE_POLICY" --output json > /dev/null
    ROLE_ARN=$(aws iam get-role --role-name $IAM_ROLE_NAME --query 'Role.Arn' --output text)
    echo "   ⏳ Waiting for IAM propagation..."
    sleep 10
fi
echo -e "${GREEN}✅ IAM role ready: $ROLE_ARN${NC}"
echo ""

# Create agent
echo -e "${YELLOW}🤖 Creating Bedrock Agent...${NC}"
RANDOM_ID=$(openssl rand -hex 2)
AGENT_RUNTIME_NAME="${AGENT_NAME}_${RANDOM_ID}"

AGENT_RESPONSE=$(aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name $AGENT_RUNTIME_NAME \
  --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"$ACCOUNT_ID.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${AGENT_NAME}\"}}" \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --role-arn arn:aws:iam::$ACCOUNT_ID:role/$IAM_ROLE_NAME \
  --region ${AWS_REGION} \
  --output json)

AGENT_ARN=$(echo "$AGENT_RESPONSE" | jq -r '.agentRuntimeArn')
echo -e "${GREEN}✅ Agent created: $AGENT_ARN${NC}"
echo ""

# Save configuration
cat > "./setup_config.json" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "aws_region": "$AWS_REGION",
  "account_id": "$ACCOUNT_ID",
  "iam_role_name": "$IAM_ROLE_NAME",
  "ecr_repo_name": "$ECR_REPO_NAME",
  "agent_name": "$AGENT_NAME",
  "agent_runtime_name": "$AGENT_RUNTIME_NAME",
  "agent_arn": "$AGENT_ARN"
}
EOF

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Agent ARN:${NC} $AGENT_ARN"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Deploy Lambda + API Gateway for Vonage webhooks"
echo "2. Configure Vonage application with webhook URLs"
echo "3. Test with a phone call"
echo ""
echo -e "${YELLOW}Cleanup:${NC} ./cleanup.sh"
echo ""
