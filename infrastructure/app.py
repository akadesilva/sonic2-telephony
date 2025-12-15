#!/usr/bin/env python3
import aws_cdk as cdk
from vonage_api_stack import VonageApiStack

app = cdk.App()
VonageApiStack(app, "VonageApiStack")
app.synth()
