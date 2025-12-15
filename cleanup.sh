#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🧹 Cleaning up Vonage Nova Sonic AgentCore resources...${NC}"
echo ""

if [ ! -f "./setup_config.json" ]; then
    echo -e "${RED}❌ setup_config.json not found${NC}"
    exit 1
fi

AWS_REGION=$(jq -r '.aws_region' ./setup_config.json)
AGENT_RUNTIME_NAME=$(jq -r '.agent_runtime_name' ./setup_config.json)
IAM_ROLE_NAME=$(jq -r '.iam_role_name' ./setup_config.json)
ECR_REPO_NAME=$(jq -r '.ecr_repo_name' ./setup_config.json)

# Delete agent runtime
echo "🗑️  Deleting agent runtime: $AGENT_RUNTIME_NAME"
aws bedrock-agentcore-control delete-agent-runtime \
    --agent-runtime-name $AGENT_RUNTIME_NAME \
    --region $AWS_REGION 2>/dev/null || echo "   Agent runtime not found"

# Delete IAM role
echo "🗑️  Deleting IAM role: $IAM_ROLE_NAME"
aws iam delete-role-policy --role-name $IAM_ROLE_NAME --policy-name ${IAM_ROLE_NAME}Policy 2>/dev/null || true
aws iam delete-role --role-name $IAM_ROLE_NAME 2>/dev/null || echo "   IAM role not found"

# Delete ECR repository
echo "🗑️  Deleting ECR repository: $ECR_REPO_NAME"
aws ecr delete-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION --force 2>/dev/null || echo "   ECR repository not found"

# Remove config file
rm -f ./setup_config.json

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
