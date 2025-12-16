from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_iam as iam,
    CfnOutput,
    Duration,
    BundlingOptions
)
from constructs import Construct
import os

class VonageApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Get runtime ARN from environment or context
        runtime_arn = self.node.try_get_context("runtime_arn") or os.environ.get("RUNTIME_ARN")
        if not runtime_arn:
            raise ValueError("RUNTIME_ARN must be set via context or environment variable")
        
        # Get Vonage signature secret (optional)
        signature_secret = self.node.try_get_context("vonage_signature_secret") or os.environ.get("VONAGE_SIGNATURE_SECRET", "")
        
        # Get allowed caller number (optional)
        allowed_caller = self.node.try_get_context("allowed_caller_number") or os.environ.get("ALLOWED_CALLER_NUMBER", "")
        
        # Lambda execution role
        lambda_role = iam.Role(
            self, "VonageLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Grant Lambda permissions to access Bedrock AgentCore
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock-agentcore:*"],
                resources=["*"]
            )
        )
        
        # Answer webhook Lambda
        answer_lambda = lambda_.Function(
            self, "AnswerWebhook",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="answer_handler.lambda_handler",
            code=lambda_.Code.from_asset(
                "../lambda",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            role=lambda_role,
            timeout=Duration.seconds(30),
            environment={
                "RUNTIME_ARN": runtime_arn,
                "VONAGE_SIGNATURE_SECRET": signature_secret,
                "ALLOWED_CALLER_NUMBER": allowed_caller
            }
        )
        
        # Event webhook Lambda
        event_lambda = lambda_.Function(
            self, "EventWebhook",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="event_handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda"),
            role=lambda_role,
            timeout=Duration.seconds(30)
        )
        
        # API Gateway
        api = apigw.RestApi(
            self, "VonageWebhooksApi",
            rest_api_name="vonage-webhooks",
            description="Vonage webhook endpoints for Nova Sonic"
        )
        
        # /answer endpoint
        answer_resource = api.root.add_resource("answer")
        answer_resource.add_method(
            "POST",
            apigw.LambdaIntegration(answer_lambda)
        )
        
        # /event endpoint
        event_resource = api.root.add_resource("event")
        event_resource.add_method(
            "POST",
            apigw.LambdaIntegration(event_lambda)
        )
        
        # Outputs
        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "AnswerUrl", value=f"{api.url}answer")
        CfnOutput(self, "EventUrl", value=f"{api.url}event")
